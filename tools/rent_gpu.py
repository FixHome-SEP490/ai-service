"""Rent a GPU on vast.ai, run the training image on it, and destroy it after.

A rented machine bills by the second whether or not anything is running on it,
so the whole point of this file is that the machine is never left behind. Three
habits enforce that:

    - the instance id is written to .vast-instance the moment it exists, before
      anything else can fail, so a machine is always recoverable from disk
    - `destroy` re-reads the instance list afterwards and refuses to report
      success until the instance is gone from it
    - `status` tells you what is running and what it has cost so far

    python tools/rent_gpu.py offers --gpu RTX_3060
    python tools/rent_gpu.py train --offer <id> --epochs 2
    python tools/rent_gpu.py logs
    python tools/rent_gpu.py status
    python tools/rent_gpu.py destroy

If a session ends while a machine is up, `destroy` with no arguments reads the
id from .vast-instance. Failing that, the web console at
https://cloud.vast.ai/instances/ has a delete button, and that is the backstop
that does not depend on this script working.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _secrets import get_secret  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTANCE_FILE = REPO_ROOT / ".vast-instance"
IMAGE = "ghcr.io/fixhome-sep490/fixhome-trainer:latest"

DISK_GB = 60
"""Enough for the image, the 2.4 GB archive, what it unpacks to, and the run.

Disk is charged for the life of the rental and cannot be grown afterwards, so
running out means starting over on a new machine.
"""

_ESTIMATED_HOURS = {"RTX_3060": 7, "RTX_3090": 4, "RTX_4090": 3, "RTX_A5000": 5}
"""Rough wall-clock for 100 epochs of YOLOv8n on 22745 images at 640px.

Guesses, replaced by measurement as soon as the smoke test reports an epoch.
"""


_KEY_HINT = (
    "Create one at cloud.vast.ai under Account -> API keys, then put it in\n"
    ".env as VAST_API_KEY=... The key can spend money; treat it like a card."
)


def _executable() -> str:
    """Path to the vastai console script.

    `python -m vastai` does not work: the package has no __main__, and its
    entry point parses arguments in a way that only holds when it is invoked as
    the console script. Look for that script beside the running interpreter, so
    the tool uses the virtualenv it was started from rather than whatever
    happens to be on PATH.
    """
    scripts = Path(sys.executable).parent
    for name in ("vastai.exe", "vastai"):
        candidate = scripts / name
        if candidate.exists():
            return str(candidate)
    found = shutil.which("vastai")
    if found:
        return found
    raise SystemExit(
        "The vastai command is not installed in this environment.\n"
        "    .venv-tools/Scripts/pip install vastai"
    )


def _cli(*args: str, capture: bool = True) -> subprocess.CompletedProcess:
    key = get_secret("VAST_API_KEY", hint=_KEY_HINT)
    command = [_executable(), *args, "--api-key", key]
    return subprocess.run(
        command,
        capture_output=capture,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _reply(result: subprocess.CompletedProcess, doing: str):
    """Parse a --raw reply, treating anything unparseable as a failure.

    The CLI exits 0 after printing "Failed with error 403: This action requires
    login", so the exit code says nothing. The reply being JSON is the only
    evidence that the request was carried out, and the message can arrive on
    either stream, so both are shown when it is not.
    """
    output = (result.stdout or "").strip()
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        detail = "\n".join(
            part for part in (output, (result.stderr or "").strip()) if part
        )
        raise SystemExit(
            f"vast.ai did not carry out the request ({doing}).\n"
            f"{detail or 'It returned nothing at all.'}\n\n"
            + (
                "A 403 here means the API key may read but not spend. Create a\n"
                "key with full permissions at cloud.vast.ai under Account, and\n"
                "put that one in .env as VAST_API_KEY.\n\n"
                if "403" in detail
                else ""
            )
            + "Check https://cloud.vast.ai/instances/ before retrying, in case\n"
            "a machine was created anyway."
        )


def _json_cli(*args: str) -> list:
    return _reply(_cli(*args, "--raw"), doing=" ".join(args))


def cmd_offers(args: argparse.Namespace) -> None:
    query = [
        f"gpu_name={args.gpu}",
        "num_gpus=1",
        f"disk_space>={DISK_GB}",
        "cuda_vers>=12.1",
        f"dph<={args.max_price}",
        "reliability>0.98",
        f"inet_down>={args.min_download}",
        "rentable=true",
    ]
    offers = _json_cli("search", "offers", " ".join(query), "-o", "dph")
    if not offers:
        raise SystemExit(
            f"No {args.gpu} under ${args.max_price}/hr met the filters.\n"
            "Try a different card or raise --max-price."
        )

    print(f"{'offer':>10}  {'$/hr':>6}  {'GPU':<16}{'down':>8}  {'disk':>7}  reliability")
    for offer in offers[: args.limit]:
        print(
            f"{offer['id']:>10}  {offer['dph_total']:>6.3f}  {offer['gpu_name']:<16}"
            f"{offer.get('inet_down', 0):>6.0f}Mb  {offer['disk_space']:>5.0f}GB"
            f"  {offer['reliability2']:.3f}"
        )

    # Hours are a guess until the smoke test measures one epoch, and the guess
    # is per card. Quoting a 3060 figure beside 4090 offers, as this did, reads
    # as a prediction about the card listed rather than about a different one.
    hours = _ESTIMATED_HOURS.get(args.gpu, 7)
    cheapest = offers[0]
    print(
        f"\nA 100-epoch run is roughly {hours} hours on a {args.gpu.replace('_', ' ')},"
        f" so about ${cheapest['dph_total'] * hours:.2f} at the cheapest offer above."
        "\nThat is an estimate; the two-epoch smoke test gives the real number."
    )
    print("Download speed matters: the dataset is a 2.4 GB archive.")


def cmd_train(args: argparse.Namespace) -> None:
    if INSTANCE_FILE.exists():
        raise SystemExit(
            f"{INSTANCE_FILE.name} already names instance "
            f"{INSTANCE_FILE.read_text().strip()}.\n"
            "Destroy it first, or delete the file if it is stale."
        )

    env = [
        f"-e HF_TOKEN={get_secret('HF_TOKEN')}",
        f"-e HF_DATASET_REPO={get_secret('HF_DATASET_REPO')}",
        f"-e HF_WEIGHTS_REPO={get_secret('HF_WEIGHTS_REPO')}",
        f"-e EPOCHS={args.epochs}",
        f"-e BATCH={args.batch}",
        f"-e RUN_NAME={args.run_name}",
    ]

    print(f"Renting offer {args.offer} and starting {args.epochs} epochs")
    result = _cli(
        "create",
        "instance",
        str(args.offer),
        "--image",
        IMAGE,
        "--disk",
        str(DISK_GB),
        "--env",
        " ".join(env),
        "--args",
        "train",
        "--raw",
    )
    created = _reply(result, doing=f"renting offer {args.offer}")
    instance_id = created.get("new_contract")
    if not instance_id:
        raise SystemExit(f"No instance id in the reply: {created}")

    # Written before anything else can fail. A machine whose id exists only in
    # this process's memory is a machine that bills until someone notices.
    INSTANCE_FILE.write_text(str(instance_id), encoding="utf-8")
    print(f"Instance {instance_id}, id saved to {INSTANCE_FILE.name}")
    print("\nIf this session dies, stop the billing with either of:")
    print(f"    python tools/rent_gpu.py destroy --instance {instance_id}")
    print("    https://cloud.vast.ai/instances/  (delete button)")


def _instance_id(explicit: Optional[int]) -> int:
    if explicit:
        return explicit
    if INSTANCE_FILE.exists():
        return int(INSTANCE_FILE.read_text().strip())
    raise SystemExit(
        f"No instance id given and no {INSTANCE_FILE.name}.\n"
        "Run `status` to list what is actually rented."
    )


def _instances() -> List[dict]:
    return _json_cli("show", "instances")


def cmd_status(args: argparse.Namespace) -> None:
    instances = _instances()
    if not instances:
        print("Nothing rented. No charges accruing.")
        if INSTANCE_FILE.exists():
            INSTANCE_FILE.unlink()
            print(f"Removed the stale {INSTANCE_FILE.name}.")
        return

    for item in instances:
        hours = (item.get("duration") or 0) / 3600
        rate = item.get("dph_total", 0)
        print(
            f"instance {item['id']}  {item.get('actual_status', '?'):<10}"
            f"  {item.get('gpu_name', '?')}"
        )
        print(f"  running {hours:.1f}h at ${rate:.3f}/hr, about ${hours * rate:.2f} so far")
        print(f"  image {item.get('image_uuid', '?')}")


def cmd_logs(args: argparse.Namespace) -> None:
    instance = _instance_id(args.instance)
    result = _cli("logs", str(instance), "--tail", str(args.tail))
    print(result.stdout or result.stderr)


def cmd_destroy(args: argparse.Namespace) -> None:
    instance = _instance_id(args.instance)
    print(f"Destroying instance {instance}")
    result = _cli("destroy", "instance", str(instance))
    print(result.stdout.strip() or result.stderr.strip())

    # The reply is not the evidence. Ask what is rented and look for it.
    remaining = [i["id"] for i in _instances()]
    if instance in remaining:
        raise SystemExit(
            f"Instance {instance} is still listed as rented and is still being\n"
            "charged. Delete it at https://cloud.vast.ai/instances/ now."
        )

    if INSTANCE_FILE.exists():
        INSTANCE_FILE.unlink()
    print(f"Gone. {len(remaining)} instance(s) still rented.")
    if remaining:
        print(f"  {remaining} — destroy these too if they are not wanted.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    offers = sub.add_parser("offers", help="what is available and what it costs")
    offers.add_argument("--gpu", default="RTX_3060")
    offers.add_argument("--max-price", type=float, default=0.40)
    offers.add_argument("--min-download", type=int, default=200, help="Mbps")
    offers.add_argument("--limit", type=int, default=10)

    train = sub.add_parser("train", help="rent a machine and start training on it")
    train.add_argument("--offer", required=True, type=int)
    train.add_argument("--epochs", type=int, default=100)
    train.add_argument("--batch", type=int, default=16)
    train.add_argument("--run-name", default="detector-v1")

    logs = sub.add_parser("logs", help="what the training container has printed")
    logs.add_argument("--instance", type=int)
    logs.add_argument("--tail", type=int, default=60)

    sub.add_parser("status", help="what is rented and what it has cost")

    destroy = sub.add_parser("destroy", help="stop the billing")
    destroy.add_argument("--instance", type=int)

    args = parser.parse_args()
    {
        "offers": cmd_offers,
        "train": cmd_train,
        "logs": cmd_logs,
        "status": cmd_status,
        "destroy": cmd_destroy,
    }[args.command](args)


if __name__ == "__main__":
    main()
