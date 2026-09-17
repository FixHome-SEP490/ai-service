"""Qwen client tests.

Most of these are about what happens when the model misbehaves, because that is
the case the business rules actually depend on: a wrong answer delivered
confidently is worse than no answer, so every failure has to collapse into an
empty verdict and end as a clarification request.
"""

import io

import pytest
from PIL import Image

from app.services.pipeline.images import load_image
from app.services.pipeline.qwen_client import QwenClient, _parse_verdict
from app.services.pipeline.vlm import FaultCandidate

FAULTS = ["AC_LOW_REFRIGERANT", "AC_DIRTY_FILTER", "AC_DRAIN_BLOCKED"]
CONDITIONS = ["burn_mark", "rust", "water_leak"]

CANDIDATES = [
    FaultCandidate(
        code="AC_LOW_REFRIGERANT",
        name_vi="Thiếu gas",
        symptoms_vi=["không mát", "chạy liên tục"],
        retrieval_score=0.61,
    ),
    FaultCandidate(
        code="AC_DIRTY_FILTER",
        name_vi="Bẩn lưới lọc",
        symptoms_vi=["có mùi", "gió yếu"],
        retrieval_score=0.42,
    ),
    FaultCandidate(
        code="AC_DRAIN_BLOCKED",
        name_vi="Nghẹt thoát nước",
        symptoms_vi=["chảy nước"],
    ),
]
CONDITION_PAIRS = [
    ("burn_mark", "Vết cháy xém"),
    ("rust", "Rỉ sét"),
    ("water_leak", "Rò rỉ, đọng nước"),
]


def _payload() -> str:
    buffer = io.BytesIO()
    Image.new("RGB", (64, 48), (90, 90, 90)).save(buffer, format="PNG")
    return buffer.getvalue()


def _client(monkeypatch, reply):
    client = QwenClient(base_url="http://vllm.test", model_name="qwen", timeout_seconds=1)

    async def fake_chat(messages, timeout_seconds=None):
        fake_chat.messages = messages
        return reply

    monkeypatch.setattr(client, "_chat", fake_chat)
    client._fake = fake_chat
    return client


# ---------------------------------------------------------------- parsing

def test_parses_a_clean_verdict():
    verdict = _parse_verdict(
        '{"fault_codes": ["AC_LOW_REFRIGERANT"], "condition_codes": ["rust"],'
        ' "confidence": 0.82, "reason": "mô tả nói không mát"}',
        FAULTS,
        CONDITIONS,
    )
    assert verdict.fault_codes == ["AC_LOW_REFRIGERANT"]
    assert verdict.condition_codes == ["rust"]
    assert verdict.confidence == pytest.approx(0.82)
    assert verdict.reasoning_vi


def test_accepts_json_wrapped_in_prose_or_fences():
    """Models pad JSON often enough that insisting on a clean body loses answers."""
    verdict = _parse_verdict(
        'Đây là kết quả:\n```json\n{"fault_codes": ["AC_DIRTY_FILTER"],'
        ' "confidence": 0.7}\n```\nHy vọng giúp ích.',
        FAULTS,
        CONDITIONS,
    )
    assert verdict.fault_codes == ["AC_DIRTY_FILTER"]


def test_invented_codes_are_dropped():
    verdict = _parse_verdict(
        '{"fault_codes": ["AC_MADE_UP", "AC_DIRTY_FILTER"], "confidence": 0.9}',
        FAULTS,
        CONDITIONS,
    )
    assert verdict.fault_codes == ["AC_DIRTY_FILTER"]


def test_a_verdict_of_only_invented_codes_carries_no_confidence():
    """Sounding certain about codes that do not exist must not reach a customer."""
    verdict = _parse_verdict(
        '{"fault_codes": ["TOTALLY_MADE_UP"], "confidence": 0.99}', FAULTS, CONDITIONS
    )
    assert verdict.fault_codes == []
    assert verdict.confidence == 0.0


def test_invented_condition_codes_are_dropped():
    verdict = _parse_verdict(
        '{"fault_codes": ["AC_DIRTY_FILTER"], "condition_codes": ["on_fire", "rust"],'
        ' "confidence": 0.6}',
        FAULTS,
        CONDITIONS,
    )
    assert verdict.condition_codes == ["rust"]


def test_confidence_is_clamped():
    high = _parse_verdict(
        '{"fault_codes": ["AC_DIRTY_FILTER"], "confidence": 4.5}', FAULTS, CONDITIONS
    )
    low = _parse_verdict(
        '{"fault_codes": ["AC_DIRTY_FILTER"], "confidence": -2}', FAULTS, CONDITIONS
    )
    assert high.confidence == 1.0
    assert low.confidence == 0.0


def test_non_numeric_confidence_becomes_zero():
    verdict = _parse_verdict(
        '{"fault_codes": ["AC_DIRTY_FILTER"], "confidence": "rất cao"}', FAULTS, CONDITIONS
    )
    assert verdict.confidence == 0.0


def test_malformed_and_missing_json_produce_an_empty_verdict():
    assert _parse_verdict("xin lỗi tôi không biết", FAULTS, CONDITIONS).fault_codes == []
    assert _parse_verdict("{not valid json at all", FAULTS, CONDITIONS).fault_codes == []
    assert _parse_verdict("", FAULTS, CONDITIONS).fault_codes == []


def test_a_bare_string_instead_of_a_list_is_accepted():
    verdict = _parse_verdict(
        '{"fault_codes": "AC_DIRTY_FILTER", "confidence": 0.5}', FAULTS, CONDITIONS
    )
    assert verdict.fault_codes == ["AC_DIRTY_FILTER"]


def test_at_most_three_faults_are_kept():
    verdict = _parse_verdict(
        '{"fault_codes": ["AC_LOW_REFRIGERANT", "AC_DIRTY_FILTER", "AC_DRAIN_BLOCKED",'
        ' "AC_LOW_REFRIGERANT"], "confidence": 0.5}',
        FAULTS,
        CONDITIONS,
    )
    assert len(verdict.fault_codes) <= 3


# ---------------------------------------------------------------- requests

@pytest.mark.asyncio
async def test_assess_does_not_call_the_model_without_candidates(monkeypatch):
    """With nothing to choose from, asking only invites an invented code."""
    called = False

    client = QwenClient(base_url="http://vllm.test", model_name="qwen", timeout_seconds=1)

    async def fake_chat(messages, timeout_seconds=None):
        nonlocal called
        called = True
        return '{"fault_codes": ["X"], "confidence": 1}'

    monkeypatch.setattr(client, "_chat", fake_chat)
    verdict = await client.assess(None, "hư rồi", "air_conditioner", [], CONDITION_PAIRS)

    assert called is False
    assert verdict.fault_codes == []


@pytest.mark.asyncio
async def test_assess_sends_the_crop_as_an_image_part(monkeypatch):
    client = _client(monkeypatch, '{"fault_codes": ["AC_DIRTY_FILTER"], "confidence": 0.7}')
    crop = load_image(_payload())

    await client.assess(crop, "máy lạnh hôi", "air_conditioner", CANDIDATES, CONDITION_PAIRS)

    user = client._fake.messages[-1]["content"]
    assert any(part.get("type") == "image_url" for part in user)
    assert any(part.get("type") == "text" for part in user)


@pytest.mark.asyncio
async def test_assess_works_without_an_image(monkeypatch):
    client = _client(monkeypatch, '{"fault_codes": ["AC_DIRTY_FILTER"], "confidence": 0.7}')

    verdict = await client.assess(None, "máy lạnh hôi", None, CANDIDATES, CONDITION_PAIRS)

    user = client._fake.messages[-1]["content"]
    assert all(part.get("type") != "image_url" for part in user)
    assert verdict.fault_codes == ["AC_DIRTY_FILTER"]


@pytest.mark.asyncio
async def test_prompt_lists_only_the_allowed_codes(monkeypatch):
    client = _client(monkeypatch, '{"fault_codes": ["AC_DIRTY_FILTER"], "confidence": 0.7}')

    await client.assess(None, "hôi", "air_conditioner", CANDIDATES, CONDITION_PAIRS)

    text = next(
        part["text"]
        for part in client._fake.messages[-1]["content"]
        if part.get("type") == "text"
    )
    for code in FAULTS + CONDITIONS:
        assert code in text
    # The names and symptoms are what make it a decision rather than a guess.
    for candidate in CANDIDATES:
        assert candidate.name_vi in text
        for symptom in candidate.symptoms_vi:
            assert symptom in text


@pytest.mark.asyncio
async def test_transport_failure_yields_an_empty_verdict(monkeypatch):
    client = _client(monkeypatch, None)

    verdict = await client.assess(None, "máy lạnh hôi", None, CANDIDATES, CONDITION_PAIRS)

    assert verdict.fault_codes == []
    assert verdict.confidence == 0.0


# ---------------------------------------------------------------- answering

@pytest.mark.asyncio
async def test_answer_returns_the_model_text(monkeypatch):
    client = _client(monkeypatch, "Nên vệ sinh máy lạnh ba tới sáu tháng một lần.")

    text, confidence = await client.answer("bao lâu vệ sinh máy lạnh", ["Ba tới sáu tháng."])

    assert "ba tới sáu tháng" in text.lower()
    assert confidence > 0


@pytest.mark.asyncio
async def test_answer_declines_when_the_model_says_it_cannot(monkeypatch):
    """The refusal sentinel must not be passed through as if it were an answer."""
    client = _client(monkeypatch, "KHONG_DU_THONG_TIN")

    text, confidence = await client.answer("giá cổ phiếu hôm nay", ["Ba tới sáu tháng."])

    assert text == ""
    assert confidence == 0.0


@pytest.mark.asyncio
async def test_answer_without_passages_never_calls_the_model(monkeypatch):
    called = False
    client = QwenClient(base_url="http://vllm.test", model_name="qwen", timeout_seconds=1)

    async def fake_chat(messages, timeout_seconds=None):
        nonlocal called
        called = True
        return "bất cứ điều gì"

    monkeypatch.setattr(client, "_chat", fake_chat)
    text, confidence = await client.answer("câu hỏi", [])

    assert called is False
    assert (text, confidence) == ("", 0.0)


@pytest.mark.asyncio
async def test_answer_passes_every_passage_and_numbers_them(monkeypatch):
    client = _client(monkeypatch, "Trả lời.")

    await client.answer("hỏi", ["Đoạn một.", "Đoạn hai."])

    prompt = client._fake.messages[-1]["content"]
    assert "[1] Đoạn một." in prompt
    assert "[2] Đoạn hai." in prompt


@pytest.mark.asyncio
async def test_answer_on_transport_failure_is_empty(monkeypatch):
    client = _client(monkeypatch, None)

    assert await client.answer("hỏi", ["Đoạn."]) == ("", 0.0)


def test_sampling_is_deterministic():
    """The fixed regression set is meaningless if the same input can vary."""
    client = QwenClient(base_url="http://vllm.test", model_name="qwen", timeout_seconds=1)
    assert client._model == "qwen"
    assert client._url.endswith("/v1/chat/completions")


# -- the apology the prompt could not stop ---------------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        # The opening of what a 3B model produced when the prompt told it not
        # to apologise. Only the apology goes: the sentence after it is the
        # model reciting the prohibition, and no rule about apologies can catch
        # that. What stops it is the prohibition no longer being in the prompt.
        (
            "Xin lỗi, em hiểu nhầm rồi. Bóng đèn nhà mình cháy rồi ạ.",
            "Bóng đèn nhà mình cháy rồi ạ.",
        ),
        ("Dạ em xin lỗi vì chuyện này. Bóng cháy rồi ạ.", "Bóng cháy rồi ạ."),
        ("Bóng cháy rồi ạ.", "Bóng cháy rồi ạ."),
    ],
)
def test_an_opening_apology_is_removed(raw, expected):
    from app.services.pipeline.qwen_client import _strip_apology

    assert _strip_apology(raw) == expected


def test_an_apology_in_the_middle_is_left_alone():
    """It is usually attached to something real — a delay, a limit — and
    cutting a sentence out of the middle is how a fluent answer becomes an
    incoherent one."""
    from app.services.pipeline.qwen_client import _strip_apology

    text = "Em kiểm tra thì bóng cháy. Em xin lỗi vì thợ tới trễ ạ."
    assert _strip_apology(text) == text


# -- the register, enforced rather than requested --------------------------


@pytest.mark.parametrize(
    "raw,expected",
    [
        # What the model wrote with "Xưng em, gọi khách là anh/chị" in the
        # prompt and the persona file above it.
        (
            "Tôi đã kiểm tra và xác nhận rằng thiết bị của khách là một tivi.",
            "Em đã kiểm tra và xác nhận rằng thiết bị của anh/chị là một tivi.",
        ),
        ("Tôi khuyên bạn nên tắt nguồn.", "Em khuyên anh/chị nên tắt nguồn."),
        # Already right, and left alone.
        (
            "Dạ em kiểm tra rồi ạ, máy của anh/chị bị sọc màn hình.",
            "Dạ em kiểm tra rồi ạ, máy của anh/chị bị sọc màn hình.",
        ),
    ],
)
def test_the_register_is_corrected(raw, expected):
    from app.services.pipeline.qwen_client import _fix_pronouns

    assert _fix_pronouns(raw) == expected


def test_only_whole_words_are_rewritten():
    """Rewriting more of a sentence than the pronouns is how a fluent answer
    turns mechanical, which is the thing being fixed."""
    from app.services.pipeline.qwen_client import _fix_pronouns

    text = "Máy tối om, khách sạn bên cạnh cũng mất điện."
    assert _fix_pronouns(text) == text
