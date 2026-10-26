"""The prices in the knowledge base must stay traceable to the catalogue.

Every figure a customer sees comes from a Backend service's price plus the
parts the fault usually needs, priced at FixHome's selling price (PO
26/10/2026; which parts, from the V3 table the team agreed on 19/10/2026). If a code is renamed in either catalogue, the fault that cited it
would otherwise keep a number nothing supports, which is invisible from the
response.
"""

import json

from app.services.pipeline.knowledge_base import DATA_DIR, get_knowledge_base


def _load(name: str) -> dict:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def test_every_fault_is_priced_from_the_tables():
    kb = get_knowledge_base()
    mapping = _load("fault_pricing_map.json")["map"]
    parts = {p["code"] for p in _load("parts_catalog.json")["parts"]}
    services = {s["code"] for s in _load("service_catalog.json")["services"]}

    for device in kb.device_types:
        for fault in kb.faults_for_device(device):
            entry = mapping.get(fault.fault_code)
            assert entry is not None, f"{fault.fault_code} has no pricing entry"
            assert entry["labour"] in services, f"{fault.fault_code}: {entry['labour']}"
            for code in entry["parts"]:
                assert code in parts, f"{fault.fault_code}: {code}"
            assert fault.labour_code == entry["labour"]
            assert fault.part_codes == entry["parts"]
            assert fault.price_reviewed


def test_a_fault_of_an_open_service_always_has_a_ceiling():
    """PO 26/10/2026: the customer is told a range, low to high, every time.

    A fault no open service repairs (a television panel, a dishwasher) is
    never priced to the customer and is left as it was.
    """
    kb = get_knowledge_base()
    for device in kb.device_types:
        for fault in kb.faults_for_device(device):
            if kb.services_for_fault(fault.fault_code):
                assert fault.price_max >= fault.price_min > 0, fault.fault_code


def test_the_floor_is_the_service_price_and_the_ceiling_adds_the_parts():
    """Low: the service's price as the booking form shows it. High: plus parts."""
    from app.services.pipeline import part_prices, pricing

    kb = get_knowledge_base()
    mapping = _load("fault_pricing_map.json")["map"]
    services = {s["code"]: s for s in _load("service_catalog.json")["services"]}
    prices = part_prices.snapshot()
    for device in kb.device_types:
        for fault in kb.faults_for_device(device):
            refs = kb.services_for_fault(fault.fault_code)
            if not refs:
                continue
            service = services[refs[0].service_code]
            assert fault.price_min == service["price_min_vnd"], fault.fault_code
            top = service["price_max_vnd"] if service["pricing"] == "fixed" else service["price_min_vnd"]
            parts = pricing.parts_ceiling(fault.fault_code, fault.device_type)
            assert fault.price_max == top + parts, fault.fault_code
            assert mapping[fault.fault_code]["parts_max"] == parts, fault.fault_code
            # Every part the ceiling counts has a price: Backend's, or the V3
            # table's for the few Backend does not sell yet.
            for group in pricing.part_groups(fault.fault_code, fault.device_type):
                assert any(prices.price(code) or part_prices.reference().get(code) for code in group), (
                    fault.fault_code, group,
                )


def test_a_fixed_price_fault_only_names_variants_backend_books():
    kb = get_knowledge_base()
    services = {s["code"]: s for s in _load("service_catalog.json")["services"]}
    for device in kb.device_types:
        for fault in kb.faults_for_device(device):
            codes = {v["code"] for v in services[fault.labour_code]["variants"]}
            assert set(fault.candidate_variants) <= codes, fault.fault_code


def test_the_assessment_flag_goes_out_as_camel_case():
    """Backend reads camelCase. A lone snake_case field reads as missing."""
    from app.schemas.diagnosis import PriceEstimate

    payload = PriceEstimate(min=100_000, max=None, requires_assessment=True).model_dump(
        by_alias=True
    )
    assert payload["requiresAssessment"] is True
    assert payload["max"] is None
    assert "requires_assessment" not in payload
