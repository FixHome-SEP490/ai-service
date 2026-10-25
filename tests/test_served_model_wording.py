"""Wording the served model produced on 25/10/2026, put right before it is shown."""

from app.services.pipeline.qwen_client import _fix_pronouns

SEEN = (
    "Em đã đọc thông tin khách gửi. Em đã kiểm tra và xác nhận rằng máy lạnh của anh/chị "
    "đang hư hỏng ở phần máy nén. Khách nên ngắt nguồn máy lạnh và không bật lại. "
    "Em sẽ chủ động mời khách đặt dịch vụ \"Sửa điều hòa\"."
)


def test_no_verdict_the_assistant_cannot_have_reached():
    fixed = _fix_pronouns(SEEN)
    assert "xác nhận" not in fixed
    assert "Theo những gì anh/chị kể, có thể máy lạnh" in fixed


def test_the_customer_is_spoken_to_not_about():
    fixed = _fix_pronouns(SEEN)
    assert "khách" not in fixed.lower()
    assert "Anh/chị nên ngắt nguồn" in fixed
    assert "Anh/chị có thể đặt dịch vụ" in fixed


def test_the_instruction_read_back_is_dropped():
    fixed = _fix_pronouns(SEEN)
    assert not fixed.startswith("Em đã đọc")
    assert fixed.startswith("Theo những gì anh/chị kể")


def test_an_ordinary_answer_is_left_alone():
    plain = "Dạ máy lạnh không mát có thể do thiếu gas. Anh/chị nên vệ sinh lưới lọc trước."
    assert _fix_pronouns(plain) == plain


def test_no_chinese_letters_reach_the_customer():
    from app.services.pipeline.qwen_client import _fix_spelling

    seen = "Em khuyên anh/chị nên đặt dịch vụ sửa máy giặt ngay để đảm bảo máy恢复正常 hoạt động."
    fixed = _fix_spelling(seen)
    assert fixed == "Em khuyên anh/chị nên đặt dịch vụ sửa máy giặt ngay để đảm bảo máy hoạt động."


def test_the_read_and_checked_opening_is_dropped_too():
    fixed = _fix_pronouns("Em đã đọc và kiểm tra thông tin anh/chị gửi. Máy giặt có thể mòn bạc đạn.")
    assert fixed == "Máy giặt có thể mòn bạc đạn."
