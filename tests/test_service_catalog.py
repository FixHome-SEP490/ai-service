"""Following Backend's service catalogue (V2/V3 codes) live, without retraining or redeploying."""

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

RETIRED = {
    "KIEM_TRA_CHAN_DOAN_THIET_BI", "SUA_DIEU_HOA", "VE_SINH_DIEU_HOA_1HP",
    "SUA_TU_LANH", "SUA_MAY_GIAT", "SUA_LO_VI_SONG",
}


def _backend_rows():
    """The shape Backend's GET /categories returns, trimmed to what matters.

    basePrice is 0 for every catalogue V2 service; the labour price is in
    priceSummary."""
    return {
        "success": True,
        "data": [
            {
                "code": "CAT_AC", "name": "Điều hòa", "isActive": True,
                "services": [
                    {"code": "AC-01", "name": "Sửa điều hòa", "basePrice": "0.00", "isActive": True,
                     "priceSummary": {"kind": "inspection_reference", "minLaborVnd": 259000, "maxLaborVnd": 459000, "suggestedLaborVnd": 259000}},
                    {"code": "AC-02", "name": "Vệ sinh điều hòa", "basePrice": "0.00", "isActive": True,
                     "priceSummary": {"kind": "fixed_range", "minLaborVnd": 209000, "maxLaborVnd": 449000}},
                    {"code": "AC-09", "name": "Vệ sinh điều hòa tủ đứng", "basePrice": "0.00", "isActive": True,
                     "priceSummary": {"kind": "fixed_range", "minLaborVnd": 499000, "maxLaborVnd": 499000}},
                    {"code": "AC-03", "name": "Lắp đặt điều hòa", "basePrice": "0.00", "isActive": True},
                ],
            },
            {
                "code": "CAT_KITCHEN", "name": "Bếp", "isActive": True,
                "services": [
                    {"code": "KT-03", "name": "Sửa máy hút mùi", "basePrice": "0.00", "isActive": True},
                    {"code": "KT-02", "name": "Vệ sinh máy hút mùi", "basePrice": "0.00", "isActive": True},
                    {"code": "KT-05", "name": "Sửa lò vi sóng", "basePrice": "0.00", "isActive": True,
                     "priceSummary": {"kind": "inspection_reference", "minLaborVnd": None, "maxLaborVnd": None, "suggestedLaborVnd": 249000}},
                ],
            },
            {
                "code": "CAT_FRIDGE", "name": "Tủ lạnh", "isActive": True,
                "services": [{"code": "FR-01", "name": "Sửa tủ lạnh", "basePrice": "0.00", "isActive": False}],
            },
            {"code": "CAT_OFF", "name": "Đã tắt", "isActive": False, "services": [{"code": "WM-01", "name": "Sửa máy giặt"}]},
            {"code": "CAT_OTHER", "name": "Khác", "isActive": True, "services": [{"code": "DICH_VU_KHAC", "name": "Khác"}]},
        ],
    }


@pytest.fixture
def live():
    sc.install(sc.LiveCatalog(sc.parse(_backend_rows())))
    yield sc.current()
    sc.install(sc.LiveCatalog())


def _codes(fault_code):
    return [r.service_code for r in KB.services_for_fault(fault_code)]


def _all_offered():
    return {c for d in KB.device_types for f in KB.faults_for_device(d) for c in _codes(f.fault_code)}


def test_without_a_live_catalogue_the_snapshot_stands_in():
    sc.install(sc.LiveCatalog())
    assert _codes("AC_DIRTY_FILTER") == ["AC-02"]
    assert _codes("FRIDGE_LOW_GAS") == ["FR-01"]
    ref = KB.services_for_fault("AC_DIRTY_FILTER")[0]
    assert (ref.base_price, ref.price_max) == (199000, 449000)


def test_no_retired_code_is_ever_offered():
    sc.install(sc.LiveCatalog())
    assert not (_all_offered() & RETIRED)
    assert all(code[:2].isalpha() and code[2] == "-" for code in _all_offered())


def test_a_service_backend_has_not_opened_is_not_offered():
    sc.install(sc.LiveCatalog())
    # Microwave, TV and dishwasher repair are not open yet (phase M3).
    assert _codes("MW_MAGNETRON") == []
    assert _codes("TV_BACKLIGHT") == []
    assert KB.fallback_service("microwave_oven") is None
    assert KB.fallback_service(None) is None


def test_each_appliance_falls_back_to_its_own_repair():
    sc.install(sc.LiveCatalog())
    assert KB.fallback_service("air_conditioner").service_code == "AC-01"
    assert KB.fallback_service("washing_machine").service_code == "WM-01"
    assert KB.fallback_service("toilet").service_code == "SA-01"


def test_parse_reads_categories_and_takes_the_price_from_the_summary():
    services = {s.code: s for s in sc.parse(_backend_rows())}
    assert "FR-01" not in services  # switched off in the admin screen
    assert "WM-01" not in services  # its whole category is off
    assert "DICH_VU_KHAC" not in services  # "Khác" is not a recommendation
    assert (services["AC-01"].base_price, services["AC-01"].price_max) == (259000, 459000)
    assert services["KT-05"].base_price == 249000  # reference only
    assert services["KT-03"].base_price is None  # 0.00 is not a price


def test_names_and_prices_follow_backend(live):
    ref = KB.services_for_fault("AC_DIRTY_FILTER")[0]
    assert ref.service_code == "AC-02"
    assert (ref.base_price, ref.price_max) == (209000, 449000)


def test_a_switched_off_service_is_not_offered(live):
    assert "FR-01" not in _codes("FRIDGE_LOW_GAS")


def test_a_new_cleaning_for_the_same_appliance_is_offered_beside_the_mapped_one(live):
    assert _codes("AC_DIRTY_FILTER") == ["AC-02", "AC-09"]


def test_a_service_opened_in_the_admin_screen_is_offered_without_a_resync(live):
    assert _codes("MW_MAGNETRON") == ["KT-05"]
    assert KB.fallback_service("microwave_oven").service_code == "KT-05"


def test_installation_is_never_offered_as_a_repair(live):
    for device in KB.device_types:
        for fault in KB.faults_for_device(device):
            assert "AC-03" not in _codes(fault.fault_code)


def test_a_service_for_an_appliance_the_knowledge_base_lacks_is_found_by_name(live):
    assert live.service_named_in("máy hút mùi nhà em kêu to quá", KB).code == "KT-03"
    assert live.service_named_in("may hut mui khong hut", KB).code == "KT-03"
    assert live.service_named_in("muốn vệ sinh máy hút mùi", KB).code == "KT-02"
    # An appliance the knowledge base covers is diagnosed, not offered by name.
    assert live.service_named_in("máy lạnh không mát", KB) is None


class _NoDetector:
    async def detect(self, image):
        return []


def _pipeline():
    return LocalPipeline(detector=_NoDetector(), vlm=StubVlm(), retriever=Retriever(KB), kb=KB)


def test_the_customer_is_pointed_at_the_service_instead_of_refused(live):
    reply = asyncio.run(_pipeline().diagnose(DiagnosisRequest(description="máy hút mùi nhà em kêu to quá")))
    assert [s.service_code for s in reply.recommended_services] == ["KT-03"]
    assert "máy hút mùi" in (reply.message_vi or "").lower()

    answer = asyncio.run(_pipeline().answer(ChatRequest(question="máy hút mùi không hút được khói")))
    assert [s.service_code for s in answer.recommended_services] == ["KT-03"]


def test_the_snapshot_also_knows_the_range_hood():
    sc.install(sc.LiveCatalog())
    reply = asyncio.run(_pipeline().diagnose(DiagnosisRequest(description="máy hút mùi nhà em kêu to quá")))
    assert [s.service_code for s in reply.recommended_services] == ["KT-03"]


def test_a_word_for_appliances_booked_alike_still_offers_their_repair():
    """"Quạt" is a ceiling or a standing fan, both "Sửa quạt điện"; "lò" is a
    microwave or an oven, booked differently, so that one only asks."""
    sc.install(sc.LiveCatalog())
    fan = asyncio.run(_pipeline().diagnose(DiagnosisRequest(description="quạt nhà em kêu to quá")))
    assert fan.status.value == "needs_clarification"
    assert [s.service_code for s in fan.recommended_services] == ["LF-03"]
    oven = asyncio.run(_pipeline().diagnose(DiagnosisRequest(description="cái lò nhà em không nóng")))
    assert oven.recommended_services == []
