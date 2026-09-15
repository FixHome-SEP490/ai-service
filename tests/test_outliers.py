"""Outlier screening tests.

The screen is a ranking, not a verdict, so what is tested is ordering: does a
photograph unlike its classmates come out above one that fits. Its accuracy at
any single image matters far less than whether a person reviewing the top of
the list finds the mistakes there.
"""

import random

import pytest
from PIL import Image, ImageDraw

from tools.screen_outliers import _centre, _distance, _scan_device, _signature


def _photo(path, seed: int, tone: int = 120, size=(320, 240)) -> None:
    """A picture whose look is driven by `tone`, with texture from `seed`."""
    rnd = random.Random(seed)
    image = Image.new("RGB", size, (tone, tone, tone))
    draw = ImageDraw.Draw(image)
    for _ in range(8):
        x, y = rnd.randint(0, size[0] - 60), rnd.randint(0, size[1] - 60)
        shade = max(0, min(255, tone + rnd.randint(-25, 25)))
        draw.rectangle([x, y, x + 50, y + 50], fill=(shade, shade, shade))
    image.save(path, quality=90)


def test_signature_is_stable_for_the_same_image(tmp_path):
    path = tmp_path / "a.jpg"
    _photo(path, seed=1)

    assert _signature(path) == _signature(path)


def test_signature_has_a_fixed_width(tmp_path):
    a, b = tmp_path / "a.jpg", tmp_path / "b.jpg"
    _photo(a, seed=1)
    _photo(b, seed=2, tone=40, size=(600, 480))

    assert len(_signature(a)) == len(_signature(b))


def test_a_different_looking_image_sits_further_from_the_centre(tmp_path):
    similar = []
    for index in range(6):
        path = tmp_path / f"s{index}.jpg"
        _photo(path, seed=index, tone=120)
        similar.append(_signature(path))

    odd_path = tmp_path / "odd.jpg"
    _photo(odd_path, seed=99, tone=245)

    centre = _centre(similar)
    typical = _distance(similar[0], centre)
    odd = _distance(_signature(odd_path), centre)

    assert odd > typical


def test_a_small_class_is_not_scanned(tmp_path):
    """Below twenty the centre says more about the sample than any image."""
    folder = tmp_path / "gas_stove"
    folder.mkdir()
    for index in range(10):
        _photo(folder / f"{index}.jpg", seed=index)

    assert _scan_device(folder) == []


def test_scan_ranks_the_odd_one_first(tmp_path):
    folder = tmp_path / "gas_stove"
    folder.mkdir()
    for index in range(30):
        _photo(folder / f"normal_{index}.jpg", seed=index, tone=120)
    _photo(folder / "intruder.jpg", seed=500, tone=250)

    scored = _scan_device(folder)

    assert scored
    assert scored[0][1] == "intruder.jpg"


def test_scan_returns_one_entry_per_image(tmp_path):
    folder = tmp_path / "sink"
    folder.mkdir()
    for index in range(25):
        _photo(folder / f"{index}.jpg", seed=index)

    assert len(_scan_device(folder)) == 25


def test_scores_are_standardised(tmp_path):
    """Reported in standard deviations, so one threshold suits every class."""
    folder = tmp_path / "toilet"
    folder.mkdir()
    for index in range(30):
        _photo(folder / f"{index}.jpg", seed=index)

    scores = [z for z, _ in _scan_device(folder)]
    mean = sum(scores) / len(scores)

    assert mean == pytest.approx(0.0, abs=1e-6)


def test_an_unreadable_file_does_not_stop_the_scan(tmp_path):
    folder = tmp_path / "faucet"
    folder.mkdir()
    for index in range(25):
        _photo(folder / f"{index}.jpg", seed=index)
    (folder / "broken.jpg").write_bytes(b"not an image")

    scored = _scan_device(folder)

    assert len(scored) == 25
    assert all(name != "broken.jpg" for _, name in scored)
