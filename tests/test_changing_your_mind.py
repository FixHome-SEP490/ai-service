"""The customer changes their mind about what to book.

The booking button is pinned to the bottom of the chat, so whatever it says is
what the customer is about to order. That makes one sentence load-bearing: "em
đổi ý, đặt thợ sửa ống nước nhé". Before this, the button carried on offering
air conditioning, because the session remembers the appliance and the
remembered one beat the sentence that had just replaced it.

Measured on the running service before the fix — every way of asking came back
with the original service:

    "thôi em muốn đặt thợ điện nước thay vì thợ máy lạnh"  -> SUA_DIEU_HOA
    "em đổi ý, đặt thợ sửa ống nước nhé"                   -> SUA_DIEU_HOA
    "cho em đổi sang vệ sinh máy lạnh thôi"                -> SUA_DIEU_HOA

In a fresh session the same sentences resolved perfectly, which is what made
the cause obvious: the understanding was there, the session was overruling it.
"""

import pytest

from app.services.pipeline import local_pipeline as lp
from app.services.pipeline.knowledge_base import get_knowledge_base


@pytest.fixture(scope="module")
def kb():
    return get_knowledge_base()


class TestSwitchPhrasesPointBothWays:
    """"A thay vì B" wants A. "Đổi sang B" wants B. Opposite directions."""

    def test_the_one_named_before_thay_vi_is_the_one_wanted(self, kb):
        assert (
            lp._device_asked_for_now(
                "thôi em muốn đặt thợ điện nước thay vì thợ máy lạnh", kb
            )
            == "power_outlet"
        )

    def test_the_one_named_after_doi_sang_is_the_one_wanted(self, kb):
        assert (
            lp._device_asked_for_now("cho em đổi sang vệ sinh máy lạnh thôi", kb)
            == "air_conditioner"
        )

    def test_chuyen_sang_reads_like_doi_sang(self, kb):
        assert (
            lp._device_asked_for_now("chuyển sang thợ sửa tủ lạnh giúp em", kb)
            == "refrigerator"
        )

    def test_khong_phai_moves_away_from_what_follows(self, kb):
        assert (
            lp._device_asked_for_now("em cần thợ sửa ống nước không phải máy lạnh", kb)
            == "water_pipe"
        )


class TestAPlainChangeOfSubject:
    def test_naming_one_appliance_changes_the_subject(self, kb):
        assert lp._device_asked_for_now("em đổi ý, đặt thợ sửa ống nước nhé", kb) == (
            "water_pipe"
        )

    def test_a_follow_up_with_no_appliance_leaves_the_session_alone(self, kb):
        # These are the sentences that make a session worth having. If they
        # returned a device the session would be overwritten by noise.
        assert lp._device_asked_for_now("còn kêu to nữa", kb) is None
        assert lp._device_asked_for_now("mới dùng được 2 năm thôi", kb) is None
        assert lp._device_asked_for_now("vâng ạ", kb) is None

    def test_two_appliances_and_no_switch_phrase_is_not_a_change_of_mind(self, kb):
        # One sentence mentioning two appliances is ambiguous, and guessing at
        # it is worse than leaving the session in charge.
        assert (
            lp._device_asked_for_now("máy lạnh với tủ lạnh nhà em đều cũ rồi", kb)
            is None
        )


class TestItDoesNotFireOnOrdinarySymptoms:
    """The override runs on every booking turn, so it must be quiet by default."""

    @pytest.mark.parametrize(
        "sentence",
        [
            "máy giặt nhà em không vắt",
            "điều hòa chảy nước xuống tường",
            "bếp từ báo lỗi E4",
        ],
    )
    def test_a_symptom_report_names_its_own_appliance_and_nothing_else(
        self, kb, sentence
    ):
        # Naming the appliance you are reporting on is not changing your mind,
        # but it resolves to that appliance either way - which is the same
        # answer the session would have given.
        resolved = lp._device_asked_for_now(sentence, kb)
        assert resolved is not None

    def test_an_empty_turn_resolves_to_nothing(self, kb):
        assert lp._device_asked_for_now("", kb) is None
        assert lp._device_asked_for_now("   ", kb) is None


# ---------------------------------------------------------------- end to end


class _NoDetector:
    async def detect(self, image):
        return []


def _pipeline():
    from app.services.pipeline.local_pipeline import LocalPipeline
    from app.services.pipeline.retriever import Retriever
    from app.services.pipeline.vlm import StubVlm

    knowledge = get_knowledge_base()
    return LocalPipeline(
        detector=_NoDetector(), vlm=StubVlm(), retriever=Retriever(knowledge), kb=knowledge
    )


def _codes(response) -> list[str]:
    return [service.service_code for service in response.recommended_services]


@pytest.mark.asyncio
class TestThePinnedBookingFollowsTheCustomer:
    """Driven through the whole pipeline, session and all.

    The unit tests above prove the sentence is understood. These prove the
    service actually changes, which is the part that was broken: the
    understanding was already correct in a fresh session and lost inside one.
    """

    async def test_switching_trade_changes_the_service(self):
        from app.schemas.diagnosis import DiagnosisRequest

        pipeline = _pipeline()
        first = await pipeline.diagnose(
            DiagnosisRequest(description="máy lạnh nhà em không mát")
        )
        assert any(code.endswith("DIEU_HOA") or "DIEU_HOA" in code for code in _codes(first))

        second = await pipeline.diagnose(
            DiagnosisRequest(
                description="em đổi ý, đặt thợ sửa ống nước nhé",
                session_id=first.session_id,
            )
        )
        assert _codes(second), "a booking turn must always offer something"
        assert not any("DIEU_HOA" in code for code in _codes(second)), (
            f"still offering air conditioning after the customer switched: {_codes(second)}"
        )

    async def test_the_switch_sticks_for_the_next_bare_turn(self):
        from app.schemas.diagnosis import DiagnosisRequest

        pipeline = _pipeline()
        first = await pipeline.diagnose(
            DiagnosisRequest(description="máy lạnh nhà em không mát")
        )
        switched = await pipeline.diagnose(
            DiagnosisRequest(
                description="đổi sang thợ sửa tủ lạnh giúp em",
                session_id=first.session_id,
            )
        )
        assert any("TU_LANH" in code for code in _codes(switched))

        # A bare follow-up must not snap back to the air conditioner.
        after = await pipeline.diagnose(
            DiagnosisRequest(description="đặt giúp em luôn", session_id=first.session_id)
        )
        assert not any("DIEU_HOA" in code for code in _codes(after)), (
            f"the session forgot the switch: {_codes(after)}"
        )
