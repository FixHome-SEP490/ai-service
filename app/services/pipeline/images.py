# app/services/pipeline/images.py
"""Image intake.

Images arrive inline from the client, either base64 in JSON or as a multipart
upload. Nothing is fetched from a URL, so the service never makes an outbound
request on behalf of a caller and there is no SSRF surface to defend.

Everything entering the pipeline passes through `load_image`, which checks the
bytes rather than trusting any declared content type, and downscales large
photos. Phone cameras produce 4000px images while the detector trains at 640px,
so downscaling costs no accuracy and saves most of the transfer and memory.
"""

from __future__ import annotations

import base64
import binascii
import io
import re
from dataclasses import dataclass
from typing import Optional

from PIL import Image, UnidentifiedImageError

from app.core.config import settings
from app.core.exceptions import InvalidImageException, UnsupportedImageException

_DATA_URI_RE = re.compile(r"^data:(?P<mime>[\w/\-.+]+);base64,(?P<payload>.+)$", re.DOTALL)

_PIL_FORMAT_TO_MIME = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}


@dataclass(frozen=True)
class ImagePayload:
    """A validated, decoded image ready for the detector or the VLM."""

    image: Image.Image
    mime_type: str
    width: int
    height: int

    def crop(self, box_xywh: tuple[int, int, int, int]) -> "ImagePayload":
        x, y, w, h = box_xywh
        cropped = self.image.crop((x, y, x + w, y + h))
        return ImagePayload(
            image=cropped,
            mime_type=self.mime_type,
            width=cropped.width,
            height=cropped.height,
        )

    def to_base64(self, quality: int = 85) -> str:
        """Re-encode for transport to the model server."""
        buffer = io.BytesIO()
        self.image.convert("RGB").save(buffer, format="JPEG", quality=quality)
        return base64.b64encode(buffer.getvalue()).decode("ascii")


def decode_base64_image(value: str) -> bytes:
    """Accept a data URI or a bare base64 string.

    The declared MIME of a data URI is deliberately ignored; `load_image`
    decides the real format from the decoded bytes.
    """
    candidate = value.strip()
    match = _DATA_URI_RE.match(candidate)
    if match:
        candidate = match.group("payload")
    candidate = "".join(candidate.split())
    try:
        return base64.b64decode(candidate, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise InvalidImageException(internal_detail=repr(exc)) from exc


def load_image(raw: bytes, max_edge: Optional[int] = None) -> ImagePayload:
    """Validate raw bytes and return a downscaled, decoded image.

    Raises before decoding anything oversized, so a large upload cannot be used
    to exhaust memory.
    """
    if not raw:
        raise InvalidImageException(internal_detail="empty image payload")
    if len(raw) > settings.IMAGE_MAX_BYTES:
        raise InvalidImageException(
            internal_detail=f"payload {len(raw)} bytes exceeds limit"
        )

    try:
        with Image.open(io.BytesIO(raw)) as probe:
            probe.verify()  # structural check; leaves the object unusable
        image = Image.open(io.BytesIO(raw))
        image.load()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise InvalidImageException(internal_detail=repr(exc)) from exc

    mime_type = _PIL_FORMAT_TO_MIME.get(image.format or "")
    if mime_type is None or mime_type not in settings.IMAGE_ALLOWED_MIME:
        raise UnsupportedImageException(
            internal_detail=f"decoded format {image.format!r} not allowed"
        )

    image = image.convert("RGB")
    limit = max_edge or settings.IMAGE_MAX_EDGE
    if max(image.width, image.height) > limit:
        image.thumbnail((limit, limit), Image.LANCZOS)

    return ImagePayload(
        image=image,
        mime_type=mime_type,
        width=image.width,
        height=image.height,
    )


def load_base64_image(value: str) -> ImagePayload:
    return load_image(decode_base64_image(value))
