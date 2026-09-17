"""Two things the customer noticed before any test did.

Asked to book, the service diagnosed. Asked a follow-up, it forgot the question
it was following up on. Both are conversation failures rather than model
failures, so both are tested without a model.
"""

import pytest

from app.schemas.chat import ChatRequest
from app.schemas.diagnosis import DiagnosisRequest, DiagnosisStatus
from app.services.pipeline.conversation import Conversation
from app.services.pipeline.knowledge_base import get_knowledge_base
from app.services.pipeline.local_pipeline import (
    LocalPipeline,
    _recent_dialogue,
    _standalone_question,
)
from app.services.pipeline.retriever import Retriever
from app.services.pipeline.vlm import StubVlm


class _RecordingVlm(StubVlm):
    """Keeps whatever the pipeline handed it, so a test can look."""

    def __init__(self) -> None:
        self.history_vi = None

    async def answer(self, question, passages_vi, safety_vi=None, history_vi=""):
        self.history_vi = history_vi
        return (passages_vi[0] if passages_vi else safety_vi or "", 0.6)


class _EmptyDetector:
    async def detect(self, image):
        return []


def _pipeline(vlm=None) -> LocalPipeline:
    kb = get_knowledge_base()
    return LocalPipeline(
        detector=_EmptyDetector(),
        vlm=vlm or StubVlm(),
        retriever=Retriever(kb),
        kb=kb,
    )


@pytest.mark.asyncio
async def test_asking_to_book_gets_the_service_not_a_diagnosis():
    """Nobody asked what was wrong.

    "Bây giờ anh muốn đặt lịch vệ sinh máy lạnh" came back as two suspected
    faults, a price range and a list of things to try first — a wall of text
    between the customer and the thing they came to do.
    """
    response = await _pipeline().diagnose(
        DiagnosisRequest(description="bây giờ anh muốn đặt lịch vệ sinh máy lạnh")
    )

    assert response.status == DiagnosisStatus.OK
    assert response.suspected_faults == []
    assert response.recommended_services
    assert response.recommended_services[0].service_code == "VE_SINH_DIEU_HOA_1HP"
    assert "Đặt thợ ngay" in response.message_vi


@pytest.mark.asyncio
async def test_booking_a_repair_names_the_repair_service_not_the_clean():
    """A clean and a repair are different services at different prices."""
    response = await _pipeline().diagnose(
        DiagnosisRequest(description="cho mình đặt thợ sửa tủ lạnh")
    )

    assert response.recommended_services[0].service_code == "SUA_TU_LANH"


@pytest.mark.asyncio
async def test_booking_without_naming_an_appliance_still_asks():
    """"Cho mình đặt lịch" does not say what to book."""
    response = await _pipeline().diagnose(DiagnosisRequest(description="cho mình đặt lịch"))

    assert response.status == DiagnosisStatus.NEEDS_CLARIFICATION


def test_a_follow_up_is_resolved_against_the_message_before_it():
    kb = get_knowledge_base()
    chat = Conversation(session_id="s")
    chat.add("customer", "chi phí thay aptomat máy giặt")
    chat.add("assistant", "...")
    chat.add("customer", "giá bao nhiêu")

    resolved = _standalone_question("giá bao nhiêu", chat, kb)

    assert "aptomat" in resolved
    assert resolved.endswith("giá bao nhiêu")


def test_a_question_that_stands_alone_is_left_alone():
    kb = get_knowledge_base()
    chat = Conversation(session_id="s")
    chat.add("customer", "chi phí thay aptomat máy giặt")
    chat.add("customer", "máy lạnh nhà em không mát nữa")

    assert (
        _standalone_question("máy lạnh nhà em không mát nữa", chat, kb)
        == "máy lạnh nhà em không mát nữa"
    )


@pytest.mark.asyncio
async def test_the_model_is_shown_what_it_already_said():
    """Without the thread the assistant answers the same question twice."""
    vlm = _RecordingVlm()
    pipeline = _pipeline(vlm=vlm)

    first = await pipeline.answer(ChatRequest(question="bảo hành bao lâu"))
    await pipeline.answer(
        ChatRequest(question="còn máy lạnh thì sao", session_id=first.session_id)
    )

    assert vlm.history_vi
    assert "bảo hành bao lâu" in vlm.history_vi
    assert "Khách:" in vlm.history_vi


def test_the_dialogue_keeps_both_sides_in_order():
    chat = Conversation(session_id="s")
    chat.add("customer", "một")
    chat.add("assistant", "hai")
    chat.add("customer", "ba")

    assert _recent_dialogue(chat).splitlines() == ["Khách: một", "Bạn: hai", "Khách: ba"]


@pytest.mark.asyncio
async def test_a_question_still_offers_something_to_book():
    """Analyse and stop is how these conversations died.

    The customer read a question, answered it, was asked again, and never
    reached a booking. Asking and offering are not exclusive.
    """
    response = await _pipeline().diagnose(DiagnosisRequest(description="hư rồi"))

    assert response.status == DiagnosisStatus.NEEDS_CLARIFICATION
    assert response.recommended_services
    assert (
        response.recommended_services[0].service_code
        == "KIEM_TRA_CHAN_DOAN_THIET_BI"
    )


@pytest.mark.asyncio
async def test_an_unsettled_appliance_is_never_offered_a_specific_repair():
    """Two words naming nothing were offered a refrigerator repair.

    The shortlist retrieved for "hư rồi" happened to be all one device, and
    that is not evidence about the customer's appliance.
    """
    response = await _pipeline().diagnose(DiagnosisRequest(description="cứu em với"))

    codes = [s.service_code for s in response.recommended_services]
    assert codes == ["KIEM_TRA_CHAN_DOAN_THIET_BI"]


@pytest.mark.asyncio
async def test_a_chat_answer_about_an_appliance_can_be_booked():
    """The button lives in the chat frame, and the chat frame had no service."""
    response = await _pipeline().answer(
        ChatRequest(question="máy giặt kêu to khi vắt")
    )

    assert response.recommended_services
    assert response.recommended_services[0].service_code == "SUA_MAY_GIAT"


@pytest.mark.asyncio
async def test_a_policy_question_is_not_turned_into_a_sales_pitch():
    """Nobody books a technician after asking how long the warranty lasts."""
    response = await _pipeline().answer(ChatRequest(question="bảo hành bao lâu"))

    assert response.recommended_services == []


def test_the_grounded_answer_speaks_the_same_way_as_every_other():
    """The surface customers actually type into skipped the voice rules.

    "Bạn nên khoá van nước trước, sau đó tôi sẽ trả lời chi tiết hơn" — wrong
    pronoun on both sides of the sentence, from the one path that never ran
    them.
    """
    from app.services.pipeline.qwen_client import (
        _fix_pronouns,
        _fix_spelling,
        _sends_the_customer_away,
        _strip_apology,
    )

    raw = (
        "Xin lỗi, đây là chi phí thay Aptomat máy giặt. "
        "Bạn nên khoá van nước trước, sau đó tôi sẽ trả lời chi tiết hơn."
    )
    cleaned = _fix_spelling(_fix_pronouns(_strip_apology(raw)))

    assert not cleaned.startswith("Xin lỗi")
    assert "Bạn" not in cleaned
    assert "tôi" not in cleaned
    assert "Anh/chị" in cleaned
    assert _sends_the_customer_away("Bạn nên liên hệ với một chuyên gia về điện tử.")


@pytest.mark.parametrize(
    "text",
    [
        "có mùi khét",
        "có nước rò",
        "có tiếng nổ",
        "không lên nguồn",
        "dạ máy lạnh hỏng",
        "máy giặt bị lỗi",
    ],
)
def test_a_fault_report_is_never_mistaken_for_a_greeting(text):
    """The worst bug of the afternoon, and it was silent.

    _is_greeting matched greeting words as prefixes of the folded message, so
    "có mùi khét" — the most dangerous thing a customer can send — was answered
    with "Dạ em chào anh/chị ạ", because "có" folds to "co" and "co" was in the
    list. Whole words only, and only when every word in the message is one.
    """
    from app.services.pipeline.local_pipeline import _is_greeting

    assert not _is_greeting(text)


@pytest.mark.parametrize(
    "text",
    ["alo", "chào em", "em ơi", "có ai không", "ok cảm ơn em", "dạ", "vâng ạ"],
)
def test_a_greeting_is_still_recognised(text):
    from app.services.pipeline.local_pipeline import _is_greeting

    assert _is_greeting(text)


def test_asking_how_the_bill_works_is_inside_the_trade():
    """"Bên mình tính giá sao" was refused as off topic.

    Bare "gia" cannot be a trade word — it lets in the price of gold — but the
    phrase is unambiguous, and how the bill is put together is the commonest
    business question there is.
    """
    pipeline = _pipeline()
    assert pipeline._is_in_the_trade("bên mình tính giá sao")
    assert pipeline._is_in_the_trade("bị lỗi")
    assert not pipeline._is_in_the_trade("giá vàng hôm nay")
    assert not pipeline._is_in_the_trade("bitcoin giá bao nhiêu")


def test_a_washer_and_a_dryer_are_asked_apart():
    """The same photograph, and different faults at different prices.

    A front-load washer and a front-load dryer are a drum behind a round glass
    door. The question has to be about something the customer can see without
    knowing which machine they own.
    """
    from app.services.pipeline import device_hint

    kb = get_knowledge_base()
    question = device_hint.confusion_question("washing_machine", "không vắt", kb)

    assert question is not None
    assert "bột giặt" in question or "nước giặt" in question


@pytest.mark.parametrize(
    "text,expected",
    [
        ("máy sấy quần áo không nóng", ["clothes_dryer"]),
        ("máy sấy nhà em lâu khô", ["clothes_dryer"]),
        ("máy sấy tóc bị cháy khét", []),
        ("tủ sấy quần áo nhà em không nóng", []),
        ("giàn phơi quần áo bị gãy", []),
        ("máy sấy bát", []),
    ],
)
def test_only_a_tumble_dryer_is_a_clothes_dryer(text, expected):
    """"Máy sấy" is four appliances, and the alias list could claim only one.

    It claimed the tumble dryer, so "máy sấy tóc bị cháy khét" arrived as one —
    and a clogged tumble dryer carries a four-step fire warning, which is what
    the customer holding a hair dryer was then given.
    """
    from app.services.pipeline import device_hint

    kb = get_knowledge_base()
    hits = [h.device_type for h in device_hint.devices_named_in(text, kb)]

    assert hits == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        ("nước lọc uống thấy mùi tanh", ["water_purifier"]),
        ("lõi lọc nước hết hạn chưa", ["water_purifier"]),
        # The words that made this risky, and do not collide.
        ("máy lạnh lọc gió bẩn", ["air_conditioner"]),
        ("lưới lọc máy rửa bát bị bít", ["dishwasher"]),
    ],
)
def test_filtered_water_reaches_the_purifier(text, expected):
    """"Nước lọc" is what people call the water, not the machine.

    "Nước lọc uống thấy mùi tanh" named no device, so it was answered with a
    question instead of the cartridge fault written for exactly it. The risk of
    adding the alias is the other filters in the house — the air-conditioner
    filter and the dishwasher strainer — and neither collides.
    """
    from app.services.pipeline import device_hint

    kb = get_knowledge_base()
    hits = [h.device_type for h in device_hint.devices_named_in(text, kb)]

    assert hits == expected


@pytest.mark.parametrize(
    "text,expected",
    [
        # The part, when the machine is never named.
        ("lồng giặt kêu cạch cạch", "washing_machine"),
        ("ngăn đá không đông", "refrigerator"),
        ("ruột ấm đóng cặn trắng", "kettle"),
        ("lưới lọc xơ đầy bông", "clothes_dryer"),
        ("chốt khoá không rút vào", "smart_lock"),
        ("mâm xoay lò vi sóng không quay", "microwave_oven"),
        ("bình gas hết nhanh quá", "gas_stove"),
        ("mặt kính bếp nứt", "induction_hob"),
    ],
)
def test_a_part_names_the_machine_it_belongs_to(text, expected):
    """Customers describe what they can see, and it is rarely the appliance.

    Ten of thirty such phrasings reached no device at all and were answered
    with a question about which appliance was broken — about an appliance the
    customer had just described a part of.
    """
    from app.services.pipeline import device_hint

    kb = get_knowledge_base()
    hits = [h.device_type for h in device_hint.devices_named_in(text, kb)]

    assert hits and hits[0] == expected


def test_aptomat_is_deliberately_not_an_alias():
    """It would take the burning hob away from the hob.

    "Aptomat" is seven characters and "bếp từ" is six, and the longest alias
    wins. Making it a socket alias sends "cắm bếp từ là nhảy aptomat" — which
    carries a safety document about a hob that trips the breaker — to the
    socket instead.
    """
    from app.services.pipeline import device_hint

    kb = get_knowledge_base()
    hits = [h.device_type for h in device_hint.devices_named_in(
        "cắm bếp từ là nhảy aptomat", kb
    )]

    assert hits[0] == "induction_hob"


@pytest.mark.asyncio
async def test_an_unanswerable_trade_question_does_not_send_them_to_support():
    """There is no support desk at the other end of that sentence.

    "Thợ có đeo khẩu trang không" came back as "vui lòng liên hệ bộ phận hỗ trợ
    của FixHome" — a repair company's assistant handing its own customer to
    somebody else over a question that ordinary. The corpus has a document
    telling the model never to say it; the fallback message said it anyway.
    """
    response = await _pipeline().answer(
        ChatRequest(question="thợ có đeo khẩu trang không")
    )

    assert "bộ phận hỗ trợ" not in response.answer_vi
    assert "đặt lịch" in response.answer_vi


@pytest.mark.asyncio
async def test_an_off_topic_question_is_not_invited_to_book_a_repair():
    """The other direction, and it is just as wrong.

    Telling somebody who asked about the weather that a technician will ring
    them is worse than the sentence it replaced.
    """
    response = await _pipeline().answer(
        ChatRequest(question="thời tiết hôm nay thế nào")
    )

    assert "đặt lịch" not in response.answer_vi
    assert "chỉ hỗ trợ" in response.answer_vi


@pytest.mark.asyncio
@pytest.mark.parametrize("text", ["hỏng", "sửa đi", "hư rồi", "cứu em với"])
async def test_with_no_appliance_it_asks_which_appliance(text):
    """Not a symptom taken from somebody else's machine.

    With nothing settled, the shortlist spans every device the words happened
    to touch. "Hỏng" was answered with "Thiết bị có hiện tượng block không lên
    không?" — a compressor, in trade slang, to someone who had typed one word.
    "Sửa đi" got "Thiết bị có hiện tượng Quạt bò không?", which is not a
    sentence. The thing actually missing is the appliance, and that is a
    question anybody can answer.
    """
    response = await _pipeline().diagnose(DiagnosisRequest(description=text))

    assert response.status == DiagnosisStatus.NEEDS_CLARIFICATION
    questions = response.clarification.questions_vi
    assert questions[0] == "Thiết bị gặp sự cố là loại nào?"
    assert not any("block" in q for q in questions)


def test_a_symptom_never_arrives_capitalised_mid_sentence():
    from app.services.pipeline.clarifier import _phrase

    assert _phrase("Quạt bò") == "Thiết bị có hiện tượng quạt bò không?"
    assert _phrase("kêu cộc cộc") == "Thiết bị có hiện tượng kêu cộc cộc không?"
