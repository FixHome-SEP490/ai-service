# app/services/pipeline/knowledge_base.py
"""Loads the curated catalog and fault knowledge base.

Every Vietnamese string, service code and price the service returns comes from
here, never from model free text. Editing the JSON is how the team changes
wording or pricing; no retraining involved.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


@dataclass(frozen=True)
class Fault:
    fault_code: str
    device_type: str
    name_vi: str
    symptoms_vi: List[str]
    service_code: str
    service_name_vi: str
    price_min: int
    price_max: int
    urgency: str
    suggested_actions_vi: List[str]


@dataclass(frozen=True)
class Policy:
    doc_id: str
    title_vi: str
    content_vi: str


class KnowledgeBase:
    def __init__(self, catalog: dict, kb: dict) -> None:
        self._device_names: Dict[str, str] = {
            d["device_type"]: d["name_vi"] for d in catalog["devices"]
        }
        self._service_groups: Dict[str, str] = {
            d["device_type"]: d["service_group"] for d in catalog["devices"]
        }
        self._condition_names: Dict[str, str] = {
            c["code"]: c["name_vi"] for c in catalog["visible_conditions"]
        }
        self._faults: List[Fault] = [Fault(**f) for f in kb["faults"]]
        self._policies: List[Policy] = [Policy(**p) for p in kb["policies"]]

    @property
    def device_types(self) -> List[str]:
        return list(self._device_names)

    @property
    def condition_codes(self) -> List[str]:
        return list(self._condition_names)

    @property
    def policies(self) -> List[Policy]:
        return list(self._policies)

    def device_name_vi(self, device_type: str) -> Optional[str]:
        return self._device_names.get(device_type)

    def service_group(self, device_type: str) -> Optional[str]:
        return self._service_groups.get(device_type)

    def condition_name_vi(self, code: str) -> Optional[str]:
        return self._condition_names.get(code)

    def faults_for_device(self, device_type: str) -> List[Fault]:
        return [f for f in self._faults if f.device_type == device_type]

    def fault(self, fault_code: str) -> Optional[Fault]:
        return next((f for f in self._faults if f.fault_code == fault_code), None)

    def all_service_groups(self) -> List[str]:
        return sorted(set(self._service_groups.values()))


@lru_cache(maxsize=1)
def get_knowledge_base() -> KnowledgeBase:
    catalog = json.loads((DATA_DIR / "device_catalog.json").read_text(encoding="utf-8"))
    kb = json.loads((DATA_DIR / "fault_knowledge_base.json").read_text(encoding="utf-8"))
    return KnowledgeBase(catalog=catalog, kb=kb)
