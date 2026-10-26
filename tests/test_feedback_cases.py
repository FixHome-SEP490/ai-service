"""Every customer-marked answer a person has reviewed stays right (tools/feedback_review.py)."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import feedback_review  # noqa: E402

from app.services.pipeline.knowledge_base import get_knowledge_base  # noqa: E402


def _cases():
    return json.loads((ROOT / "tools" / "feedback_cases.json").read_text(encoding="utf-8"))["cases"]


def test_every_case_names_a_real_fault_of_its_appliance():
    kb = get_knowledge_base()
    for case in _cases():
        fault = kb.fault(case["fault"])
        assert fault is not None, case
        assert fault.device_type == case["device"], case


def test_every_case_is_answered_with_its_fault_among_the_first_three():
    assert feedback_review.check() == 0


def test_the_answer_today_is_read_from_the_words():
    pipeline, _kb = feedback_review._pipeline()
    now = feedback_review.answer_now(pipeline, "quạt điện quạt phải lấy tay quay mới chạy")
    assert now["device"] == "electric_fan"
    assert "FAN_CAPACITOR" in now["faults"]
