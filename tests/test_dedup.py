"""Near-duplicate detection tests.

The threshold is the whole design, so these pin it from both sides. Too loose
and twenty people photographing one hallway socket contribute twenty samples
that land in different splits and inflate the score. Too tight and two different
sockets of the same model get merged, throwing away real data.
"""

import random

import pytest
from PIL import Image, ImageDraw

from tools.collect_images import (
    PHASH_MAX_DISTANCE,
    _near_duplicate_of,
    _perceptual_hash,
)


def _scene(seed: int, width: int = 900, height: int = 700) -> Image.Image:
    """A distinct scene per seed, so different seeds are different devices."""
    rnd = random.Random(seed)
    image = Image.new("RGB", (width, height), (rnd.randint(60, 200),) * 3)
    draw = ImageDraw.Draw(image)
    for _ in range(12):
        x, y = rnd.randint(0, width - 160), rnd.randint(0, height - 160)
        draw.rectangle(
            [x, y, x + rnd.randint(40, 150), y + rnd.randint(40, 150)],
            fill=(rnd.randint(0, 255), rnd.randint(0, 255), rnd.randint(0, 255)),
        )
    return image


def _distance(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def test_identical_images_hash_identically():
    assert _perceptual_hash(_scene(1)) == _perceptual_hash(_scene(1))


def test_a_slight_crop_is_still_the_same_photograph():
    original = _scene(1)
    cropped = original.crop(
        (6, 6, original.width - 6, original.height - 6)
    ).resize(original.size)

    assert _distance(_perceptual_hash(original), _perceptual_hash(cropped)) <= PHASH_MAX_DISTANCE


def test_a_resize_is_still_the_same_photograph():
    """A phone shot and its downscaled copy must not both enter the dataset."""
    original = _scene(3)
    smaller = original.resize((original.width // 2, original.height // 2))

    assert _distance(_perceptual_hash(original), _perceptual_hash(smaller)) <= PHASH_MAX_DISTANCE


def test_different_devices_stay_apart():
    """The failure that costs real data: merging two sockets of the same model."""
    for seed in range(2, 12):
        distance = _distance(_perceptual_hash(_scene(1)), _perceptual_hash(_scene(seed)))
        assert distance > PHASH_MAX_DISTANCE, f"seed {seed} collided at distance {distance}"


def test_lookup_finds_the_owner_of_a_near_duplicate():
    original = _perceptual_hash(_scene(5))
    cropped = _perceptual_hash(
        _scene(5).crop((4, 4, 896, 696)).resize((900, 700))
    )
    seen = {original: "power_outlet_abc.jpg"}

    assert _near_duplicate_of(cropped, seen) == "power_outlet_abc.jpg"


def test_lookup_returns_nothing_for_an_unseen_image():
    seen = {_perceptual_hash(_scene(6)): "power_outlet_abc.jpg"}

    assert _near_duplicate_of(_perceptual_hash(_scene(7)), seen) is None


def test_lookup_on_an_empty_table():
    assert _near_duplicate_of(_perceptual_hash(_scene(8)), {}) is None


@pytest.mark.parametrize("seed", [10, 11, 12, 13])
def test_hash_is_sixty_four_bits(seed):
    assert 0 <= _perceptual_hash(_scene(seed)) < 2**64
