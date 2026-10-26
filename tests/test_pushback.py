"""The assistant notices, in the conversation, that the customer says it was wrong.

PO 26/10/2026: no "Chưa đúng" button. "Sai rồi", "không phải bệnh đó", "em
đoán chưa đúng" are what a customer who disagrees actually writes; the reply
to that turn carries `customerDisagreed` so Backend can keep it for
tools/feedback_review.py, and the assistant reads the rest of the turn as the
customer's own account instead of moving down the list it already had.
"""

import asyncio

import pytest

from app.schemas.chat import ChatRequest
from app.schemas.diagnosis import DiagnosisRequest
from app.services.pipeline import service_catalog as sc
from app.services.pipeline.knowledge_base import get_knowledge_base
from app.services.pipeline.local_pipeline import LocalPipeline
from app.services.pipeline.retriever import Retriever
from app.services.pipeline.vlm import StubVlm

KB = get_knowledge_base()


class _NoDetector:
    async def detect(self, image):
        return []


def _pipeline():
    sc.install(sc.LiveCatalog())
    return LocalPipeline(detector=_NoDetector(), vlm=StubVlm(), retriever=Retriever(KB), kb=KB)


def _two_turns(first, second, ask=False):
    async def run():
        pipeline = _pipeline()
        one = await pipeline.diagnose(DiagnosisRequest(description=first))
        if ask:
            two = await pipeline.answer(ChatRequest(question=second, session_id=one.session_id))
        else:
            two = await pipeline.diagnose(DiagnosisRequest(description=second, session_id=one.session_id))
        return one, two

    return asyncio.run(run())


@pytest.mark.parametrize(
    "first, second",
    [
        ("máy lạnh chạy mà không mát", "không phải đâu em"),
        ("tủ lạnh kêu to", "nói sai rồi em ơi"),
        ("tủ lạnh ngăn mát không lạnh", "em đoán chưa đúng rồi, ngăn đá cũng không đông"),
        ("máy giặt kêu to", "e đoán sai rồi, nó kêu lúc cấp nước thôi"),
        ("quạt điện không quay", "ủa em ơi sai rồi"),
        ("tủ lạnh kêu to", "chẩn đoán sai rồi"),
        ("bình nóng lạnh không nóng", "không phải do điện đâu, đèn vẫn sáng"),
    ],
)
def test_a_customer_saying_the_answer_is_wrong_is_noticed(first, second):
    one, two = _two_turns(first, second)
    noticed = two.customer_disagreed
    assert noticed is not None, second
    assert noticed.kind == "fault"
    assert noticed.rejected == [one.suspected_faults[0].fault_code]
    assert noticed.rejected_vi == [one.suspected_faults[0].name_vi]
    assert noticed.said_vi == first
    assert noticed.correction_vi == second
    assert noticed.rejected[0] not in [f.fault_code for f in two.suspected_faults]


@pytest.mark.parametrize(
    "first, second",
    [
        ("máy giặt không vắt", "không dùng được nữa luôn"),
        ("máy giặt không vắt", "chưa dùng lần nào từ hôm qua"),
        ("tủ lạnh không lạnh", "em nhầm, là tủ đông"),
        ("máy lạnh không mát", "máy báo sai giờ hẹn giờ"),
        ("máy lạnh không mát", "không, em chưa vệ sinh"),
        ("máy lạnh không mát", "em nói đúng rồi"),
        ("máy lạnh không mát", "đúng rồi, cảm ơn em"),
        ("máy lạnh không mát", "nó còn kêu to nữa"),
        ("quạt trần quay yếu", "không phải quạt trần mà là quạt đứng"),
    ],
)
def test_an_ordinary_follow_up_is_not_taken_for_one(first, second):
    _one, two = _two_turns(first, second)
    assert two.customer_disagreed is None, second


def test_a_question_saying_so_is_noticed_too():
    _one, two = _two_turns("máy lạnh chạy mà không mát", "sai rồi, vậy là bị gì?", ask=True)
    assert two.customer_disagreed is not None


def test_the_rest_of_the_turn_is_read_as_the_account():
    """ "Sai rồi, ..." then the right symptom: the old reading stops counting."""
    _one, two = _two_turns("máy giặt kêu to", "không phải bệnh đó, máy kêu lúc cấp nước")
    assert two.suspected_faults[0].fault_code == "WM_NO_WATER_INLET"


def test_turning_down_one_cause_keeps_the_symptom():
    """ "Đầu lọc thì kiểm tra rồi, không sao" rules out a cause, not the story."""
    _one, two = _two_turns("vòi nước nhà mình nước chảy yếu", "đầu lọc thì nhà mình kiểm tra rồi, không sao")
    assert two.suspected_faults and two.suspected_faults[0].fault_code == "FAUCET_CARTRIDGE"


def test_it_is_said_once():
    async def run():
        pipeline = _pipeline()
        one = await pipeline.diagnose(DiagnosisRequest(description="máy lạnh chạy mà không mát"))
        two = await pipeline.diagnose(DiagnosisRequest(description="không phải đâu em", session_id=one.session_id))
        three = await pipeline.diagnose(DiagnosisRequest(description="nó còn kêu to nữa", session_id=one.session_id))
        return two, three

    two, three = asyncio.run(run())
    assert two.customer_disagreed is not None
    assert three.customer_disagreed is None


def test_it_travels_as_camel_case():
    _one, two = _two_turns("máy lạnh chạy mà không mát", "không phải đâu em")
    body = two.model_dump(by_alias=True)
    assert set(body["customerDisagreed"]) == {"kind", "rejected", "rejectedVi", "saidVi", "correctionVi"}
