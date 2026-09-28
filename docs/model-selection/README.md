# Model selection: the evidence

The service had been built on YOLO11s and Qwen2.5-VL-3B before anyone asked
whether other models would have done better. This folder is the answer, run
afterwards and recorded so it can be checked: each claim about why these two
models were kept is backed by a file here, and each file says how it was made.

Nothing in this folder is a number typed in by hand. The JSON files are written
by the scripts named below, and the review deck reads its figures from them.

## What was measured, and where it is

| Question | File | Written by |
|---|---|---|
| Would a paid API be cheaper? | `api-cost.json` | `tools/api_cost_estimate.py` |
| Which detector architecture? | `detectors.json` | `tools/compare_architectures.py` |
| How well does the production detector name appliances? | `production-yolo11s.json` | `tools/eval_detector.py` |
| Could Qwen alone replace the detector? | `qwen2.5-vl-3b-instruct-awq-closed.json` | `tools/eval_vlm_device.py --mode closed` |
| Qwen against InternVL, in Vietnamese | `*-vietnamese.json`, `internvl2_5-4b-awq-closed.json` | `tools/eval_vlm_device.py` |

`api-cost.json` is an estimate, not a measurement: published prices times stated
assumptions. Every assumption is a named constant at the top of the script, so
disagreeing with one means changing it and rerunning, not arguing with the
result.

Everything else is measured.

## The detector comparison

Three architectures, trained with one variable changed.

| Held fixed | Value |
|---|---|
| Dataset | `phamductoan3883/fixhome-devices` on the Hugging Face Hub |
| Split | persisted in `datasets/split.json`, seed `20260915` |
| Image size | 640 px |
| Epochs | 30 |
| Batch | 16 |
| Hardware | RTX 3090, the same model for every run |
| Training code | `docker/train/entrypoint.sh`, `ultralytics==8.3.*` |

What changed: the starting weights, `yolo11s.pt`, `yolov10s.pt`, `rtdetr-l.pt`.
YOLO11s is a one-stage CNN with an anchor-free head and NMS. YOLOv10s removes
NMS by training with two label assignments. RT-DETR-l is a different family, a
transformer encoder-decoder with neither anchors nor NMS.

The runs were started with:

```
python tools/rent_gpu.py train --offer <id> --model yolo11s.pt  --epochs 30 --batch 16 --run-name select-yolo11s-e30
python tools/rent_gpu.py train --offer <id> --model yolov10s.pt --epochs 30 --batch 16 --run-name select-yolov10s-e30
python tools/rent_gpu.py train --offer <id> --model rtdetr-l.pt --epochs 30 --batch 16 --run-name select-rtdetr-l-e30
```

Each run published its weights and its own test pass to the weights repository
under its run name. All three were then scored again on one machine, so no
number in the table came from a different place than its neighbours:

```
python tools/compare_architectures.py --run select-yolo11s-e30 --run select-yolov10s-e30 --run select-rtdetr-l-e30
```

Parameters and GFLOPs are counted on the fused inference graph. YOLOv10 keeps a
second, one-to-many head that exists only for training and is dropped on
fusing; counted unfused it would be billed for about 3 GFLOPs it never spends.
GPU time is the `Speed:` line of each run's own test pass on its RTX 3090, read
from the training log copied into `logs/`.

The YOLO11s figures here are not the production detector's. Production trained
for 70 epochs at batch 48; these runs are 30 epochs at batch 16 for all three,
because a comparison is only fair when every entry gets the same budget.

## The language-model comparison

Seven open vision-language models of similar size were considered. Five were
ruled out on facts from their own model cards:

| Model | Parameters | Ruled out because |
|---|---|---|
| MiniCPM-V 2.6 | 8.1B | too large to share one card with the detector |
| Phi-3.5-vision | 4.2B | no 4-bit weights from the authors; about 8 GB in bf16 |
| PaliGemma 2 | 3.0B | "not a multi-turn chatbot", built "for fine-tuning" (its card) |
| SmolVLM2 | 2.2B | "Language(s): English" (its card) |
| Moondream2 | 1.9B | multilingual support described as a future extension (its changelog) |

Parameter counts come from the Hugging Face API's safetensors totals.

Two remained, Qwen2.5-VL-3B-Instruct and InternVL2.5-4B, both with official
4-bit AWQ weights. Neither could be ruled out on paper, so they were measured
head to head on identical RTX A4000 cards, both served by the stock
`vllm/vllm-openai:v0.29.0` image at temperature 0, on the same test photos.

Two questions each:

- **closed** — shown a photograph, pick the appliance from the detector's own
  list of 22. The same photos and the same truth as `eval_detector.py`.
- **vietnamese** — asked in Vietnamese with no list, is the reply Vietnamese,
  and does it name the right appliance by a name customers use?

```
python tools/eval_vlm_device.py --base-url http://<host>:<port>/v1 --api-key <key> --model <name> --mode closed
python tools/eval_vlm_device.py --base-url http://<host>:<port>/v1 --api-key <key> --model <name> --mode vietnamese
```

The `closed` run on Qwen doubles as the answer to "why two models": it is Qwen
doing the detector's job with no detector in front of it.

A serving box for either model was rented with the stock image and these
arguments, which is all it takes to reproduce the endpoint:

```
vastai create instance <offer> --image vllm/vllm-openai:v0.29.0 --disk 60 --env "-p 8000:8000" \
  --args <model> --served-model-name <model> --host 0.0.0.0 --port 8000 \
         --max-model-len 8192 --gpu-memory-utilization 0.90 --api-key <key>
```

InternVL additionally takes `--trust-remote-code`.

Both `closed` runs were served from the same host, so their latencies compare
the models. The host serving InternVL went offline before its `vietnamese` run
finished; that run was repeated from the start on another RTX A4000 with the
same image and arguments. Its accuracy is comparable; its latency includes a
different network path and is not used to compare speed.

"Names it" in the `vietnamese` mode means the reply contains a name for the
right appliance that `app/data/device_catalog.json` knows, the same catalogue
the knowledge-base lookup reads. A reply that is fair Vietnamese but not in the
catalogue, "ống nhựa PVC" for a water pipe, is counted as unparsed. The rule is
strict and it is the same for both models.

## Reading the numbers honestly

Scored photos are the test images whose label file names exactly one
appliance; a photograph of two appliances cannot be marked as one answer.
Every script uses the same rule, so every accuracy here is over the same set.

A reply that names none of the choices is counted separately as unparsed, not
as wrong and not as right.
