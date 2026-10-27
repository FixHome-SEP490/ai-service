"""The trained fault chooser (VLM_FAULT_MODEL), switched on and off.

Off, which is the default, nothing changes: retrieval's shortlist is offered
and retrieval's leader comes first on a text-only turn. On, the adapter is
offered every fault of the appliance and its pick leads, with retrieval's
order kept behind it, two possibilities in all as the base model mostly gives.
"""

import asyncio
from types import SimpleNamespace as F

from app.core import config
from app.schemas.diagnosis import DiagnosisRequest
from app.services.pipeline import service_catalog as sc
from app.services.pipeline.knowledge_base import get_knowledge_base
from app.services.pipeline.local_pipeline import LocalPipeline, _ranked_by_retrieval
from app.services.pipeline.retriever import Retriever
from app.services.pipeline.vlm import StubVlm, VlmVerdict

KB = get_knowledge_base()
SAID = "máy lạnh không mát"


class _NoDetector:
    async def detect(self, image):
        return []


class _Picker(StubVlm):
    """Answers with one fixed fault and remembers what it was offered."""

    def __init__(self, pick=None):
        self.pick = pick
        self.offered = []

    async def assess_context(self, crop, context, candidate_condition_codes):
        self.offered = [c.fault.fault_code for c in context.candidates]
        pick = self.pick or (self.offered[0] if self.offered else None)
        return VlmVerdict(fault_codes=[pick] if pick else [], confidence=0.9)


def _ask(vlm):
    sc.install(sc.LiveCatalog())
    pipeline = LocalPipeline(detector=_NoDetector(), vlm=vlm, retriever=Retriever(KB), kb=KB)
    reply = asyncio.run(pipeline.diagnose(DiagnosisRequest(description=SAID)))
    return [f.fault_code for f in reply.suspected_faults]


def _outsider(offered):
    """An air-conditioner fault retrieval did not put on its shortlist."""
    return next(f.fault_code for f in KB.faults_for_device("air_conditioner") if f.fault_code not in offered)


def test_the_picked_fault_leads_and_retrieval_follows():
    shortlist = [F(fault_code="AC_LOW_REFRIGERANT"), F(fault_code="AC_DIRTY_FILTER")]
    assert _ranked_by_retrieval(["AC_DIRTY_FILTER"], shortlist, saw_a_photograph=False, model_leads=True) == [
        "AC_DIRTY_FILTER", "AC_LOW_REFRIGERANT",
    ]
    # Off, the same answer puts retrieval's leader first, as before.
    assert _ranked_by_retrieval(["AC_DIRTY_FILTER"], shortlist, saw_a_photograph=False)[0] == "AC_LOW_REFRIGERANT"


def test_a_pick_that_agrees_with_retrieval_still_leaves_a_second_possibility():
    shortlist = [F(fault_code=c) for c in ("AC_LOW_REFRIGERANT", "AC_DIRTY_FILTER", "AC_COMPRESSOR_FAULT", "AC_PCB_FAULT")]
    assert _ranked_by_retrieval(["AC_LOW_REFRIGERANT"], shortlist, saw_a_photograph=False, model_leads=True) == [
        "AC_LOW_REFRIGERANT", "AC_DIRTY_FILTER",
    ]
    assert _ranked_by_retrieval(["AC_PCB_FAULT"], shortlist, saw_a_photograph=False, model_leads=True) == [
        "AC_PCB_FAULT", "AC_LOW_REFRIGERANT",
    ]
    # What the customer ruled out is not among the possibilities either.
    assert _ranked_by_retrieval(
        ["AC_PCB_FAULT"], shortlist, saw_a_photograph=False, model_leads=True, excluded={"AC_LOW_REFRIGERANT"},
    ) == ["AC_PCB_FAULT", "AC_DIRTY_FILTER"]


def test_a_pick_outside_the_offer_or_ruled_out_does_not_lead():
    shortlist = [F(fault_code="AC_LOW_REFRIGERANT"), F(fault_code="AC_DIRTY_FILTER")]
    assert _ranked_by_retrieval(["AC_INVENTED"], shortlist, saw_a_photograph=False, model_leads=True) == ["AC_LOW_REFRIGERANT"]
    assert _ranked_by_retrieval(
        ["AC_DIRTY_FILTER"], shortlist, saw_a_photograph=False, model_leads=True, excluded={"AC_DIRTY_FILTER"},
    ) == ["AC_LOW_REFRIGERANT"]


def test_off_by_default_retrieval_leads_and_the_shortlist_is_unchanged(monkeypatch):
    monkeypatch.setattr(config.settings, "VLM_FAULT_MODEL", "")
    leader_vlm = _Picker()
    leader = _ask(leader_vlm)[0]
    shortlist = list(leader_vlm.offered)
    outsider = _outsider(shortlist)
    picker = _Picker(outsider)
    assert _ask(picker)[0] == leader
    assert picker.offered == shortlist


def test_on_the_adapter_sees_the_whole_appliance_and_its_pick_leads(monkeypatch):
    monkeypatch.setattr(config.settings, "VLM_FAULT_MODEL", "")
    base = _Picker()
    leader = _ask(base)[0]

    monkeypatch.setattr(config.settings, "VLM_FAULT_MODEL", "fixhome-fault")
    wide = _Picker()
    _ask(wide)
    assert wide.offered[: len(base.offered)] == base.offered  # retrieval's order first
    assert len(base.offered) < len(wide.offered) <= config.settings.VLM_FAULT_CANDIDATES
    outsider = next(code for code in wide.offered if code not in base.offered)
    assert _ask(_Picker(outsider))[:2] == [outsider, leader]
