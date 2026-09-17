# tools/compare_detectors.py
"""Put two detector evaluations side by side, class by class.

A new model is only better than the number it replaces, and the old number was
measured on a different split, before five devices were added and before the
air-conditioner cap. So both runs are measured with `eval_detector.py` on the
same split first, and this reads the two files it writes.

    python tools/eval_detector.py --weights <v1> --split test --out docs/v1.json
    python tools/eval_detector.py --weights <v2> --split test --out docs/v2.json
    python tools/compare_detectors.py docs/v1.json docs/v2.json

Two totals, not one, and this is the point of the tool. The older model has no
name for the five devices added since, so it cannot score on them at all;
comparing a model that knows twenty-two classes against one that knows
seventeen, across all twenty-two, credits the new one for a test the old one
was never given. The honest comparison is on the classes both models have, and
the new classes are reported separately as what was bought rather than as an
improvement.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _rows(path: Path) -> dict[str, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {row["class"]: row for row in data["classes"]}


def _total(rows: dict[str, dict], names) -> tuple[int, int, float]:
    n = sum(rows[c]["n"] for c in names if c in rows)
    correct = sum(rows[c]["correct"] for c in names if c in rows)
    return n, correct, (correct / n if n else 0.0)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument(
        "--regression",
        type=float,
        default=0.03,
        help=(
            "a drop of more than this on a class both models know is called "
            "out by name. Three points by default: below that is the noise of "
            "a few images changing sides on a class of eighty."
        ),
    )
    args = parser.parse_args()

    before, after = _rows(args.before), _rows(args.after)
    shared = sorted(before.keys() & after.keys())
    added = sorted(after.keys() - before.keys())
    lost = sorted(before.keys() - after.keys())

    print(f"trước: {args.before}")
    print(f"sau:   {args.after}\n")

    print(f"{'lớp':<20}{'trước':>9}{'sau':>9}{'đổi':>9}{'ảnh':>7}")
    print("-" * 54)
    regressions = []
    for name in sorted(shared, key=lambda c: after[c]["accuracy"] - before[c]["accuracy"]):
        was, now = before[name]["accuracy"], after[name]["accuracy"]
        delta = now - was
        print(
            f"{name:<20}{was:>8.1%}{now:>9.1%}{delta:>+9.1%}{after[name]['n']:>7}"
        )
        if delta < -args.regression:
            regressions.append((name, was, now, after[name].get("confused_with", {})))

    if added:
        print(f"\n{'lớp mới':<20}{'độ chính xác':>18}{'ảnh':>7}")
        print("-" * 54)
        for name in sorted(added, key=lambda c: -after[c]["accuracy"]):
            print(f"{name:<20}{after[name]['accuracy']:>17.1%}{after[name]['n']:>7}")

    if lost:
        print(f"\nCÓ LỚP BIẾN MẤT: {lost}")
        print("  Mô hình mới không còn nhận ra thứ mô hình cũ nhận ra được.")

    n_s, _c_s, acc_s = _total(after, shared)
    _was_n, _was_c, was_acc = _total(before, shared)
    print(f"\n{'':<20}{'trước':>9}{'sau':>9}{'đổi':>9}{'ảnh':>7}")
    print("-" * 54)
    print(
        f"{'chung 2 mô hình':<20}{was_acc:>8.1%}{acc_s:>9.1%}"
        f"{acc_s - was_acc:>+9.1%}{n_s:>7}"
    )
    if added:
        n_a, _c_a, acc_a = _total(after, added)
        print(f"{'chỉ mô hình mới':<20}{'—':>9}{acc_a:>9.1%}{'—':>9}{n_a:>7}")
        n_all, _c_all, acc_all = _total(after, after.keys())
        print(f"{'toàn bộ mô hình mới':<20}{'—':>9}{acc_all:>9.1%}{'—':>9}{n_all:>7}")

    print()
    if regressions:
        print(f"TỤT trên {len(regressions)} lớp mà cả hai mô hình đều biết:")
        for name, was, now, confused in regressions:
            worst = ", ".join(
                f"{k} {v}" for k, v in list(confused.items())[:3]
            )
            print(f"  {name}: {was:.1%} -> {now:.1%}   nhầm thành {worst}")
        print("\n  Một lớp tụt trong khi tổng số tăng vẫn là một lớp khách gặp.")
    else:
        print("Không lớp nào tụt quá ngưỡng.")


if __name__ == "__main__":
    main()
