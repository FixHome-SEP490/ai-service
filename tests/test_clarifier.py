"""Clarifying question tests.

The property that matters is not that a question is produced, but that its
answer removes candidates. A question everyone on the shortlist would answer the
same way is a form field, not a diagnosis step.
"""

import pytest

from app.services.pipeline import clarifier
from app.services.pipeline.knowledge_base import Discriminator, Fault


def _fault(code: str, symptoms: list[str]) -> Fault:
    return Fault(
        fault_code=code,
        device_type="air_conditioner",
        name_vi=code,
        symptoms_vi=symptoms,
        price_min=0,
        price_max=0,
        urgency="LOW",
        suggested_actions_vi=[],
    )


A = _fault("A", ["không mát", "chạy liên tục", "bám tuyết"])
B = _fault("B", ["không mát", "có mùi", "gió yếu"])
C = _fault("C", ["không mát", "nhảy aptomat"])


def test_no_candidates_means_no_questions():
    assert clarifier.build_questions([], "gì đó") == []


def test_a_symptom_every_candidate_shares_is_never_asked():
    """"Không mát" is on all three, so the answer cannot rule anything out."""
    questions = clarifier.build_questions([A, B, C], "máy lạnh hỏng")

    assert all("không mát" not in q.text_vi for q in questions)


def test_a_distinguishing_symptom_is_asked():
    questions = clarifier.build_questions([A, B], "máy lạnh hỏng")
    asked = " ".join(q.text_vi for q in questions)

    assert "có mùi" in asked or "bám tuyết" in asked


def test_what_the_customer_already_said_is_not_asked_back():
    """Asking about something just written reads as not having listened."""
    questions = clarifier.build_questions([A, B], "máy lạnh có mùi hôi khó chịu")

    assert all("có mùi" not in q.text_vi for q in questions)


def test_a_single_candidate_gets_confirmation_questions():
    questions = clarifier.build_questions([A], "máy lạnh hỏng")

    assert questions
    assert any("bám tuyết" in q.text_vi for q in questions)


def test_question_count_is_capped():
    assert len(clarifier.build_questions([A, B, C], "hỏng", limit=2)) <= 2


# ------------------------------------------------------- discriminators

CLEANED = Discriminator(
    device_type="air_conditioner",
    question_vi="Máy lạnh có được vệ sinh gần đây không?",
    favours_if_yes=["A"],
    favours_if_no=["B"],
)
IRRELEVANT = Discriminator(
    device_type="air_conditioner",
    question_vi="Câu hỏi không liên quan tới danh sách hiện tại?",
    favours_if_yes=["X"],
    favours_if_no=["Y"],
)
ONE_SIDED = Discriminator(
    device_type="air_conditioner",
    question_vi="Câu hỏi chỉ chạm một bên?",
    favours_if_yes=["A"],
    favours_if_no=["Z"],
)


def test_a_hand_written_question_is_preferred_over_a_templated_one():
    questions = clarifier.build_questions(
        [A, B], "máy lạnh hỏng", discriminators=[CLEANED]
    )

    assert questions[0].text_vi == CLEANED.question_vi


def test_a_question_touching_neither_candidate_is_skipped():
    questions = clarifier.build_questions(
        [A, B], "máy lạnh hỏng", discriminators=[IRRELEVANT]
    )

    assert all(q.text_vi != IRRELEVANT.question_vi for q in questions)


def test_a_question_whose_other_side_is_empty_is_skipped():
    """Both sides must intersect the shortlist, or an answer rules nothing out."""
    questions = clarifier.build_questions(
        [A, B], "máy lạnh hỏng", discriminators=[ONE_SIDED]
    )

    assert all(q.text_vi != ONE_SIDED.question_vi for q in questions)


def test_templated_questions_fill_the_remaining_slots():
    questions = clarifier.build_questions(
        [A, B], "máy lạnh hỏng", discriminators=[CLEANED], limit=3
    )

    assert len(questions) > 1
    assert questions[0].text_vi == CLEANED.question_vi


def test_no_duplicate_questions():
    questions = clarifier.build_questions(
        [A, B, C], "máy lạnh hỏng", discriminators=[CLEANED]
    )
    texts = [q.text_vi for q in questions]

    assert len(texts) == len(set(texts))


# ------------------------------------------------------- fallback

def test_knowing_the_device_removes_the_question_about_the_device():
    with_device = clarifier.device_questions("Máy lạnh")
    without = clarifier.device_questions(None)

    assert any("loại nào" in q for q in without)
    assert all("loại nào" not in q for q in with_device)
    assert any("Máy lạnh" in q for q in with_device)


@pytest.mark.parametrize("description", ["", "   ", "hư rồi"])
def test_an_empty_description_does_not_break_anything(description):
    assert clarifier.build_questions([A, B], description)
