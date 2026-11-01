"""Every service Backend has open can be booked by saying what you want done.

PO 01/11/2026: a customer asked for "dịch vụ vệ sinh tủ lạnh" and was offered
"Sửa tủ lạnh". The catalogue sells the cleaning; the assistant could not reach
it. Measured the same day on the 58 sentences of
tools/service_understanding_cases.py: 27 got the right service first, and 12 of
the 37 open services were reached by no wording at all, because a cleaning, an
installation or a move is not a fault and services were only found through
faults. After asking what work is wanted (service_catalog.asked_kind): all of
them.
"""

import asyncio

import pytest

from app.schemas.diagnosis import DiagnosisRequest
from app.services.pipeline import service_catalog
from app.services.pipeline.knowledge_base import get_knowledge_base
from app.services.pipeline.local_pipeline import LocalPipeline
from app.services.pipeline.retriever import Retriever
from app.services.pipeline.vlm import StubVlm
from tools.service_understanding_cases import CASES

KB = get_knowledge_base()


class _NoDetector:
    async def detect(self, image):
        return []


def _pipeline() -> LocalPipeline:
    return LocalPipeline(detector=_NoDetector(), vlm=StubVlm(), retriever=Retriever(KB), kb=KB)


def _first_service(text: str, pipeline=None, session_id=None):
    pipeline = pipeline or _pipeline()
    reply = asyncio.run(pipeline.diagnose(DiagnosisRequest(description=text, images=[], session_id=session_id)))
    return reply, (reply.recommended_services[0].service_code if reply.recommended_services else None)


@pytest.mark.parametrize("text,expected", CASES)
def test_the_service_asked_for_or_described_comes_first(text, expected):
    _, got = _first_service(text)
    assert got == expected, text


def test_every_open_service_has_a_sentence_that_books_it():
    open_codes = set(service_catalog.snapshot().services)
    covered = {code for _, code in CASES}
    assert open_codes - covered == set(), "a service Backend sells has no sentence in tools/service_understanding_cases.py"


@pytest.mark.parametrize(
    "text,kind",
    [
        ("vệ sinh tủ lạnh", "clean"),
        ("bảo dưỡng máy lọc nước", "clean"),
        ("thay lõi lọc nước", "clean"),
        ("tháo máy lạnh ra vệ sinh", "clean"),
        ("lắp máy giặt mới", "install"),
        ("treo tivi", "install"),
        ("di dời điều hòa sang phòng khác", "move"),
        ("thay bồn cầu", "replace"),
        ("máy lạnh không mát", None),
        # the installation already happened: what is asked for is a repair
        ("máy lạnh mới lắp bị chảy nước", None),
        ("thợ lắp sai nên quạt rung", None),
    ],
)
def test_the_kind_of_work_asked_for_is_read_from_the_words(text, kind):
    assert service_catalog.asked_kind(text) == kind


@pytest.mark.parametrize(
    "text,not_this",
    [
        ("máy lạnh mới lắp bị chảy nước", "AC-03"),
        ("tủ lạnh có mùi khét", "FR-02"),
        ("quạt treo tường không quay", "LF-02"),
        ("thay gioăng tủ lạnh", "FR-02"),
    ],
)
def test_a_problem_that_mentions_the_work_is_still_a_problem(text, not_this):
    _, got = _first_service(text)
    assert got != not_this, text


def test_a_cleaning_asked_for_with_no_fault_is_offered_without_a_diagnosis():
    reply, got = _first_service("vệ sinh tủ lạnh")
    assert got == "FR-02"
    assert reply.suspected_faults == []
    assert "Vệ sinh, bảo dưỡng tủ lạnh" in reply.message_vi


def test_another_appliance_cleaned_in_the_same_chat_keeps_the_first_one_booked():
    """The conversation of the PO's screenshot, 01/11/2026."""
    pipeline = _pipeline()
    first, _ = _first_service("máy lạnh chảy nước, không lạnh", pipeline)
    second, got = _first_service(
        "tôi còn 1 tủ lạnh xuất hiện mùi hôi khó chịu cần thêm dịch vụ vệ sinh tủ lạnh",
        pipeline,
        session_id=first.session_id,
    )
    assert got == "FR-02"
    by_device = {d.device_type: d.service.service_code for d in second.devices if d.service}
    assert by_device.get("refrigerator") == "FR-02"
    assert by_device.get("air_conditioner") in {"AC-01", "AC-02"}
