"""Download the surveyed Roboflow datasets and normalise them to our classes.

Each dataset uses its own class names and its own class ordering. Importing them
as-is would give the detector several classes meaning the same thing and one
class id meaning different things in different files, which is the quiet way to
train a model that looks fine in the logs and is useless in practice. So every
label is rewritten to this project's `device_type` ids, and anything not in the
map is dropped.

    set ROBOFLOW_API_KEY=...
    python tools/fetch_roboflow.py list
    python tools/fetch_roboflow.py download --all
    python tools/fetch_roboflow.py download --device water_heater

Output lands in datasets/roboflow/<device_type>/, in the same images and labels
layout the reviewed crawl produces, so `build_dataset.py export` can fold both
in through one code path.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent))

from roboflow_sources import SOURCES, RoboflowSource, coverage, sources_for  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = REPO_ROOT / "datasets" / "roboflow"
CACHE_ROOT = REPO_ROOT / "datasets" / "_roboflow_cache"


def _class_index() -> Dict[str, int]:
    import json

    catalog = json.loads(
        (REPO_ROOT / "app" / "data" / "device_catalog.json").read_text(encoding="utf-8")
    )
    devices = [d["device_type"] for d in catalog["devices"] if d.get("detector_class")]
    return {name: index for index, name in enumerate(devices)}


def cmd_list(args: argparse.Namespace) -> None:
    print(f"{'dataset':<52}{'images':>8}  covers")
    for source in SOURCES:
        images = str(source.images) if source.images else "?"
        print(f"{source.slug:<52}{images:>8}  {', '.join(source.covers)}")
        if source.note:
            print(f"{'':<52}{'':>8}  note: {source.note}")

    print("\nPer class, conservative estimate (not a measurement):")
    print(f"  {'class':<20}{'datasets':>9}{'est. images':>13}")
    for device_type, entry in sorted(
        coverage().items(), key=lambda kv: -kv[1]["estimate"]
    ):
        print(f"  {device_type:<20}{entry['datasets']:>9}{entry['estimate']:>13}")
    print(
        "  Multi-class sets are divided by their class count, so these are lower\n"
        "  bounds to plan against. Exact figures come from the download step."
    )
    print("\nAll sources are CC BY 4.0 and must be credited in the report.")


def _download(source: RoboflowSource, api_key: str) -> Optional[Path]:
    try:
        from roboflow import Roboflow
    except ImportError:  # pragma: no cover - tooling only
        raise SystemExit("roboflow is not installed. pip install -r requirements-tools.txt")

    destination = CACHE_ROOT / source.workspace / source.project
    if (destination / "data.yaml").exists():
        print(f"  cached: {destination}")
        return destination

    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        rf = Roboflow(api_key=api_key)
        project = rf.workspace(source.workspace).project(source.project)
        version = project.version(source.version)
        dataset = version.download("yolov8", location=str(destination), overwrite=True)
        return Path(dataset.location)
    except Exception as exc:  # noqa: BLE001 - third-party raises broadly
        # One unavailable dataset must not abort the others; several of these
        # are small community projects that can disappear or change version.
        print(f"  FAILED {source.slug}: {type(exc).__name__}: {exc}")
        return None


def _names_from_yaml(dataset_dir: Path) -> List[str]:
    """Read class names without pulling in a YAML dependency."""
    text = (dataset_dir / "data.yaml").read_text(encoding="utf-8")
    inside = text.split("names:", 1)[1]
    if "[" in inside.split("\n", 1)[0]:
        raw = inside.split("[", 1)[1].split("]", 1)[0]
        return [item.strip().strip("'\"") for item in raw.split(",") if item.strip()]

    names: List[str] = []
    for line in inside.splitlines()[1:]:
        stripped = line.strip()
        if not stripped.startswith("-") and ":" not in stripped:
            break
        if stripped.startswith("-"):
            names.append(stripped[1:].strip().strip("'\""))
        elif ":" in stripped:
            names.append(stripped.split(":", 1)[1].strip().strip("'\""))
        else:
            break
    return names


def _convert(source: RoboflowSource, dataset_dir: Path, class_index: Dict[str, int]) -> Counter:
    names = _names_from_yaml(dataset_dir)
    lowered = {name.lower(): name for name in names}
    remap: Dict[int, int] = {}
    remap_names: Dict[int, str] = {}

    for raw_name, device_type in source.class_map.items():
        actual = lowered.get(raw_name.lower())
        if actual is None or device_type not in class_index:
            continue
        remap[names.index(actual)] = class_index[device_type]
        remap_names[names.index(actual)] = device_type

    if not remap:
        print(f"  no usable classes; dataset declares {names}")
        return Counter()

    counts: Counter = Counter()
    for split in ("train", "valid", "test"):
        labels_dir = dataset_dir / split / "labels"
        images_dir = dataset_dir / split / "images"
        if not labels_dir.exists():
            continue
        for label_path in labels_dir.glob("*.txt"):
            kept: List[str] = []
            device_type = None
            for line in label_path.read_text(encoding="utf-8").splitlines():
                parts = line.split()
                if len(parts) < 5:
                    continue
                original = int(parts[0])
                if original not in remap:
                    continue  # a class this project does not model
                device_type = remap_names[original]
                kept.append(" ".join([str(remap[original])] + parts[1:5]))
            if not kept or device_type is None:
                continue

            image_path = next(
                (p for p in images_dir.glob(f"{label_path.stem}.*")), None
            )
            if image_path is None:
                continue

            out_images = OUT_ROOT / device_type / "images"
            out_labels = OUT_ROOT / device_type / "labels"
            out_images.mkdir(parents=True, exist_ok=True)
            out_labels.mkdir(parents=True, exist_ok=True)
            stem = f"{source.workspace}_{label_path.stem}"
            shutil.copy2(image_path, out_images / f"{stem}{image_path.suffix}")
            (out_labels / f"{stem}.txt").write_text("\n".join(kept) + "\n", encoding="utf-8")
            counts[device_type] += 1
    return counts


def cmd_download(args: argparse.Namespace) -> None:
    api_key = os.environ.get("ROBOFLOW_API_KEY", "").strip()
    if not api_key:
        raise SystemExit(
            "ROBOFLOW_API_KEY is not set. Create a free Roboflow account, then\n"
            "copy the key from Settings and export it before running this."
        )

    selected = SOURCES if args.all else sources_for(args.device)
    if not selected:
        raise SystemExit(f"No surveyed dataset covers {args.device!r}")

    class_index = _class_index()
    totals: Counter = Counter()
    for source in selected:
        print(f"\n{source.slug}")
        dataset_dir = _download(source, api_key)
        if dataset_dir is None:
            continue
        counts = _convert(source, dataset_dir, class_index)
        for device_type, count in counts.items():
            print(f"  {device_type:<20}{count:>6} images")
        totals.update(counts)

    print("\nImported per class:")
    for device_type, count in sorted(totals.items(), key=lambda kv: -kv[1]):
        print(f"  {device_type:<20}{count:>6}")
    print(f"\nOutput: {OUT_ROOT}")
    print("Next: python tools/build_dataset.py export --include-reviewed --include-roboflow")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="surveyed datasets and how much each class has")

    download = sub.add_parser("download", help="download and normalise to our classes")
    group = download.add_mutually_exclusive_group(required=True)
    group.add_argument("--all", action="store_true")
    group.add_argument("--device")

    args = parser.parse_args()
    {"list": cmd_list, "download": cmd_download}[args.command](args)


if __name__ == "__main__":
    main()
