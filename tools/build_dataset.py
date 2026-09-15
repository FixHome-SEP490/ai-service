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
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

# Vietnamese class names crash the default Windows console codepage.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = REPO_ROOT / "app" / "data" / "device_catalog.json"
SPLIT_PATH = REPO_ROOT / "datasets" / "split.json"
REVIEWED_ROOT = REPO_ROOT / "datasets" / "reviewed"
ROBOFLOW_ROOT = REPO_ROOT / "datasets" / "roboflow"
SOURCES_PATH_NAME = "sources.json"

SOURCE_LABELS = {
    "open_images": "Open Images V7, hand-drawn boxes",
    "roboflow": "Roboflow Universe, hand-drawn boxes",
    "collected": "collected for this project, boxes drawn automatically",
}

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
        import fiftyone as fo
        import fiftyone.zoo as foz
    except ImportError:  # pragma: no cover - tooling only
        raise SystemExit(
            "fiftyone is not installed. pip install -r requirements-tools.txt"
        )

    catalog = load_catalog()
    mapping = open_images_mapping(catalog)
    classes = sorted(mapping)
    print(f"Requesting {len(classes)} Open Images classes, up to {args.limit_per_class} each")

    # One class at a time. Asking for all of them under a single max_samples
    # lets the common classes swallow the budget: a combined request returned
    # 865 televisions against 71 ovens, and a detector trained on that learns
    # the prior rather than the object.
    dataset = None
    for index, class_name in enumerate(classes, start=1):
        print(f"  [{index}/{len(classes)}] {class_name}")
        part_name = f"{args.dataset_name}-{index:02d}"
        if part_name in fo.list_datasets():
            fo.delete_dataset(part_name)
        # No overwrite= here. The zoo treats it as "delete the downloaded
        # split", so passing it per class wipes the images the previous classes
        # just fetched: one run left 326 files on disk for 5273 samples, and the
        # failure only appears later as missing-file errors during export.
        part = foz.load_zoo_dataset(
            "open-images-v7",
            split="train",
            label_types=["detections"],
            classes=[class_name],
            max_samples=args.limit_per_class,
            dataset_name=part_name,
        )
        if dataset is None:
            if args.dataset_name in fo.list_datasets():
                fo.delete_dataset(args.dataset_name)
            dataset = fo.Dataset(args.dataset_name)
        dataset.add_samples(part)
        part.delete()
    # Zoo datasets are non-persistent by default, so the registration is dropped
    # when this process exits and `export` later reports the dataset as missing,
    # even though every image is still on disk. Re-running then looks like a
    # second full download. Mark it persistent so the work survives.
    dataset.persistent = True
    dataset.save()
    print(f"Downloaded {len(dataset)} samples into FiftyOne dataset {dataset.name!r}")
    print("Next: python tools/build_dataset.py export --out datasets/fixhome")


def _content_hash(path: Path) -> str:
    """Hash file bytes so identical or re-saved copies group together."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 16), b""):
            digest.update(chunk)
    return digest.hexdigest()


SHARD_COUNT = 64
"""Subdirectories per split.

The Hugging Face Hub refuses a push where any single directory holds more than
ten thousand files, and it refuses the whole push rather than the offending
directory: one export put 10064 training images in one folder and the upload
died after transferring every image but no labels, while still exiting zero.

Ultralytics finds a label by swapping `/images/` for `/labels/` in the image
path, so nesting is safe as long as both sides are sharded identically.
"""


def _shard_of(stem: str) -> str:
    """Stable bucket from the filename, so a re-export lands files identically."""
    value = int(hashlib.sha256(stem.encode()).hexdigest()[:8], 16) % SHARD_COUNT
    return f"{value:02d}"


def _shard_dirs(out_root: Path, split: str, stem: str) -> tuple[Path, Path]:
    shard = _shard_of(stem)
    images = out_root / "images" / split / shard
    labels = out_root / "labels" / split / shard
    images.mkdir(parents=True, exist_ok=True)
    labels.mkdir(parents=True, exist_ok=True)
    return images, labels


def _split_for(digest: str) -> str:
    """Pick a split from the content hash itself.

    Deciding per item rather than by slicing a shuffled list matters because
    images arrive in batches. The previous version proportioned a list, so
    merging a source one image at a time computed int(1 * 0.8) == 0 train and
    sent every newly added image to test: one run put all 11791 air conditioner
    images in the test split and left training with none.

    Hashing gives the same answer whether an image arrives alone or among
    thousands, and the same answer on every machine, so a rerun cannot quietly
    reshuffle what the previous numbers were measured on.
    """
    bucket = int(hashlib.sha256(f"{SPLIT_SEED}:{digest}".encode()).hexdigest()[:8], 16) % 100
    if bucket < SPLIT_RATIOS["train"] * 100:
        return "train"
    if bucket < (SPLIT_RATIOS["train"] + SPLIT_RATIOS["val"]) * 100:
        return "val"
    return "test"


def _assign_splits(groups: List[str]) -> Dict[str, str]:
    """Assign whole duplicate-groups to a split, never individual images."""
    return {group: _split_for(group) for group in sorted(groups)}


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
    missing = 0
    for sample in dataset:
        path = Path(sample.filepath)
        if not path.exists():
            missing += 1
            continue
        by_hash[_content_hash(path)].append(sample)
    if missing:
        print(
            f"{missing} samples reference files no longer on disk and were skipped.\n"
            "  Re-run: build_dataset.py download --limit-per-class N"
        )

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
    sources: Dict[str, str] = {}
    for digest, samples in by_hash.items():
        split = assignment.get(digest)
        if split is None:  # new image added after the split was fixed
            split = "train"
        for sample in samples:
            for device_type in _write_sample(
                sample, out_root, split, mapping, class_index, sources
            ):
                counts[(split, device_type)] += 1

    extra_roots: List[Tuple[Path, str]] = []
    if args.include_reviewed:
        extra_roots.append((REVIEWED_ROOT, "collected"))
    if args.include_roboflow:
        # datasets/roboflow is one folder per class, each with images/ labels/
        extra_roots.extend(
            (d, "roboflow")
            for d in sorted(ROBOFLOW_ROOT.glob("*"))
            if (d / "images").is_dir()
        )
    for root, source_name in extra_roots:
        _merge_extra(
            root, out_root, assignment, counts, device_types, sources, source_name
        )

    _write_sources(out_root, sources, device_types)
    _write_data_yaml(out_root, device_types)
    _print_counts(counts, device_types)


def _detections_of(sample) -> List:
    """Find the Detections field whatever the zoo happened to name it.

    Open Images samples arrive under `ground_truth`, other sources use
    `detections`, and hardcoding either one silently yields an empty dataset
    rather than an error.
    """
    for field in ("ground_truth", "detections", "objects"):
        try:
            value = sample[field]
        except (KeyError, AttributeError):
            continue
        inner = getattr(value, "detections", None)
        if inner:
            return inner
    return []


def _write_sample(
    sample,
    out_root: Path,
    split: str,
    mapping: Dict[str, str],
    class_index: Dict[str, int],
    sources: Dict[str, str],
) -> List[str]:
    """Returns every project class present in the image, or an empty list."""
    labels = _detections_of(sample)

    if not labels:
        return []

    lines: List[str] = []
    present: List[str] = []
    for label in labels:
        device_type = mapping.get(label.label)
        if device_type is None:
            continue  # a class we did not ask for; ignore it
        if device_type not in present:
            present.append(device_type)
        # FiftyOne bounding_box is [x, y, w, h] relative to image size,
        # which YOLO wants as centre-x, centre-y, w, h. Same normalisation.
        x, y, w, h = label.bounding_box
        lines.append(
            f"{class_index[device_type]} {x + w / 2:.6f} {y + h / 2:.6f} {w:.6f} {h:.6f}"
        )

    if not lines:
        return []

    source = Path(sample.filepath)
    image_dir, label_dir = _shard_dirs(out_root, split, source.stem)
    shutil.copy2(source, image_dir / source.name)
    (label_dir / f"{source.stem}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    sources[source.name] = "open_images"
    return present


def _merge_extra(
    source_root: Path,
    out_root: Path,
    assignment: Dict[str, str],
    counts: Counter,
    device_types: List[str],
    sources: Dict[str, str],
    source_name: str,
) -> None:
    """Fold another images/labels pair into the dataset under the same split.

    Used for hand-reviewed crawled images and for imported Roboflow sets. Both
    carry hardware the public sets lack, so they are the part of the training
    data that decides whether the detector works on a real customer photo.
    Everything goes through the same content-hash split, so a duplicate arriving
    from a second source cannot leak across train and test.
    """
    images_dir = source_root / "images"
    labels_dir = source_root / "labels"
    if not images_dir.exists():
        print(f"No images at {source_root}; skipping")
        return

    added = 0
    for image_path in sorted(p for p in images_dir.iterdir() if p.is_file()):
        label_path = labels_dir / f"{image_path.stem}.txt"
        if not label_path.exists():
            continue
        digest = _content_hash(image_path)
        split = assignment.get(digest)
        if split is None:
            split = _split_for(digest)
            assignment[digest] = split

        target_images, target_labels = _shard_dirs(out_root, split, image_path.stem)
        shutil.copy2(image_path, target_images / image_path.name)
        shutil.copy2(label_path, target_labels / label_path.name)
        sources[image_path.name] = source_name

        for line in label_path.read_text(encoding="utf-8").splitlines():
            parts = line.split()
            if parts:
                counts[(split, device_types[int(parts[0])])] += 1
        added += 1

    SPLIT_PATH.write_text(
        json.dumps(
            {"seed": SPLIT_SEED, "ratios": SPLIT_RATIOS, "assignment": assignment}, indent=2
        ),
        encoding="utf-8",
    )
    print(f"Merged {added} images from {source_root}")


def _write_sources(out_root: Path, sources: Dict[str, str], device_types: List[str]) -> None:
    """Record provenance, and emit a test list per source.

    One training run, several numbers. Evaluating the same weights separately on
    marketplace photographs and on photographs taken in real rooms is what shows
    the domain gap, and it costs an evaluation pass rather than a second rental.

    Ultralytics accepts a file of image paths wherever it accepts a directory,
    so each list here is directly usable as `val:` in a data.yaml.
    """
    (out_root / SOURCES_PATH_NAME).write_text(
        json.dumps(
            {"labels": SOURCE_LABELS, "images": sources}, ensure_ascii=False, indent=2
        ),
        encoding="utf-8",
    )

    lists_dir = out_root / "splits"
    lists_dir.mkdir(parents=True, exist_ok=True)

    per_source: Dict[str, List[str]] = defaultdict(list)
    for split_dir in (out_root / "images" / "test").glob("*"):
        if not split_dir.is_dir():
            continue
        for image in split_dir.glob("*"):
            source = sources.get(image.name)
            if source:
                per_source[source].append(f"./images/test/{split_dir.name}/{image.name}")

    for source, paths in sorted(per_source.items()):
        target = lists_dir / f"test_{source}.txt"
        target.write_text("\n".join(sorted(paths)) + "\n", encoding="utf-8")
        print(f"  test split for {source}: {len(paths)} images -> {target.name}")


def _write_data_yaml(out_root: Path, device_types: List[str]) -> None:
    out_root.mkdir(parents=True, exist_ok=True)
    names = "\n".join(f"  {i}: {name}" for i, name in enumerate(device_types))
    (out_root / "data.yaml").write_text(
        # Deliberately not absolute. This dataset is uploaded and unpacked
        # somewhere else, where a path from this machine names nothing -- and
        # here it would carry a Windows drive letter, spaces and Vietnamese
        # diacritics into a Linux container. The training entry point rewrites
        # this line to wherever the files actually landed.
        "path: .\n"
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
        "--include-reviewed",
        action="store_true",
        help="also fold in hand-reviewed crawled images from datasets/reviewed",
    )
    export.add_argument(
        "--include-roboflow",
        action="store_true",
        help="also fold in imported Roboflow sets from datasets/roboflow",
    )
    export.add_argument(
        "--resplit",
        action="store_true",
        help="discard the saved split; only for a deliberate reset",
    )

    args = parser.parse_args()
    {"report": cmd_report, "download": cmd_download, "export": cmd_export}[args.command](args)


if __name__ == "__main__":
    main()
