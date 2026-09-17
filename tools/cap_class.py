# tools/cap_class.py
"""Trim one over-represented class out of the train split.

air_conditioner arrived with 9,999 boxes, a third of the whole set and
thirty-two times the smallest class. It is also the class the detector is best
at: 97% on the held-out test set, with 461 test images behind that number.
Every extra air-conditioner image buys nothing and costs the other twenty-one
classes attention in every epoch, plus a proportional share of the GPU bill.

Only images whose labels are *entirely* that class are removed, so no other
class loses a box. Only the train split is touched: val and test stay exactly
as they were, which is what makes the next run's numbers comparable to the last
one's.

Deterministic: images are removed in sorted order, so two runs of this script
produce the same dataset.

    python tools/cap_class.py --class-name air_conditioner --max-boxes 2500
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "datasets" / "fixhome"


def load_names(dataset: Path) -> dict:
    data = yaml.safe_load((dataset / "data.yaml").read_text(encoding="utf-8"))
    return {name: index for index, name in data["names"].items()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default=str(DATASET))
    parser.add_argument("--class-name", required=True)
    parser.add_argument("--max-boxes", type=int, required=True)
    parser.add_argument("--split", default="train")
    parser.add_argument(
        "--dry-run", action="store_true", help="say what would go, delete nothing"
    )
    args = parser.parse_args()

    dataset = Path(args.dataset)
    index = load_names(dataset)[args.class_name]
    labels = sorted((dataset / "labels" / args.split).rglob("*.txt"))

    total = 0
    pure: list[Path] = []
    for path in labels:
        rows = [r for r in path.read_text(encoding="utf-8").splitlines() if r.strip()]
        classes = {int(r.split()[0]) for r in rows}
        count = sum(1 for r in rows if int(r.split()[0]) == index)
        total += count
        if count and classes == {index}:
            pure.append(path)

    if total <= args.max_boxes:
        print(f"{args.class_name}: {total} boxes, already under {args.max_boxes}")
        return

    removed_boxes = 0
    removed_files = 0
    for path in pure:
        if total - removed_boxes <= args.max_boxes:
            break
        rows = [r for r in path.read_text(encoding="utf-8").splitlines() if r.strip()]
        if args.dry_run:
            removed_boxes += len(rows)
            removed_files += 1
            continue
        # The image sits under images/<split>/<same relative path>, and an image
        # without its label is worse than no image: YOLO reads it as a photo
        # containing nothing, which teaches the opposite of what is wanted.
        relative = path.relative_to(dataset / "labels" / args.split)
        for image in (dataset / "images" / args.split / relative.parent).glob(
            relative.stem + ".*"
        ):
            image.unlink()
        path.unlink()
        removed_boxes += len(rows)
        removed_files += 1

    verb = "would remove" if args.dry_run else "removed"
    print(
        f"{args.class_name}: {total} boxes in {args.split}; "
        f"{verb} {removed_files} images ({removed_boxes} boxes), "
        f"leaving {total - removed_boxes}"
    )


if __name__ == "__main__":
    main()
