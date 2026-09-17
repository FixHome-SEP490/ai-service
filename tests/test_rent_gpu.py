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
