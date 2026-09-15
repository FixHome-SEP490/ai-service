"""Image intake tests.

The pipeline trusts nothing a client declares, so these cover what happens when
the bytes disagree with the label, when the payload is too large, and when a
phone sends a photo far bigger than the detector needs.
"""

import base64
import io

import pytest
from PIL import Image

from app.core.exceptions import InvalidImageException, UnsupportedImageException
from app.services.pipeline.images import (
    decode_base64_image,
    load_base64_image,
    load_image,
)


def _encode(image: Image.Image, fmt: str = "PNG") -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format=fmt)
    return buffer.getvalue()


def _png_bytes(width: int = 64, height: int = 48) -> bytes:
    return _encode(Image.new("RGB", (width, height), (10, 20, 30)))


def test_accepts_bare_base64_and_data_uri():
    raw = _png_bytes()
    bare = base64.b64encode(raw).decode("ascii")
    assert decode_base64_image(bare) == raw
    assert decode_base64_image(f"data:image/png;base64,{bare}") == raw


def test_whitespace_in_base64_is_tolerated():
    """Clients and JSON formatters wrap long strings; that must not break intake."""
    raw = _png_bytes()
    wrapped = "\n".join(
        base64.b64encode(raw).decode("ascii")[i : i + 40]
        for i in range(0, len(base64.b64encode(raw)), 40)
    )
    assert decode_base64_image(wrapped) == raw


def test_rejects_malformed_base64():
    with pytest.raises(InvalidImageException):
        decode_base64_image("not base64 at all!!")


def test_rejects_empty_payload():
    with pytest.raises(InvalidImageException):
        load_image(b"")


def test_rejects_non_image_bytes():
    with pytest.raises(InvalidImageException):
        load_image(b"%PDF-1.7 this is not an image")


def test_format_is_decided_by_bytes_not_by_declared_mime():
    """A PNG announced as JPEG is still handled as the PNG it actually is."""
    raw = _png_bytes()
    declared_wrong = "data:image/jpeg;base64," + base64.b64encode(raw).decode("ascii")
    payload = load_base64_image(declared_wrong)
    assert payload.mime_type == "image/png"


def test_rejects_allowed_looking_but_unsupported_format():
    raw = _encode(Image.new("RGB", (32, 32), (0, 0, 0)), fmt="BMP")
    with pytest.raises(UnsupportedImageException):
        load_image(raw)


def test_rejects_oversized_payload(monkeypatch):
    from app.core import config

    monkeypatch.setattr(config.settings, "IMAGE_MAX_BYTES", 100)
    with pytest.raises(InvalidImageException):
        load_image(_png_bytes(200, 200))


def test_large_photo_is_downscaled_preserving_aspect_ratio():
    """Phone photos dwarf the 640px the detector trains at; shrink on intake."""
    payload = load_image(_png_bytes(3000, 2000), max_edge=1024)
    assert max(payload.width, payload.height) == 1024
    assert payload.width / payload.height == pytest.approx(1.5, rel=0.01)


def test_small_photo_is_not_upscaled():
    payload = load_image(_png_bytes(200, 100), max_edge=1024)
    assert (payload.width, payload.height) == (200, 100)


def test_crop_returns_the_requested_region():
    payload = load_image(_png_bytes(100, 80))
    cropped = payload.crop((10, 10, 40, 30))
    assert (cropped.width, cropped.height) == (40, 30)


def test_round_trip_through_base64_stays_loadable():
    """What the pipeline hands the model server must survive re-encoding."""
    payload = load_image(_png_bytes(120, 90))
    reloaded = load_base64_image(payload.to_base64())
    assert (reloaded.width, reloaded.height) == (120, 90)
    assert reloaded.mime_type == "image/jpeg"
