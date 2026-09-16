"""Measure the detector the way the product is judged, not the way training is.

Training reports mAP, which grades the box as well as the name and at ten
tightening thresholds. It is the right measure for a detector and the wrong one
for this product: a customer photographs their broken appliance and wants to
know the system recognised it. Nobody checks whether the rectangle hugged the
edge.

So this asks a simpler question. For each test photograph, does the detector's
highest-confidence answer name the right appliance? That single number is the
one worth quoting to anyone, and it is much higher than mAP, which is why the
two must never be confused when reporting.

    python tools/eval_detector.py --weights weights/detector-v1/.../best.pt

Per class, because the average hides everything. One class with ten thousand
photographs can carry a mean that six starved classes are dragging down.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET = REPO_ROOT / "datasets" / "fixhome"


def _truth_of(image: Path, names: List[str]) -> Optional[str]:
    """The class written in the label file beside the image.

    Only the first box: these are single-object photographs, and an image whose
    label lists two devices cannot be scored as one answer.
    """
    label = Path(str(image).replace("images", "labels")).with_suffix(".txt")
    if not label.exists():
        return None
    lines = [line for line in label.read_text().splitlines() if line.strip()]
    if len(lines) != 1:
        return None
    try:
        return names[int(lines[0].split()[0])]
    except (ValueError, IndexError):
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", required=True)
    parser.add_argument("--split", default="test")
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--limit", type=int, default=0, help="0 means every image")
    parser.add_argument("--out", help="write the table to this JSON file")
    args = parser.parse_args()

    from ultralytics import YOLO

    model = YOLO(args.weights)
    names = [model.names[i] for i in sorted(model.names)]

    images = sorted((DATASET / "images" / args.split).rglob("*.jpg"))
    if args.limit:
        images = images[: args.limit]
    if not images:
        raise SystemExit(f"No images under {DATASET / 'images' / args.split}")

    print(f"{len(images)} images, confidence floor {args.conf}\n")

    total = Counter()
    correct = Counter()
    missed = Counter()
    confused: Dict[str, Counter] = defaultdict(Counter)

    for index, image in enumerate(images, start=1):
        truth = _truth_of(image, names)
        if truth is None:
            continue
        total[truth] += 1

        result = model.predict(str(image), conf=args.conf, verbose=False)
        boxes = result[0].boxes if result else []
        if len(boxes) == 0:
            # Nothing found at all is a different failure from naming the wrong
            # appliance: one asks the customer for a better photo, the other
            # confidently sends them to the wrong service.
            missed[truth] += 1
            continue

        best = max(boxes, key=lambda b: float(b.conf[0]))
        predicted = names[int(best.cls[0])]
        if predicted == truth:
            correct[truth] += 1
        else:
            confused[truth][predicted] += 1

        if index % 200 == 0:
            print(f"  ...{index}/{len(images)}")

    rows = []
    print(f"\n{'class':<20}{'n':>6}{'correct':>9}{'missed':>8}{'wrong':>7}  accuracy")
    for name in sorted(total, key=lambda c: -total[c]):
        n = total[name]
        hit = correct[name]
        gone = missed[name]
        wrong = n - hit - gone
        rows.append(
            {
                "class": name,
                "n": n,
                "correct": hit,
                "missed": gone,
                "wrong": wrong,
                "accuracy": round(hit / n, 4),
                "confused_with": dict(confused[name].most_common(3)),
            }
        )
        print(f"{name:<20}{n:>6}{hit:>9}{gone:>8}{wrong:>7}  {hit / n:>7.1%}")

    n_all = sum(total.values())
    hit_all = sum(correct.values())
    print(f"\n{'overall':<20}{n_all:>6}{hit_all:>9}{sum(missed.values()):>8}"
          f"{n_all - hit_all - sum(missed.values()):>7}  {hit_all / n_all:>7.1%}")

    worst = [r for r in rows if r["accuracy"] < 0.75]
    if worst:
        print("\nBelow 75%, and what each was mistaken for:")
        for row in sorted(worst, key=lambda r: r["accuracy"]):
            pairs = ", ".join(f"{k} {v}" for k, v in row["confused_with"].items())
            print(f"  {row['class']:<20}{row['accuracy']:>6.1%}   {pairs or 'nothing found'}")

    if args.out:
        Path(args.out).write_text(
            json.dumps(
                {"weights": args.weights, "split": args.split, "classes": rows},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"\nWritten to {args.out}")


if __name__ == "__main__":
    main()
