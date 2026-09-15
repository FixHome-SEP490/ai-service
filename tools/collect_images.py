"""Collect the class images public datasets cover badly.

Replaces an earlier crawler built on `icrawler`. That approach was removed after
its output was inspected rather than counted: for the query "ổ cắm điện
Panasonic" it returned an architecture-thesis poster and a plate of fried
chicken, and for the English control "electrical wall socket" it returned model
aircraft box art. The cause is not the Vietnamese text. Google's image markup no
longer parses at all, and Bing serves unrelated results to non-browser clients,
which a scripted crawler cannot tell apart from real ones. A crawler that
silently returns the wrong images is worse than none, because the mistake only
surfaces after training.

Two paths remain, and the first is the one to use.

    python tools/collect_images.py plan
    python tools/collect_images.py import --device power_outlet --from D:/photos/sockets
    python tools/collect_images.py fetch --device power_outlet   # needs SERPER_API_KEY
    python tools/collect_images.py stats

`import` ingests photographs taken directly. For the classes that need help this
is not a fallback, it is the better data: a socket photographed in a real
hallway under real light is exactly the domain the detector is deployed into,
while a catalogue photograph of the same socket is not.

`fetch` uses a paid search API, which does return real results. It is optional,
it costs money, and what it returns is still product photography.

Both paths share the same intake: content-hash deduplication against a
persistent manifest, re-encoding, and a size floor.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

from PIL import Image, UnidentifiedImageError

# iPhones save HEIC by default and Pillow cannot read it unaided, so without
# this a folder of phone photos is silently counted as unreadable — the worst
# possible failure for someone who just spent an afternoon taking them.
try:
    import pillow_heif

    pillow_heif.register_heif_opener()
    HEIF_AVAILABLE = True
except ImportError:  # pragma: no cover - optional dependency
    HEIF_AVAILABLE = False

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = REPO_ROOT / "app" / "data" / "device_catalog.json"
RAW_ROOT = REPO_ROOT / "datasets" / "collected"
MANIFEST_PATH = RAW_ROOT / "manifest.json"

MIN_EDGE = 300
"""Below this a photo carries too little detail to be worth annotating."""

MAX_EDGE = 1600

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".heic"}

# Queries stay Vietnamese and carry local brand names: a generic noun returns
# international stock photography, while a brand sold here returns the hardware
# actually installed in local homes. Only `fetch` uses them.
COLLECTION_PLAN: Dict[str, dict] = {
    "power_outlet": {
        "target": 600,
        "tier": "critical",
        "queries": [
            "ổ cắm điện Panasonic",
            "ổ cắm điện Sino",
            "công tắc ổ cắm Điện Quang",
            "ổ cắm điện âm tường",
            "ổ cắm điện bị cháy đen",
        ],
        "why": "Open Images is US NEMA and EU Schuko; Vietnam uses 2-pin universal",
    },
    "gas_stove": {
        "target": 400,
        "tier": "critical",
        "queries": [
            "bếp gas đôi Rinnai",
            "bếp gas Namilux",
            "bếp gas mini để bàn",
            "bếp gas Sunhouse",
        ],
        "why": "Open Images is Western built-in ranges; Vietnam uses countertop burners",
    },
    "water_heater": {
        "target": 400,
        "tier": "critical",
        "queries": [
            "bình nóng lạnh Ariston",
            "bình nóng lạnh Ferroli",
            "máy nước nóng trực tiếp Panasonic",
        ],
        "why": "no Open Images class; Roboflow covers it only partially",
    },
    "air_conditioner": {
        "target": 200,
        "tier": "supplement",
        "queries": ["máy lạnh Daikin treo tường", "dàn lạnh điều hòa gia đình"],
        "why": "Roboflow already supplies volume; this only narrows the domain gap",
    },
    "washing_machine": {
        "target": 300,
        "tier": "critical",
        "queries": ["máy giặt Aqua cửa trên", "máy giặt Toshiba lồng đứng"],
        "why": "Open Images leans front-loading; Vietnam is largely top-loading",
    },
    "water_pipe": {
        "target": 250,
        "tier": "critical",
        "queries": ["ống nước bị rò rỉ", "đường ống nước trong nhà"],
        "why": "no Open Images class",
    },
    "electric_fan": {
        "target": 150,
        "tier": "supplement",
        "queries": ["quạt cây Asia", "quạt bàn Senko"],
        "why": "covered by Open Images; local brands narrow the domain gap",
    },
}


def load_catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def _device_names() -> Dict[str, str]:
    return {d["device_type"]: d["name_vi"] for d in load_catalog()["devices"]}


def cmd_plan(args: argparse.Namespace) -> None:
    names = _device_names()
    total = sum(entry["target"] for entry in COLLECTION_PLAN.values())
    print(f"Classes needing extra images: {len(COLLECTION_PLAN)}   total target: {total}\n")
    for device_type, entry in sorted(
        COLLECTION_PLAN.items(), key=lambda kv: (kv[1]["tier"] != "critical", kv[0])
    ):
        print(
            f"[{entry['tier'].upper()}] {device_type} "
            f"({names.get(device_type, '?')}) — {entry['target']} images"
        )
        print(f"  reason: {entry['why']}")
        if entry["queries"]:
            print(f"  queries: {', '.join(entry['queries'])}")
        print()
    print(
        "Photographs you take yourself are the better source for every class\n"
        "listed as critical, and they are the only source that fixes the gap\n"
        "between catalogue photos and the photos customers actually send.\n\n"
        "  python tools/collect_images.py import --device power_outlet --from <folder>"
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


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _normalise(data: bytes, destination: Path) -> bool:
    """Re-encode to JPEG, reject anything too small, cap the long edge."""
    try:
        from io import BytesIO

        with Image.open(BytesIO(data)) as image:
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


def _ingest(device_type: str, payloads, manifest: Dict[str, str]) -> Counter:
    """Deduplicate, normalise and file a stream of (name, bytes) pairs."""
    result: Counter = Counter()
    out_dir = RAW_ROOT / device_type
    for _name, data in payloads:
        digest = _digest(data)
        if digest in manifest:
            result["duplicate"] += 1
            continue
        destination = out_dir / f"{device_type}_{digest[:12]}.jpg"
        if _normalise(data, destination):
            manifest[digest] = device_type
            result["kept"] += 1
        else:
            result["rejected"] += 1
    return result


def cmd_import(args: argparse.Namespace) -> None:
    device_type = args.device
    if device_type not in _device_names():
        raise SystemExit(f"{device_type!r} is not in the device catalog")

    source = Path(args.source).expanduser()
    if not source.is_dir():
        raise SystemExit(f"Not a directory: {source}")

    files = [
        p
        for p in sorted(source.rglob("*"))
        if p.is_file() and p.suffix.lower() in IMAGE_SUFFIXES
    ]
    if not files:
        raise SystemExit(f"No images found under {source}")

    heic = sum(1 for p in files if p.suffix.lower() in {".heic", ".heif"})
    if heic and not HEIF_AVAILABLE:
        raise SystemExit(
            f"{heic} of these files are HEIC, which Pillow cannot read on its own.\n"
            "Without the decoder they would be discarded as unreadable, and the\n"
            "count would look like the photos were simply bad.\n\n"
            "  pip install pillow-heif\n\n"
            "Or set the phone camera to Most Compatible / JPEG and copy again."
        )

    print(f"{device_type}: reading {len(files)} files from {source}")
    manifest = _load_manifest()

    def payloads():
        for path in files:
            try:
                yield path.name, path.read_bytes()
            except OSError as exc:
                print(f"  unreadable {path.name}: {type(exc).__name__}: {exc}")

    counts = _ingest(device_type, payloads(), manifest)
    _save_manifest(manifest)

    have = len(list((RAW_ROOT / device_type).glob("*.jpg")))
    target = COLLECTION_PLAN.get(device_type, {}).get("target", 0)
    print(
        f"  kept {counts['kept']}, duplicates {counts['duplicate']}, "
        f"too small or unreadable {counts['rejected']}"
    )
    print(f"  total now {have}" + (f" / {target}" if target else ""))
    print("\nNext: python tools/autolabel.py run --device " + device_type)


def _serper_image_urls(query: str, limit: int, api_key: str) -> List[str]:
    """Query a paid search API. NOT exercised in this repository's checks."""
    request = urllib.request.Request(
        "https://google.serper.dev/images",
        data=json.dumps({"q": query, "gl": "vn", "hl": "vi", "num": limit}).encode(),
        headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        print(f"  query failed: {type(exc).__name__}: {exc}")
        return []
    return [item["imageUrl"] for item in payload.get("images", []) if item.get("imageUrl")]


def _download(url: str) -> Optional[bytes]:
    request = urllib.request.Request(
        url, headers={"User-Agent": "Mozilla/5.0 (compatible; FixHomeDatasetBot/1.0)"}
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.read()
    except Exception:  # noqa: BLE001 - any failure is just a skipped image
        return None


def cmd_fetch(args: argparse.Namespace) -> None:
    api_key = os.environ.get("SERPER_API_KEY", "").strip()
    if not api_key:
        raise SystemExit(
            "SERPER_API_KEY is not set.\n\n"
            "Free image search is not usable here: Google's markup no longer\n"
            "parses and Bing serves unrelated results to scripted clients, so\n"
            "what comes back looks like data and is not. A paid search API\n"
            "returns real results; serper.dev has a free allowance.\n\n"
            "Or skip this entirely and photograph the devices:\n"
            "  python tools/collect_images.py import --device <name> --from <folder>"
        )

    entry = COLLECTION_PLAN.get(args.device)
    if entry is None:
        raise SystemExit(
            f"{args.device!r} is not in the plan. Options: {', '.join(COLLECTION_PLAN)}"
        )

    manifest = _load_manifest()
    per_query = max(1, entry["target"] // max(1, len(entry["queries"])))
    print(f"{args.device}: target {entry['target']}")

    for query in entry["queries"]:
        print(f"  {query}")
        urls = _serper_image_urls(query, per_query, api_key)
        print(f"    {len(urls)} urls")

        def payloads(urls=urls):
            for url in urls:
                data = _download(url)
                if data:
                    yield url, data

        counts = _ingest(args.device, payloads(), manifest)
        print(
            f"    kept {counts['kept']}, duplicates {counts['duplicate']}, "
            f"rejected {counts['rejected']}"
        )

    _save_manifest(manifest)
    have = len(list((RAW_ROOT / args.device).glob("*.jpg")))
    print(f"\n  total now {have} / {entry['target']}")
    print(
        "\nInspect a sample before trusting it. Any search result is product\n"
        "photography, not the conditions customers photograph in."
    )


def cmd_stats(args: argparse.Namespace) -> None:
    counts: Counter = Counter()
    if RAW_ROOT.exists():
        for directory in RAW_ROOT.iterdir():
            if directory.is_dir():
                counts[directory.name] = sum(1 for _ in directory.glob("*.jpg"))

    print(f"{'class':<20}{'have':>8}{'target':>8}{'short':>8}   (* = critical)")
    for device_type, entry in COLLECTION_PLAN.items():
        have = counts.get(device_type, 0)
        mark = "*" if entry["tier"] == "critical" else " "
        print(
            f"{mark}{device_type:<19}{have:>8}{entry['target']:>8}"
            f"{max(0, entry['target'] - have):>8}"
        )

    for device_type in sorted(set(counts) - set(COLLECTION_PLAN)):
        print(f" {device_type:<19}{counts[device_type]:>8}{'-':>8}{'-':>8}")

    print(f"\nTotal collected: {sum(counts.values())}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("plan", help="what still needs images, how many, and why")

    importer = sub.add_parser("import", help="ingest photographs from a folder")
    importer.add_argument("--device", required=True)
    importer.add_argument("--from", dest="source", required=True)

    fetch = sub.add_parser("fetch", help="paid search API; requires SERPER_API_KEY")
    fetch.add_argument("--device", required=True)

    sub.add_parser("stats", help="how far each class is from its target")

    args = parser.parse_args()
    {
        "plan": cmd_plan,
        "import": cmd_import,
        "fetch": cmd_fetch,
        "stats": cmd_stats,
    }[args.command](args)


if __name__ == "__main__":
    main()
