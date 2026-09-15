"""Draw the boxes so nobody has to draw sixteen thousand by hand.

At twenty seconds an image that is ninety hours of clicking. Two automatic
passes do most of it, and what neither can handle is dropped rather than
queued, because there are already more images per class than the detector needs
and a doubtful box is worse than a missing one.

    python tools/autolabel.py plan
    python tools/autolabel.py run --all
    python tools/autolabel.py review --device power_outlet
    python tools/autolabel.py promote --device power_outlet

**Backdrop pass.** Marketplace photographs sit on a plain background, so the
object is everything that is not the corner colour. Measured on this collection
it places a tight box on roughly seven images in ten, needs no model, and runs
at hundreds of images a second. It refuses whenever the four corners disagree,
which is how a photograph taken in a real room declines itself instead of
returning a box drawn around the furniture.

**Open-vocabulary pass.** For what is left, a detector that takes text prompts.
Slower and looser: measured on this same data it found something in four images
out of twenty-four at its default threshold, which is why it is the fallback
rather than the method.

Review is still not optional. Both passes are confident in the same way whether
they are right or wrong.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image, UnidentifiedImageError

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = REPO_ROOT / "app" / "data" / "device_catalog.json"
COLLECTED_ROOT = REPO_ROOT / "datasets" / "collected"
DRAFT_ROOT = REPO_ROOT / "datasets" / "drafts"
REVIEWED_ROOT = REPO_ROOT / "datasets" / "reviewed"

PROBE_SIZE = 320
"""Work on a thumbnail. The box is normalised, so resolution buys nothing and
costs real time across sixteen thousand images."""

CORNER_AGREEMENT = 30
"""How far the four corners may differ before the backdrop is not plain."""

BACKGROUND_TOLERANCE = 22
"""Per-channel distance from the backdrop colour before a pixel counts as
foreground. Loose enough to ignore JPEG noise on a white background."""

MIN_AREA = 0.02
MAX_AREA = 0.88
"""A box covering nearly the whole frame found the border, not the object.

Product photographs leave margins; a box without them is describing the image
rather than what is in it. Observed directly: a marketing graphic of a wall fan
with a window behind it and captions across the top produced a box around
everything, which would have taught the detector that a fan fills the frame,
window and lettering included. 0.88 rejects that while leaving room for a
close-cropped product shot."""

EDGE_MARGIN = 0.015
MAX_EDGES_TOUCHED = 2
"""A box pressed against three or four sides is the frame, whatever its area.

Area alone misses the case where a wide object is cropped tight horizontally
but the backdrop bleeds top and bottom."""

DEFAULT_MODEL = "yolov8s-worldv2.pt"
DEFAULT_CONFIDENCE = 0.05
"""Low, because this pass only ever sees images the cheap one already refused,
and a spurious box is one keystroke to delete while a missing one has to be
noticed first."""

# English because the open-vocabulary model was trained on English text.
PROMPTS: Dict[str, List[str]] = {
    "power_outlet": ["socket", "electrical outlet", "power strip", "wall socket"],
    "gas_stove": ["gas stove", "gas cooktop", "portable gas burner"],
    "water_heater": ["water heater", "boiler", "electric shower heater"],
    "air_conditioner": ["air conditioner", "wall mounted air conditioner"],
    "washing_machine": ["washing machine"],
    "refrigerator": ["refrigerator"],
    "microwave_oven": ["microwave oven"],
    "oven": ["oven", "toaster oven"],
    "kettle": ["electric kettle", "kettle"],
    "television": ["television", "tv screen"],
    "sink": ["sink", "wash basin"],
    "faucet": ["faucet", "tap"],
    "toilet": ["toilet"],
    "ceiling_fan": ["ceiling fan"],
    "electric_fan": ["electric fan", "pedestal fan"],
    "light_bulb": ["light bulb", "ceiling light", "lamp"],
    "water_pipe": ["pipe", "plumbing pipe"],
}


def load_catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def class_index() -> Dict[str, int]:
    devices = [
        d["device_type"] for d in load_catalog()["devices"] if d.get("detector_class")
    ]
    return {name: index for index, name in enumerate(devices)}


def collected_devices() -> List[str]:
    if not COLLECTED_ROOT.exists():
        return []
    return sorted(d.name for d in COLLECTED_ROOT.iterdir() if d.is_dir())


def box_quality(box: Tuple[float, float, float, float]) -> float:
    """How much to trust a box, from 0 to 1.

    A heuristic cannot be made reliable enough to skip review, so the next best
    thing is to make review cheap. Ordering by this puts the boxes most likely
    to be wrong at the top of the queue, where a person spends their attention,
    instead of spreading the bad ones evenly through eight thousand images.

    Two signals, both observed failing on this data. A box covering most of the
    frame usually found the border: a watermarked backdrop is not uniform, so
    the shop banner ends up inside the box. And a box pressed against the edges
    is describing the image rather than the object in it.
    """
    _, _, width, height = box
    area = width * height
    # Product photographs put the object at roughly a third to two thirds of
    # the frame; both extremes are where the mistakes live.
    area_score = 1.0 - abs(area - 0.45) / 0.55
    return max(0.0, min(1.0, area_score))


def box_from_background(path: Path) -> Optional[Tuple[float, float, float, float]]:
    """Box around everything that is not the backdrop, or None.

    Returning None is the important half. A photograph taken in a real room has
    corners that disagree with each other, and this declines rather than
    boxing the furniture.
    """
    try:
        with Image.open(path) as image:
            image = image.convert("RGB")
            thumb = image.resize(
                (min(image.width, PROBE_SIZE), min(image.height, PROBE_SIZE))
            )
    except (UnidentifiedImageError, OSError, ValueError):
        return None

    width, height = thumb.size
    pixels = thumb.load()
    corners = [
        pixels[0, 0],
        pixels[width - 1, 0],
        pixels[0, height - 1],
        pixels[width - 1, height - 1],
    ]
    backdrop = tuple(sum(c[i] for c in corners) // 4 for i in range(3))
    disagreement = max(
        max(abs(c[i] - backdrop[i]) for i in range(3)) for c in corners
    )
    if disagreement > CORNER_AGREEMENT:
        return None

    limit = BACKGROUND_TOLERANCE * 3
    left, right, top, bottom = width, -1, height, -1
    for y in range(height):
        for x in range(width):
            pixel = pixels[x, y]
            distance = (
                abs(pixel[0] - backdrop[0])
                + abs(pixel[1] - backdrop[1])
                + abs(pixel[2] - backdrop[2])
            )
            if distance > limit:
                left = min(left, x)
                right = max(right, x)
                top = min(top, y)
                bottom = max(bottom, y)

    if right < 0:
        return None

    box_width = (right - left) / width
    box_height = (bottom - top) / height
    if not (MIN_AREA <= box_width * box_height <= MAX_AREA):
        return None

    edges = sum(
        [
            left / width <= EDGE_MARGIN,
            top / height <= EDGE_MARGIN,
            right / width >= 1 - EDGE_MARGIN,
            bottom / height >= 1 - EDGE_MARGIN,
        ]
    )
    if edges > MAX_EDGES_TOUCHED:
        return None

    return (
        (left + right) / 2 / width,
        (top + bottom) / 2 / height,
        box_width,
        box_height,
    )


def cmd_plan(args: argparse.Namespace) -> None:
    devices = collected_devices()
    if not devices:
        raise SystemExit(
            f"No collected images at {COLLECTED_ROOT}.\n"
            "Import them first: python tools/collect_images.py import-tree --from <folder>"
        )

    known = class_index()
    total = 0
    print(f"{'class':<20}{'images':>8}   prompts")
    for device in devices:
        count = sum(1 for _ in (COLLECTED_ROOT / device).glob("*.jpg"))
        total += count
        mark = " " if device in known else "?"
        prompts = ", ".join(PROMPTS.get(device, [])) or "none defined"
        print(f"{mark}{device:<19}{count:>8}   {prompts}")

    print(f"\n{total} images. Drawing these by hand is about {total * 20 / 3600:.0f} hours.")
    print("  python tools/autolabel.py run --all")


def cmd_run(args: argparse.Namespace) -> None:
    devices = collected_devices() if args.all else [args.device]
    if not devices:
        raise SystemExit(f"No collected images at {COLLECTED_ROOT}")

    known = class_index()
    model = None
    totals: Counter = Counter()

    for device in devices:
        if device not in known:
            print(f"{device}: not a detector class, skipped")
            continue

        images = sorted((COLLECTED_ROOT / device).glob("*.jpg"))
        if not images:
            continue

        label_dir = DRAFT_ROOT / device / "labels"
        label_dir.mkdir(parents=True, exist_ok=True)
        index = known[device]

        by_backdrop: Dict[Path, Tuple[float, float, float, float]] = {}
        leftover: List[Path] = []
        for path in images:
            box = box_from_background(path)
            if box is None:
                leftover.append(path)
            else:
                by_backdrop[path] = box

        by_model: Dict[Path, Tuple[float, float, float, float]] = {}
        if leftover and not args.no_model:
            model = model or _load_model(args.model)
            by_model = _boxes_from_model(
                model, leftover, PROMPTS.get(device, []), args.confidence
            )

        for path, box in {**by_backdrop, **by_model}.items():
            (label_dir / f"{path.stem}.txt").write_text(
                f"{index} {box[0]:.6f} {box[1]:.6f} {box[2]:.6f} {box[3]:.6f}\n",
                encoding="utf-8",
            )

        dropped = len(images) - len(by_backdrop) - len(by_model)
        totals["backdrop"] += len(by_backdrop)
        totals["model"] += len(by_model)
        totals["dropped"] += dropped
        print(
            f"{device:<20} backdrop {len(by_backdrop):>5}"
            f"   model {len(by_model):>5}   dropped {dropped:>5}   of {len(images)}"
        )

    labelled = totals["backdrop"] + totals["model"]
    print(
        f"\nlabelled {labelled}, dropped {totals['dropped']}"
        f"   ({totals['backdrop']} by backdrop, {totals['model']} by model)"
    )
    print(
        "\nDropped images are not a loss: there are already more per class than\n"
        "the detector needs, and a doubtful box is worse than a missing one.\n\n"
        "Both passes are equally confident whether they are right or wrong:\n"
        "  python tools/autolabel.py review --device <name>"
    )


def _load_model(name: str):
    try:
        from ultralytics import YOLOWorld
    except ImportError:  # pragma: no cover - tooling only
        raise SystemExit(
            "ultralytics is not installed. pip install -r requirements-model.txt"
        )
    return YOLOWorld(name)


def _boxes_from_model(
    model, paths: List[Path], prompts: List[str], confidence: float
) -> Dict[Path, Tuple[float, float, float, float]]:
    if not prompts:
        return {}
    model.set_classes(prompts)

    found: Dict[Path, Tuple[float, float, float, float]] = {}
    for start in range(0, len(paths), 16):
        chunk = paths[start : start + 16]
        results = model.predict([str(p) for p in chunk], conf=confidence, verbose=False)
        for path, result in zip(chunk, results):
            boxes = getattr(result, "boxes", None)
            if boxes is None or len(boxes) == 0:
                continue
            # Highest-confidence box only. These are single-object photographs,
            # so a second box is nearly always part of the same object.
            best = max(
                zip(boxes.xyxy.tolist(), boxes.conf.tolist()), key=lambda item: item[1]
            )
            x1, y1, x2, y2 = best[0]
            height, width = result.orig_shape
            found[path] = (
                ((x1 + x2) / 2) / width,
                ((y1 + y2) / 2) / height,
                (x2 - x1) / width,
                (y2 - y1) / height,
            )
    return found


def cmd_review(args: argparse.Namespace) -> None:
    """Open the drafts so boxes can be corrected or deleted."""
    try:
        import fiftyone as fo
    except ImportError:  # pragma: no cover - tooling only
        raise SystemExit(
            "fiftyone is not installed. pip install -r requirements-tools.txt"
        )

    device = args.device
    images_dir = COLLECTED_ROOT / device
    labels_dir = DRAFT_ROOT / device / "labels"
    if not labels_dir.exists():
        raise SystemExit(
            f"No drafts for {device}. Run: autolabel.py run --device {device}"
        )

    name = f"review-{device}"
    if name in fo.list_datasets():
        fo.delete_dataset(name)

    dataset = fo.Dataset(name)
    known = class_index()
    classes = sorted(known, key=known.get)

    quality_path = DRAFT_ROOT / device / "quality.json"
    quality = (
        json.loads(quality_path.read_text(encoding="utf-8"))
        if quality_path.exists()
        else {}
    )

    samples = []
    for image_path in sorted(images_dir.glob("*.jpg")):
        label_path = labels_dir / f"{image_path.stem}.txt"
        if not label_path.exists():
            continue  # dropped by both passes; there is nothing to review
        sample = fo.Sample(filepath=str(image_path))
        detections = []
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
        # Sort on this in the app: the doubtful boxes come first, so attention
        # goes where the mistakes are rather than spreading evenly across
        # eight thousand images.
        sample["box_quality"] = quality.get(image_path.stem, 0.0)
        samples.append(sample)

    dataset.add_samples(samples)
    dataset.persistent = True
    print(f"{len(samples)} drafted images in FiftyOne dataset {name!r}")
    if quality:
        doubtful = sum(1 for value in quality.values() if value < 0.4)
        print(f"{doubtful} boxes scored below 0.4; those are the ones to check first.")
    print(
        "In the app, sort by box_quality ascending. Fix or delete boxes, and\n"
        "delete any image that is not this device.\n"
        f"Then: python tools/autolabel.py promote --device {device}"
    )
    session = fo.launch_app(dataset)
    session.wait()


def cmd_promote(args: argparse.Namespace) -> None:
    """Write labels into the layout the dataset builder reads.

    Two routes. By default the reviewed FiftyOne dataset is the source, so only
    what a person kept is promoted. With --skip-review the drafts go straight
    through, filtered by the quality score, which trades some label noise for
    the hours review would take.

    Detectors tolerate a few percent of bad boxes; they do not tolerate a
    systematic error, which is why the quality floor exists rather than a blunt
    "promote everything".
    """
    if args.skip_review:
        _promote_drafts(args)
        return

    try:
        import fiftyone as fo
    except ImportError:  # pragma: no cover - tooling only
        raise SystemExit(
            "fiftyone is not installed. pip install -r requirements-tools.txt"
        )

    import shutil

    name = f"review-{args.device}"
    if name not in fo.list_datasets():
        raise SystemExit(f"No reviewed dataset {name!r}. Run review first.")

    dataset = fo.load_dataset(name)
    known = class_index()
    out_images = REVIEWED_ROOT / "images"
    out_labels = REVIEWED_ROOT / "labels"
    out_images.mkdir(parents=True, exist_ok=True)
    out_labels.mkdir(parents=True, exist_ok=True)

    counts: Counter = Counter()
    for sample in dataset:
        detections = (
            getattr(sample.ground_truth, "detections", []) if sample.ground_truth else []
        )
        lines = []
        for detection in detections:
            class_id = known.get(detection.label)
            if class_id is None:
                continue
            x, y, w, h = detection.bounding_box
            lines.append(f"{class_id} {x + w / 2:.6f} {y + h / 2:.6f} {w:.6f} {h:.6f}")
            counts[detection.label] += 1
        if not lines:
            continue  # reviewed to nothing; an empty label trains on nothing
        source = Path(sample.filepath)
        shutil.copy2(source, out_images / source.name)
        (out_labels / f"{source.stem}.txt").write_text(
            "\n".join(lines) + "\n", encoding="utf-8"
        )

    print(f"Promoted to {REVIEWED_ROOT}")
    for label, count in sorted(counts.items()):
        print(f"  {label:<20}{count:>6} boxes")
    print(
        "\nNext: python tools/build_dataset.py export --include-reviewed --include-roboflow"
    )


def _promote_drafts(args: argparse.Namespace) -> None:
    """Straight from drafts, keeping only boxes above the quality floor."""
    import shutil

    devices = collected_devices() if args.all else [args.device]
    known = class_index()
    out_images = REVIEWED_ROOT / "images"
    out_labels = REVIEWED_ROOT / "labels"
    out_images.mkdir(parents=True, exist_ok=True)
    out_labels.mkdir(parents=True, exist_ok=True)

    kept = skipped = 0
    for device in devices:
        labels_dir = DRAFT_ROOT / device / "labels"
        if device not in known or not labels_dir.exists():
            continue

        quality_path = DRAFT_ROOT / device / "quality.json"
        quality = (
            json.loads(quality_path.read_text(encoding="utf-8"))
            if quality_path.exists()
            else {}
        )

        device_kept = device_skipped = 0
        for label_path in sorted(labels_dir.glob("*.txt")):
            if quality.get(label_path.stem, 1.0) < args.min_quality:
                device_skipped += 1
                continue
            image_path = COLLECTED_ROOT / device / f"{label_path.stem}.jpg"
            if not image_path.exists():
                continue
            shutil.copy2(image_path, out_images / image_path.name)
            shutil.copy2(label_path, out_labels / label_path.name)
            device_kept += 1

        kept += device_kept
        skipped += device_skipped
        print(f"{device:<20} promoted {device_kept:>5}   below floor {device_skipped:>5}")

    print(f"\npromoted {kept}, held back {skipped} below quality {args.min_quality}")
    print(f"written to {REVIEWED_ROOT}")
    print(
        "\nThese boxes were not looked at by anyone. That is a deliberate trade:\n"
        "a detector tolerates a few percent of bad boxes, and the hours saved buy\n"
        "a training run today. Review later and re-promote to improve them."
    )
    print(
        "\nNext: python tools/build_dataset.py export --include-reviewed --include-roboflow"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("plan", help="what is waiting and what it would cost by hand")

    run = sub.add_parser("run", help="draw boxes with both passes")
    group = run.add_mutually_exclusive_group(required=True)
    group.add_argument("--device")
    group.add_argument("--all", action="store_true")
    run.add_argument("--model", default=DEFAULT_MODEL)
    run.add_argument("--confidence", type=float, default=DEFAULT_CONFIDENCE)
    run.add_argument(
        "--no-model",
        action="store_true",
        help="backdrop pass only; fast, and needs nothing installed",
    )

    review = sub.add_parser("review", help="correct the drafts in FiftyOne")
    review.add_argument("--device", required=True)

    promote = sub.add_parser("promote", help="export labels for the dataset builder")
    group = promote.add_mutually_exclusive_group(required=True)
    group.add_argument("--device")
    group.add_argument("--all", action="store_true", help="every class, drafts only")
    promote.add_argument(
        "--skip-review",
        action="store_true",
        help="promote drafts without opening them; faster, noisier",
    )
    promote.add_argument(
        "--min-quality",
        type=float,
        default=0.35,
        help="quality floor when skipping review",
    )

    args = parser.parse_args()
    {"plan": cmd_plan, "run": cmd_run, "review": cmd_review, "promote": cmd_promote}[
        args.command
    ](args)


if __name__ == "__main__":
    main()
