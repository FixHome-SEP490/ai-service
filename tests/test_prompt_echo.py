"""The model must not read the prompt back to the customer.

Found by running the 564-case suite against the served model rather than a stub:
six of the 471 answers it wrote opened with "Khách: <the question>" followed by
"Trả lời dựa trên tài liệu trên:". That is the shape of the worked dialogues in
the corpus and of the instruction wrapped around the passages, and a 3B model
shown a question-and-answer layout completes the layout.

All six were price questions, where the price table is placed first and its rows
read most like a form to be filled in.

Handled after generation rather than in the prompt, for the same reason as the
apology: shown a prohibition, a model this size prints the prohibition.
"""

import pytest

from app.services.pipeline.qwen_client import _strip_prompt_echo

# Verbatim from the suite run, so the test fails if the fix stops covering the
# thing it was written for.
REAL_LEAKS = [
    (
        "Khách: Thay ổ cắm hết bao nhiêu tiền?\n\nTrả lời dựa trên tài liệu trên:"
        "\n\n- Tiền công — Thay ổ cắm điện, tiền công: 100.000đ một cái.",
        "- Tiền công — Thay ổ cắm điện, tiền công: 100.000đ một cái.",
    ),
    (
        "Khách: bao lâu nên vệ sinh máy lạnh một lần\n\nTrả lời: Máy lạnh nên vệ "
        "sinh khoảng ba đến sáu tháng một lần.",
        "Máy lạnh nên vệ sinh khoảng ba đến sáu tháng một lần.",
    ),
    (
        "Khách: Bảo hành bao lâu?\n\nTrả lời: Bảo hành công và bảo hành linh kiện "
        "có thời hạn riêng.",
        "Bảo hành công và bảo hành linh kiện có thời hạn riêng.",
    ),
]


@pytest.mark.parametrize("raw,expected", REAL_LEAKS)
def test_the_question_and_answer_labels_are_removed(raw, expected):
    assert _strip_prompt_echo(raw) == expected


def test_an_answer_that_is_only_the_frame_becomes_empty():
    """One of the six echoed the frame twice and never reached an answer.

    Returning the fragment would show the customer a sentence about documents.
    Returning nothing is correct: the caller already falls back to the retrieved
    passages when generation comes back empty — worse prose, right content.
    """
    raw = (
        "Khách: block máy lạnh 12000 btu giá nhiêu\n\n"
        "Trả lời dựa trên tài liệu trên:\n\nKhách: block máy lạnh 12000 btu"
    )
    assert _strip_prompt_echo(raw) == ""


@pytest.mark.parametrize(
    "text",
    [
        "Dạ có ạ.",
        "Máy lạnh nên vệ sinh ba tới sáu tháng một lần ạ.",
        "Dạ mùi khét là dấu hiệu gấp, anh/chị ngắt aptomat giúp em ạ.",
        # The word appears mid-sentence as ordinary Vietnamese, not as a label.
        "Anh/chị trả lời giúp em là máy có kêu không ạ.",
        "Khách hàng nào cũng được bảo hành như nhau ạ.",
    ],
)
def test_a_real_answer_is_left_alone(text):
    """Only a label at the front, and only whole lines of it.

    "Khách hàng" opens with the same four letters as the label and is an ordinary
    subject; cutting on the word rather than on the label followed by a colon
    would have removed the first sentence of a correct answer.
    """
    assert _strip_prompt_echo(text) == text


def test_stripping_is_applied_wherever_the_model_answers():
    """Three call sites compose the guards; all three must include this one.

    The apology stripper was added to one and missed another for a week, which
    is why this checks the source rather than trusting the three to stay in step.
    """
    from pathlib import Path

    source = Path("app/services/pipeline/qwen_client.py").read_text(encoding="utf-8")
    composed = source.count("_strip_prompt_echo(raw.strip())")
    guarded = source.count("_strip_apology(_strip_prompt_echo")
    assert composed == 3, composed
    assert guarded == 3, guarded
