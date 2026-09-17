"""Every fault leads somewhere a customer can actually book.

The mapping was empty for weeks behind a note saying it waited on Backend to
agree a catalogue. Backend had agreed one and seeded twenty-nine services; the
note outlived the fact. These tests exist so the next such gap is loud.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.pipeline.knowledge_base import get_knowledge_base

MAPPING = Path("app/data/service_mapping.json")
FALLBACK = "KIEM_TRA_CHAN_DOAN_THIET_BI"


@pytest.fixture(scope="module")
def mapped() -> dict:
    data = json.loads(MAPPING.read_text(encoding="utf-8"))
    return {m["fault_code"]: m["services"] for m in data["mappings"]}


def test_every_fault_leads_to_a_service(mapped):
    kb = get_knowledge_base()
    codes = {
        fault.fault_code
        for device in kb.device_types
        for fault in kb.faults_for_device(device)
    }
    assert not codes - set(mapped), f"bệnh chưa ánh xạ: {sorted(codes - set(mapped))}"
    assert not set(mapped) - codes, f"ánh xạ thừa: {sorted(set(mapped) - codes)}"


def test_every_service_carries_a_name_a_customer_can_read(mapped):
    """The code is for Backend; the name is what the answer says out loud."""
    for fault, services in mapped.items():
        assert services, fault
        for service in services:
            assert service["service_code"], fault
            assert service["name_vi"].strip(), fault


def test_cleaning_is_not_booked_as_a_repair(mapped):
    """A dirty filter costs a cleaning, not a repair, and the catalogue prices
    them differently."""
    assert mapped["AC_DIRTY_FILTER"][0]["service_code"].startswith("VE_SINH")
    assert mapped["AC_LOW_REFRIGERANT"][0]["service_code"] == "SUA_DIEU_HOA"


def test_the_fallback_is_a_real_service_not_a_placeholder(mapped):
    """Six of the seventeen appliances have no repair service of their own, so
    the fallback carries real traffic and has to be a real bookable thing."""
    using = [f for f, s in mapped.items() if s[0]["service_code"] == FALLBACK]
    assert using, "không ca nào dùng tới dịch vụ khảo sát — kiểm lại quy tắc"
    assert all(s[0]["name_vi"] for f, s in mapped.items() if f in using)


def test_the_mapping_is_in_step_with_the_backend_seed():
    """Editing the seed without regenerating is how this drifts back to empty."""
    from tools.map_services import service_for, services_in_seed

    catalogue = services_in_seed()
    kb = get_knowledge_base()
    for device in kb.device_types:
        for fault in kb.faults_for_device(device):
            assert service_for(fault.fault_code, device) in catalogue
