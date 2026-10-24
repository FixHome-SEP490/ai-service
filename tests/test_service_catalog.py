"""Following Backend's service catalogue live, without retraining or redeploying."""

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
FALLBACK = KB.FALLBACK_SERVICE_CODE


def _backend_rows():
    """The shape Backend's GET /services returns, trimmed to what matters."""
    return {
        "success": True,
        "data": [
            {"code": FALLBACK, "name": "Kiểm tra/chẩn đoán thiết bị tại nhà", "basePrice": "100000.00", "isActive": True},
            {"code": "VE_SINH_DIEU_HOA_1HP", "name": "Vệ sinh điều hòa treo tường 1–1.5 HP", "basePrice": "190000.00", "isActive": True},
            {"code": "VE_SINH_DIEU_HOA_2HP", "name": "Vệ sinh điều hòa treo tường 2–2.5 HP", "basePrice": "220000.00", "isActive": True},
            {"code": "SUA_DIEU_HOA", "name": "Sửa điều hòa không mát / chảy nước", "basePrice": "150000.00", "isActive": True},
            {"code": "SUA_LO_VI_SONG", "name": "Sửa lò vi sóng", "basePrice": "160000.00", "isActive": True},
            {"code": "THAY_VOI_SEN", "name": "Thay vòi sen - tiền công", "basePrice": "150000.00", "isActive": True},
            {"code": "LAP_QUAT_TREO_TUONG", "name": "Lắp quạt treo tường - tiền công", "basePrice": "150000.00", "isActive": True},
            {"code": "SUA_MAY_HUT_MUI", "name": "Vệ sinh & sửa motor máy hút mùi", "basePrice": "150000.00", "isActive": True},
            {"code": "SUA_TU_LANH", "name": "Sửa tủ lạnh", "basePrice": "180000.00", "isActive": False},
            {"code": "DICH_VU_KHAC", "name": "Khác", "basePrice": "0.00", "isActive": True},
        ],
        "meta": {"page": 1, "limit": 100, "total": 10, "totalPages": 1},
    }


@pytest.fixture
def live():
    sc.install(sc.LiveCatalog(sc.parse(_backend_rows())))
    yield sc.current()
    sc.install(sc.LiveCatalog())


def _codes(fault_code):
    return [r.service_code for r in KB.services_for_fault(fault_code)]


def test_without_a_live_catalogue_the_static_mapping_is_untouched():
    sc.install(sc.LiveCatalog())
    static = {f.fault_code: _codes(f.fault_code) for d in KB.device_types for f in KB.faults_for_device(d)}
    assert static["AC_DIRTY_FILTER"] == ["VE_SINH_DIEU_HOA_1HP"]
    assert static["MW_MAGNETRON"] == [FALLBACK]


def test_parse_reads_backend_shape_and_drops_what_cannot_be_booked():
    services = {s.code: s for s in sc.parse(_backend_rows())}
    assert "SUA_TU_LANH" not in services  # switched off in the admin screen
    assert "DICH_VU_KHAC" not in services  # "Khác" is not a recommendation
    assert services["SUA_DIEU_HOA"].base_price == 150000


def test_names_and_prices_follow_backend(live):
    ref = KB.services_for_fault("AC_DIRTY_FILTER")[0]
    assert ref.service_code == "VE_SINH_DIEU_HOA_1HP"
    assert ref.base_price == 190000


def test_a_switched_off_service_is_not_offered(live):
    assert "SUA_TU_LANH" not in _codes("FRIDGE_LOW_GAS")


def test_cleaning_in_another_size_is_offered_beside_the_mapped_one(live):
    assert _codes("AC_DIRTY_FILTER")[:2] == ["VE_SINH_DIEU_HOA_1HP", "VE_SINH_DIEU_HOA_2HP"]


def test_a_new_general_repair_goes_in_front_of_the_inspection(live):
    assert _codes("MW_MAGNETRON") == ["SUA_LO_VI_SONG", FALLBACK]


def test_a_narrow_repair_does_not_attach_to_a_fault_it_does_not_name(live):
    assert "THAY_VOI_SEN" not in _codes("FAUCET_LOW_FLOW")


def test_installation_is_never_offered_as_a_repair(live):
    for device in KB.device_types:
        for fault in KB.faults_for_device(device):
            assert "LAP_QUAT_TREO_TUONG" not in _codes(fault.fault_code)


def test_a_service_for_an_appliance_the_knowledge_base_lacks_is_found_by_name(live):
    assert live.service_named_in("máy hút mùi nhà em kêu to quá", KB).code == "SUA_MAY_HUT_MUI"
    assert live.service_named_in("may hut mui khong hut", KB).code == "SUA_MAY_HUT_MUI"
    # An appliance the knowledge base covers is diagnosed, not offered by name.
    assert live.service_named_in("máy lạnh không mát", KB) is None


class _NoDetector:
    async def detect(self, image):
        return []


def _pipeline():
    return LocalPipeline(detector=_NoDetector(), vlm=StubVlm(), retriever=Retriever(KB), kb=KB)


def test_the_customer_is_pointed_at_the_new_service_instead_of_refused(live):
    reply = asyncio.run(_pipeline().diagnose(DiagnosisRequest(description="máy hút mùi nhà em kêu to quá")))
    assert [s.service_code for s in reply.recommended_services] == ["SUA_MAY_HUT_MUI"]
    assert "máy hút mùi" in (reply.message_vi or "")

    answer = asyncio.run(_pipeline().answer(ChatRequest(question="máy hút mùi không hút được khói")))
    assert [s.service_code for s in answer.recommended_services] == ["SUA_MAY_HUT_MUI"]


def test_without_the_catalogue_nothing_is_offered_by_name():
    sc.install(sc.LiveCatalog())
    reply = asyncio.run(_pipeline().diagnose(DiagnosisRequest(description="máy hút mùi nhà em kêu to quá")))
    assert "SUA_MAY_HUT_MUI" not in [s.service_code for s in reply.recommended_services]
