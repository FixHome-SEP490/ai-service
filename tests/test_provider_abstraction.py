import pytest

from app.schemas.chat import AnswerStatus, ChatRequest
from app.schemas.diagnosis import DiagnosisRequest, DiagnosisStatus, Engine, UrgencyLevel
from app.services.ai_provider import MockAIProvider


@pytest.mark.asyncio
async def test_mock_provider_satisfies_diagnosis_contract():
    provider = MockAIProvider()
    request = DiagnosisRequest(description="Quạt kêu cộc cộc, quay chậm hơn lúc trước")

    response = await provider.diagnose(request)

    assert response.status == DiagnosisStatus.OK
    assert response.engine == Engine.MOCK
    assert response.suspected_faults
    assert response.recommended_services
    assert response.price_estimate.min <= response.price_estimate.max
    assert response.price_estimate.currency == "VND"
    assert response.urgency in set(UrgencyLevel)
    assert 0.0 <= response.confidence <= 1.0
    assert "kỹ thuật viên" in response.disclaimer_vi


@pytest.mark.asyncio
async def test_mock_provider_answers_chat():
    provider = MockAIProvider()
    response = await provider.answer(ChatRequest(question="Bao lâu vệ sinh máy lạnh?"))

    assert response.status == AnswerStatus.OK
    assert response.answer_vi
    assert response.disclaimer_vi
