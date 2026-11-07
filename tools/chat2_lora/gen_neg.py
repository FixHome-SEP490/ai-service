"""Rows that are not a fault, so the adapter does not learn that every message names one.

Vague complaints (should ask) and generic damage (dropped, flooded, knocked:
concluded on no fault, the repair service). Written here from templates, never
taken from understanding_bank (whose vague list is scored), and any phrase that
exists in the bank is skipped.

    python gen_neg.py <ai-service dir> <base_url> <key> <out.jsonl>
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
from app.services.chat2.menu import devices  # noqa: E402

base_url, key, out = sys.argv[2], sys.argv[3], sys.argv[4]
bank = json.loads((root / "tools" / "understanding_bank.json").read_text(encoding="utf-8"))
seen = {p.strip().lower() for v in bank["devices"].values() for p in v.get("vague", [])}
seen |= {
    p.strip().lower()
    for v in bank["devices"].values()
    for k in v["faults"].values()
    for x in k.values()
    for p in x
}

VAGUE = [
    "{d} nhà em có vấn đề rồi",
    "{d} dạo này cứ sao sao ấy em",
    "xem giúp em cái {d} với",
    "{d} hình như bị hư rồi",
    "cái {d} nhà mình trục trặc",
    "{d} nhà em không được bình thường lắm",
    "em muốn hỏi về cái {d}, nó bị gì đó",
    "{d} có chuyện rồi, giúp em với",
]
DAMAGE = [
    "{d} bị rơi xuống đất",
    "lúc dọn nhà làm đổ cái {d}",
    "{d} bị ngập nước hôm mưa lớn",
    "chuyển nhà xong cái {d} bị va mạnh",
    "con em lỡ xô ngã cái {d}",
]
items = []
for dev, name in devices().items():
    n = name.lower()
    for t in VAGUE:
        items.append({"device": dev, "kind": "vague", "text": t.format(d=n)})
    for t in DAMAGE:
        items.append({"device": dev, "kind": "damage", "text": t.format(d=n)})
items = [i for i in items if i["text"].lower() not in seen]
print("items", len(items), flush=True)


class Teacher(B.ChatBrain):
    async def _call(self, client, messages, schema, max_tokens, model=None):
        props = schema.get("properties", {})
        if "need_kind" in props:
            pinned = copy.deepcopy(schema)
            pp = pinned["properties"]
            pp["fault_code"]["enum"] = [B.NONE]
            if self._kind == "vague":
                pp["need_kind"]["enum"] = [B.UNCLEAR]
                pp["decision"]["enum"] = ["ask"]
            else:
                pp["need_kind"]["enum"] = [B.DAMAGE]
                pp["decision"]["enum"] = ["conclude"]
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
    sem = asyncio.Semaphore(8)
    rows = []
    async with httpx.AsyncClient() as client:

        async def one(it):
            t = Teacher(
                base_url,
                "m",
                key,
                timeout_s=120,
                extra_body={"chat_template_kwargs": {"enable_thinking": False}},
            )
            t._kind, t._rows = it["kind"], []
            async with sem:
                try:
                    v = await t.turn(client, [B.Turn("user", it["text"])], it["device"])
                except Exception as exc:
                    print("err", type(exc).__name__, flush=True)
                    return
            if t._rows:
                rows.append(
                    {**it, **t._rows[0], "natural": {"decision": v.decision, "fault": v.fault_code}}
                )

        await asyncio.gather(*(one(i) for i in items))
    with open(out, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print("done", len(rows), flush=True)


asyncio.run(main())
