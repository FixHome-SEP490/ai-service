"""LoRA on Qwen3.5-9B (bf16) for the chat2 turn call. Runs on the dev box.

    python3 train_lora.py /root/data/train.jsonl /root/lora [epochs]

Loss only on the assistant JSON. Targets the full-attention projections and every
MLP of the language model; the Gated DeltaNet projections are left alone so the
adapter loads in vLLM without the GDN LoRA path.
"""

import json
import math
import os
import random
import sys
import time

import torch
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForImageTextToText, AutoTokenizer

data, out = sys.argv[1], sys.argv[2]
epochs = int(sys.argv[3]) if len(sys.argv) > 3 else 2
BASE = os.environ.get("BASE", "Qwen/Qwen3.5-9B")
LR, ACC, MAXLEN = float(os.environ.get("LR", "1e-4")), int(os.environ.get("ACC", "8")), 7168
random.seed(0)
torch.manual_seed(0)

tok = AutoTokenizer.from_pretrained(BASE)
rows = [json.loads(line) for line in open(data, encoding="utf-8")]
examples = []
for r in rows:
    prompt = tok.apply_chat_template(
        r["messages"], tokenize=False, add_generation_prompt=True, enable_thinking=False
    )
    p_ids = tok(prompt, add_special_tokens=False)["input_ids"]
    t_ids = tok(r["target"].strip() + "<|im_end|>", add_special_tokens=False)["input_ids"]
    ids = (p_ids + t_ids)[:MAXLEN]
    labels = ([-100] * len(p_ids) + t_ids)[:MAXLEN]
    examples.append((ids, labels))
lens = sorted(len(e[0]) for e in examples)
print(
    "examples",
    len(examples),
    "tokens p50",
    lens[len(lens) // 2],
    "max",
    lens[-1],
    "total",
    sum(lens),
    flush=True,
)
print("sample prompt tail:", repr(prompt[-200:]), flush=True)

model = AutoModelForImageTextToText.from_pretrained(
    BASE, dtype=torch.bfloat16, device_map={"": 0}, attn_implementation="sdpa"
)
model.config.use_cache = False
model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
model.enable_input_require_grads()
cfg = LoraConfig(
    r=int(os.environ.get("RANK", "16")),
    lora_alpha=int(os.environ.get("ALPHA", "32")),
    lora_dropout=0.05,
    target_modules=r".*language_model.*\.(q_proj|k_proj|v_proj|o_proj|gate_proj|up_proj|down_proj)$",
    task_type="CAUSAL_LM",
)
model = get_peft_model(model, cfg)
model.print_trainable_parameters()

params = [p for p in model.parameters() if p.requires_grad]
opt = torch.optim.AdamW(params, lr=LR, weight_decay=0.0)
steps = math.ceil(len(examples) * epochs / ACC)
warm = max(10, steps // 20)
sched = torch.optim.lr_scheduler.LambdaLR(
    opt, lambda s: min(1.0, (s + 1) / warm) * 0.5 * (1 + math.cos(math.pi * min(1.0, s / steps)))
)

model.train()
step, t0, seen, run_loss, n_loss = 0, time.time(), 0, 0.0, 0
for ep in range(epochs):
    order = list(range(len(examples)))
    random.shuffle(order)
    for i, k in enumerate(order):
        ids, labels = examples[k]
        x = torch.tensor([ids], device="cuda")
        y = torch.tensor([labels], device="cuda")
        loss = model(input_ids=x, labels=y).loss / ACC
        loss.backward()
        run_loss += loss.item() * ACC
        n_loss += 1
        seen += len(ids)
        if (i + 1) % ACC == 0 or i == len(order) - 1:
            torch.nn.utils.clip_grad_norm_(params, 1.0)
            opt.step()
            sched.step()
            opt.zero_grad(set_to_none=True)
            step += 1
            if step % 10 == 0:
                el = time.time() - t0
                print(
                    f"ep {ep} step {step}/{steps} loss {run_loss / n_loss:.4f} lr {sched.get_last_lr()[0]:.2e} "
                    f"tok/s {seen / el:.0f} elapsed {el / 60:.1f}m eta {(steps - step) * el / step / 60:.1f}m",
                    flush=True,
                )
                run_loss, n_loss = 0.0, 0
    model.save_pretrained(f"{out}/pick-e{ep + 1}")
    print("saved", f"{out}/pick-e{ep + 1}", flush=True)
print("DONE", (time.time() - t0) / 60, "min", flush=True)
