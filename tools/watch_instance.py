"""Follow a rented instance until it serves, printing what vast.ai says about it.

    python tools/watch_instance.py <instance id> [--minutes 25]

`rent_gpu.py status` shows only "loading", which hides the reason a box never
comes up: two rentals on 24/10/2026 sat in "loading" for over thirty minutes
and were destroyed blind. vast.ai does say why, in `status_msg` (a failed
registry login, a stalled layer, a driver error); this prints it every thirty
seconds, with the published API address once there is one and whether the
service answers on it.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.request

sys.path.insert(0, __file__.rsplit("tools", 1)[0] + "tools")
import rent_gpu  # noqa: E402

FIELDS = ("actual_status", "intended_status", "cur_state", "status_msg")


def health(base: str) -> str:
    try:
        with urllib.request.urlopen(f"{base}/health", timeout=8) as reply:
            body = json.loads(reply.read().decode("utf-8"))
        return f"vlm={body.get('vlm', {}).get('attached')} detector={body.get('detector', {}).get('attached')}"
    except Exception as exc:  # still loading, or not routed
        return f"no answer ({type(exc).__name__})"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("instance")
    parser.add_argument("--minutes", type=float, default=25)
    args = parser.parse_args()
    end = time.time() + args.minutes * 60
    last = None
    while time.time() < end:
        detail = rent_gpu._reply(
            rent_gpu._cli("show", "instance", str(args.instance), "--raw"), doing="reading the instance"
        )
        state = {k: (str(detail.get(k)) or "")[:160] for k in FIELDS}
        host = (detail.get("public_ipaddr") or "").strip()
        mapping = (detail.get("ports") or {}).get(f"{rent_gpu.SERVE_PORT}/tcp") or []
        base = f"http://{host}:{mapping[0].get('HostPort')}" if host and mapping else ""
        line = " | ".join(f"{k}={v}" for k, v in state.items())
        if base:
            line += f" | {base} {health(base)}"
        if line != last:
            print(time.strftime("%H:%M:%S"), line, flush=True)
            last = line
        if base and "vlm=True" in line:
            print(f"READY AI_SERVICE_URL={base}")
            return
        time.sleep(30)
    print("GAVE UP")
    sys.exit(1)


if __name__ == "__main__":
    main()
