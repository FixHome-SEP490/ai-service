# tools/api_cost_estimate.py
"""What a hosted vision API would cost, against running the model ourselves.

Every figure here is either a published price or an assumption stated in the
open, so that anyone who disagrees with the result can change the assumption
and rerun it rather than argue with a number.

    python tools/api_cost_estimate.py

Prices are OpenAI's standard tier as published on developers.openai.com/api/
docs/pricing, read on 2026-09-28. Image tokens follow the rules in that site's
vision guide, which differ by model and are the reason the cheapest model for
text is not the cheapest for photographs: gpt-4o-mini counts a photograph as
roughly thirty times more tokens than gpt-4o does.

The result is not "an API is always dearer". It is where the two lines cross,
because self-hosting is a flat monthly cost and an API is a cost per call.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[1]

# ---- published prices, USD per 1M tokens, standard tier -------------------
PRICES = {
    "gpt-4o": {"input": 2.50, "output": 10.00},
    "gpt-4o-mini": {"input": 0.15, "output": 0.60},
    "gpt-4.1-mini": {"input": 0.40, "output": 1.60},
}

# ---- assumptions, each one open to challenge ------------------------------
IMAGE_W, IMAGE_H = 1024, 768
"""What the mobile and web clients send after their own resize."""

TEXT_IN_TOKENS = 1_500
"""System prompt, the retrieval shortlist with symptoms, and the customer's
words. Measured on the prompts qwen_client.py builds, rounded up."""

TEXT_OUT_TOKENS = 250
"""The fault codes plus the Vietnamese reply the customer reads."""

CALLS_PER_USER_PER_MONTH = 10
"""A diagnosis is a short conversation, and every message is a call. Ten a
month is a heavy user; halve it and every crossover below doubles."""

RENTED_GPU_PER_HOUR = 0.108
"""The RTX A4000 the service has run on, per hour, on vast.ai."""

OWNED_GPU_ELECTRICITY_PER_MONTH = 13.0
"""An owned 16GB card at about 150 W, all month, at about 3,000 VND per kWh."""

HOURS_PER_MONTH = 730


def image_tokens(model: str, width: int = IMAGE_W, height: int = IMAGE_H) -> int:
    """Token count for one photograph at high detail, per the vision guide."""
    if model == "gpt-4.1-mini":
        # 32 px patches, times a model-specific multiplier.
        patches = math.ceil(width / 32) * math.ceil(height / 32)
        return math.ceil(patches * 1.62)
    # Tile models: fit within 2048, scale the short side to 768, count 512 tiles.
    scale = min(1.0, 2048 / max(width, height))
    w, h = width * scale, height * scale
    short = min(w, h)
    if short > 768:
        w, h = w * 768 / short, h * 768 / short
    tiles = math.ceil(w / 512) * math.ceil(h / 512)
    base, per_tile = (2833, 5667) if model == "gpt-4o-mini" else (85, 170)
    return base + per_tile * tiles


def cost_per_call(model: str) -> float:
    price = PRICES[model]
    tokens_in = TEXT_IN_TOKENS + image_tokens(model)
    return (tokens_in * price["input"] + TEXT_OUT_TOKENS * price["output"]) / 1_000_000


def main() -> None:
    rented = RENTED_GPU_PER_HOUR * HOURS_PER_MONTH
    owned = OWNED_GPU_ELECTRICITY_PER_MONTH
    users = [100, 1_000, 5_000, 10_000]

    print(f"Assumptions: {IMAGE_W}x{IMAGE_H} photo, {TEXT_IN_TOKENS} text tokens in, "
          f"{TEXT_OUT_TOKENS} out, {CALLS_PER_USER_PER_MONTH} calls per user per month\n")

    rows = []
    for model in PRICES:
        per_call = cost_per_call(model)
        monthly = {u: per_call * u * CALLS_PER_USER_PER_MONTH for u in users}
        crossover_rented = rented / per_call / CALLS_PER_USER_PER_MONTH
        crossover_owned = owned / per_call / CALLS_PER_USER_PER_MONTH
        rows.append({
            "model": model,
            "image_tokens": image_tokens(model),
            "usd_per_call": round(per_call, 5),
            "usd_per_month": {str(u): round(v, 2) for u, v in monthly.items()},
            "users_where_rented_gpu_is_cheaper": round(crossover_rented),
            "users_where_owned_gpu_is_cheaper": round(crossover_owned),
        })
        print(f"{model:<14} {image_tokens(model):>6} image tokens   ${per_call:.4f} per call")
        print("               " + "   ".join(f"{u:>6} users ${v:>7.2f}" for u, v in monthly.items()))
        print(f"               cheaper to self-host above ~{crossover_rented:,.0f} users (rented GPU)"
              f", ~{crossover_owned:,.0f} users (owned GPU)\n")

    print("Self-hosted, any number of users up to the card's capacity:")
    print(f"   rented RTX A4000, 24/7   ${rented:.2f} per month")
    print(f"   owned 16GB card          ${owned:.2f} per month in electricity, plus the card once")

    out = REPO_ROOT / "docs" / "model-selection" / "api-cost.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "prices_source": "developers.openai.com/api/docs/pricing, standard tier, read 2026-09-28",
        "image_token_source": "developers.openai.com/api/docs/guides/images-vision",
        "assumptions": {
            "image_px": [IMAGE_W, IMAGE_H],
            "text_in_tokens": TEXT_IN_TOKENS,
            "text_out_tokens": TEXT_OUT_TOKENS,
            "calls_per_user_per_month": CALLS_PER_USER_PER_MONTH,
            "rented_gpu_usd_per_hour": RENTED_GPU_PER_HOUR,
            "owned_gpu_electricity_usd_per_month": OWNED_GPU_ELECTRICITY_PER_MONTH,
        },
        "self_host_usd_per_month": {"rented": round(rented, 2), "owned": owned},
        "api": rows,
    }, indent=2), encoding="utf-8")
    print(f"\nwritten to {out.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
