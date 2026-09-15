"""Move the dataset and the trained weights through the Hugging Face Hub.

A rented GPU is disposable, so nothing important may live only on it. The
dataset goes up once and is pulled at the start of every run; the weights come
back at the end. Losing the machine then costs nothing.

    python tools/hub.py whoami
    python tools/hub.py push-dataset --repo <user>/fixhome-devices
    python tools/hub.py pull-weights --repo <user>/fixhome-detector --run <name>

GitHub is not an option for the dataset: it blocks files over 100 MB, asks that
repositories stay under a gigabyte, and Git LFS gives one gigabyte of storage
and one gigabyte of monthly bandwidth on the free plan, which a single clone
would exhaust. The Hub is built for this and costs nothing.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _secrets import describe, get_secret  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = REPO_ROOT / "datasets" / "fixhome"
WEIGHTS_DIR = REPO_ROOT / "weights"

_HUB_DIR_LIMIT = 10000
"""Files per directory the Hub accepts. Exceeding it rejects the entire push."""


def _overfull_directories(root: Path) -> list[tuple[Path, int]]:
    counts: dict[Path, int] = {}
    for path in root.rglob("*"):
        if path.is_file():
            counts[path.parent] = counts.get(path.parent, 0) + 1
    return sorted(
        ((d.relative_to(root), n) for d, n in counts.items() if n > _HUB_DIR_LIMIT),
        key=lambda item: -item[1],
    )

_TOKEN_HINT = (
    "Create a token at huggingface.co/settings/tokens with the Write role.\n"
    "A Read token can download but cannot upload, and the error it produces\n"
    "does not make that obvious."
)


def _api(token: str):
    try:
        from huggingface_hub import HfApi
    except ImportError:  # pragma: no cover - tooling only
        raise SystemExit(
            "huggingface_hub is not installed. pip install -r requirements-tools.txt"
        )
    return HfApi(token=token)


def cmd_whoami(args: argparse.Namespace) -> None:
    print(describe("HF_TOKEN"))
    token = get_secret("HF_TOKEN", hint=_TOKEN_HINT)
    info = _api(token).whoami()
    print(f"account: {info.get('name')}")
    # Says what the token can do without printing any of it.
    scopes = (info.get("auth") or {}).get("accessToken", {}).get("role")
    print(f"token role: {scopes or 'unknown'}")
    if scopes == "read":
        print("\nThis token cannot upload. Create one with the Write role.")


def cmd_push_dataset(args: argparse.Namespace) -> None:
    source = Path(args.source) if args.source else DATASET_DIR
    if not (source / "data.yaml").exists():
        raise SystemExit(
            f"No dataset at {source}.\n"
            "Build it first: python tools/build_dataset.py export --include-roboflow"
        )

    token = get_secret("HF_TOKEN", hint=_TOKEN_HINT)
    api = _api(token)
    api.create_repo(args.repo, repo_type="dataset", private=args.private, exist_ok=True)

    size_mb = sum(f.stat().st_size for f in source.rglob("*") if f.is_file()) / 1e6
    count = sum(1 for f in source.rglob("*") if f.is_file())
    print(f"Uploading {count} files, {size_mb:.0f} MB, from {source}")
    print("This is one upload; every later training run pulls it in seconds.")

    crowded = _overfull_directories(source)
    if crowded:
        raise SystemExit(
            "The Hub refuses a push where any directory holds more than "
            f"{_HUB_DIR_LIMIT} files, and it rejects the whole push rather than\n"
            "the offending directory. These are over the limit:\n"
            + "".join(f"  {path}  ({count} files)\n" for path, count in crowded)
            + "\nRe-export to shard them:\n"
            "  python tools/build_dataset.py export --include-roboflow"
        )

    api.upload_folder(
        folder_path=str(source),
        repo_id=args.repo,
        repo_type="dataset",
        commit_message=args.message,
        # Mirror, do not merge. An upload only adds and updates, so re-exporting
        # into a different layout leaves the old one beside the new one: one run
        # left 11224 stale unsharded images next to 12513 sharded ones, and
        # training would have scanned images with no labels beside them.
        delete_patterns=["**"],
    )

    # Checked rather than trusted. An earlier push moved every image, no labels
    # at all, and still exited zero.
    remote = api.list_repo_files(args.repo, repo_type="dataset")
    uploaded = len([f for f in remote if f != ".gitattributes"])
    if uploaded != count:
        raise SystemExit(
            f"\n{uploaded} files on the Hub but {count} locally. The push did not "
            "land as expected.\nCheck the output above for the reason."
        )

    images = sum(1 for f in remote if f.startswith("images/"))
    labels = sum(1 for f in remote if f.startswith("labels/"))
    if images != labels:
        raise SystemExit(
            f"\n{images} images but {labels} labels on the Hub. Training would "
            "silently skip the unpaired ones."
        )

    print(f"\nDone: {uploaded} files at https://huggingface.co/datasets/{args.repo}")
    print(f"Set HF_DATASET_REPO={args.repo} when running the trainer.")


def cmd_pull_weights(args: argparse.Namespace) -> None:
    token = get_secret("HF_TOKEN", hint=_TOKEN_HINT)
    try:
        from huggingface_hub import snapshot_download
    except ImportError:  # pragma: no cover - tooling only
        raise SystemExit("huggingface_hub is not installed.")

    destination = WEIGHTS_DIR / args.run if args.run else WEIGHTS_DIR
    destination.mkdir(parents=True, exist_ok=True)
    path = snapshot_download(
        repo_id=args.repo,
        repo_type="model",
        token=token,
        local_dir=str(destination),
        allow_patterns=[f"{args.run}/**"] if args.run else None,
    )
    print(f"Downloaded to {path}")

    best = next(Path(path).rglob("best.pt"), None)
    if best is None:
        print("No best.pt found; check the run name against the repository.")
        return
    print(f"\nWeights: {best}")
    print(f"Point the service at them: YOLO_WEIGHTS_PATH={best}")


def cmd_list_runs(args: argparse.Namespace) -> None:
    token = get_secret("HF_TOKEN", hint=_TOKEN_HINT)
    files = _api(token).list_repo_files(args.repo, repo_type="model")
    runs = sorted({f.split("/")[0] for f in files if "/" in f})
    if not runs:
        print(f"No runs in {args.repo} yet.")
        return
    print(f"Runs in {args.repo}:")
    for run in runs:
        print(f"  {run}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("whoami", help="check the token works and what it may do")

    push = sub.add_parser("push-dataset", help="upload the exported dataset")
    push.add_argument("--repo", required=True, help="e.g. yourname/fixhome-devices")
    push.add_argument("--source", help=f"default: {DATASET_DIR}")
    push.add_argument("--private", action="store_true")
    push.add_argument("--message", default="Update dataset")

    pull = sub.add_parser("pull-weights", help="download trained weights")
    pull.add_argument("--repo", required=True, help="e.g. yourname/fixhome-detector")
    pull.add_argument("--run", help="a single run directory; omit for everything")

    runs = sub.add_parser("list-runs", help="what training runs are published")
    runs.add_argument("--repo", required=True)

    args = parser.parse_args()
    {
        "whoami": cmd_whoami,
        "push-dataset": cmd_push_dataset,
        "pull-weights": cmd_pull_weights,
        "list-runs": cmd_list_runs,
    }[args.command](args)


if __name__ == "__main__":
    main()
