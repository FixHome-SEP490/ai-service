"""The prices in the knowledge base must stay traceable to the two tables.

Every figure a customer sees now comes from a labour row plus representative
parts. If a code is renamed in either catalogue, the fault that cited it would
otherwise keep a number nothing supports, which is invisible from the response.
"""

import json

from app.services.pipeline.knowledge_base import DATA_DIR, get_knowledge_base


def _load(name: str) -> dict:
    return json.loads((DATA_DIR / name).read_text(encoding="utf-8"))


def test_every_fault_is_priced_from_the_tables():
    kb = get_knowledge_base()
    mapping = _load("fault_pricing_map.json")["map"]
    parts = {p["code"] for p in _load("parts_catalog.json")["parts"]}
    labour = {s["service_code"] for s in _load("labour_catalog.json")["services"]}

    for device in kb.device_types:
        for fault in kb.faults_for_device(device):
            entry = mapping.get(fault.fault_code)
            assert entry is not None, f"{fault.fault_code} has no pricing entry"
            assert entry["labour"] in labour, f"{fault.fault_code}: {entry['labour']}"
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


def test_the_floor_is_always_labour_the_customer_would_pay():
    kb = get_knowledge_base()
    labour = {s["service_code"]: s["price"] for s in _load("labour_catalog.json")["services"]}
    for device in kb.device_types:
        for fault in kb.faults_for_device(device):
            assert fault.price_min == labour[fault.labour_code]
