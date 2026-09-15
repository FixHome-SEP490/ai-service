"""Crawl images for classes public datasets do not cover well.

Open Images supplies most classes with boxes already drawn. This fills the rest,
and more importantly fills the Vietnam-specific gap: public photos of sockets
and stoves are overwhelmingly American or European, and a detector trained only
on those misreads the hardware in a Vietnamese house.

    python tools/crawl_images.py plan
    python tools/crawl_images.py fetch --device power_outlet
    python tools/crawl_images.py fetch --all
    python tools/crawl_images.py stats

Crawled images arrive with no boxes, which is the expensive part. Run
`tools/autolabel.py` next to get draft boxes, then correct them rather than
drawing from scratch.

Search terms are Vietnamese on purpose. Querying "power outlet" returns the
hardware this project must not be trained on; querying "ổ cắm điện" returns the
hardware it will actually meet.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from collections import Counter
from pathlib import Path
from typing import Dict

from PIL import Image, UnidentifiedImageError

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = REPO_ROOT / "app" / "data" / "device_catalog.json"
RAW_ROOT = REPO_ROOT / "datasets" / "crawled"
MANIFEST_PATH = RAW_ROOT / "manifest.json"

MIN_EDGE = 300
"""Below this a photo carries too little detail to be worth annotating."""

MAX_EDGE = 1600

# Vietnamese queries and the quantity each class needs.
#
# Brand names are in the queries on purpose. A generic Vietnamese noun still
# returns a lot of international stock photography, but "o cam Panasonic" or
# "binh nong lanh Ferroli" returns the hardware actually sold and installed in
# Vietnamese homes, which is the hardware this detector will be shown.
#
# Two tiers. CRITICAL classes are the ones where public datasets are actively
# misleading: the photos exist, but they are of different hardware. SUPPLEMENT
# classes are adequately covered by Open Images; a smaller Vietnamese sample
# just narrows the gap between training photos and customer photos.
CRAWL_PLAN: Dict[str, dict] = {
    "power_outlet": {
        "target": 600,
        "tier": "critical",
        "queries": [
            "ổ cắm điện Panasonic",
            "ổ cắm điện Sino",
            "công tắc ổ cắm Điện Quang",
            "ổ cắm điện âm tường",
            "mặt công tắc ổ cắm gia đình",
            "ổ cắm điện đôi 3 chấu",
            "ổ cắm kéo dài Lioa",
            "ổ cắm điện bị cháy đen",
            "ổ cắm điện trong nhà",
        ],
        "why": "Open Images is mostly US NEMA and EU Schuko; Vietnam uses 2-pin universal",
    },
    "gas_stove": {
        "target": 400,
        "tier": "critical",
        "queries": [
            "bếp gas đôi Rinnai",
            "bếp gas Namilux",
            "bếp gas mini để bàn",
            "bếp gas Sunhouse",
            "bếp gas âm Malloca",
            "bếp gas hồng ngoại",
            "bếp gas bị nghẹt lửa",
        ],
        "why": "Open Images is Western built-in ranges; Vietnam uses countertop twin burners",
    },
    "water_heater": {
        "target": 400,
        "tier": "critical",
        "queries": [
            "bình nóng lạnh Ariston",
            "bình nóng lạnh Ferroli",
            "bình nóng lạnh Rossi treo tường",
            "máy nước nóng trực tiếp Panasonic",
            "máy nước nóng Centon",
            "máy nước nóng năng lượng mặt trời",
        ],
        "why": "no Open Images class at all",
    },
    "air_conditioner": {
        "target": 400,
        "tier": "critical",
        "queries": [
            "máy lạnh Daikin treo tường",
            "điều hòa Panasonic trong nhà",
            "máy lạnh Casper",
            "máy lạnh Aqua treo tường",
            "dàn lạnh điều hòa gia đình",
            "cục nóng điều hòa",
            "máy lạnh bị chảy nước",
        ],
        "why": "no Open Images class; supplements the Roboflow sets with Vietnamese wall units",
    },
    "washing_machine": {
        "target": 300,
        "tier": "critical",
        "queries": [
            "máy giặt Aqua cửa trên",
            "máy giặt Toshiba lồng đứng",
            "máy giặt Sanyo cửa trên",
            "máy giặt LG cửa trên",
            "máy giặt cửa trên gia đình",
        ],
        "why": "Open Images leans front-loading; Vietnam is largely top-loading",
    },
    "water_pipe": {
        "target": 250,
        "tier": "critical",
        "queries": [
            "ống nước PPR Bình Minh",
            "đường ống nước trong nhà",
            "ống nước bị rò rỉ",
            "mối nối ống nước bị rỉ sét",
        ],
        "why": "no Open Images class; feeds the VLM stage even without detection",
    },
    "electric_fan": {
        "target": 150,
        "tier": "supplement",
        "queries": [
            "quạt cây Asia",
            "quạt bàn Senko",
            "quạt hộp gia đình",
        ],
        "why": "covered by Open Images; Vietnamese brands narrow the domain gap",
    },
    "ceiling_fan": {
        "target": 150,
        "tier": "supplement",
        "queries": [
            "quạt trần Panasonic",
            "quạt trần gia đình Việt Nam",
        ],
        "why": "covered by Open Images; adds local ceiling mounts",
    },
    "kettle": {
        "target": 150,
        "tier": "supplement",
        "queries": [
            "ấm siêu tốc Sunhouse",
            "ấm đun nước điện gia đình",
        ],
        "why": "covered by Open Images; adds the local kettle shapes",
    },
    "faucet": {
        "target": 150,
        "tier": "supplement",
        "queries": [
            "vòi nước lavabo",
            "vòi rửa chén inox",
            "vòi nước bị rò rỉ",
        ],
        "why": "covered by Open Images; adds local fittings",
    },
    "light_bulb": {
        "target": 150,
        "tier": "supplement",
        "queries": [
            "bóng đèn LED Điện Quang",
            "bóng đèn LED âm trần",
            "đèn tuýp LED",
        ],
        "why": "covered by Open Images; adds local fixtures",
    },
    "refrigerator": {
        "target": 120,
        "tier": "supplement",
        "queries": ["tủ lạnh Aqua", "tủ lạnh Sanyo gia đình"],
        "why": "covered by Open Images; adds local models",
    },
    "microwave_oven": {
        "target": 120,
        "tier": "supplement",
        "queries": [
            "lò vi sóng Sharp",
            "lò vi sóng gia đình Việt Nam",
        ],
        "why": "covered by Open Images; also helps separate it from oven",
    },
    "oven": {
        "target": 120,
        "tier": "supplement",
        "queries": [
            "lò nướng điện Sunhouse",
            "lò nướng thùng gia đình",
        ],
        "why": "covered by Open Images; the oven and microwave pair confuses most easily",
    },
    "television": {
        "target": 120,
        "tier": "supplement",
        "queries": [
            "tivi treo tường phòng khách",
            "smart tivi gia đình",
        ],
        "why": "covered by Open Images; adds in-situ rather than product shots",
    },
    "sink": {
        "target": 120,
        "tier": "supplement",
        "queries": ["bồn rửa chén inox", "lavabo rửa mặt"],
        "why": "covered by Open Images; adds local fittings",
    },
    "toilet": {
        "target": 120,
        "tier": "supplement",
        "queries": ["bồn cầu Inax", "bồn cầu Viglacera"],
        "why": "covered by Open Images; adds local models",
    },
}


def load_catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def _device_names() -> Dict[str, str]:
    return {d["device_type"]: d["name_vi"] for d in load_catalog()["devices"]}


def cmd_plan(args: argparse.Namespace) -> None:
    names = _device_names()
    total = sum(entry["target"] for entry in CRAWL_PLAN.values())
    print(f"Classes needing crawled images: {len(CRAWL_PLAN)}   total target: {total}\n")
    for device_type, entry in sorted(
        CRAWL_PLAN.items(), key=lambda kv: (kv[1]["tier"] != "critical", kv[0])
    ):
        tier = entry["tier"].upper()
        print(f"[{tier}] {device_type} ({names.get(device_type, '?')}) — {entry['target']} images")
        print(f"  reason: {entry['why']}")
        print(f"  queries: {', '.join(entry['queries'])}\n")
    print(
        "Crawled images have no boxes. Budget review time, not drawing time:\n"
        "  python tools/autolabel.py run --device <name>"
    )


def _load_manifest() -> Dict[str, str]:
    if MANIFEST_PATH.exists():
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {}


def _save_manifest(manifest: Dict[str, str]) -> None:
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _normalise(path: Path, destination: Path) -> bool:
    """Re-encode to JPEG, drop images too small to annotate, cap the long edge.

    Search engines return thumbnails, logos and banners alongside real photos;
    the size floor removes most of that without a human looking at it.
    """
    try:
        with Image.open(path) as image:
            image = image.convert("RGB")
            if min(image.width, image.height) < MIN_EDGE:
                return False
            if max(image.width, image.height) > MAX_EDGE:
                image.thumbnail((MAX_EDGE, MAX_EDGE), Image.LANCZOS)
            destination.parent.mkdir(parents=True, exist_ok=True)
            image.save(destination, format="JPEG", quality=90)
            return True
    except (UnidentifiedImageError, OSError, ValueError):
        return False


def _crawl_one(device_type: str, entry: dict, engine: str, staging: Path) -> None:
    try:
        from icrawler.builtin import BingImageCrawler, GoogleImageCrawler
    except ImportError:  # pragma: no cover - tooling only
        raise SystemExit("icrawler is not installed. pip install -r requirements-tools.txt")

    crawler_cls = {"google": GoogleImageCrawler, "bing": BingImageCrawler}[engine]
    per_query = max(1, entry["target"] // len(entry["queries"]))

    for query in entry["queries"]:
        target_dir = staging / engine / query.replace(" ", "_")
        target_dir.mkdir(parents=True, exist_ok=True)
        print(f"  [{engine}] {query} -> up to {per_query}")
        crawler = crawler_cls(storage={"root_dir": str(target_dir)}, log_level=40)
        # Oversample: a good share of every result page is unusable, and the
        # size filter and hash dedup below will discard it.
        crawler.crawl(keyword=query, max_num=int(per_query * 1.5), min_size=(MIN_EDGE, MIN_EDGE))


def cmd_fetch(args: argparse.Namespace) -> None:
    if args.tier:
        devices = [d for d, e in CRAWL_PLAN.items() if e["tier"] == args.tier]
    elif args.all:
        devices = list(CRAWL_PLAN)
    else:
        devices = [args.device]
    if args.device and args.device not in CRAWL_PLAN:
        raise SystemExit(
            f"{args.device!r} is not in the crawl plan. Options: {', '.join(CRAWL_PLAN)}"
        )

    manifest = _load_manifest()
    for device_type in devices:
        entry = CRAWL_PLAN[device_type]
        print(f"\n{device_type}: target {entry['target']}")
        staging = RAW_ROOT / "_staging" / device_type
        if staging.exists():
            shutil.rmtree(staging)

        for engine in args.engines.split(","):
            _crawl_one(device_type, entry, engine.strip(), staging)

        out_dir = RAW_ROOT / device_type
        kept = duplicates = rejected = 0
        existing = sum(1 for _ in out_dir.glob("*.jpg")) if out_dir.exists() else 0

        for source in sorted(staging.rglob("*")):
            if not source.is_file():
                continue
            digest = _file_hash(source)
            if digest in manifest:
                duplicates += 1
                continue
            destination = out_dir / f"{device_type}_{digest[:12]}.jpg"
            if _normalise(source, destination):
                manifest[digest] = device_type
                kept += 1
            else:
                rejected += 1

        shutil.rmtree(staging, ignore_errors=True)
        print(
            f"  kept {kept}, duplicates {duplicates}, too small or unreadable {rejected}"
        )
        print(f"  total now {existing + kept} / {entry['target']}")

    _save_manifest(manifest)
    print(f"\nManifest: {MANIFEST_PATH}")
    print("Next: python tools/autolabel.py run --all")


def cmd_stats(args: argparse.Namespace) -> None:
    names = _device_names()
    counts: Counter = Counter()
    if RAW_ROOT.exists():
        for directory in RAW_ROOT.iterdir():
            if directory.is_dir() and not directory.name.startswith("_"):
                counts[directory.name] = sum(1 for _ in directory.glob("*.jpg"))

    print(f"{'class':<20}{'have':>8}{'target':>8}{'short':>8}   (* = critical)")
    for device_type, entry in CRAWL_PLAN.items():
        have = counts.get(device_type, 0)
        short = max(0, entry["target"] - have)
        mark = "*" if entry["tier"] == "critical" else " "
        print(f"{mark}{device_type:<19}{have:>8}{entry['target']:>8}{short:>8}")

    extra = set(counts) - set(CRAWL_PLAN)
    for device_type in sorted(extra):
        print(f"{device_type:<20}{counts[device_type]:>8}{'-':>8}{'-':>8}")

    total = sum(counts.values())
    print(f"\nTotal crawled: {total}")
    print(f"Classes tracked: {', '.join(names.get(d, d) for d in CRAWL_PLAN)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("plan", help="what needs crawling, how many, and why")

    fetch = sub.add_parser("fetch", help="crawl, deduplicate and normalise")
    group = fetch.add_mutually_exclusive_group(required=True)
    group.add_argument("--device", help="one class from the plan")
    group.add_argument("--all", action="store_true", help="every class in the plan")
    group.add_argument(
        "--tier",
        choices=["critical", "supplement"],
        help="critical is where public data is actively misleading; do it first",
    )
    fetch.add_argument(
        "--engines",
        default="google,bing",
        help="comma separated; two engines overlap less than one engine twice",
    )

    sub.add_parser("stats", help="how far each class is from its target")

    args = parser.parse_args()
    {"plan": cmd_plan, "fetch": cmd_fetch, "stats": cmd_stats}[args.command](args)


if __name__ == "__main__":
    main()
