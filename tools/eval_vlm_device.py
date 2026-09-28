# tools/eval_vlm_device.py
"""Ask the language model alone to name the appliance, scored like the detector.

The pipeline runs two models where one might seem to do: Qwen2.5-VL can look at
a photograph, so why keep a detector in front of it? This answers that with a
measurement instead of an argument. Qwen is shown each test photograph whole,
with no detector and no crop, and asked to pick the appliance from the same
closed list of twenty-two classes the detector chooses from. It is scored on
exactly the images `eval_detector.py` scores, against exactly the same truth,
so the two numbers sit side by side without a footnote.

    python tools/eval_vlm_device.py --base-url http://<ip>:<port>/v1 --api-key <key>

The model is served by the stock vllm/vllm-openai image, not by this service,
because the service puts the detector in front of Qwen and that is the thing
being measured without. The exact rental is recorded beside the results.

Three outcomes, not two. A reply that names none of the twenty-two classes is
counted as unparsed and reported on its own line: folding it into "wrong" would
make the model look worse at recognising appliances than it is, and folding it
into "right" would be inventing an answer it never gave.

Two modes, because the choice between candidate models rests on two claims and
each deserves its own measurement:

    closed       pick from the fixed English list, as above
    vietnamese   the question is asked in Vietnamese with no list at all, and
                 the reply is scored on whether it is Vietnamese and whether
                 it names the right appliance by its Vietnamese name or one
                 of the aliases customers actually use

The second is the one the product lives on. The service writes to Vietnamese
customers, so a model that recognises a washing machine but calls it one in
English, or answers a Vietnamese question in Chinese, fails the job however
well it does on the first.
"""

from __future__ import annotations

import argparse
import base64
import json
import sys
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[1]
DATASET = REPO_ROOT / "datasets" / "fixhome"
CATALOG = REPO_ROOT / "app" / "data" / "device_catalog.json"
MODEL = "Qwen/Qwen2.5-VL-3B-Instruct-AWQ"


def _class_names() -> List[str]:
    """The detector's class list, in its own order, from the dataset it trains on."""
    names: Dict[int, str] = {}
    in_names = False
    for line in (DATASET / "data.yaml").read_text(encoding="utf-8").splitlines():
        if line.startswith("names:"):
            in_names = True
            continue
        if in_names:
            key, _, value = line.strip().partition(":")
            if not value.strip():
                break
            names[int(key)] = value.strip()
    return [names[i] for i in sorted(names)]


def _truth_of(image: Path, names: List[str]) -> Optional[str]:
    """Identical to eval_detector._truth_of, so both models face the same test."""
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


def _prompt(names: List[str]) -> str:
    """The closed list, each class with its Vietnamese name so neither language
    is a handicap. The detector chooses from these twenty-two and nothing else,
    so the model is held to the same menu."""
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    vi = {d["device_type"]: d["name_vi"] for d in catalog["devices"]}
    options = "\n".join(f"- {n} ({vi.get(n, '')})" for n in names)
    return (
        "Look at the photograph and name the one household appliance it shows.\n"
        "Answer with exactly one label from this list and nothing else:\n"
        f"{options}"
    )


def _parse(reply: str, names: List[str]) -> Optional[str]:
    """First class named in the reply. Longest labels first, so that a reply
    naming `water_heater` is not read as the shorter label inside it."""
    text = reply.lower().replace(" ", "_").replace("-", "_")
    for name in sorted(names, key=len, reverse=True):
        if name in text:
            return name
    return None


VI_PROMPT = ("Thiết bị gia dụng trong ảnh là gì? Trả lời bằng một cụm từ tiếng Việt, "
             "không giải thích.")


def _fold(text: str) -> str:
    import unicodedata

    text = text.lower().replace("đ", "d")
    text = "".join(c for c in unicodedata.normalize("NFD", text)
                   if unicodedata.category(c) != "Mn")
    return " ".join("".join(c if c.isalnum() else " " for c in text).split())


def _vietnamese_names() -> Dict[str, List[str]]:
    """Every Vietnamese way the catalogue knows to name each class, folded."""
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    out: Dict[str, List[str]] = {}
    for device in catalog["devices"]:
        if not device.get("detector_class"):
            continue
        names = [device["name_vi"], *device.get("aliases_vi", [])]
        out[device["device_type"]] = sorted({_fold(n) for n in names if n}, key=len, reverse=True)
    return out


def _parse_vietnamese(reply: str, vi_names: Dict[str, List[str]]) -> Optional[str]:
    """The class whose Vietnamese name matches the longest stretch of the reply,
    so that "máy sấy quần áo" is not read as "máy" or "quạt trần" as "quạt"."""
    text = f" {_fold(reply)} "
    best, best_len = None, 0
    for device, names in vi_names.items():
        for name in names:
            if f" {name} " in text and len(name) > best_len:
                best, best_len = device, len(name)
    return best


def _is_vietnamese(reply: str) -> bool:
    """Vietnamese carries diacritics no other language on the menu uses. A reply
    with none of them was not written in Vietnamese."""
    marks = set("ăâđêôơưáàảãạắằẳẵặấầẩẫậéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ")
    return any(c in marks for c in reply.lower())


def _ask(client: httpx.Client, url: str, key: str, model: str, prompt: str,
         image: Path, max_tokens: int = 16) -> Tuple[str, float]:
    payload = base64.b64encode(image.read_bytes()).decode()
    body = {
        "model": model,
        "temperature": 0.0,
        "max_tokens": max_tokens,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/jpeg;base64,{payload}"}},
                    {"type": "text", "text": prompt},
                ],
            }
        ],
    }
    started = time.perf_counter()
    for attempt in range(4):
        try:
            response = client.post(
                f"{url}/chat/completions",
                json=body,
                headers={"Authorization": f"Bearer {key}"},
                timeout=120,
            )
            response.raise_for_status()
            reply = response.json()["choices"][0]["message"]["content"]
            return reply, time.perf_counter() - started
        except (httpx.HTTPError, KeyError):
            if attempt == 3:
                raise
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("unreachable")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True, help="OpenAI-compatible, ending in /v1")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--model", default=MODEL, help="served model name")
    parser.add_argument("--mode", choices=["closed", "vietnamese"], default="closed")
    parser.add_argument("--split", default="test")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--limit", type=int, default=0, help="0 means every image")
    parser.add_argument("--out", help="defaults to docs/model-selection/<model>-<mode>.json")
    args = parser.parse_args()

    names = _class_names()
    vi_names = _vietnamese_names()
    prompt = _prompt(names) if args.mode == "closed" else VI_PROMPT
    max_tokens = 16 if args.mode == "closed" else 24
    images = sorted((DATASET / "images" / args.split).rglob("*.jpg"))
    scored = [(image, _truth_of(image, names)) for image in images]
    scored = [(image, truth) for image, truth in scored if truth is not None]
    if args.limit:
        scored = scored[: args.limit]
    print(f"{args.model}, mode {args.mode}: {len(images)} images in {args.split}, "
          f"{len(scored)} scorable as one answer")

    total, correct, unparsed, vietnamese = Counter(), Counter(), Counter(), Counter()
    confused: Dict[str, Counter] = defaultdict(Counter)
    latencies: List[float] = []
    samples: List[dict] = []
    failed_calls = 0

    with httpx.Client() as client, ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {
            pool.submit(_ask, client, args.base_url.rstrip("/"), args.api_key, args.model,
                        prompt, image, max_tokens): (image, truth)
            for image, truth in scored
        }
        for done, future in enumerate(as_completed(futures), start=1):
            image, truth = futures[future]
            try:
                reply, seconds = future.result()
            except Exception:  # noqa: BLE001 - a dead call is reported, not fatal
                failed_calls += 1
                continue
            latencies.append(seconds)
            if args.mode == "closed":
                predicted = _parse(reply, names)
            else:
                predicted = _parse_vietnamese(reply, vi_names)
                if _is_vietnamese(reply):
                    vietnamese[truth] += 1
            total[truth] += 1
            if predicted is None:
                unparsed[truth] += 1
            elif predicted == truth:
                correct[truth] += 1
            else:
                confused[truth][predicted] += 1
            if len(samples) < 40:
                samples.append({"image": image.name, "truth": truth, "reply": reply})
            if done % 200 == 0:
                print(f"  ...{done}/{len(scored)}  running accuracy "
                      f"{sum(correct.values()) / max(1, sum(total.values())):.1%}")

    rows = []
    for name in sorted(total, key=lambda c: -total[c]):
        n = total[name]
        rows.append({
            "class": name,
            "n": n,
            "correct": correct[name],
            "unparsed": unparsed[name],
            "wrong": n - correct[name] - unparsed[name],
            "accuracy": round(correct[name] / n, 4),
            "confused_with": dict(confused[name].most_common(3)),
        })

    n_all = sum(total.values())
    hit_all = sum(correct.values())
    latencies.sort()
    summary = {
        "model": args.model,
        "mode": args.mode,
        "served_by": "vllm/vllm-openai:v0.29.0, stock image, temperature 0",
        "input": "whole photograph, no detector, no crop",
        "question": prompt,
        "split": args.split,
        "scorable": n_all,
        "failed_calls": failed_calls,
        "correct": hit_all,
        "unparsed": sum(unparsed.values()),
        "accuracy": round(hit_all / n_all, 4),
        "accuracy_of_parsed": round(hit_all / max(1, n_all - sum(unparsed.values())), 4),
        "latency_s_median": round(latencies[len(latencies) // 2], 3),
        "latency_s_p95": round(latencies[int(len(latencies) * 0.95)], 3),
        "per_class": rows,
        "sample_replies": samples,
    }
    if args.mode == "vietnamese":
        summary["replied_in_vietnamese"] = round(sum(vietnamese.values()) / n_all, 4)

    print()
    print(f"overall  {hit_all}/{n_all}  {hit_all / n_all:.1%}   unparsed {summary['unparsed']}"
          f"   failed calls {failed_calls}   median {summary['latency_s_median']}s")
    if args.mode == "vietnamese":
        print(f"replied in Vietnamese  {summary['replied_in_vietnamese']:.1%}")

    slug = args.model.split("/")[-1].lower()
    out = REPO_ROOT / (args.out or f"docs/model-selection/{slug}-{args.mode}.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"written to {out.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
