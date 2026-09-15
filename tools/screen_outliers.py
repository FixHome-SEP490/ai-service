"""Find images that do not look like the rest of their class.

Twenty people collected these. Some photographed a copper pipe and filed it
under air conditioner, some caught an induction hob among the gas stoves, and
some pictures are of a room with the device barely in it. Every one of those
teaches the detector that its class contains something it does not.

The screen is deliberately blunt: describe each image with a small feature
vector, find the centre of each class, and flag the images furthest from it.
That does not decide anything. It produces a review queue ordered so the worst
offenders come first, because the useful property here is not accuracy but
ordering — a person skimming a hundred flagged images finds the mistakes in
minutes, where skimming twenty thousand finds nothing.

    python tools/screen_outliers.py scan
    python tools/screen_outliers.py review --device gas_stove
    python tools/screen_outliers.py quarantine --device gas_stove --top 50

Nothing is deleted. `quarantine` moves files aside so a wrong call costs a move
back rather than a lost photograph.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from PIL import Image, UnidentifiedImageError

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[1]
COLLECTED_ROOT = REPO_ROOT / "datasets" / "collected"
QUARANTINE_ROOT = REPO_ROOT / "datasets" / "quarantine"
REPORT_PATH = REPO_ROOT / "datasets" / "outliers.json"

GRID = 4
"""Cells per side for the colour signature. Four is coarse on purpose: finer
grids start separating a socket photographed left of centre from the same
socket photographed right of centre, which is not the difference being looked
for."""


def _signature(path: Path) -> List[float]:
    """A small, order-dependent description of the image.

    Mean colour per cell of a 4x4 grid, plus overall brightness and contrast.
    Crude compared to a learned embedding, and chosen for it: this runs on a
    laptop over twenty thousand images before any GPU is rented, and it only
    has to be good enough to sort obvious mistakes to the top.
    """
    with Image.open(path) as image:
        small = image.convert("RGB").resize((GRID * 8, GRID * 8), Image.BILINEAR)

    pixels = list(small.getdata())
    width = GRID * 8
    cell = 8

    features: List[float] = []
    for row in range(GRID):
        for column in range(GRID):
            reds = greens = blues = 0
            for y in range(row * cell, (row + 1) * cell):
                base = y * width
                for x in range(column * cell, (column + 1) * cell):
                    r, g, b = pixels[base + x]
                    reds += r
                    greens += g
                    blues += b
            count = cell * cell
            features += [reds / count / 255, greens / count / 255, blues / count / 255]

    grey = [(r + g + b) / 3 for r, g, b in pixels]
    mean = sum(grey) / len(grey)
    variance = sum((v - mean) ** 2 for v in grey) / len(grey)
    features += [mean / 255, math.sqrt(variance) / 255]
    return features


def _centre(vectors: Sequence[Sequence[float]]) -> List[float]:
    size = len(vectors[0])
    return [sum(v[i] for v in vectors) / len(vectors) for i in range(size)]


def _distance(a: Sequence[float], b: Sequence[float]) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def _scan_device(device_dir: Path) -> List[Tuple[float, str]]:
    images = sorted(device_dir.glob("*.jpg"))
    if len(images) < 20:
        # Below this the centre is pulled around by whatever is there, and the
        # distances say more about the sample than about any image in it.
        return []

    vectors: Dict[str, List[float]] = {}
    for path in images:
        try:
            vectors[path.name] = _signature(path)
        except (UnidentifiedImageError, OSError, ValueError):
            vectors[path.name] = []

    usable = {name: v for name, v in vectors.items() if v}
    if len(usable) < 20:
        return []

    centre = _centre(list(usable.values()))
    scored = [(_distance(v, centre), name) for name, v in usable.items()]

    # Report in standard deviations, so a threshold means the same thing for a
    # visually uniform class as for a varied one.
    distances = [d for d, _ in scored]
    mean = sum(distances) / len(distances)
    spread = math.sqrt(sum((d - mean) ** 2 for d in distances) / len(distances)) or 1e-9

    scored = [((d - mean) / spread, name) for d, name in scored]
    scored.sort(reverse=True)
    return scored


def cmd_scan(args: argparse.Namespace) -> None:
    if not COLLECTED_ROOT.exists():
        raise SystemExit(
            f"No collected images at {COLLECTED_ROOT}.\n"
            "Import them first: python tools/collect_images.py import-tree --from <folder>"
        )

    report: Dict[str, List[dict]] = defaultdict(list)
    print(f"{'class':<20}{'images':>8}{'flagged':>9}{'worst z':>9}")

    for device_dir in sorted(d for d in COLLECTED_ROOT.iterdir() if d.is_dir()):
        scored = _scan_device(device_dir)
        if not scored:
            count = sum(1 for _ in device_dir.glob("*.jpg"))
            print(f"{device_dir.name:<20}{count:>8}{'-':>9}{'too few':>9}")
            continue

        flagged = [(z, name) for z, name in scored if z >= args.threshold]
        report[device_dir.name] = [
            {"file": name, "z": round(z, 2)} for z, name in flagged
        ]
        print(
            f"{device_dir.name:<20}{len(scored):>8}{len(flagged):>9}"
            f"{scored[0][0]:>9.1f}"
        )

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(
            {"threshold": args.threshold, "flagged": report}, ensure_ascii=False, indent=2
        ),
        encoding="utf-8",
    )

    total = sum(len(v) for v in report.values())
    print(f"\n{total} images flagged at z >= {args.threshold}, written to {REPORT_PATH}")
    print(
        "\nFlagged means 'unlike its classmates', not 'wrong'. A correct photo of\n"
        "an unusual model lands here too. Look before removing:\n"
        "  python tools/screen_outliers.py review --device <name>"
    )


def cmd_review(args: argparse.Namespace) -> None:
    if not REPORT_PATH.exists():
        raise SystemExit("No report yet. Run: python tools/screen_outliers.py scan")

    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    flagged = report["flagged"].get(args.device)
    if not flagged:
        print(f"{args.device}: nothing flagged.")
        return

    folder = COLLECTED_ROOT / args.device
    print(f"{args.device}: {len(flagged)} flagged, worst first\n")
    for entry in flagged[: args.limit]:
        print(f"  z={entry['z']:>5}  {folder / entry['file']}")

    print(
        f"\nOpen the folder and look at these. To set the worst ones aside:\n"
        f"  python tools/screen_outliers.py quarantine --device {args.device} --top N"
    )


def cmd_quarantine(args: argparse.Namespace) -> None:
    if not REPORT_PATH.exists():
        raise SystemExit("No report yet. Run: python tools/screen_outliers.py scan")

    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    flagged = report["flagged"].get(args.device, [])
    if not flagged:
        print(f"{args.device}: nothing flagged.")
        return

    source = COLLECTED_ROOT / args.device
    destination = QUARANTINE_ROOT / args.device
    destination.mkdir(parents=True, exist_ok=True)

    moved = 0
    for entry in flagged[: args.top]:
        path = source / entry["file"]
        if path.exists():
            shutil.move(str(path), str(destination / entry["file"]))
            moved += 1

    print(f"Moved {moved} images to {destination}")
    print(
        "Nothing was deleted. Move any back if the call was wrong:\n"
        f"  move {destination}\\<file> {source}\\"
    )


def cmd_restore(args: argparse.Namespace) -> None:
    source = QUARANTINE_ROOT / args.device
    if not source.is_dir():
        raise SystemExit(f"Nothing quarantined for {args.device}")

    destination = COLLECTED_ROOT / args.device
    destination.mkdir(parents=True, exist_ok=True)
    moved = 0
    for path in source.glob("*.jpg"):
        shutil.move(str(path), str(destination / path.name))
        moved += 1
    print(f"Restored {moved} images to {destination}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="rank every image by how unlike its class it is")
    scan.add_argument(
        "--threshold",
        type=float,
        default=2.5,
        help="standard deviations from the class centre before flagging",
    )

    review = sub.add_parser("review", help="list what was flagged, worst first")
    review.add_argument("--device", required=True)
    review.add_argument("--limit", type=int, default=40)

    quarantine = sub.add_parser("quarantine", help="move the worst aside, not delete")
    quarantine.add_argument("--device", required=True)
    quarantine.add_argument("--top", type=int, default=50)

    restore = sub.add_parser("restore", help="put quarantined images back")
    restore.add_argument("--device", required=True)

    args = parser.parse_args()
    {
        "scan": cmd_scan,
        "review": cmd_review,
        "quarantine": cmd_quarantine,
        "restore": cmd_restore,
    }[args.command](args)


if __name__ == "__main__":
    main()
