"""The technician review of the knowledge base, and the draft questions waiting for it.

Drafts are written by us, not by a technician, so they never reach a customer
until one has marked them right: they live in their own file, the service
does not read it, and only an approved draft is moved into the live table.
"""

from __future__ import annotations

import json

from app.services.pipeline.knowledge_base import get_knowledge_base
from app.services.pipeline.retriever import Retriever
from tools import kb_review


def _data():
    return kb_review.load()


def test_every_draft_names_real_faults_of_its_own_appliance():
    raw, drafts = _data()
    device_of = {f["fault_code"]: f["device_type"] for f in raw["faults"]}
    ids = [d["id"] for d in drafts["drafts"]]
    assert len(ids) == len(set(ids))
    for d in drafts["drafts"]:
        assert d["question_vi"].endswith("?"), d["id"]
        assert d["favours_if_yes"] and d["favours_if_no"], d["id"]
        assert not set(d["favours_if_yes"]) & set(d["favours_if_no"]), d["id"]
        for code in d["favours_if_yes"] + d["favours_if_no"]:
            assert device_of.get(code) == d["device_type"], (d["id"], code)


def test_drafts_are_not_used_by_the_service():
    raw, drafts = _data()
    kb = get_knowledge_base()
    live = {d.question_vi for d in kb.discriminators_for_device(None)}
    assert live == {d["question_vi"] for d in raw["discriminators"]}
    assert not live & {d["question_vi"] for d in drafts["drafts"]}


def test_drafts_only_cover_pairs_nothing_separates_yet():
    raw, drafts = _data()
    live = kb_review.separated_pairs(raw["discriminators"])
    for d in drafts["drafts"]:
        assert kb_review.separated_pairs([d]) - live, f"{d['id']} adds nothing the live table lacks"


def test_the_drafts_answer_the_worst_confusions():
    raw, drafts = _data()
    rows = kb_review.confusions(raw, Retriever(get_knowledge_base()), raw["discriminators"])
    covered = kb_review.separated_pairs(drafts["drafts"])
    worst = [frozenset((a, b)) for count, _, a, b in rows if count >= 4]
    assert worst, "the measure found nothing; it is broken, not perfect"
    assert all(pair in covered for pair in worst)


def test_the_sheet_rows_line_up_with_the_headers():
    raw, drafts = _data()
    faults = kb_review.fault_rows(raw)
    questions = kb_review.question_rows(raw, drafts)
    assert len(faults) == len(raw["faults"])
    assert all(len(r) == len(kb_review.FAULT_HEADERS) for r in faults)
    assert len(questions) == len(raw["discriminators"]) + len(drafts["drafts"])
    assert all(len(r) == len(kb_review.QUESTION_HEADERS) for r in questions)
    assert sum(r[1] == kb_review.DRAFT for r in questions) == len(drafts["drafts"])


def _reviewed(raw, drafts, verdicts):
    rows = kb_review.question_rows(raw, drafts)
    for row in rows:
        if row[0] in verdicts:
            row[6], row[7] = verdicts[row[0]]
    return rows


def test_an_approved_draft_moves_into_the_live_table_and_nothing_else_changes():
    raw, drafts = _data()
    before = json.dumps(raw, sort_keys=True)
    first, second, third = (d["id"] for d in drafts["drafts"][:3])
    new_raw, new_drafts, report = kb_review.apply_review(
        raw, drafts, _reviewed(raw, drafts, {first: ("Đúng", ""), second: ("Sửa", "Tivi có tiếng mà không có hình phải không ạ?"), third: ("Bỏ", "")})
    )
    assert json.dumps(raw, sort_keys=True) == before, "inputs are not changed"
    assert len(new_raw["discriminators"]) == len(raw["discriminators"]) + 2
    assert new_raw["discriminators"][-1]["question_vi"] == "Tivi có tiếng mà không có hình phải không ạ?"
    remaining = {d["id"] for d in new_drafts["drafts"]}
    assert first not in remaining and second not in remaining and third in remaining
    assert new_raw["faults"] == raw["faults"]
    assert any(third in line for line in report)


def test_a_fix_with_no_new_question_or_an_odd_answer_moves_nothing():
    raw, drafts = _data()
    first, second = (d["id"] for d in drafts["drafts"][:2])
    new_raw, new_drafts, report = kb_review.apply_review(raw, drafts, _reviewed(raw, drafts, {first: ("Sửa", ""), second: ("ok", "")}))
    assert new_raw["discriminators"] == raw["discriminators"]
    assert len(new_drafts["drafts"]) == len(drafts["drafts"])
    assert len(report) == 2


def test_changes_to_live_questions_and_faults_are_reported_for_a_person():
    raw, drafts = _data()
    _, _, report = kb_review.apply_review(raw, drafts, _reviewed(raw, drafts, {"Q01": ("Bỏ", "")}))
    assert any(line.startswith("Q01") and "sửa tay" in line for line in report)
    faults = kb_review.fault_rows(raw)
    faults[0][8], faults[0][9] = "Sửa", "giá từ 150.000"
    lines = kb_review.fault_report(faults)
    assert len(lines) == 1 and "giá từ 150.000" in lines[0]
