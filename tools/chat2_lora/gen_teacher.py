"""Training rows for the fault-choice adapter, from the dev half of understanding_bank.

For every dev phrase the real brain runs (router, then the turn call), but the turn
call's schema pins fault_code to the labelled fault and decision to conclude, so the
base model writes the rest of the JSON (need, reply, service) around the right
answer. A row is the exact messages of that call plus the JSON it wrote. The natural
(unpinned) answer is recorded too, to count how often the base was already right.

    python gen_teacher.py <ai-service dir> <base_url> <key> <out.jsonl>
"""

import asyncio
import copy
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
sys.path.insert(0, str(root))
sys.path.insert(0, str(root / "tools"))
import httpx  # noqa: E402
from app.services.chat2 import brain as B  # noqa: E402
from eval_understanding import split_of  # noqa: E402

base_url, key, out = sys.argv[2], sys.argv[3], sys.argv[4]
bank = json.loads((root / "tools" / "understanding_bank.json").read_text(encoding="utf-8"))
items = []
for device, v in bank["devices"].items():
    for code, kinds in v["faults"].items():
        for kind in ("clear", "indirect"):
            for p in kinds.get(kind, []):
                if split_of(p) == "dev":
                    items.append({"device": device, "fault": code, "kind": kind, "text": p})
print("items", len(items), flush=True)


class Teacher(B.ChatBrain):
    async def _call(self, client, messages, schema, max_tokens, model=None):
        gold = getattr(self, "_gold", None)
        props = schema.get("properties", {})
        if gold and "need_kind" in props:
            pinned = copy.deepcopy(schema)
            pp = pinned["properties"]
            pp["fault_code"]["enum"] = [gold]
            pp["decision"]["enum"] = ["conclude"]
            pp["need_kind"]["enum"] = [B.SYMPTOM, B.DAMAGE]
            body = {
                "model": self._model,
                "messages": messages,
                "temperature": 0.0,
                "max_tokens": max_tokens,
                "structured_outputs": {"json": pinned},
                "stop": ["\n\n\n"],
                **self._extra,
            }
            r = await client.post(
                self._url, json=body, headers=self._headers, timeout=self._timeout
            )
            r.raise_for_status()
            self._rows.append(
                {"messages": messages, "target": r.json()["choices"][0]["message"]["content"]}
            )
        return await super()._call(client, messages, schema, max_tokens, model)


async def main():
    sem = asyncio.Semaphore(16)
    rows, stats = [], {"rows": 0, "natural_right": 0, "no_turn": 0, "err": 0}
    extra = {"chat_template_kwargs": {"enable_thinking": False}}
    async with httpx.AsyncClient() as client:

        async def one(it):
            t = Teacher(base_url, "m", key, timeout_s=90, extra_body=extra)
            t._gold, t._rows = it["fault"], []
            async with sem:
                try:
                    v = await t.turn(client, [B.Turn("user", it["text"])], it["device"])
                except Exception as exc:
                    stats["err"] += 1
                    print("err", type(exc).__name__, str(exc)[:120], flush=True)
                    return
            if not t._rows:
                stats["no_turn"] += 1
                return
            right = v.decision == "conclude" and v.fault_code == it["fault"]
            stats["natural_right"] += right
            for r in t._rows[:1]:
                rows.append(
                    {
                        **it,
                        **r,
                        "natural": {"decision": v.decision, "fault": v.fault_code},
                        "natural_right": right,
                    }
                )
            stats["rows"] += 1
            if stats["rows"] % 100 == 0:
                print(stats, flush=True)

        await asyncio.gather(*(one(i) for i in items))
    with open(out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("done", stats, flush=True)


asyncio.run(main())
