# tools/find_wrong_device.py
"""Find images filed under one device that are actually another.

"Máy sấy" in Vietnamese is a clothes dryer, a hair dryer, a dish dryer and a
shoe dryer. The collector searched "máy sấy LG", "máy sấy 8kg", "máy sấy cũ" —
and Vietnamese marketplaces answered with hair dryers. Those images went into
the clothes_dryer class and taught the detector that a hair dryer is a tumble
dryer, which then carries a tumble dryer's lint-fire warning.

The screen uses COCO, not our own detector. COCO has a `hair drier` class, so a
stock model can say "this is a hair dryer" about an image our model has never
been able to describe at all. It is the only outside opinion available, and
outside is the point: our detector was trained on the contamination.

    python tools/find_wrong_device.py --device clothes_dryer --coco-class "hair drier"
    python tools/find_wrong_device.py --device clothes_dryer --coco-class "hair drier" --delete

Nothing is deleted without --delete, and what it deletes is the image together
with its label, because an image without a label teaches the detector that the
photograph contains nothing.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "datasets" / "fixhome"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def images_of(dataset: Path, index: int, splits: list[str]):
    """Every image whose labels are entirely this class, with its label path."""
    for split in splits:
        for label in sorted((dataset / "labels" / split).rglob("*.txt")):
            rows = [r for r in label.read_text(encoding="utf-8").splitlines() if r.strip()]
            if not rows or any(int(r.split()[0]) != index for r in rows):
                continue
            relative = label.relative_to(dataset / "labels" / split)
            for image in (dataset / "images" / split / relative.parent).glob(
                relative.stem + ".*"
            ):
                yield split, image, label


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", default=str(DATASET))
    parser.add_argument("--device", required=True, help="the class to screen")
    parser.add_argument(
        "--coco-class",
        required=True,
        help='what it must not be, in COCO\'s words, e.g. "hair drier"',
    )
    parser.add_argument("--model", default="yolo11s.pt", help="stock COCO weights")
    parser.add_argument(
        "--conf",
        type=float,
        default=0.25,
        help="confidence floor. Low on purpose: this produces a list to look at.",
    )
    parser.add_argument("--splits", default="train,val,test")
    parser.add_argument("--delete", action="store_true")
    parser.add_argument("--out", default="")
    args = parser.parse_args()

    from ultralytics import YOLO

    dataset = Path(args.dataset)
    names = yaml.safe_load((dataset / "data.yaml").read_text(encoding="utf-8"))["names"]
    index = next(i for i, n in names.items() if n == args.device)

    model = YOLO(args.model)
    target = next(
        i for i, n in model.model.names.items() if n == args.coco_class
    )

    rows = list(images_of(dataset, index, args.splits.split(",")))
    print(f"{len(rows)} ảnh thuần {args.device}, đang soi bằng {args.model}")

    flagged: list[tuple[str, Path, Path, float]] = []
    for n, (split, image, label) in enumerate(rows, start=1):
        result = model.predict(
            source=str(image), conf=args.conf, verbose=False, device="cpu"
        )[0]
        best = 0.0
        for box in result.boxes:
            if int(box.cls[0]) == target:
                best = max(best, float(box.conf[0]))
        if best:
            flagged.append((split, image, label, best))
        if n % 50 == 0:
            print(f"  {n}/{len(rows)}  đã gắn cờ {len(flagged)}", flush=True)

    flagged.sort(key=lambda r: -r[3])
    print(f"\n{len(flagged)} ảnh bị nghi là {args.coco_class}:")
    for split, image, _label, score in flagged[:40]:
        print(f"  {score:.2f}  {split}  {image.name}")

    if args.out:
        Path(args.out).write_text(
            "\n".join(str(image) for _s, image, _l, _c in flagged), encoding="utf-8"
        )
        print(f"\nDanh sách đầy đủ: {args.out}")

    if not args.delete:
        print("\nChưa xoá gì. Thêm --delete để xoá ảnh và nhãn đi cùng.")
        return

    for _split, image, label, _score in flagged:
        image.unlink(missing_ok=True)
        label.unlink(missing_ok=True)
    print(f"\nĐã xoá {len(flagged)} ảnh và nhãn đi cùng.")


if __name__ == "__main__":
    main()
