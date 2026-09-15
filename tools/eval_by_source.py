"""Evaluate one set of weights separately on each source of images.

Training twice — once on public data, once with the collected photographs — is
the obvious way to show the second set helped, and it costs a second GPU rental
and a day of waiting.

Evaluating once per source costs an evaluation pass. The same weights are scored
on marketplace product photographs and on photographs taken in real rooms, and
the difference between those two numbers is the domain gap. That is the figure
worth putting in a report, and it is not obtainable from a single overall score
however good that score looks.

    python tools/eval_by_source.py list
    python tools/eval_by_source.py run --weights runs/detector/weights/best.pt

Needs a GPU to be quick but will run on a CPU given patience.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = REPO_ROOT / "datasets" / "fixhome"
RESULTS_PATH = REPO_ROOT / "datasets" / "eval_by_source.json"


def _sources(dataset_dir: Path) -> dict:
    path = dataset_dir / "sources.json"
    if not path.exists():
        raise SystemExit(
            f"No {path.name} in {dataset_dir}.\n"
            "Re-export the dataset so provenance is recorded:\n"
            "  python tools/build_dataset.py export --include-reviewed --include-roboflow"
        )
    return json.loads(path.read_text(encoding="utf-8"))


def _split_files(dataset_dir: Path) -> Dict[str, Path]:
    lists = sorted((dataset_dir / "splits").glob("test_*.txt"))
    return {path.stem.removeprefix("test_"): path for path in lists}


def cmd_list(args: argparse.Namespace) -> None:
    dataset_dir = Path(args.dataset)
    meta = _sources(dataset_dir)
    splits = _split_files(dataset_dir)

    if not splits:
        raise SystemExit("No per-source test lists. Re-export the dataset.")

    print(f"{'source':<16}{'test images':>12}   description")
    for source, path in splits.items():
        count = sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line)
        print(f"{source:<16}{count:>12}   {meta['labels'].get(source, '')}")

    print(
        "\nA score on 'collected' far below the others is the domain gap, not a\n"
        "broken model. It is fixed with photographs taken in real conditions,\n"
        "not with more epochs."
    )


def _write_data_yaml(dataset_dir: Path, source: str, names: List[str]) -> Path:
    """A data.yaml whose validation set is one source's test images."""
    target = dataset_dir / "splits" / f"data_{source}.yaml"
    listed = "\n".join(f"  {index}: {name}" for index, name in enumerate(names))
    target.write_text(
        f"path: {dataset_dir.resolve().as_posix()}\n"
        "train: images/train\n"
        f"val: splits/test_{source}.txt\n"
        f"test: splits/test_{source}.txt\n\n"
        f"names:\n{listed}\n",
        encoding="utf-8",
    )
    return target


def cmd_run(args: argparse.Namespace) -> None:
    try:
        from ultralytics import YOLO
    except ImportError:  # pragma: no cover - tooling only
        raise SystemExit(
            "ultralytics is not installed. pip install -r requirements-model.txt"
        )

    dataset_dir = Path(args.dataset)
    splits = _split_files(dataset_dir)
    if not splits:
        raise SystemExit("No per-source test lists. Re-export the dataset.")

    names = _class_names(dataset_dir)
    if not names:
        raise SystemExit(f"No class names in {dataset_dir / 'data.yaml'}")
    model = YOLO(args.weights)

    results: Dict[str, dict] = {}
    for source, _ in splits.items():
        data_yaml = _write_data_yaml(dataset_dir, source, names)
        print(f"\n=== {source}")
        metrics = model.val(data=str(data_yaml), split="test", verbose=False)
        box = metrics.box
        results[source] = {
            "map50": round(float(box.map50), 4),
            "map50_95": round(float(box.map), 4),
            "precision": round(float(box.mp), 4),
            "recall": round(float(box.mr), 4),
        }
        print(
            f"  mAP50 {results[source]['map50']:.3f}"
            f"   mAP50-95 {results[source]['map50_95']:.3f}"
            f"   P {results[source]['precision']:.3f}"
            f"   R {results[source]['recall']:.3f}"
        )

    RESULTS_PATH.write_text(
        json.dumps({"weights": str(args.weights), "by_source": results}, indent=2),
        encoding="utf-8",
    )

    print(f"\nWritten to {RESULTS_PATH}")
    _report_gap(results)


def _class_names(dataset_dir: Path) -> List[str]:
    text = (dataset_dir / "data.yaml").read_text(encoding="utf-8")
    names: List[str] = []
    for line in text.split("names:", 1)[1].splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if ":" not in stripped:
            break
        _, _, name = stripped.partition(":")
        names.append(name.strip())
    return names


def _report_gap(results: Dict[str, dict]) -> None:
    if "collected" not in results or len(results) < 2:
        return

    others = [v["map50"] for k, v in results.items() if k != "collected"]
    if not others:
        return

    public = sum(others) / len(others)
    ours = results["collected"]["map50"]
    gap = public - ours

    print(f"\npublic sources {public:.3f}   collected {ours:.3f}   gap {gap:+.3f}")
    if gap > 0.15:
        print(
            "A gap this size means the training photographs do not look like the\n"
            "ones being scored. More epochs will not close it; photographs taken\n"
            "in real conditions will."
        )
    elif gap < -0.05:
        print(
            "The collected set scores higher, which usually means it is the easier\n"
            "set rather than the model being better. Check what is in it."
        )
    else:
        print("The sources score alike, so the training data covers both.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    listing = sub.add_parser("list", help="what sources exist and how big each test set is")
    listing.add_argument("--dataset", default=str(DATASET_DIR))

    run = sub.add_parser("run", help="score one set of weights on each source")
    run.add_argument("--weights", required=True)
    run.add_argument("--dataset", default=str(DATASET_DIR))

    args = parser.parse_args()
    {"list": cmd_list, "run": cmd_run}[args.command](args)


if __name__ == "__main__":
    main()
