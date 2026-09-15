"""Build the detector training set from Open Images V7.

Fourteen of the fifteen detector classes already exist in Open Images with
hand-drawn boxes under CC-BY, so they cost nothing to annotate. This script
pulls only those classes, renames them to the project's device types, and writes
a YOLO dataset. Air conditioner has no Open Images class and must come from
Roboflow plus the team's own photos; run `report` to see what is still missing.

    python tools/build_dataset.py report
    python tools/build_dataset.py download --limit-per-class 400
    python tools/build_dataset.py export --out datasets/fixhome

Two rules this script enforces, both of which quietly ruin a model when broken.
Near-duplicate images are grouped by content hash so the same appliance cannot
land in both train and test, which would inflate the reported accuracy. And the
split is written to disk and reused, so numbers stay comparable between runs
instead of shifting every time someone retrains.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional

# Vietnamese class names crash the default Windows console codepage.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = REPO_ROOT / "app" / "data" / "device_catalog.json"
SPLIT_PATH = REPO_ROOT / "datasets" / "split.json"

SPLIT_RATIOS = {"train": 0.8, "val": 0.1, "test": 0.1}
SPLIT_SEED = 20260915


def load_catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def detector_devices(catalog: dict) -> List[dict]:
    return [d for d in catalog["devices"] if d.get("detector_class")]


def open_images_mapping(catalog: dict) -> Dict[str, str]:
    """Open Images class name -> project device_type."""
    return {
        d["open_images_class"]: d["device_type"]
        for d in detector_devices(catalog)
        if d.get("open_images_class")
    }


def cmd_report(args: argparse.Namespace) -> None:
    catalog = load_catalog()
    devices = detector_devices(catalog)
    available = [d for d in devices if d.get("open_images_class")]
    missing = [d for d in devices if not d.get("open_images_class")]

    print(f"Detector classes: {len(devices)}")
    print(f"\nFrom Open Images V7, boxes included ({len(available)}):")
    for d in available:
        print(f"  {d['device_type']:<20} <- {d['open_images_class']}")

    print(f"\nMust be collected manually ({len(missing)}):")
    for d in missing:
        print(f"  {d['device_type']:<20} ({d['name_vi']})")

    print(
        "\nEven for classes Open Images covers, public photos are mostly studio\n"
        "product shots. Real customer photos are dim, angled and cluttered, so\n"
        "hold back a test split of your own photographs for every class."
    )


def cmd_download(args: argparse.Namespace) -> None:
    """Pull only the needed classes. The full dataset is 1.7M images."""
    try:
        import fiftyone.zoo as foz
    except ImportError:  # pragma: no cover - tooling only
        raise SystemExit(
            "fiftyone is not installed. pip install -r requirements-tools.txt"
        )

    catalog = load_catalog()
    mapping = open_images_mapping(catalog)
    classes = sorted(mapping)
    print(f"Requesting {len(classes)} Open Images classes: {', '.join(classes)}")

    dataset = foz.load_zoo_dataset(
        "open-images-v7",
        split="train",
        label_types=["detections"],
        classes=classes,
        max_samples=args.limit_per_class * len(classes),
        dataset_name=args.dataset_name,
        overwrite=args.overwrite,
    )
    print(f"Downloaded {len(dataset)} samples into FiftyOne dataset {dataset.name!r}")
    print("Next: python tools/build_dataset.py export --out datasets/fixhome")


def _content_hash(path: Path) -> str:
    """Hash file bytes so identical or re-saved copies group together."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _assign_splits(groups: List[str]) -> Dict[str, str]:
    """Assign whole duplicate-groups to a split, never individual images."""
    rng = random.Random(SPLIT_SEED)
    shuffled = sorted(groups)
    rng.shuffle(shuffled)

    total = len(shuffled)
    n_train = int(total * SPLIT_RATIOS["train"])
    n_val = int(total * SPLIT_RATIOS["val"])

    assignment: Dict[str, str] = {}
    for index, group in enumerate(shuffled):
        if index < n_train:
            assignment[group] = "train"
        elif index < n_train + n_val:
            assignment[group] = "val"
        else:
            assignment[group] = "test"
    return assignment


def cmd_export(args: argparse.Namespace) -> None:
    try:
        import fiftyone as fo
    except ImportError:  # pragma: no cover - tooling only
        raise SystemExit(
            "fiftyone is not installed. pip install -r requirements-tools.txt"
        )

    catalog = load_catalog()
    mapping = open_images_mapping(catalog)
    device_types = [d["device_type"] for d in detector_devices(catalog)]
    class_index = {name: i for i, name in enumerate(device_types)}

    dataset = fo.load_dataset(args.dataset_name)
    out_root = Path(args.out)

    # Group by content hash first so duplicates cannot straddle two splits.
    by_hash: Dict[str, List] = defaultdict(list)
    for sample in dataset:
        by_hash[_content_hash(Path(sample.filepath))].append(sample)

    reuse = SPLIT_PATH.exists() and not args.resplit
    if reuse:
        assignment = json.loads(SPLIT_PATH.read_text(encoding="utf-8"))["assignment"]
        print(f"Reusing split from {SPLIT_PATH}")
    else:
        assignment = _assign_splits(list(by_hash))
        SPLIT_PATH.parent.mkdir(parents=True, exist_ok=True)
        SPLIT_PATH.write_text(
            json.dumps(
                {"seed": SPLIT_SEED, "ratios": SPLIT_RATIOS, "assignment": assignment},
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"Wrote split to {SPLIT_PATH}")

    counts: Counter = Counter()
    for digest, samples in by_hash.items():
        split = assignment.get(digest)
        if split is None:  # new image added after the split was fixed
            split = "train"
        for sample in samples:
            written = _write_sample(sample, out_root, split, mapping, class_index)
            if written:
                counts[(split, written)] += 1

    _write_data_yaml(out_root, device_types)
    _print_counts(counts, device_types)


def _write_sample(
    sample, out_root: Path, split: str, mapping: Dict[str, str], class_index: Dict[str, int]
) -> Optional[str]:
    detections = getattr(sample, "detections", None)
    labels = getattr(detections, "detections", []) if detections else []

    lines: List[str] = []
    device_type: Optional[str] = None
    for label in labels:
        device_type = mapping.get(label.label)
        if device_type is None:
            continue  # a class we did not ask for; ignore it
        # FiftyOne bounding_box is [x, y, w, h] relative to image size,
        # which YOLO wants as centre-x, centre-y, w, h. Same normalisation.
        x, y, w, h = label.bounding_box
        lines.append(
            f"{class_index[device_type]} {x + w / 2:.6f} {y + h / 2:.6f} {w:.6f} {h:.6f}"
        )

    if not lines:
        return None

    source = Path(sample.filepath)
    image_dir = out_root / "images" / split
    label_dir = out_root / "labels" / split
    image_dir.mkdir(parents=True, exist_ok=True)
    label_dir.mkdir(parents=True, exist_ok=True)

    shutil.copy2(source, image_dir / source.name)
    (label_dir / f"{source.stem}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return device_type


def _write_data_yaml(out_root: Path, device_types: List[str]) -> None:
    out_root.mkdir(parents=True, exist_ok=True)
    names = "\n".join(f"  {i}: {name}" for i, name in enumerate(device_types))
    (out_root / "data.yaml").write_text(
        f"path: {out_root.resolve().as_posix()}\n"
        "train: images/train\n"
        "val: images/val\n"
        "test: images/test\n\n"
        f"names:\n{names}\n",
        encoding="utf-8",
    )
    print(f"Wrote {out_root / 'data.yaml'}")


def _print_counts(counts: Counter, device_types: List[str]) -> None:
    print("\nImages per class and split:")
    header = f"{'class':<20}" + "".join(f"{s:>8}" for s in ("train", "val", "test"))
    print(header)
    for device_type in device_types:
        row = f"{device_type:<20}"
        for split in ("train", "val", "test"):
            row += f"{counts.get((split, device_type), 0):>8}"
        print(row)

    thin = [
        d for d in device_types if sum(counts.get((s, d), 0) for s in SPLIT_RATIOS) < 150
    ]
    if thin:
        print(
            "\nUnder 150 images, expect unstable detection and collect more:\n  "
            + ", ".join(thin)
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("report", help="show which classes are covered and which are not")

    download = sub.add_parser("download", help="fetch the needed Open Images classes")
    download.add_argument("--limit-per-class", type=int, default=400)
    download.add_argument("--dataset-name", default="fixhome-openimages")
    download.add_argument("--overwrite", action="store_true")

    export = sub.add_parser("export", help="write a YOLO dataset with a fixed split")
    export.add_argument("--out", default="datasets/fixhome")
    export.add_argument("--dataset-name", default="fixhome-openimages")
    export.add_argument(
        "--resplit",
        action="store_true",
        help="discard the saved split; only for a deliberate reset",
    )

    args = parser.parse_args()
    {"report": cmd_report, "download": cmd_download, "export": cmd_export}[args.command](args)


if __name__ == "__main__":
    main()
