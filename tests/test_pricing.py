"""The estimate runs from the service's own price to that price plus the parts (PO 26/10/2026).

The low end is the figure the booking form shows beside the service, so the
customer sent there from the chat sees the same number. The high end adds the
parts the fault usually needs, at FixHome's selling price, over every size and
technology of that part for the appliance.
"""

import asyncio

import pytest

from app.schemas.diagnosis import DiagnosisRequest
from app.services.pipeline import part_prices, pricing
from app.services.pipeline import service_catalog as sc
from app.services.pipeline.knowledge_base import get_knowledge_base
from app.services.pipeline.local_pipeline import LocalPipeline
from app.services.pipeline.retriever import Retriever
from app.services.pipeline.vlm import StubVlm

KB = get_knowledge_base()


@pytest.fixture(autouse=True)
def _snapshot_prices():
    part_prices.install(part_prices.PartPrices())
    sc.install(sc.LiveCatalog())
    yield
    part_prices.install(part_prices.PartPrices())


def _price(code):
    return part_prices.snapshot().price(code)


def test_a_repair_priced_on_site_starts_at_the_reference_the_form_shows():
    estimate = pricing.estimate("AC-01", ["AC_CAPACITOR"], "air_conditioner")
    assert estimate.min == estimate.labour_min == estimate.labour_max == 249_000
    capacitors = [_price(c) for c in ("AC021", "AC022", "AC023", "AC024", "AC025", "AC026")]
    assert estimate.parts_max == max(capacitors)
    assert estimate.max == 249_000 + max(capacitors)
    assert estimate.requires_assessment


def test_a_fixed_price_service_spans_its_variants_until_one_is_known():
    estimate = pricing.estimate("AC-02", ["AC_DIRTY_FILTER"], "air_conditioner")
    assert (estimate.min, estimate.max, estimate.parts_max) == (199_000, 449_000, 0)
    assert not estimate.requires_assessment
    wall = pricing.estimate("AC-02", ["AC_DIRTY_FILTER"], "air_conditioner", "AC-02-02")
    assert (wall.min, wall.max) == (219_000, 219_000)


def test_a_part_is_priced_on_every_size_and_technology_of_it():
    """The customer's compressor may be 9.000 BTU mono or 24.000 BTU inverter."""
    estimate = pricing.estimate("AC-01", ["AC_COMPRESSOR_FAULT"], "air_conditioner")
    dearest = max(_price(c) for c in ("AC001", "AC004", "AC005", "AC008"))
    assert estimate.parts_max == dearest == _price("AC008")


def test_a_refrigerant_leak_needs_the_gas_refill_and_the_filter_together():
    """Priced on a refill for the machine (PO 27/10/2026), not on a 3 kg bottle."""
    gas = max(_price(c) for c in ("ACG001", "ACG002", "ACG003", "ACG004"))
    drier = max(_price(c) for c in ("AC051", "ACV089", "ACV090"))
    assert pricing.parts_ceiling("AC_LOW_REFRIGERANT", "air_conditioner") == gas + drier
    fridge_gas = max(_price(c) for c in ("RFG001", "RFG002", "RFG003", "RFG004"))
    assert pricing.parts_ceiling("FRIDGE_LOW_GAS", "refrigerator") > fridge_gas


def test_an_exact_part_is_not_widened_to_its_whole_kind():
    """The indoor DC fan motor shares a kind with the dearer outdoor one."""
    assert pricing.parts_ceiling("AC_INDOOR_FAN_MOTOR", "air_conditioner") == max(_price("AC029"), _price("AC030"))


def test_the_ceiling_follows_backend_prices_when_they_change():
    before = pricing.parts_ceiling("WM_NO_SPIN", "washing_machine")
    live = dict(part_prices.snapshot().prices)
    for code in ("WM023",) + tuple(c for c, p in part_prices.parts().items() if p.kind == "drive belt"):
        live[code] = 900_000
    part_prices.install(part_prices.PartPrices(live, loaded_at=1.0))
    assert pricing.parts_ceiling("WM_NO_SPIN", "washing_machine") == 900_000 != before


def test_backend_prices_are_read_from_the_public_list():
    assert part_prices.parse({"data": {"items": [{"sku": "AC002", "name": "x", "price": "2000000.00"}, {"sku": "", "price": 5}]}}) == {
        "AC002": 2_000_000
    }
    assert part_prices.url_from_catalog("https://api.fixhome.sbs/api/v1/services") == "https://api.fixhome.sbs/api/v1/parts/prices"
    assert part_prices.url_from_catalog("") == ""


def test_sockets_and_bulbs_are_priced_at_what_fixhome_sells_them_for():
    """Added to Backend's parts on 27/10/2026; before that, the V3 table stood in."""
    assert _price("OUT001") == 25_000
    assert part_prices.reference() == {}
    assert pricing.parts_ceiling("OUTLET_BROKEN_FACE", "power_outlet") > 0


def test_a_part_backend_does_not_sell_keeps_its_table_price(monkeypatch):
    live = {code: price for code, price in part_prices.snapshot().prices.items() if not code.startswith("OUT")}
    part_prices.install(part_prices.PartPrices(live, loaded_at=1.0))
    monkeypatch.setattr(part_prices, "reference", lambda: {"OUT006": 50_000, "OUT007": 30_000})
    assert pricing.parts_ceiling("OUTLET_BROKEN_FACE", "power_outlet") == 50_000


class _NoDetector:
    async def detect(self, image):
        return []


def test_the_answer_quotes_the_service_price_the_booking_form_shows():
    pipeline = LocalPipeline(detector=_NoDetector(), vlm=StubVlm(), retriever=Retriever(KB), kb=KB)
    reply = asyncio.run(pipeline.diagnose(DiagnosisRequest(description="máy lạnh chạy mà không mát")))
    assert reply.recommended_services[0].service_code == "AC-01"
    assert reply.price_estimate.min == 249_000
    assert reply.price_estimate.labour_min == 249_000
    assert reply.price_estimate.max == 249_000 + pricing.parts_ceiling(
        reply.suspected_faults[0].fault_code, "air_conditioner"
    )
    body = reply.model_dump(by_alias=True)["priceEstimate"]
    assert {"labourMin", "labourMax", "partsMax"} <= set(body)
