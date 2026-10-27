"""Measure the adapter the way service will run it, against what service does today.

Loads the served AWQ model in vLLM with the adapter attached (`enable_lora`) and
answers every val and test prompt twice, without and with the adapter, greedy.
Scored against the labelled fault:

    retrieval   the first fault offered: what service puts first today
    base        the base model's own first pick
    adapter     the adapter's first pick
    asks        for messages that settle nothing (gold null): no fault chosen

Writes results.json (by split and by kind) and predictions.jsonl.
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

SERVED = os.environ.get("SERVED_MODEL", "Qwen/Qwen2.5-VL-3B-Instruct-AWQ")
DATA = Path(os.environ.get("DATA_DIR", "/workspace/data"))
ADAPTER = Path(os.environ.get("OUT_DIR", "/workspace/adapter"))
RANK = int(os.environ.get("RANK", "16"))
MAX_EVAL = int(os.environ.get("MAX_EVAL", "0"))


def first_code(text: str, offered):
    match = re.search(r"\{.*\}", text or "", re.S)
    if not match:
        return None, False
    try:
        body = json.loads(match.group(0))
    except ValueError:
        return None, False
    codes = [c for c in body.get("fault_codes") or [] if isinstance(c, str) and c in offered]
    return (codes[0] if codes else None), True


def main() -> None:
    from vllm import LLM, SamplingParams
    from vllm.lora.request import LoRARequest

    started = time.time()
    llm = LLM(
        model=SERVED, enable_lora=True, max_lora_rank=max(16, RANK), max_model_len=8192,
        gpu_memory_utilization=0.85,
    )
    tok = llm.get_tokenizer()
    params = SamplingParams(temperature=0.0, max_tokens=96)
    lora = LoRARequest("fixhome-fault", 1, str(ADAPTER))
    results = {}
    predictions = []
    for split in ("val", "test"):
        path = DATA / f"{split}.jsonl"
        if not path.exists():
            continue
        rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
        if MAX_EVAL:
            rows = rows[:MAX_EVAL]
        prompts = [tok.apply_chat_template(r["messages"][:2], tokenize=False, add_generation_prompt=True) for r in rows]
        base_out = llm.generate(prompts, params)
        tuned_out = llm.generate(prompts, params, lora_request=lora)
        table = {}
        for row, b, t in zip(rows, base_out, tuned_out):
            gold = row["gold"]
            b_code, b_ok = first_code(b.outputs[0].text, row["offered"])
            t_code, t_ok = first_code(t.outputs[0].text, row["offered"])
            leader = row["offered"][0] if row["offered"] else None
            for kind in (row["kind"], "all"):
                cell = table.setdefault(kind, {"n": 0, "retrieval": 0, "base": 0, "adapter": 0, "adapter_or_retrieval": 0, "adapter_json": 0})
                cell["n"] += 1
                if gold is None:
                    cell["retrieval"] += 0
                    cell["base"] += b_code is None
                    cell["adapter"] += t_code is None
                    cell["adapter_or_retrieval"] += t_code is None
                else:
                    cell["retrieval"] += leader == gold
                    cell["base"] += b_code == gold
                    cell["adapter"] += t_code == gold
                    cell["adapter_or_retrieval"] += gold in (t_code, leader)
                cell["adapter_json"] += t_ok
            predictions.append({"split": split, "kind": row["kind"], "gold": gold, "retrieval": leader, "base": b_code, "adapter": t_code, "turns": row.get("turns")})
        for kind, cell in table.items():
            for key in ("retrieval", "base", "adapter", "adapter_or_retrieval", "adapter_json"):
                cell[key + "_pct"] = round(100 * cell[key] / cell["n"], 1)
        results[split] = table
        print(f"== {split}")
        for kind, cell in sorted(table.items()):
            print(f"  {kind:11} n={cell['n']:5}  retrieval {cell['retrieval_pct']:5}%  base {cell['base_pct']:5}%  adapter {cell['adapter_pct']:5}%  adapter|retrieval {cell['adapter_or_retrieval_pct']:5}%  json {cell['adapter_json_pct']}%")
    results["minutes"] = round((time.time() - started) / 60, 1)
    results["served"] = SERVED
    ADAPTER.mkdir(parents=True, exist_ok=True)
    (ADAPTER / "results.json").write_text(json.dumps(results, indent=1))
    with (ADAPTER / "predictions.jsonl").open("w", encoding="utf-8") as f:
        for p in predictions:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    sys.exit(main())
