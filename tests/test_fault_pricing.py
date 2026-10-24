"""The prices in the knowledge base must stay traceable to the catalogue.

Every figure a customer sees comes from a Backend service's labour (S) plus
the parts the fault usually needs (P), from the V3 table the team agreed on
19/10/2026. If a code is renamed in either catalogue, the fault that cited it
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


def test_a_fault_either_has_a_ceiling_or_says_a_technician_must_look():
    """The two are exclusive, and one of them always holds.

    A fault with neither would show a floor alone, which reads as the price of
    the whole job.
    """
    kb = get_knowledge_base()
    for device in kb.device_types:
        for fault in kb.faults_for_device(device):
            if fault.requires_assessment:
                assert fault.price_max == 0
            else:
                assert fault.price_max >= fault.price_min > 0


def test_the_floor_is_the_service_labour_plus_the_cheapest_parts():
    kb = get_knowledge_base()
    mapping = _load("fault_pricing_map.json")["map"]
    services = {s["code"]: s for s in _load("service_catalog.json")["services"]}
    for device in kb.device_types:
        for fault in kb.faults_for_device(device):
            entry = mapping[fault.fault_code]
            assert fault.price_min == entry["labour_min"] + entry["parts_min"], fault.fault_code
            # The labour is the service's own price, not a figure of our own.
            assert entry["labour_min"] >= services[fault.labour_code]["price_min_vnd"], fault.fault_code


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
