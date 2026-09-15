"""Read API keys from the environment or a local .env file.

Keys stay out of the shell history and out of chat transcripts: write them once
into `.env`, which is git-ignored, and every tool picks them up from there. A
value already exported in the environment wins, so CI and one-off overrides
still work.

Nothing here ever prints a key. Failures report the variable name and where to
put it, never the value.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

ENV_PATH = Path(__file__).resolve().parents[1] / ".env"


def _from_env_file(name: str) -> Optional[str]:
    if not ENV_PATH.exists():
        return None
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip() != name:
            continue
        value = value.strip()
        # Tolerate quoted values; a key pasted with quotes is a common slip and
        # failing on it looks identical to the key being wrong.
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        return value.strip() or None
    return None


def get_secret(name: str, *, hint: str = "") -> str:
    """Return the named secret, or exit with instructions that do not leak it."""
    value = os.environ.get(name, "").strip() or _from_env_file(name)
    if value:
        return value

    message = [
        f"{name} is not set.",
        "",
        f"Put it in {ENV_PATH.name} at the repository root (git-ignored):",
        "",
        f"    {name}=<your key>",
        "",
        "or export it in the shell. Do not paste it into a chat or a commit.",
    ]
    if hint:
        message += ["", hint]
    raise SystemExit("\n".join(message))


def describe(name: str) -> str:
    """Say whether a secret is available, without revealing any of it."""
    if os.environ.get(name, "").strip():
        return f"{name}: found in environment"
    if _from_env_file(name):
        return f"{name}: found in {ENV_PATH.name}"
    return f"{name}: not set"
