"""Guards on the tool that spends money.

Everything else in this repository is free to get wrong twice. A mistake here
either bills for a machine nobody is watching or destroys weights that took
four hours and cannot be regenerated, because the machine that produced them is
deleted the minute it finishes.

So the one piece of judgement in `rent_gpu train` that is not a network call
gets pinned here: whether continuing a run would overwrite the run it continues
from.
"""

import pytest

from tools import rent_gpu
from tools.rent_gpu import resume_conflict


def test_ordinary_run_has_nothing_to_complain_about():
    """No --resume-from is the normal path and must never be refused."""
    assert resume_conflict("detector-v2", "") == ""


def test_continuing_under_the_same_name_is_refused():
    """The failure this exists for.

    publish_weights uploads into a folder named after the run. Continuing
    detector-v2 as detector-v2 replaces the weights it just read, so the
    seventy epochs already paid for are gone and the run cannot be repeated.
    """
    complaint = resume_conflict("detector-v2", "detector-v2/weights/best.pt")
    assert complaint
    assert "overwrite" in complaint
    # The message has to carry a way forward, not just a refusal: this is read
    # by someone who has already decided to spend another forty minutes.
    assert "detector-v2-more" in complaint


def test_continuing_under_a_different_name_is_allowed():
    assert resume_conflict("detector-v3", "detector-v2/weights/best.pt") == ""
    assert resume_conflict("detector-v2-more", "detector-v2/weights/best.pt") == ""


def test_a_name_that_merely_starts_the_same_is_allowed():
    """detector-v2-more must not be read as being inside detector-v2.

    The first version of this compared with startswith(run_name), which made
    every sensible continuation name — the exact thing the error message
    recommends — refuse itself.
    """
    assert resume_conflict("detector-v2", "detector-v2-more/weights/best.pt") == ""


@pytest.mark.parametrize(
    "resume_from",
    [
        "detector-v2/weights/best.pt",
        "/detector-v2/weights/best.pt",
        "detector-v2/weights/best.pt/",
    ],
)
def test_leading_and_trailing_slashes_do_not_slip_past(resume_from):
    """A path pasted out of the Hub's web interface carries a leading slash."""
    assert resume_conflict("detector-v2", resume_from)


class TestDestroyFindsTheBoxYouRented:
    """`destroy` with no argument must find the machine that is actually billing.

    It looked only in the trainer's file. Serving is what gets rented most
    days, so the ordinary case was `destroy` refusing with "No instance id
    given and no .vast-instance" while an A4000 carried on at twelve cents an
    hour - and that message reads like "nothing is rented", which is the one
    reading that costs money. Seen for real, with the box still up.
    """

    def test_the_serving_box_is_found_without_an_argument(self, tmp_path, monkeypatch):
        serve = tmp_path / ".vast-serve-instance"
        serve.write_text("51447047", encoding="utf-8")
        monkeypatch.setattr(rent_gpu, "SERVE_INSTANCE_FILE", serve)
        monkeypatch.setattr(rent_gpu, "INSTANCE_FILE", tmp_path / ".vast-instance")

        assert rent_gpu._instance_id(None) == 51447047

    def test_the_training_box_is_still_found(self, tmp_path, monkeypatch):
        trainer = tmp_path / ".vast-instance"
        trainer.write_text("42", encoding="utf-8")
        monkeypatch.setattr(rent_gpu, "SERVE_INSTANCE_FILE", tmp_path / ".vast-serve")
        monkeypatch.setattr(rent_gpu, "INSTANCE_FILE", trainer)

        assert rent_gpu._instance_id(None) == 42

    def test_an_explicit_id_beats_both_files(self, tmp_path, monkeypatch):
        serve = tmp_path / ".vast-serve-instance"
        serve.write_text("51447047", encoding="utf-8")
        monkeypatch.setattr(rent_gpu, "SERVE_INSTANCE_FILE", serve)
        monkeypatch.setattr(rent_gpu, "INSTANCE_FILE", tmp_path / ".vast-instance")

        assert rent_gpu._instance_id(999) == 999

    def test_with_no_file_it_says_how_to_find_the_id(self, tmp_path, monkeypatch):
        monkeypatch.setattr(rent_gpu, "SERVE_INSTANCE_FILE", tmp_path / ".vast-serve")
        monkeypatch.setattr(rent_gpu, "INSTANCE_FILE", tmp_path / ".vast-instance")

        with pytest.raises(SystemExit) as refused:
            rent_gpu._instance_id(None)

        # The message has to point somewhere, or it reads as "all clear".
        assert "status" in str(refused.value)
        assert "--instance" in str(refused.value)


class TestTheCardGenerationIsChecked:
    """AWQ needs compute capability 7.5, and nothing else in the listing says so.

    A Tesla V100 looks like the best machine available on every visible
    measure - 32 GB of VRAM, a 14.6 Gb/s link, reliability 0.999, CUDA 13.0 -
    and it cannot run this model at all. It was recommended as the first
    fallback for exactly those reasons, rented, and vLLM refused:

        The quantization method auto_awq is not supported for the current GPU.
        Minimum capability: 75. Current capability: 70.
    """

    def test_volta_is_below_the_floor(self):
        assert rent_gpu._compute_cap({"compute_cap": 700}) < rent_gpu.SERVE_MIN_COMPUTE_CAP

    def test_pascal_is_below_the_floor(self):
        assert rent_gpu._compute_cap({"compute_cap": 610}) < rent_gpu.SERVE_MIN_COMPUTE_CAP

    def test_turing_is_the_oldest_that_passes(self):
        assert rent_gpu._compute_cap({"compute_cap": 750}) >= rent_gpu.SERVE_MIN_COMPUTE_CAP

    def test_ampere_and_ada_pass(self):
        for cap in (860, 890, 1200):
            assert rent_gpu._compute_cap({"compute_cap": cap}) >= rent_gpu.SERVE_MIN_COMPUTE_CAP

    def test_a_missing_or_unparseable_value_reads_as_unknown(self):
        # Unknown must not be treated as unsuitable: an offer id typed off the
        # website is legitimate, and the check says what it could not verify.
        assert rent_gpu._compute_cap({}) == 0
        assert rent_gpu._compute_cap({"compute_cap": None}) == 0
        assert rent_gpu._compute_cap({"compute_cap": "n/a"}) == 0
