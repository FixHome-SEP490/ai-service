"""The served model's answers from 25/10/2026, as the customer is shown them.

Every input here is a sentence the served Qwen2.5-VL-3B wrote in the chat
suite, the live dialogues or the multi-appliance run. tools/audit_wording.py
counted the faults on all 1,232 of them: 95.2 percent had at least one.
"""

from app.services.pipeline.qwen_client import _loops, _services_in, _tidy_answer


def test_the_assistant_does_not_promise_to_book():
    seen = (
        "Có khả năng hư hỏng là máy lọc nước rò rỉ nước. Anh/chị nên khóa van cấp nước vào máy. "
        "Em sẽ đặt dịch vụ sửa chữa máy lọc nước cho anh/chị."
    )
    fixed = _tidy_answer(seen, services=("Sửa máy lọc nước",))
    assert "Em sẽ đặt" not in fixed
    assert fixed.endswith('Anh/chị bấm Đặt thợ để đặt dịch vụ "Sửa máy lọc nước", thợ FixHome sẽ tới kiểm tra ạ.')


def test_the_offer_names_the_service_the_button_books_not_the_models_guess():
    seen = 'Em sẽ đặt lịch thợ với dịch vụ "Fix Home" để anh/chị có thể lựa chọn đúng tên dịch vụ được cho.'
    fixed = _tidy_answer(seen, services=("Sửa tivi",))
    assert "Fix Home" not in fixed
    assert "đúng tên dịch vụ" not in fixed
    assert '"Sửa tivi"' in fixed


def test_nothing_is_offered_when_the_repair_is_not_open():
    seen = (
        "Anh/chị nên thử tai nghe hoặc loa ngoài. Em sẽ đặt thợ đến tận nơi để kiểm tra. "
        'Anh/chị có thể đặt dịch vụ này với tên gọi "FixHome".'
    )
    fixed = _tidy_answer(seen, services=())
    assert "Đặt thợ" not in fixed
    assert "FixHome" not in fixed
    assert fixed == "Anh/chị nên thử tai nghe hoặc loa ngoài."


def test_a_second_promise_is_dropped_not_offered_twice():
    seen = (
        "Em sẽ đặt lịch sửa chữa cho anh/chị với dịch vụ Sửa điều hòa. "
        "Em sẽ giúp anh/chị đặt lịch và đảm bảo rằng dịch vụ được thực hiện."
    )
    fixed = _tidy_answer(seen, services=("Sửa điều hòa",))
    assert fixed.count("Đặt thợ") == 1
    assert "Em sẽ giúp" not in fixed


def test_the_instruction_is_not_read_back_after_a_greeting_or_a_heading():
    seen = (
        "Dạ anh/chị yên tâm, em xem giúp ngay ạ. Em đã đọc và kiểm tra thông tin anh/chị gửi. "
        "Có khả năng hư hỏng là lỏng mặt nạ."
    )
    assert _tidy_answer(seen) == "Dạ anh/chị yên tâm, em xem giúp ngay ạ. Có khả năng hư hỏng là lỏng mặt nạ."
    section = "Về quạt trần: Em đã đọc và kiểm tra thông tin anh/chị gửi. Có khả năng hư hỏng là khô dầu."
    assert _tidy_answer(section) == "Về quạt trần: Có khả năng hư hỏng là khô dầu."


def test_the_label_read_as_a_sentence_keeps_the_finding():
    seen = "Anh/chị đang nói về hư hỏng máy nén trong máy lạnh."
    assert _tidy_answer(seen) == "Em hiểu anh/chị đang hỏi về hư hỏng máy nén trong máy lạnh."


def test_a_price_with_no_upper_end_is_said_as_a_floor():
    broken = "Chi phí sẽ dao động từ 279.000đ đến khi kỹ thuật viên kiểm tra tận nơi."
    assert _tidy_answer(broken) == "Chi phí từ 279.000đ, thợ kiểm tra tận nơi rồi mới báo giá chính xác."
    estimate = "Chi phí khoảng 799.000đ, phần còn lại kỹ thuật viên phải xem tận nơi mới tính được."
    assert _tidy_answer(estimate).startswith("Chi phí từ 799.000đ, phần còn lại")


def test_no_alarm_words_and_fault_names_read_mid_sentence():
    seen = "Có khả năng hư hỏng là Hỏng rơ le nhiệt hoặc Hỏng thanh đốt. Anh/chị tắt nguồn ngay lập tức."
    assert _tidy_answer(seen) == "Có khả năng hư hỏng là hỏng rơ le nhiệt hoặc hỏng thanh đốt. Anh/chị tắt nguồn ngay."


def test_filler_and_notes_meant_for_the_assistant_are_dropped():
    seen = (
        "Anh/chị nên khóa van bình gas ngay. Em sẽ đảm bảo rằng anh/chị được tư vấn và hỗ trợ tốt nhất có thể. "
        "Đầu tiên, hãy hỏi khách về có trẻ nhỏ trong nhà hay không. Chúc anh/chị may mắn!"
    )
    assert _tidy_answer(seen) == "Anh/chị nên khóa van bình gas ngay."


def test_the_customer_is_addressed_not_described():
    assert _tidy_answer("Dạ, khách, bồn cầu xả yếu có thể do nghẹt.") == "Dạ, bồn cầu xả yếu có thể do nghẹt."
    assert _tidy_answer("Việc khách cần làm ngay là kiểm tra cửa máy.") == "Việc anh/chị cần làm ngay là kiểm tra cửa máy."


def test_a_repeated_sentence_is_said_once():
    seen = "Anh/chị nên rút phích cắm trước khi kiểm tra. Anh/chị nên rút phích cắm trước khi kiểm tra."
    assert _tidy_answer(seen) == "Anh/chị nên rút phích cắm trước khi kiểm tra."


def test_an_answer_stuck_in_a_loop_is_recognised():
    line = "Nếu ổ cắm đang có dấu hiệu báo trước, hãy hỏi về dấu hiệu báo trước của ổ cắm. "
    assert _loops(line * 4)
    assert not _loops("Anh/chị nên rút phích cắm. Có thể do hỏng tụ. Chi phí từ 199.000đ.")


def test_the_services_are_read_from_the_facts():
    facts = "- máy: máy lạnh\n- lỗi: thiếu gas\n- dịch vụ: Sửa điều hòa | Vệ sinh điều hòa"
    assert _services_in(facts) == ("Sửa điều hòa", "Vệ sinh điều hòa")
    assert _services_in("- máy: tivi\n- lỗi: hỏng loa") == ()


def test_the_data_handed_back_is_not_an_answer():
    from app.services.pipeline.qwen_client import _reads_back_the_data

    # fixhome.sbs, 25/10/2026, the served model with the first wording of the facts.
    seen = (
        "Có thể hỏng: mòn bạc đạn lồng giặt hoặc không vắt. Chi phí tham khảo: từ 529.000đ. "
        "Anh/chị có thể làm trước: Giảm tải mỗi mẻ giặt. Dịch vụ để đặt: Sửa máy giặt"
    )
    assert _reads_back_the_data(seen)
    assert _reads_back_the_data("- lỗi: mòn bạc đạn\n- giá: từ 529.000đ")
    assert not _reads_back_the_data(
        "Dạ, máy giặt kêu to khi vắt có thể do mòn bạc đạn ạ. Chi phí tham khảo từ 529.000đ."
    )
    # The served model, 28/10/2026: the facts' separator copied into the prose.
    assert _reads_back_the_data(
        "Dạ, thiết bị vệ sinh nhà mình có thể bị hỏng lõi vòi trộn hoặc mòn gioăng, rò rỉ vòi nước | rò rỉ chân vòi, mối nối."
    )


def test_a_good_answer_is_left_as_it_is():
    good = (
        "Máy lạnh chảy nước có thể do nghẹt ống thoát nước dàn lạnh. Chi phí tham khảo từ 199.000đ đến 349.000đ. "
        "Anh/chị có thể tắt máy và lau khô sàn trước."
    )
    assert _tidy_answer(good, services=("Sửa điều hòa",)) == good


def test_a_symptom_is_not_an_answer_to_the_microwave_question():
    from app.services.pipeline import device_hint
    from app.services.pipeline.knowledge_base import get_knowledge_base

    kb = get_knowledge_base()
    for said in ("nó không nóng luôn em", "có nguy hiểm không em", "mà nó đánh lửa"):
        assert device_hint.resolve_confusion_answer(said, "microwave_oven", kb) is None, said
    assert device_hint.resolve_confusion_answer("dạ không có", "microwave_oven", kb) == "oven"
    assert device_hint.resolve_confusion_answer("có ạ", "microwave_oven", kb) == "microwave_oven"
