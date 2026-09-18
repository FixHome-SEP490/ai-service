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
"""Rough wall-clock for a full run at 640px, batch 48.

Now anchored to a real one rather than to a guess: detector-v2 was yolo11s over
70 epochs on 23,678 images, and took 3 hours 20 minutes on a rented RTX 3090 for
72 US cents. The 3060 figure is about double that.
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
    # The CLI writes its own stdout, and on Windows that defaults to the ANSI
    # code page. Training logs are full of box-drawing characters from the
    # progress bar, so `logs` died inside vast.ai's own process with
    # "'charmap' codec can't encode characters" — and exited 0 while doing it.
    # Our own process then printed that sentence in place of the log, and
    # anything reading it for a word like "Done" saw a successful command that
    # simply never contained the word. A machine billing by the second, watched
    # by something that can no longer see it finish.
    environment = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    return subprocess.run(
        command,
        capture_output=capture,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=environment,
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


SERVE_KNOWN_GOOD_MACHINE = 27076
"""The host that has served this image end to end, measured not guessed.

RTX A4000, 16 GB, CUDA 13.0, 6.8 Gb/s down, reliability 0.999, around twelve
cents an hour, Delaware. It pulled the 8.74 GB image in about three minutes,
loaded Qwen, and answered on its published port.

Five hosts were tried before it and four failed, each differently, which is why
this is written down rather than rediscovered:

    545 Mbps, CUDA 12.2   pull retried for 33 minutes and never finished
    6.6 Gb/s, CUDA 12.6   pulled in under a minute, then CUDA error 803:
                          "unsupported display driver / cuda driver combination"
    1.4 Gb/s, CUDA 13.0   pull stalled at 19 minutes
    4.8 Gb/s, CUDA 13.2   container healthy, published port unreachable from
                          outside — reliability 0.981, host not verified

The two mechanical requirements are enforced by _check_serve_host. The third is
not mechanical: a host can pass both and still not route traffic to its own
published port, and the only defence is to prefer a host that has done the job.

    python tools/rent_gpu.py offers --machine 27076

If it is not rentable, sort candidates by reliability rather than by price. The
serving box costs cents an hour and a failed rental costs fifteen minutes.
"""

SERVE_MIN_DOWNLOAD_MBPS = 3000
"""What the serving image needs of the host's link, measured rather than guessed.

The image is 8.74 GB across forty-three layers and one of those layers is
5.12 GB, inherited from the vLLM base. A single blob that size does not resume:
a stalled transfer restarts, so a slow link does not pull the image slowly, it
fails to pull it at all. Three rentals demonstrated this in one afternoon. At
545 and 1,355 Mbps the pull retried for thirty-three and nineteen minutes
without finishing; at 6,662 Mbps it completed in under a minute, and at
6,902 Mbps in about three.

Deliberately far above the 200 Mbps default for `offers`, which sizes a 2.4 GB
dataset archive rather than this image.
"""


def _cuda(offer: dict) -> float:
    try:
        return float(offer.get("cuda_max_good") or 0)
    except (TypeError, ValueError):
        return 0.0


def cmd_offers(args: argparse.Namespace) -> None:
    query = [
        "num_gpus=1",
        f"disk_space>={DISK_GB}",
        # No CUDA filter. `cuda_vers>=12.1` and `cuda_max_good>=12.1` both
        # return nothing at all for RTX 5090 hosts, which report CUDA 13.0 —
        # the comparison fails somewhere above 12.x rather than excluding a
        # genuinely unsuitable machine. On every other card the filter changed
        # no result, so it was hiding a whole class of hardware and buying
        # nothing. What the image actually needs is checked in `train` instead.
        # VRAM, not just the model name. The plan is a 12GB card and the
        # entrypoint's memory split is written for one; an RTX 3060 also ships
        # as an 8GB board under the same name, and renting one would load Qwen,
        # leave the detector nothing, and run out of CUDA memory partway
        # through the first request with a photograph in it.
        #
        # In gigabytes. The search API takes GB here while the offer it returns
        # reports gpu_ram in megabytes, so the obvious 12*1024 matches nothing
        # at all and reads like there are no 3060s left.
        f"gpu_ram>={args.min_vram}",
        f"dph<={args.max_price}",
        "reliability>0.98",
        f"inet_down>={args.min_download}",
        "rentable=true",
    ]
    # One host, by id, for the machine already known to serve this image. The
    # card name is dropped in that case: the point is the host, and it does not
    # have a 3060 in it.
    if args.machine:
        query.append(f"machine_id={args.machine}")
    else:
        query.append(f"gpu_name={args.gpu}")
    offers = _json_cli("search", "offers", " ".join(query), "-o", "dph")
    if not offers:
        if args.machine:
            raise SystemExit(
                "\n".join(
                    [
                        f"Host {args.machine} has nothing rentable under "
                        f"${args.max_price}/hr right now.",
                        "It is frequently rented by us — run `status` before",
                        "concluding it is gone. A fully rented host returns no",
                        "offers at all rather than an unavailable one.",
                        "Otherwise drop --machine and sort candidates by",
                        "reliability rather than by price.",
                    ]
                )
            )
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
        f"{'offer':>10}  {'$/hr':>6}  {'GPU':<16}{'vram':>6}{'down':>8}  {'disk':>7}"
        f"  {'cuda':>5}  reliability"
    )
    for offer in offers[: args.limit]:
        print(
            f"{offer['id']:>10}  {offer['dph_total']:>6.3f}  {offer['gpu_name']:<16}"
            f"{offer.get('gpu_ram', 0) / 1024:>4.0f}GB"
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
    # The card's name, and the two facts that decide whether the serving image
    # can run at all. Storing only the name meant `serve` had nothing to check
    # against and accepted a host whose driver was too old for the image.
    OFFER_CACHE.write_text(
        json.dumps(
            {
                str(o["id"]): {
                    "gpu_name": o["gpu_name"],
                    "cuda": _cuda(o),
                    "inet_down": o.get("inet_down") or 0,
                }
                for o in offers
            },
            indent=1,
        ),
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


def _cached_offer(offer_id: int) -> Optional[dict]:
    """What the last `offers` run recorded about this id, or None.

    Tolerates a cache written before the entry became a dictionary, so an
    upgrade does not make every stored id look unknown.
    """
    if not OFFER_CACHE.exists():
        return None
    try:
        entry = json.loads(OFFER_CACHE.read_text(encoding="utf-8")).get(str(offer_id))
    except (json.JSONDecodeError, OSError):
        return None
    if entry is None:
        return None
    if isinstance(entry, str):
        return {"gpu_name": entry, "cuda": 0.0, "inet_down": 0}
    return entry


def _cached_gpu(offer_id: int) -> Optional[str]:
    entry = _cached_offer(offer_id)
    return entry.get("gpu_name") if entry else None


def _check_serve_host(offer_id: int, force: bool) -> None:
    """Refuse a host the serving image cannot run on, before renting it.

    Two unsuitabilities, both visible in the offer listing and both discovered
    the expensive way instead. A driver below CUDA 13.0 accepts the rental,
    pulls nine gigabytes and then fails at engine initialisation with
    "unsupported display driver / cuda driver combination". A link below a few
    gigabits per second never finishes pulling the image's 5 GB layer.

    Unknown is not treated as unsuitable: an id typed off the website is
    legitimate. It says what it could not check instead.
    """
    entry = _cached_offer(offer_id)
    if entry is None:
        print(
            f"Offer {offer_id} was not in the last `offers` listing, so its driver\n"
            f"and link speed could not be checked. The image needs CUDA "
            f"{SERVE_MIN_CUDA} or\nnewer and at least "
            f"{SERVE_MIN_DOWNLOAD_MBPS} Mbps; below either, the rental is wasted."
        )
        return

    cuda = float(entry.get("cuda") or 0)
    down = float(entry.get("inet_down") or 0)
    print(
        f"Offer {offer_id}: {entry.get('gpu_name', '?')}, "
        f"CUDA {cuda or 'unknown'}, {down:.0f} Mbps"
    )

    problems = []
    if cuda and cuda < SERVE_MIN_CUDA:
        problems.append(
            f"CUDA {cuda} is below the {SERVE_MIN_CUDA} this image needs. vLLM "
            "would fail at engine initialisation after the image had been pulled."
        )
    if down and down < SERVE_MIN_DOWNLOAD_MBPS:
        problems.append(
            f"{down:.0f} Mbps is below {SERVE_MIN_DOWNLOAD_MBPS}. The image's "
            "5 GB layer does not resume, so a slow link fails rather than waits."
        )
    if problems and not force:
        raise SystemExit(
            "\n".join(
                ["", "This host cannot serve the image:"]
                + [f"  - {line}" for line in problems]
                + [
                    "",
                    "Find a suitable one with:",
                    f"    python tools/rent_gpu.py offers --min-cuda {SERVE_MIN_CUDA}"
                    f" --min-download {SERVE_MIN_DOWNLOAD_MBPS}",
                    "",
                    "Or pass --force-host to rent it anyway.",
                ]
            )
        )


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


def resume_conflict(run_name: str, resume_from: str) -> str:
    """Why this pair of names would destroy the weights it starts from.

    publish_weights uploads a finished run into a folder named after the
    run, so continuing detector-v2 under the name detector-v2 replaces the
    very weights --resume-from read, and there is then no way back to the
    seventy epochs already paid for. The machine that made them is gone.

    Returns the complaint, or an empty string when the pair is safe.
    """
    if not resume_from:
        return ""
    first = resume_from.strip("/").split("/")[0]
    if first != run_name:
        return ""
    return "\n".join(
        [
            f"--run-name {run_name} is the run --resume-from reads from.",
            "publish_weights uploads a finished run under its run name, so"
            " this would overwrite the weights it started from and leave no"
            " way back to them.",
            f"Give the continued run its own name, e.g. {run_name}-more.",
        ]
    )

def cmd_train(args: argparse.Namespace) -> None:
    # First, before a secret is read or a machine is rented: this one is
    # free to detect and expensive to discover afterwards.
    conflict = resume_conflict(args.run_name, args.resume_from)
    if conflict:
        raise SystemExit(conflict)

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
        f"-e MODEL={args.model}",
        f"-e RUN_NAME={args.run_name}",
    ]
    # Only sent when asked for. The entrypoint treats an empty LR0 as "use the
    # default", but an unset one reads better in the container's own log of
    # what it was given.
    if args.resume_from:
        env.append(f"-e RESUME_FROM={args.resume_from}")
    if args.lr0:
        env.append(f"-e LR0={args.lr0}")
    if args.warmup:
        env.append(f"-e WARMUP={args.warmup}")


    if args.resume_from:
        print(f"Continuing from {args.resume_from} for {args.epochs} more epochs")
    print(f"Renting offer {args.offer} and starting {args.epochs} epochs")
    create = [
        "create",
        "instance",
        str(args.offer),
        "--image",
        IMAGE,
        "--disk",
        str(DISK_GB),
        "--env",
        " ".join(env),
    ]
    # The trainer image is on GHCR and this organisation forbids public
    # packages, so the rented box has to log in before it can pull. Without
    # this the pull fails with no message anybody sees: the instance sits at
    # "loading" indefinitely, billing by the second, and looks exactly like a
    # slow download. Twenty-seven minutes of one went by before anyone asked
    # why the serve path had a --login and this one did not.
    login = _registry_login()
    if login:
        create += ["--login", login]
    else:
        print("No GHCR credentials found; the pull will fail unless the image")
        print("has been made public. Set GHCR_TOKEN in .env, or run `gh auth login`.")
    result = _cli(*create, "--raw", trailing=("--args", "train"))
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

    _check_serve_host(args.offer, args.force_host)

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

    # Ask the box whether it is actually answering before handing the address to
    # anybody. A published port is not a working service: the container can be
    # up while the model is still loading, and one host published the port and
    # never routed to it at all. Pasting a dead address into Backend's .env and
    # then debugging Backend is the expensive version of this mistake.
    state = _serve_health(base)
    print(f"AI_SERVICE_URL={base}")
    print(f"  {state}")
    print()
    print("Paste into the consumer that needs it:")
    print()
    print(f"  Backend  .env          AI_SERVICE_URL={base}")
    print(f"  Mobile   .env          EXPO_PUBLIC_AI_SERVICE_URL={base}")
    print(f"  Eval     shell         AI_SERVICE_URL={base}")
    print()
    print(f"  chat     {base}/chat")
    print(f"  health   {base}/health")
    print(f"  diagnose {base}/api/v1/diagnosis/analyze-upload")

    if args.write_env:
        target = Path(args.write_env)
        lines = []
        if target.exists():
            lines = [
                line
                for line in target.read_text(encoding="utf-8").splitlines()
                if not line.startswith(("AI_SERVICE_URL=", "EXPO_PUBLIC_AI_SERVICE_URL="))
            ]
        lines += [f"AI_SERVICE_URL={base}", f"EXPO_PUBLIC_AI_SERVICE_URL={base}"]
        target.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
        print()
        print(f"Written to {target} (previous AI_SERVICE_URL lines replaced)")


def _serve_health(base: str) -> str:
    """One line on whether the service behind this address is ready.

    Deliberately not a hard failure: the address is still worth printing while
    the model loads, and the caller usually wants to paste it and wait. What it
    must not do is stay silent, because "the port is published" and "the AI
    works" are three and a half minutes apart on the fastest host measured.
    """
    try:
        import urllib.request

        with urllib.request.urlopen(f"{base}/health", timeout=10) as reply:
            payload = json.loads(reply.read().decode("utf-8"))
    except Exception as error:  # noqa: BLE001 - reported, never raised
        return f"not answering yet ({type(error).__name__}) — models load in about 3m30s"

    vlm = (payload.get("vlm") or {}).get("attached")
    detector = (payload.get("detector") or {}).get("attached")
    chunks = (payload.get("knowledge") or {}).get("chunks")
    if vlm and detector:
        return f"READY — Qwen and detector attached, {chunks} knowledge passages"
    missing = ", ".join(
        name for name, ok in (("Qwen", vlm), ("detector", detector)) if not ok
    )
    return f"answering, but {missing} not attached yet — {chunks} passages loaded"


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


_NOT_A_LOG = ("codec can't encode", "codec can't decode")
"""Sentences the CLI prints instead of the log, while exiting 0.

Reported as a failure here rather than passed on, because the caller most
likely to read this is a watcher looking for the word that means training
finished, and a command that succeeds while returning no log is indistinguish-
able from a run still in progress. The machine goes on billing.
"""


def cmd_logs(args: argparse.Namespace) -> None:
    instance = _instance_id(args.instance)
    result = _cli("logs", str(instance), "--tail", str(args.tail))
    output = result.stdout or result.stderr
    if any(marker in output for marker in _NOT_A_LOG):
        raise SystemExit(
            "\n".join(
                [
                    f"The CLI failed to print the log rather than printing it: {output.strip()}",
                    "This exits 0 on its own, so it has to be turned into a failure here.",
                    f"Read it directly at https://cloud.vast.ai/instances/ ({instance}).",
                ]
            )
        )
    print(output)


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

    # Both files. Clearing only the trainer's left the serving one naming a
    # machine that had just been destroyed, and the next `serve` refused to
    # start and said to destroy it first — twice in one afternoon.
    for path in (INSTANCE_FILE, SERVE_INSTANCE_FILE):
        if path.exists() and path.read_text(encoding="utf-8").strip() == str(instance):
            path.unlink()
    print(f"Gone. {len(remaining)} instance(s) still rented.")
    if remaining:
        print(f"  {remaining} — destroy these too if they are not wanted.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    offers = sub.add_parser("offers", help="what is available and what it costs")
    offers.add_argument("--gpu", default="RTX_3060")
    offers.add_argument("--max-price", type=float, default=0.40)
    offers.add_argument(
        "--min-vram",
        type=int,
        default=12,
        help="GB of VRAM; 12 is what the deployment was planned around",
    )
    offers.add_argument("--min-download", type=int, default=200, help="Mbps")
    offers.add_argument(
        "--machine",
        type=int,
        default=0,
        help=(
            "list only this host, ignoring --gpu. "
            f"{SERVE_KNOWN_GOOD_MACHINE} is the one that has served this image."
        ),
    )
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
    train.add_argument("--batch", type=int, default=48)
    train.add_argument("--run-name", default="detector-v3")
    train.add_argument(
        "--model",
        default="yolo11s.pt",
        help=(
            "starting weights. yolo11s.pt is what detector-v2 was trained on and "
            "what every published figure refers to: 9.4M parameters, roughly "
            "three times the epoch time of yolov8n.pt, and it fits a 12GB card "
            "at 640px beside Qwen. The default used to be yolov8n.pt, which "
            "meant an unattended run produced a model nothing could be compared "
            "against. Changing this changes what the numbers mean, so record it "
            "in the run name."
        ),
    )
    train.add_argument(
        "--resume-from",
        default="",
        help=(
            "continue from weights already published, given as the path inside "
            "the weights repo, e.g. detector-v2/weights/best.pt. The machine "
            "that produced them no longer exists, so this is the only way to "
            "buy more epochs without paying again for the ones already run. "
            "Not a true resume: the schedule starts over, which is why the "
            "learning rate drops to 0.002 unless --lr0 says otherwise."
        ),
    )
    train.add_argument(
        "--lr0",
        default="",
        help="starting learning rate; default 0.002 when --resume-from is set",
    )
    train.add_argument(
        "--warmup",
        default="",
        help="warmup epochs; default 1 when --resume-from is set",
    )
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
    serve.add_argument(
        "--weights-run",
        default="detector-v2-yolo11s",
        help=(
            "which published run the served detector uses. v2 knows twenty-two "
            "devices to v1's seventeen, and on the seventeen they share it "
            "names 86.2 percent correctly against v1's 83.9, measured on the "
            "same images. See docs/DETECTOR-V2.md."
        ),
    )
    serve.add_argument(
        "--force-host",
        action="store_true",
        help="rent a host whose driver or link the image needs more of",
    )
    serve.add_argument("--max-len", type=int, default=8192)

    address = sub.add_parser("address", help="where the served API answers")
    address.add_argument(
        "--write-env",
        default="",
        metavar="PATH",
        help=(
            "also write AI_SERVICE_URL and EXPO_PUBLIC_AI_SERVICE_URL into this "
            ".env file, replacing any previous lines. Every rental publishes a "
            "different host and port, so this is the step that is otherwise done "
            "by hand and got wrong."
        ),
    )
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
