"""How many customers one served instance can talk to at once.

    python tools/load_test.py --url http://host:port --users 10 30 50

Each simulated customer holds a short conversation of its own - a symptom, a
follow-up that rules something out, a question - in its own session, all of
them at the same time. What is measured is what a customer would feel: how
long each reply takes, how many fail, and how many conversations finish per
minute. The model's own ceiling is VLM_TIMEOUT_SECONDS; a reply slower than
that falls back to retrieval, so the share of replies that came back with no
model in them is reported too.
"""

from __future__ import annotations

import argparse
import asyncio
import random
import sys
import time
from pathlib import Path
from typing import List

import httpx

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))

CONVERSATIONS = [
    ("máy lạnh nhà em không mát", "mới vệ sinh tuần trước rồi", "vậy giờ là bị gì ạ"),
    ("tủ lạnh chảy nước ra sàn", "đã thông lỗ thoát nước rồi mà vẫn chảy", "sửa hết bao nhiêu tiền"),
    ("máy giặt không vắt", "không phải lệch đồ đâu", "có cần gọi thợ không"),
    ("bình nóng lạnh không nóng", "thay thanh đốt rồi vẫn không nóng", "nên đặt dịch vụ nào"),
    ("quạt trần quay yếu", "không phải tụ đâu", "vậy giờ sao"),
    ("bếp từ báo lỗi E1", "mặt kính còn nguyên", "có nguy hiểm không"),
    ("vòi nước nhỏ giọt suốt", "mới thay gioăng rồi", "tự sửa được không"),
    ("ổ cắm có mùi khét", "chắc không phải chập đâu", "giờ làm sao"),
]


async def _conversation(client: httpx.AsyncClient, url: str, turns, latencies: List[float], failures: List[str]) -> bool:
    session = None
    for index, text in enumerate(turns):
        question = index == len(turns) - 1
        path = "/api/v1/chat/ask" if question else "/api/v1/diagnosis/analyze"
        body = {"question": text} if question else {"description": text}
        if session:
            body["sessionId"] = session
        started = time.perf_counter()
        try:
            response = await client.post(f"{url}{path}", json=body, timeout=60.0)
            latencies.append(time.perf_counter() - started)
            if response.status_code != 200:
                failures.append(f"{response.status_code}")
                return False
            session = response.json().get("sessionId") or session
        except httpx.HTTPError as error:
            latencies.append(time.perf_counter() - started)
            failures.append(type(error).__name__)
            return False
    return True


async def _round(url: str, users: int) -> dict:
    latencies: List[float] = []
    failures: List[str] = []
    rng = random.Random(users)
    limits = httpx.Limits(max_connections=users + 5, max_keepalive_connections=users + 5)
    async with httpx.AsyncClient(limits=limits) as client:
        started = time.perf_counter()
        results = await asyncio.gather(
            *(_conversation(client, url, rng.choice(CONVERSATIONS), latencies, failures) for _ in range(users))
        )
        elapsed = time.perf_counter() - started
    ordered = sorted(latencies)
    pick = lambda q: ordered[min(len(ordered) - 1, int(len(ordered) * q))] if ordered else 0.0  # noqa: E731
    return {
        "users": users,
        "finished": sum(results),
        "replies": len(latencies),
        "failures": len(failures),
        "p50": pick(0.5),
        "p95": pick(0.95),
        "max": ordered[-1] if ordered else 0.0,
        "seconds": elapsed,
        "per_minute": 60 * sum(results) / elapsed if elapsed else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--users", type=int, nargs="+", default=[10, 30, 50])
    args = parser.parse_args()
    url = args.url.rstrip("/")
    print(f"{'người':>6} {'xong':>6} {'lỗi':>5} {'p50 s':>7} {'p95 s':>7} {'max s':>7} {'cuộc/phút':>10}")
    for users in args.users:
        row = asyncio.run(_round(url, users))
        print(
            f"{row['users']:>6} {row['finished']:>6} {row['failures']:>5} {row['p50']:>7.2f} "
            f"{row['p95']:>7.2f} {row['max']:>7.2f} {row['per_minute']:>10.1f}"
        )


if __name__ == "__main__":
    main()
