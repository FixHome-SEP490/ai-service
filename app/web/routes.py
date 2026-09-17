"""The chat page the service serves about itself.

Deliberately part of the service rather than a separate app. A rented box
publishes one port; anything on a second port, or on a laptop, is not
shareable, and "send the team a link" was the whole request. Served from here
it lives at the same address the API does and needs nothing installed.

The page is a single file of plain HTML, CSS and JavaScript with no build step
and no CDN, because the box has no toolchain and an outbound fetch is one more
thing to fail in front of an audience.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()

_PAGE = Path(__file__).with_name("chat.html")


@router.get("/chat", response_class=HTMLResponse, include_in_schema=False)
async def chat_page() -> HTMLResponse:
    """Read per request, so editing the file during a demo needs no restart."""
    return HTMLResponse(_PAGE.read_text(encoding="utf-8"))
