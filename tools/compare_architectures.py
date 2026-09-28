# tools/compare_architectures.py
"""Score several detector architectures trained on the same data, on one machine.

The model-selection runs differ in one thing only, the architecture. Same
dataset, same persisted split, same seed, same image size, same epochs, same
batch; `rent_gpu.py train --model` swaps the starting weights and nothing else.
This reads the weights those runs published and scores every one of them here,
on the same test split, with the same Ultralytics version the runs trained
with, so that no number in the table came from a different place than its
neighbours.

    python tools/compare_architectures.py \
        --run select-yolo11s-e30 --run select-yolov10s-e30 --run select-rtdetr-l-e30

Four things per model, because accuracy alone chooses nothing:

    map50, map50_95   the detection metrics, box and name together
    top1              the product metric: does the most confident box name the
                      right appliance, scored exactly as eval_detector.py does
    params, gflops    what it costs to hold and to run
    cpu_ms            median time per photograph on this machine's CPU, after
                      warm-up; the same machine for every model, so the column
                      compares models rather than machines

GPU latency is not measured here, because this machine has no CUDA build of
torch. It comes from each run's own test pass on the rented card, recorded in
that run's log, and every run rented the same card model. Pass the saved logs
with --log RUN=PATH and the "Speed:" line of the final test pass is read out of
each; the logs themselves are copied beside the results, so the figure can be
checked against the line it came from.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import statistics
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET = REPO_ROOT / "datasets" / "fixhome"
WEIGHTS_ROOT = REPO_ROOT / "weights" / "model-selection"


def _load(weights: Path):
    from ultralytics import RTDETR, YOLO

    return RTDETR(str(weights)) if "rtdetr" in weights.as_posix() else YOLO(str(weights))


def _absolute_yaml() -> Path:
    """data.yaml ships with a relative root, which Ultralytics resolves against
    its own settings directory rather than the file. Point it here."""
    lines = (DATASET / "data.yaml").read_text(encoding="utf-8").splitlines()
    fixed = [f"path: {DATASET.as_posix()}" if line.startswith("path:") else line
             for line in lines]
    handle = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8")
    handle.write("\n".join(fixed) + "\n")
    handle.close()
    return Path(handle.name)


def _truth_of(image: Path, names: List[str]):
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


def _gpu_speed(log: Path) -> Optional[dict]:
    """The last Speed line in a training log: the test pass on the rented GPU."""
    text = log.read_text(encoding="utf-8", errors="replace")
    found = list(re.finditer(r"Speed:\s*([\d.]+)ms preprocess,\s*([\d.]+)ms inference,"
                             r".*?([\d.]+)ms postprocess", text))
    if not found:
        return None
    pre, infer, post = (float(g) for g in found[-1].groups())
    gpu = re.search(r"GPU:\s*(.+)", text)
    return {"preprocess_ms": pre, "inference_ms": infer, "postprocess_ms": post,
            "total_ms": round(pre + infer + post, 2),
            "gpu": gpu.group(1).strip() if gpu else None}


def _counts(model) -> tuple:
    """Parameters and GFLOPs of the graph that actually runs at inference.

    Counted on a fused copy: YOLOv10 carries a second, one-to-many head that
    exists only to train and is dropped on fusing, so counting the unfused
    model would bill it for about 3 GFLOPs it never spends. model.info() is not
    used because it returns nothing when asked to be quiet.
    """
    import copy

    from ultralytics.utils.torch_utils import get_flops, get_num_params

    fused = copy.deepcopy(model.model).fuse(verbose=False)
    return get_num_params(fused), get_flops(fused, 640)


def _score(run: str, yaml: Path, latency_images: int) -> dict:
    weights = WEIGHTS_ROOT / run / "weights" / "best.pt"
    if not weights.exists():
        raise SystemExit(f"{weights} is missing. Download the run first (see the README).")
    model = _load(weights)
    names = [model.names[i] for i in sorted(model.names)]
    print(f"\n== {run}")

    params, gflops = _counts(model)

    metrics = model.val(data=str(yaml), split="test", device="cpu", batch=8,
                        plots=False, verbose=False)
    map50, map50_95 = float(metrics.box.map50), float(metrics.box.map)
    precision, recall = float(metrics.box.mp), float(metrics.box.mr)
    print(f"   mAP50 {map50:.3f}   mAP50-95 {map50_95:.3f}   P {precision:.3f}   R {recall:.3f}")

    images = sorted((DATASET / "images" / "test").rglob("*.jpg"))
    total, correct, missed = Counter(), Counter(), Counter()
    for image in images:
        truth = _truth_of(image, names)
        if truth is None:
            continue
        total[truth] += 1
        boxes = model.predict(str(image), conf=0.25, device="cpu", verbose=False)[0].boxes
        if len(boxes) == 0:
            missed[truth] += 1
            continue
        best = max(boxes, key=lambda b: float(b.conf[0]))
        if names[int(best.cls[0])] == truth:
            correct[truth] += 1
    scorable, hit = sum(total.values()), sum(correct.values())
    print(f"   top-1 appliance {hit}/{scorable} = {hit / scorable:.1%}   no box {sum(missed.values())}")

    sample = images[:latency_images]
    for image in sample[:5]:
        model.predict(str(image), device="cpu", verbose=False)
    timings = []
    for image in sample:
        started = time.perf_counter()
        model.predict(str(image), device="cpu", verbose=False)
        timings.append((time.perf_counter() - started) * 1000)
    cpu_ms = statistics.median(timings)
    print(f"   {params / 1e6:.1f}M params   {gflops:.1f} GFLOPs   CPU {cpu_ms:.0f} ms/photo")

    return {
        "run": run,
        "architecture": model.model.__class__.__name__,
        "map50": round(map50, 4),
        "map50_95": round(map50_95, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "top1": round(hit / scorable, 4),
        "top1_correct": hit,
        "scorable": scorable,
        "no_box": sum(missed.values()),
        "params_m": round(params / 1e6, 2),
        "gflops": round(gflops, 1),
        "cpu_ms_median": round(cpu_ms, 1),
        "cpu_latency_images": len(sample),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="append", required=True,
                        help="run name as published, e.g. select-yolo11s-e30")
    parser.add_argument("--latency-images", type=int, default=100)
    parser.add_argument("--log", action="append", default=[],
                        help="RUN=PATH to a saved training log, for the GPU speed line")
    parser.add_argument("--out", default="docs/model-selection/detectors.json")
    args = parser.parse_args()

    import platform
    import ultralytics

    logs = dict(item.split("=", 1) for item in args.log)
    log_dir = REPO_ROOT / "docs" / "model-selection" / "logs"
    yaml = _absolute_yaml()
    rows = []
    for run in args.run:
        row = _score(run, yaml, args.latency_images)
        if run in logs:
            source = Path(logs[run])
            row["gpu_speed"] = _gpu_speed(source)
            log_dir.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, log_dir / f"{run}.log")
            print(f"   GPU {row['gpu_speed']}")
        rows.append(row)
    out = REPO_ROOT / args.out
    # Runs finish hours apart; a run scored earlier is kept unless rescored now.
    if out.exists():
        scored = {row["run"] for row in rows}
        earlier = json.loads(out.read_text(encoding="utf-8")).get("models", [])
        rows = [row for row in earlier if row["run"] not in scored] + rows
    report = {
        "conditions": {
            "dataset": "phamductoan3883/fixhome-devices",
            "split": "test, persisted in datasets/split.json, seed 20260915",
            "scored_on": f"{platform.processor() or platform.machine()}, CPU, "
                         f"ultralytics {ultralytics.__version__}",
            "same_for_every_run": "dataset, split, seed, 640 px, 30 epochs, batch 16",
        },
        "models": rows,
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    print(f"\n{'run':<24}{'mAP50':>7}{'mAP50-95':>10}{'top-1':>8}{'params':>8}{'GFLOPs':>8}{'CPU ms':>8}")
    for row in rows:
        print(f"{row['run']:<24}{row['map50']:>7.3f}{row['map50_95']:>10.3f}{row['top1']:>8.1%}"
              f"{row['params_m']:>7.1f}M{row['gflops']:>8.1f}{row['cpu_ms_median']:>8.0f}")
    print(f"\nwritten to {out.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
