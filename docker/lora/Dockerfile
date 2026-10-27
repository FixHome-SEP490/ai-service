# LoRA training image for the fault-choosing adapter (PO 27/10/2026).
#
# Built on the serving image's own vLLM base, so the adapter is trained with the
# transformers that ships beside the vLLM that will serve it, and the evaluation
# on the rented box loads it exactly the way service will: the AWQ model the
# service runs, with the adapter attached through vLLM's LoRA support.
#
#   docker run --gpus all --rm -e HF_TOKEN=... -e HF_DATASET_REPO=... \
#     -e HF_WEIGHTS_REPO=... -e DATA_RUN=fault-v1 -e RUN_NAME=lora-fault-v1 \
#     ghcr.io/fixhome-sep490/fixhome-lora:latest train
FROM vllm/vllm-openai:v0.29.0

ENV PYTHONUNBUFFERED=1 \
    HF_HOME=/workspace/.hf \
    HF_HUB_ENABLE_HF_TRANSFER=0

RUN pip install --no-cache-dir "peft>=0.13,<1" "accelerate>=1.0" "huggingface_hub>=0.26"

WORKDIR /opt/lora
COPY docker/lora/train_lora.py docker/lora/eval_lora.py docker/lora/entrypoint.sh ./
RUN chmod +x entrypoint.sh

ENTRYPOINT ["/opt/lora/entrypoint.sh"]
CMD ["train"]
