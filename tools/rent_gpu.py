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
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _secrets import _from_env_file, get_secret  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[1]
INSTANCE_FILE = REPO_ROOT / ".vast-instance"
SERVE_INSTANCE_FILE = REPO_ROOT / ".vast-serve-instance"
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


def _cli(*args: str, trailing: tuple = (), capture: bool = True) -> subprocess.CompletedProcess:
    """Run the CLI. Anything in `trailing` goes after the key, never before.

    `create instance --args train` hands every remaining argument to the
    container, so a `--api-key` written after it is swallowed as a container
    argument and never reaches vast.ai. The request then arrives unauthenticated
    and comes back "403: This action requires login" — which reads as the key
    being wrong, and cost an afternoon on that assumption. `--args` has to be
    last, so it travels separately from the arguments that belong to the CLI.
    """
    key = get_secret("VAST_API_KEY", hint=_KEY_HINT)
    command = [_executable(), *args, "--api-key", key, *trailing]
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


SERVE_MIN_CUDA = 13.0
"""What the pinned vLLM image needs of the host driver.

vLLM 0.29 is built against a CUDA the 12.6 drivers on cheaper hosts cannot run:
the rental succeeds, the model never loads, and the log says "unsupported
display driver / cuda driver combination" after the image has been pulled.
"""


def _cuda(offer: dict) -> float:
    try:
        return float(offer.get("cuda_max_good") or 0)
    except (TypeError, ValueError):
        return 0.0


def cmd_offers(args: argparse.Namespace) -> None:
    query = [
        f"gpu_name={args.gpu}",
        "num_gpus=1",
        f"disk_space>={DISK_GB}",
        # No CUDA filter. `cuda_vers>=12.1` and `cuda_max_good>=12.1` both
        # return nothing at all for RTX 5090 hosts, which report CUDA 13.0 —
        # the comparison fails somewhere above 12.x rather than excluding a
        # genuinely unsuitable machine. On every other card the filter changed
        # no result, so it was hiding a whole class of hardware and buying
        # nothing. What the image actually needs is checked in `train` instead.
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

    if args.min_cuda:
        # Filtered here rather than in the query, because the server-side CUDA
        # comparison returns nothing at all above 12.x. A host whose driver is
        # too old for the image accepts the rental and then fails at startup
        # with "unsupported display driver / cuda driver combination", which
        # costs a whole rental to discover.
        offers = [o for o in offers if _cuda(o) >= args.min_cuda]
        if not offers:
            raise SystemExit(
                f"No {args.gpu} offer has a driver supporting CUDA {args.min_cuda}."
            )

    print(
        f"{'offer':>10}  {'$/hr':>6}  {'GPU':<16}{'down':>8}  {'disk':>7}"
        f"  {'cuda':>5}  reliability"
    )
    for offer in offers[: args.limit]:
        print(
            f"{offer['id']:>10}  {offer['dph_total']:>6.3f}  {offer['gpu_name']:<16}"
            f"{offer.get('inet_down', 0):>6.0f}Mb  {offer['disk_space']:>5.0f}GB"
            f"  {_cuda(offer):>5.1f}  {offer['reliability2']:.3f}"
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

    # Remember every offer shown, not just the ones printed, so `train` can say
    # which card an id belongs to and refuse one the image cannot run.
    OFFER_CACHE.write_text(
        json.dumps({str(o["id"]): o["gpu_name"] for o in offers}, indent=1),
        encoding="utf-8",
    )


UNSUPPORTED_GPUS = ("5090", "5080", "RTX PRO 6000", "B200", "GB200")
"""Blackwell cards the training image cannot use.

The image is pinned to pytorch/pytorch:2.4.1-cuda12.1, whose kernels are built
for sm_90 and below. A Blackwell card is sm_120, so the run dies on the first
convolution with "no kernel image is available for execution on the device" —
after paying to download 2.4 GB of dataset onto a machine that was never going
to train. Using one means rebuilding the image on CUDA 12.8 with torch 2.7+,
which also resets the numerical baseline every previous run was compared on.
"""


OFFER_CACHE = REPO_ROOT / ".vast-offers.json"
"""What the last `offers` run listed, so `train` knows which card an id is.

There is no way to look one up: `search offers "id=..."` returns nothing for
every syntax tried, and an unfiltered search returns 64 rows out of thousands,
so the offer usually is not among them. Caching what was listed is the only
reading of the card that does not depend on guessing.
"""


def _cached_gpu(offer_id: int) -> Optional[str]:
    if not OFFER_CACHE.exists():
        return None
    try:
        return json.loads(OFFER_CACHE.read_text(encoding="utf-8")).get(str(offer_id))
    except (json.JSONDecodeError, OSError):
        return None


def _check_gpu_supported(offer_id: int, force: bool) -> None:
    """Refuse a card the image cannot run, before any money is spent.

    Unknown is not treated as unsupported: an id typed from the website is
    perfectly legitimate, and blocking it would make the tool unusable. It says
    what it could not check instead.
    """
    gpu = _cached_gpu(offer_id)
    if gpu is None:
        print(
            f"Offer {offer_id} was not in the last `offers` listing, so the card\n"
            "could not be checked. If it is a 5090 or another Blackwell card,\n"
            "stop: this image is CUDA 12.1 and the run will fail after paying to\n"
            "download the dataset."
        )
        return

    print(f"Offer {offer_id}: {gpu}")
    if any(bad in gpu for bad in UNSUPPORTED_GPUS) and not force:
        raise SystemExit(
            f"\nA {gpu} cannot run this image.\n\n"
            "The image is built on CUDA 12.1 and a Blackwell card needs 12.8, so\n"
            "the run would die on the first convolution, having already paid to\n"
            "pull 2.4 GB of dataset onto it.\n\n"
            "Rebuild docker/train/Dockerfile on a CUDA 12.8 base first, or pick\n"
            "an Ada or Ampere card: 4090, 3090, A5000, 3060.\n"
            "Pass --force-gpu only once the image has actually been rebuilt."
        )


def cmd_train(args: argparse.Namespace) -> None:
    _check_gpu_supported(args.offer, args.force_gpu)

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
        "--raw",
        trailing=("--args", "train"),
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


SERVE_IMAGE = "ghcr.io/fixhome-sep490/fixhome-serve:latest"
"""The whole service in one container: vLLM, the detector, retrieval and the API.

Renting a box for Qwen alone and leaving the API and the detector on a laptop
was a testing shortcut that quietly became the deployment. It costs the
detector ten times its latency, since it then runs on a CPU, and it means
Backend has to reach somebody's laptop.
"""

SERVE_PORT = 8000
"""The API port. vLLM stays on loopback inside the container.

Nothing outside has any business talking to the model directly, and a rented
box publishes its ports to the open internet.
"""


def _registry_login() -> Optional[str]:
    """Docker credentials for the rented box, or None if the image is public.

    The serving image lives on GHCR and this organisation does not allow public
    packages, so the rented machine has to log in before it can pull. vast.ai
    takes the credentials as literal `docker login` arguments and runs them on
    the box; they are passed straight through and never printed here.

    GHCR accepts any GitHub token with read:packages as the password, and the
    username is ignored for token auth. Prefer GHCR_TOKEN in .env; fall back to
    whatever `gh` is already authenticated with, so a developer who has signed
    in to the CLI needs no extra setup.
    """
    token = os.environ.get("GHCR_TOKEN", "").strip() or _from_env_file("GHCR_TOKEN")
    if not token and shutil.which("gh"):
        try:
            token = subprocess.run(
                ["gh", "auth", "token"], capture_output=True, text=True, timeout=20
            ).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            token = ""
    if not token:
        return None
    user = os.environ.get("GITHUB_ACTOR", "").strip() or "fixhome"
    return f"-u {user} -p {token} ghcr.io"


def cmd_serve(args: argparse.Namespace) -> None:
    """Rent a second machine and serve Qwen on it.

    Separate from the trainer on purpose: a training run owns the whole card,
    and serving is a different lifetime anyway — it outlives the run that
    produced the detector.
    """
    if SERVE_INSTANCE_FILE.exists():
        raise SystemExit(
            f"{SERVE_INSTANCE_FILE.name} already names instance "
            f"{SERVE_INSTANCE_FILE.read_text().strip()}.\n"
            "Destroy it first, or delete the file if it is stale."
        )

    env = " ".join(
        [
            # -p publishes the API port; without it the service answers only
            # inside the instance, which is no use to anything.
            f"-p {SERVE_PORT}:{SERVE_PORT}",
            f"-e HF_TOKEN={get_secret('HF_TOKEN')}",
            f"-e HF_WEIGHTS_REPO={get_secret('HF_WEIGHTS_REPO')}",
            f"-e WEIGHTS_RUN={args.weights_run}",
            f"-e GPU_FRACTION={args.gpu_fraction}",
            f"-e MAX_LEN={args.max_len}",
        ]
    )
    create = [
        "create",
        "instance",
        str(args.offer),
        "--image",
        SERVE_IMAGE,
        "--disk",
        "60",
        "--env",
        env,
    ]
    login = _registry_login()
    if login:
        create += ["--login", login]
    else:
        print("No GHCR credentials found; the pull will fail unless the image")
        print("has been made public. Set GHCR_TOKEN in .env, or run `gh auth login`.")
    result = _cli(*create, "--raw", trailing=("--args", "serve"))
    created = _reply(result, doing=f"renting offer {args.offer} to serve Qwen")
    instance_id = created.get("new_contract")
    if not instance_id:
        raise SystemExit(f"No instance id in the reply: {created}")

    SERVE_INSTANCE_FILE.write_text(str(instance_id), encoding="utf-8")
    print(f"Serving instance {instance_id}, id saved to {SERVE_INSTANCE_FILE.name}")
    print("First start pulls the image and the model, several minutes.")
    print("The API only opens once Qwen answers, so a 404 here means it is")
    print("still loading rather than broken.")
    print(f"\n    python tools/rent_gpu.py address --instance {instance_id}")
    print(f"    python tools/rent_gpu.py destroy --instance {instance_id}")


def cmd_address(args: argparse.Namespace) -> None:
    """Where the served API actually answers.

    A rented instance publishes each container port on some arbitrary host
    port, so the address cannot be guessed and changes with every rental.
    """
    instance = _instance_id_for(args.instance, SERVE_INSTANCE_FILE)
    detail = _reply(
        _cli("show", "instance", str(instance), "--raw"), doing="reading the instance"
    )
    host = detail.get("public_ipaddr")
    mapping = (detail.get("ports") or {}).get(f"{SERVE_PORT}/tcp") or []
    if not host or not mapping:
        print(f"status: {detail.get('actual_status')}")
        raise SystemExit(
            "No published address yet. The instance is probably still starting;\n"
            "try again in a minute."
        )
    port = mapping[0].get("HostPort")
    base = f"http://{str(host).strip()}:{port}"
    print(f"AI_SERVICE_URL={base}")
    print(f"  health   {base}/health")
    print(f"  diagnose {base}/api/v1/diagnosis/analyze-upload")


def _instance_id_for(explicit: Optional[int], path: Path) -> int:
    if explicit:
        return explicit
    if path.exists():
        return int(path.read_text().strip())
    raise SystemExit(
        f"No instance id given and no {path.name}.\n"
        "Run `status` to list what is actually rented."
    )


def _instance_id(explicit: Optional[int]) -> int:
    return _instance_id_for(explicit, INSTANCE_FILE)


def _instances() -> List[dict]:
    return _json_cli("show", "instances")


def cmd_status(args: argparse.Namespace) -> None:
    instances = _instances()
    if not instances:
        print("Nothing rented. No charges accruing.")
        # Both files, not just the trainer's. Clearing one and leaving the
        # other meant `serve` refused to start the next day, pointing at an
        # instance that had been destroyed and saying to destroy it first.
        for path in (INSTANCE_FILE, SERVE_INSTANCE_FILE):
            if path.exists():
                path.unlink()
                print(f"Removed the stale {path.name}.")
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
    # -y or it stops on a confirmation prompt with stdin closed, and reports
    # nothing destroyed while the machine keeps billing.
    result = _cli("destroy", "instance", str(instance), "-y")
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
    offers.add_argument(
        "--min-cuda",
        type=float,
        default=0.0,
        help=f"host driver must support this CUDA; use {SERVE_MIN_CUDA} for serving",
    )

    train = sub.add_parser("train", help="rent a machine and start training on it")
    train.add_argument("--offer", required=True, type=int)
    train.add_argument("--epochs", type=int, default=100)
    train.add_argument("--batch", type=int, default=16)
    train.add_argument("--run-name", default="detector-v1")
    train.add_argument(
        "--force-gpu",
        action="store_true",
        help="rent a card the image cannot use; only after rebuilding it",
    )

    logs = sub.add_parser("logs", help="what the training container has printed")
    logs.add_argument("--instance", type=int)
    logs.add_argument("--tail", type=int, default=60)

    sub.add_parser("status", help="what is rented and what it has cost")

    serve = sub.add_parser("serve", help="rent a second machine and serve Qwen")
    serve.add_argument("--offer", required=True, type=int)
    serve.add_argument(
        "--gpu-fraction",
        type=float,
        default=0.70,
        help="share of VRAM for Qwen; the rest is the detector's",
    )
    serve.add_argument("--weights-run", default="detector-v1")
    serve.add_argument("--max-len", type=int, default=8192)

    address = sub.add_parser("address", help="where the served API answers")
    address.add_argument("--instance", type=int)

    destroy = sub.add_parser("destroy", help="stop the billing")
    destroy.add_argument("--instance", type=int)

    args = parser.parse_args()
    {
        "offers": cmd_offers,
        "train": cmd_train,
        "logs": cmd_logs,
        "status": cmd_status,
        "destroy": cmd_destroy,
        "serve": cmd_serve,
        "address": cmd_address,
    }[args.command](args)


if __name__ == "__main__":
    main()
