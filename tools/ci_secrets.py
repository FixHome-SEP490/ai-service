"""Copy credentials from the local .env into GitHub Actions secrets.

Typing a token into a terminal puts it in the shell history, and pasting it into
a chat puts it in a transcript. This reads the value from `.env`, which is
git-ignored, and hands it to `gh secret set` over stdin so it never appears as a
command argument either.

    python tools/ci_secrets.py status
    python tools/ci_secrets.py push

Only names this file knows about are copied, so an unrelated key in `.env`
cannot be uploaded by accident.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _secrets import _from_env_file, describe  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = "FixHome-SEP490/ai-service"

# name -> why the workflow needs it
SECRETS = {
    "DOCKERHUB_USERNAME": "Docker Hub account the trainer image is published under",
    "DOCKERHUB_TOKEN": "Docker Hub access token with Read & Write, not the password",
}

# Non-secret switches. Kept separate because a variable is readable afterwards
# and a secret is not, and mixing them hides which is which.
VARIABLES = {
    "DOCKERHUB_ENABLED": "true",
}


def _gh(args: list[str], stdin: str | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["gh", *args],
        input=stdin,
        text=True,
        capture_output=True,
    )


def cmd_status(args: argparse.Namespace) -> None:
    print("Local .env:")
    for name in SECRETS:
        print(f"  {describe(name)}")

    print(f"\nAlready set on {REPO}:")
    result = _gh(["secret", "list", "--repo", REPO])
    print(result.stdout.strip() or "  (none, or no permission to list)")

    result = _gh(["variable", "list", "--repo", REPO])
    print(result.stdout.strip() or "  (no variables)")


def cmd_push(args: argparse.Namespace) -> None:
    missing = [name for name in SECRETS if not _from_env_file(name)]
    if missing:
        raise SystemExit(
            "Not in .env: " + ", ".join(missing) + "\n\n"
            "Add them to .env at the repository root, which is git-ignored:\n"
            + "".join(f"    {name}=<value>    # {why}\n" for name, why in SECRETS.items())
            + "\nUse a Docker Hub access token, not the account password. Tokens can\n"
            "be revoked one at a time and are scoped to Read & Write on repositories."
        )

    for name in SECRETS:
        value = _from_env_file(name)
        # Passed on stdin so the value is never a process argument, which would
        # be visible to anything listing processes.
        result = _gh(["secret", "set", name, "--repo", REPO], stdin=value)
        if result.returncode != 0:
            raise SystemExit(f"Failed to set {name}: {result.stderr.strip()}")
        print(f"set secret {name}")

    for name, value in VARIABLES.items():
        result = _gh(["variable", "set", name, "--repo", REPO, "--body", value])
        if result.returncode != 0:
            raise SystemExit(f"Failed to set variable {name}: {result.stderr.strip()}")
        print(f"set variable {name}={value}")

    print(
        "\nRe-run the Trainer image workflow to publish to Docker Hub:\n"
        f"  gh workflow run trainer-image.yml --repo {REPO}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="what is in .env and what is already on GitHub")
    sub.add_parser("push", help="copy the known names from .env to GitHub")
    args = parser.parse_args()
    {"status": cmd_status, "push": cmd_push}[args.command](args)


if __name__ == "__main__":
    main()
