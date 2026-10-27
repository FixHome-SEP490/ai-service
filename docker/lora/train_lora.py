"""Train the fault-choosing LoRA adapter on captured pipeline prompts.

Input: train.jsonl / val.jsonl from tools/build_lora_data.py, each line
{"messages": [system, user, assistant], ...}. Only the assistant answer is
learned; the prompt is context. The language model gets the adapter; the vision
tower is untouched (photographs still go to the base model).

Everything that matters is printed and written to train_log.json beside the
adapter: versions, seed, hyperparameters, steps, losses, time.
"""

from __future__ import annotations

import json
import math
import os
import random
import sys
import time
from pathlib import Path

import torch

BASE = os.environ.get("BASE_MODEL", "Qwen/Qwen2.5-VL-3B-Instruct")
DATA = Path(os.environ.get("DATA_DIR", "/workspace/data"))
OUT = Path(os.environ.get("OUT_DIR", "/workspace/adapter"))
EPOCHS = float(os.environ.get("EPOCHS", "1"))
LR = float(os.environ.get("LR", "1e-4"))
RANK = int(os.environ.get("RANK", "16"))
ALPHA = int(os.environ.get("ALPHA", str(2 * RANK)))
MAX_LEN = int(os.environ.get("MAX_LEN", "3584"))
BATCH = int(os.environ.get("BATCH", "4"))
ACCUM = int(os.environ.get("ACCUM", "4"))
MAX_TRAIN = int(os.environ.get("MAX_TRAIN", "0"))
SEED = int(os.environ.get("SEED", "20261027"))
TARGETS = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]


def load(name: str):
    rows = [json.loads(line) for line in (DATA / name).read_text(encoding="utf-8").splitlines() if line.strip()]
    return rows


def main() -> None:
    import peft
    import transformers
    from peft import LoraConfig, get_peft_model
    from transformers import AutoTokenizer

    try:
        from transformers import Qwen2_5_VLForConditionalGeneration as ModelClass
    except ImportError:  # newer transformers
        from transformers import AutoModelForImageTextToText as ModelClass

    random.seed(SEED)
    torch.manual_seed(SEED)
    started = time.time()
    print(f"torch {torch.__version__}, transformers {transformers.__version__}, peft {peft.__version__}")
    print(f"base {BASE}, epochs {EPOCHS}, lr {LR}, rank {RANK}, alpha {ALPHA}, max_len {MAX_LEN}, batch {BATCH}x{ACCUM}")

    tok = AutoTokenizer.from_pretrained(BASE)
    model = ModelClass.from_pretrained(BASE, torch_dtype=torch.bfloat16, attn_implementation="sdpa").to("cuda")
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={"use_reentrant": False})
    model.enable_input_require_grads()
    # Language model only: a regex that keeps the vision tower's MLP (which
    # shares the projection names) out of the adapter.
    config = LoraConfig(
        r=RANK, lora_alpha=ALPHA, lora_dropout=0.05, bias="none", task_type="CAUSAL_LM",
        target_modules=r"^(?!.*visual).*\.(" + "|".join(TARGETS) + r")$",
    )
    model = get_peft_model(model, config)
    model.print_trainable_parameters()

    def encode(row):
        prompt = tok.apply_chat_template(row["messages"][:2], tokenize=False, add_generation_prompt=True)
        answer = row["messages"][2]["content"] + "<|im_end|>\n"
        p = tok(prompt, add_special_tokens=False)["input_ids"]
        a = tok(answer, add_special_tokens=False)["input_ids"]
        if len(p) + len(a) > MAX_LEN:
            p = p[-(MAX_LEN - len(a)):]  # keep the end of the prompt: the candidates and the latest words
        return p + a, [-100] * len(p) + a

    train = load("train.jsonl")
    val = load("val.jsonl")
    random.shuffle(train)
    if MAX_TRAIN:
        train = train[:MAX_TRAIN]
    encoded = [encode(r) for r in train]
    lengths = sorted(len(x[0]) for x in encoded)
    print(f"train {len(encoded)}, val {len(val)}, tokens median {lengths[len(lengths) // 2]}, p95 {lengths[int(len(lengths) * .95)]}, max {lengths[-1]}", flush=True)

    optimizer = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=LR, weight_decay=0.0)
    steps_total = math.ceil(len(encoded) * EPOCHS / (BATCH * ACCUM))
    warmup = max(1, steps_total // 20)

    def lr_at(step):
        if step < warmup:
            return LR * (step + 1) / warmup
        progress = (step - warmup) / max(1, steps_total - warmup)
        return LR * 0.5 * (1 + math.cos(math.pi * progress))

    def batches():
        order = list(range(len(encoded)))
        rounds = math.ceil(EPOCHS)
        for r in range(rounds):
            random.shuffle(order)
            limit = len(order) if r + 1 <= EPOCHS else int(len(order) * (EPOCHS - r))
            chosen = sorted(order[:limit], key=lambda i: len(encoded[i][0]))  # similar lengths together
            groups = [chosen[i:i + BATCH] for i in range(0, len(chosen), BATCH)]
            random.shuffle(groups)
            yield from groups

    def collate(idx):
        width = max(len(encoded[i][0]) for i in idx)
        ids = torch.full((len(idx), width), tok.pad_token_id or 0, dtype=torch.long)
        labels = torch.full((len(idx), width), -100, dtype=torch.long)
        mask = torch.zeros((len(idx), width), dtype=torch.long)
        for row, i in enumerate(idx):
            x, y = encoded[i]
            ids[row, : len(x)] = torch.tensor(x)
            labels[row, : len(y)] = torch.tensor(y)
            mask[row, : len(x)] = 1
        return ids.cuda(), labels.cuda(), mask.cuda()

    # The answer is a few dozen tokens at the end of a prompt of thousands, so
    # the vocabulary projection is taken only where there is something to
    # learn. Through `labels=` the model projects every position in fp32:
    # 4 x 3584 x 151k logits, 8.7 GB, and the first run ran out of memory.
    inner = model.base_model.model
    head = inner.get_output_embeddings()

    def answer_loss(ids, labels, mask):
        hidden = inner.model(input_ids=ids, attention_mask=mask, use_cache=False).last_hidden_state
        target = labels[:, 1:]
        where = target != -100
        logits = head(hidden[:, :-1][where]).float()
        return torch.nn.functional.cross_entropy(logits, target[where])

    model.train()
    log = {"losses": []}
    step = 0
    running = 0.0
    for micro, idx in enumerate(batches()):
        ids, labels, mask = collate(idx)
        loss = answer_loss(ids, labels, mask) / ACCUM
        loss.backward()
        running += loss.item()
        if (micro + 1) % ACCUM == 0:
            for group in optimizer.param_groups:
                group["lr"] = lr_at(step)
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            optimizer.zero_grad(set_to_none=True)
            step += 1
            if step % 10 == 0 or step == 1:
                elapsed = time.time() - started
                print(f"step {step}/{steps_total} loss {running:.4f} lr {lr_at(step):.2e} {elapsed / 60:.1f} min", flush=True)
            log["losses"].append([step, round(running, 5)])
            running = 0.0

    OUT.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(OUT)
    tok.save_pretrained(OUT)
    # vLLM matches adapter modules by name; a plain list is the form every
    # version reads. The weights themselves only cover the language model.
    cfg_path = OUT / "adapter_config.json"
    cfg = json.loads(cfg_path.read_text())
    cfg["target_modules"] = TARGETS
    cfg_path.write_text(json.dumps(cfg, indent=1))
    log.update({
        "base": BASE, "epochs": EPOCHS, "lr": LR, "rank": RANK, "alpha": ALPHA, "max_len": MAX_LEN,
        "batch": BATCH, "accum": ACCUM, "seed": SEED, "train_examples": len(encoded), "steps": step,
        "minutes": round((time.time() - started) / 60, 1), "torch": torch.__version__,
        "transformers": transformers.__version__, "peft": peft.__version__,
        "gpu": torch.cuda.get_device_name(0),
    })
    (OUT / "train_log.json").write_text(json.dumps(log, indent=1))
    print(f"saved adapter to {OUT} after {log['minutes']} min")


if __name__ == "__main__":
    sys.exit(main())
