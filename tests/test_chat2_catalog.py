"""The chat follows Backend's service catalogue without a rebuild (07/11).

Each test installs a catalogue the way `service_catalog.refresh_forever`
does after a fetch, and puts the snapshot back afterwards."""

from dataclasses import replace

import pytest

from app.services.chat2 import catalog as live
from app.services.chat2.answer import index
from app.services.chat2.brain import _without_device, unlisted_offer
from app.services.chat2.menu import menu_for
from app.services.chat2.provider import _services
from app.services.pipeline import service_catalog
from app.services.pipeline.service_catalog import LiveCatalog, LiveService, parse


@pytest.fixture
def backend():
    """Install a catalogue: the snapshot's services, changed by the test."""
    def install(change=lambda services: services):
        services = change(list(service_catalog.snapshot().services.values()))
        service_catalog.install(LiveCatalog(services, loaded_at=1.0))
    yield install
    service_catalog.install(LiveCatalog())


def test_without_a_fetch_the_snapshot_is_the_menu():
    assert live.current() is service_catalog.snapshot()
    assert {s.code for s in menu_for("air_conditioner").services} == {"AC-01", "AC-02", "AC-03", "AC-04"}


def test_a_service_the_admin_closes_is_not_offered(backend):
    backend(lambda services: [s for s in services if s.code != "AC-02"])
    menu = menu_for("air_conditioner")
    assert "AC-02" not in {s.code for s in menu.services}
    # The dirty filter booked AC cleaning; with it closed it books the repair.
    assert menu.fault("AC_DIRTY_FILTER").service_code == "AC-01"
    assert "Vệ sinh điều hòa" not in index()["catalog:air_conditioner"].text_vi
    assert "Vệ sinh điều hòa" not in index()["catalog:services"].text_vi


def test_a_new_price_reaches_the_menu_and_the_price_table(backend):
    backend(lambda services: [replace(s, base_price=299000, price_max=299000) if s.code == "AC-02" else s for s in services])
    assert menu_for("air_conditioner").service("AC-02").price_min == 299000
    assert "Vệ sinh điều hòa: 299.000đ (" in index()["catalog:air_conditioner"].text_vi


def test_a_new_service_joins_the_appliance_its_name_names(backend):
    new = LiveService(code="LF-09", name_vi="Vệ sinh quạt trần", base_price=99000, category_vi="Đèn & quạt")
    backend(lambda services: [*services, new])
    menu = menu_for("ceiling_fan")
    assert menu.service("LF-09") is not None and menu.service("LF-09").kind == "clean"
    assert "Vệ sinh quạt trần: 99.000đ" in index()["catalog:ceiling_fan"].text_vi
    assert "Vệ sinh quạt trần" in index()["catalog:services"].text_vi
    # Not the electric fan's: the longer name wins.
    assert menu_for("electric_fan").service("LF-09") is None


def test_a_new_repair_that_names_a_fault_is_booked_for_it(backend):
    new = LiveService(code="FR-09", name_vi="Thay gioăng cửa tủ lạnh", base_price=150000, category_vi="Tủ lạnh")
    backend(lambda services: [*services, new])
    menu = menu_for("refrigerator")
    assert menu.fault("FRIDGE_DOOR_GASKET").service_code == "FR-09"
    assert menu.fault("FRIDGE_LOW_GAS").service_code == "FR-01"
    assert menu.repair_service.code == "FR-01"


def test_a_service_for_an_appliance_without_a_menu_is_offered(backend):
    new = LiveService(code="VC-01", name_vi="Sửa máy hút bụi", base_price=150000, category_vi="Thiết bị gia dụng")
    backend(lambda services: [*services, new])
    assert unlisted_offer("máy hút bụi nhà em không hút nữa").code == "VC-01"
    verdict = _without_device("repair", None, 0.0, {"other_appliance": "máy hút bụi"}, "máy hút bụi nhà em không hút nữa")
    assert verdict.decision == "conclude" and verdict.service_code == "VC-01"
    assert "Sửa máy hút bụi" in verdict.reply_vi and "chưa nhận" not in verdict.reply_vi
    assert [s.service_code for s in _services(verdict)] == ["VC-01"]


def test_without_such_a_service_the_appliance_is_declined():
    verdict = _without_device("repair", None, 0.0, {"other_appliance": "máy hút bụi"}, "máy hút bụi nhà em không hút nữa")
    assert verdict.decision == "not_repair" and "chưa nhận máy hút bụi" in verdict.reply_vi


def test_backend_categories_name_the_groups_and_a_closed_group_closes_its_services():
    body = {"data": [
        {"code": "AC-02", "name": "Vệ sinh điều hòa", "isActive": True,
         "category": {"name": "Điều hòa", "isActive": True}, "priceSummary": {"kind": "fixed_range", "minLaborVnd": 199000}},
        {"code": "WM-01", "name": "Sửa máy giặt", "isActive": True, "category": {"name": "Máy giặt", "isActive": False}},
    ]}
    services = parse(body)
    assert [(s.code, s.category_vi) for s in services] == [("AC-02", "Điều hòa")]


def test_the_written_index_still_carries_the_snapshot_tables():
    assert index()["catalog:services"].text_vi.endswith(live.NOT_TAKEN_VI)
    assert "catalog:refrigerator" in index()
