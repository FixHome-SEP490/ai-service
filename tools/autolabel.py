"""Draft bounding boxes for crawled images so they only need correcting.

Drawing well over a thousand boxes by hand is many hours of clicking. An open-vocabulary
detector takes text prompts with no training and gets most of those boxes close
enough that the job becomes review instead of drawing — minutes per hundred
images rather than minutes per image.

    python tools/autolabel.py run --all
    python tools/autolabel.py review --device power_outlet
    python tools/autolabel.py promote --device power_outlet

Review is not optional. Pseudo-labels are wrong often enough that shipping them
unchecked trains the detector on the model's mistakes, and those mistakes are
systematic rather than random, so they do not average out.

The prompts are English because the open-vocabulary model was trained on English
text; the crawl queries stay Vietnamese because search engines are not.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = REPO_ROOT / "app" / "data" / "device_catalog.json"
COLLECTED_ROOT = REPO_ROOT / "datasets" / "collected"
DRAFT_ROOT = REPO_ROOT / "datasets" / "drafts"
REVIEWED_ROOT = REPO_ROOT / "datasets" / "reviewed"

DEFAULT_MODEL = "yolov8s-worldv2.pt"
DEFAULT_CONFIDENCE = 0.15
"""Deliberately low. A missing box costs more review effort than a spurious one:
deleting a wrong box is one keystroke, noticing an absent one means looking."""

# Text prompts for the open-vocabulary detector, per device type.
PROMPTS: Dict[str, List[str]] = {
    "power_outlet": ["electrical outlet", "wall socket", "power socket", "light switch panel"],
    "gas_stove": ["gas stove", "gas cooktop", "portable gas burner"],
    "water_heater": ["water heater", "boiler tank on wall", "electric shower heater"],
    "air_conditioner": ["air conditioner", "wall mounted air conditioner", "ac outdoor unit"],
    "washing_machine": ["washing machine"],
    "water_pipe": ["water pipe", "plumbing pipe", "pipe joint"],
    "refrigerator": ["refrigerator"],
    "microwave_oven": ["microwave oven"],
    "oven": ["oven"],
    "kettle": ["electric kettle"],
    "television": ["television"],
    "sink": ["sink"],
    "faucet": ["faucet", "tap"],
    "toilet": ["toilet"],
    "ceiling_fan": ["ceiling fan"],
    "electric_fan": ["electric fan", "pedestal fan"],
    "light_bulb": ["light bulb", "ceiling light"],
}


def load_catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def detector_class_index() -> Dict[str, int]:
    devices = [d["device_type"] for d in load_catalog()["devices"] if d.get("detector_class")]
    return {name: index for index, name in enumerate(devices)}


def _crawled_devices() -> List[str]:
    if not COLLECTED_ROOT.exists():
        return []
    return sorted(
        d.name
        for d in COLLECTED_ROOT.iterdir()
        if d.is_dir() and not d.name.startswith("_")
    )


def cmd_run(args: argparse.Namespace) -> None:
    try:
        from ultralytics import YOLOWorld
    except ImportError:  # pragma: no cover - tooling only
        raise SystemExit("ultralytics is not installed. pip install -r requirements-model.txt")

    devices = _crawled_devices() if args.all else [args.device]
    if not devices:
        raise SystemExit(f"No crawled images under {COLLECTED_ROOT}. Run tools/collect_images.py first.")

    class_index = detector_class_index()
    model = YOLOWorld(args.model)

    for device_type in devices:
        prompts = PROMPTS.get(device_type)
        if prompts is None:
            print(f"{device_type}: no prompt defined, skipped")
            continue
        if device_type not in class_index:
            print(f"{device_type}: not a detector class, skipped")
            continue

        images = sorted((COLLECTED_ROOT / device_type).glob("*.jpg"))
        if not images:
            print(f"{device_type}: no images")
            continue

        # One prompt set per class: the detector only ever has to answer
        # "where is this thing", never "which of fifteen things is this".
        model.set_classes(prompts)
        out_labels = DRAFT_ROOT / device_type / "labels"
        out_labels.mkdir(parents=True, exist_ok=True)

        boxed = empty = 0
        print(f"\n{device_type}: {len(images)} images, prompts {prompts}")
        for start in range(0, len(images), args.batch):
            chunk = images[start : start + args.batch]
            results = model.predict(
                [str(p) for p in chunk], conf=args.confidence, verbose=False
            )
            for image_path, result in zip(chunk, results):
                lines = _to_yolo_lines(result, class_index[device_type], args.max_boxes)
                (out_labels / f"{image_path.stem}.txt").write_text(
                    "\n".join(lines) + ("\n" if lines else ""), encoding="utf-8"
                )
                if lines:
                    boxed += 1
                else:
                    empty += 1
            print(f"  {min(start + args.batch, len(images))}/{len(images)}", end="\r")

        print(f"\n  drafted {boxed}, nothing found {empty} -> {out_labels}")
        if empty:
            print(
                f"  {empty} images got no box. Usually they are not the device at all;"
                " delete them during review rather than drawing boxes."
            )

    print("\nNext: python tools/autolabel.py review --device <name>")


def _to_yolo_lines(result, class_id: int, max_boxes: int) -> List[str]:
    boxes = getattr(result, "boxes", None)
    if boxes is None or len(boxes) == 0:
        return []

    height, width = result.orig_shape
    rows = []
    for xyxy, conf in zip(boxes.xyxy.tolist(), boxes.conf.tolist()):
        x1, y1, x2, y2 = xyxy
        rows.append((conf, x1, y1, x2, y2))
    rows.sort(reverse=True)

    lines = []
    for _, x1, y1, x2, y2 in rows[:max_boxes]:
        cx = ((x1 + x2) / 2) / width
        cy = ((y1 + y2) / 2) / height
        bw = (x2 - x1) / width
        bh = (y2 - y1) / height
        if bw <= 0 or bh <= 0:
            continue
        lines.append(f"{class_id} {cx:.6f} {cy:.6f} {bw:.6f} {bh:.6f}")
    return lines


def cmd_review(args: argparse.Namespace) -> None:
    """Open the drafts in FiftyOne so boxes can be corrected or deleted."""
    try:
        import fiftyone as fo
    except ImportError:  # pragma: no cover - tooling only
        raise SystemExit("fiftyone is not installed. pip install -r requirements-tools.txt")

    device_type = args.device
    images_dir = COLLECTED_ROOT / device_type
    labels_dir = DRAFT_ROOT / device_type / "labels"
    if not labels_dir.exists():
        raise SystemExit(f"No drafts for {device_type}. Run: autolabel.py run --device {device_type}")

    dataset_name = f"review-{device_type}"
    if dataset_name in fo.list_datasets():
        fo.delete_dataset(dataset_name)

    dataset = fo.Dataset(dataset_name)
    class_index = detector_class_index()
    classes = sorted(class_index, key=class_index.get)

    samples = []
    for image_path in sorted(images_dir.glob("*.jpg")):
        sample = fo.Sample(filepath=str(image_path))
        label_path = labels_dir / f"{image_path.stem}.txt"
        detections = []
        if label_path.exists():
            for line in label_path.read_text(encoding="utf-8").splitlines():
                parts = line.split()
                if len(parts) != 5:
                    continue
                cid, cx, cy, bw, bh = int(parts[0]), *map(float, parts[1:])
                detections.append(
                    fo.Detection(
                        label=classes[cid],
                        bounding_box=[cx - bw / 2, cy - bh / 2, bw, bh],
                    )
                )
        sample["ground_truth"] = fo.Detections(detections=detections)
        samples.append(sample)

    dataset.add_samples(samples)
    dataset.persistent = True
    print(f"Loaded {len(samples)} samples into FiftyOne dataset {dataset_name!r}")
    print(
        "In the app: fix or delete boxes, and delete images that are not the device.\n"
        "Close the app when finished, then run:\n"
        f"  python tools/autolabel.py promote --device {device_type}"
    )
    session = fo.launch_app(dataset)
    session.wait()


def cmd_promote(args: argparse.Namespace) -> None:
    """Write the reviewed dataset out in YOLO layout, ready to merge."""
    try:
        import fiftyone as fo
    except ImportError:  # pragma: no cover - tooling only
        raise SystemExit("fiftyone is not installed. pip install -r requirements-tools.txt")

    device_type = args.device
    dataset_name = f"review-{device_type}"
    if dataset_name not in fo.list_datasets():
        raise SystemExit(f"No reviewed dataset {dataset_name!r}. Run review first.")

    dataset = fo.load_dataset(dataset_name)
    class_index = detector_class_index()
    out_images = REVIEWED_ROOT / "images"
    out_labels = REVIEWED_ROOT / "labels"
    out_images.mkdir(parents=True, exist_ok=True)
    out_labels.mkdir(parents=True, exist_ok=True)

    import shutil

    counts: Counter = Counter()
    for sample in dataset:
        detections = getattr(sample.ground_truth, "detections", []) if sample.ground_truth else []
        if not detections:
            continue  # reviewed to nothing; drop rather than train on an empty box
        source = Path(sample.filepath)
        lines = []
        for detection in detections:
            class_id = class_index.get(detection.label)
            if class_id is None:
                continue
            x, y, w, h = detection.bounding_box
            lines.append(f"{class_id} {x + w / 2:.6f} {y + h / 2:.6f} {w:.6f} {h:.6f}")
            counts[detection.label] += 1
        if not lines:
            continue
        shutil.copy2(source, out_images / source.name)
        (out_labels / f"{source.stem}.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"Promoted to {REVIEWED_ROOT}")
    for label, count in sorted(counts.items()):
        print(f"  {label:<20}{count:>6} boxes")
    print("\nNext: python tools/build_dataset.py export --include-reviewed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="draft boxes with an open-vocabulary detector")
    group = run.add_mutually_exclusive_group(required=True)
    group.add_argument("--device")
    group.add_argument("--all", action="store_true")
    run.add_argument("--model", default=DEFAULT_MODEL)
    run.add_argument("--confidence", type=float, default=DEFAULT_CONFIDENCE)
    run.add_argument("--batch", type=int, default=16)
    run.add_argument("--max-boxes", type=int, default=3)

    review = sub.add_parser("review", help="correct the drafts in FiftyOne")
    review.add_argument("--device", required=True)

    promote = sub.add_parser("promote", help="export reviewed labels in YOLO layout")
    promote.add_argument("--device", required=True)

    args = parser.parse_args()
    {"run": cmd_run, "review": cmd_review, "promote": cmd_promote}[args.command](args)


if __name__ == "__main__":
    main()
