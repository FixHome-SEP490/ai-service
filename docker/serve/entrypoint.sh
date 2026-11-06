#!/usr/bin/env bash
# Start the chat model, wait until it can actually answer, then start the API.
#
# The order matters and so does the waiting. The API degrades a failed model
# call into "ask the customer a question", which is right when the model is
# down and wrong during startup: every request in the first two minutes would
# come back as a clarification, the service would look healthy, and nobody
# would know the difference.
#
# Both share one GPU, so vLLM is told to leave room. The chat model is
# Qwen3.5-9B served text only: the detector reads the photographs and the
# model never sees one. Which build depends on the card, picked below from its
# memory unless VLM_MODEL_NAME says otherwise. Measured 06/11, same code, same
# 707 cases: FP8 on a 24GB RTX 3090 got 83.1% of clear descriptions right
# (16.1% wrong and sure of it), 4-bit AWQ on a 16GB RTX 4060 Ti 75.9% (22.3%).
# FP8 does not fit 16GB: quantised at load it pulls the 19GB bf16 weights onto
# the card, and the published FP8 checkpoint is 14GB. AWQ is 7.5GB of weights,
# and at 0.80 leaves a KV cache of 62,557 tokens and 3.2GB to the detector.

set -euo pipefail

VLM_PORT="${VLM_PORT:-8001}"
API_PORT="${API_PORT:-8000}"
FP8_MODEL="RedHatAI/Qwen3.5-9B-FP8-dynamic"
AWQ_MODEL="cyankiwi/Qwen3.5-9B-AWQ-4bit"
# 22,000 MiB rather than 24,576: cards sold as 24GB report a little less.
FP8_MIN_MIB="${FP8_MIN_MIB:-22000}"
GPU_FRACTION="${GPU_FRACTION:-0.80}"
# No image or video inputs: the vision tower is never loaded and its memory
# goes to the KV cache. Qwen3.5 keeps one Mamba cache block per running
# sequence and has ~200 of them at this size, so vLLM's default of 256
# sequences fails at CUDA graph capture; 64 is more than one card serves.
read -r -a MODEL_ARGS <<< "${VLM_EXTRA_ARGS:---max-num-seqs 64}"
MODEL_ARGS+=(--limit-mm-per-prompt '{"image":0,"video":0}')
export AI_ENGINE="${AI_ENGINE:-chat2}"
MAX_LEN="${MAX_LEN:-8192}"
WEIGHTS_DIR="${WEIGHTS_DIR:-/workspace/weights}"
# The fault-choosing adapter (docker/lora), by run name in HF_WEIGHTS_REPO.
# Unset, Qwen is served as it always was and retrieval leads.
LORA_RUN="${LORA_RUN:-}"
LORA_NAME="fixhome-fault"
LORA_ARGS=()

log() { printf '\n== %s\n' "$*"; }

log "GPU"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || {
  echo "No GPU visible. Pass --gpus all." >&2
  exit 1
}

pick_model() {
  if [[ -n "${VLM_MODEL_NAME:-}" ]]; then
    MODEL="${VLM_MODEL_NAME}"
    log "Model ${MODEL} (set by VLM_MODEL_NAME)"
    return
  fi
  local mib
  mib="$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -n 1 | tr -dc '0-9')"
  if [[ -n "${mib}" ]] && (( mib >= FP8_MIN_MIB )); then
    MODEL="${FP8_MODEL}"
  else
    MODEL="${AWQ_MODEL}"
  fi
  log "Model ${MODEL} for a card of ${mib:-unknown} MiB"
}
pick_model

fetch_weights() {
  if [[ -n "${YOLO_WEIGHTS_PATH:-}" && -f "${YOLO_WEIGHTS_PATH}" ]]; then
    log "Detector weights already at ${YOLO_WEIGHTS_PATH}"
    return
  fi
  if [[ -z "${HF_WEIGHTS_REPO:-}" ]]; then
    log "HF_WEIGHTS_REPO unset; the detector will fall back to the stub"
    log "Every photograph will come back as the same appliance."
    return
  fi

  local run="${WEIGHTS_RUN:-detector-v1}"
  log "Downloading ${HF_WEIGHTS_REPO}/${run}"
  python3 - "$HF_WEIGHTS_REPO" "$run" "$WEIGHTS_DIR" <<'PY'
import sys
from huggingface_hub import snapshot_download

repo, run, target = sys.argv[1], sys.argv[2], sys.argv[3]
path = snapshot_download(
    repo_id=repo, repo_type="model", local_dir=target,
    allow_patterns=[f"{run}/weights/best.pt"],
)
print(path)
PY

  local found
  found="$(find "${WEIGHTS_DIR}" -name best.pt -print -quit)"
  if [[ -z "${found}" ]]; then
    # Refuse rather than start on the stub. A stub that answers every photo
    # with the same appliance is worse than a service that will not start,
    # because it looks like it is working.
    echo "No best.pt under ${WEIGHTS_DIR} after download." >&2
    echo "Check HF_WEIGHTS_REPO and WEIGHTS_RUN=${run}." >&2
    exit 1
  fi
  export YOLO_WEIGHTS_PATH="${found}"
  log "Detector weights at ${YOLO_WEIGHTS_PATH}"
}

fetch_adapter() {
  [[ -n "${LORA_RUN}" ]] || return 0
  log "Downloading adapter ${HF_WEIGHTS_REPO}/${LORA_RUN}"
  python3 - "$HF_WEIGHTS_REPO" "$LORA_RUN" "$WEIGHTS_DIR" <<'PY'
import sys
from huggingface_hub import snapshot_download

repo, run, target = sys.argv[1], sys.argv[2], sys.argv[3]
snapshot_download(
    repo_id=repo, repo_type="model", local_dir=target,
    allow_patterns=[f"{run}/adapter_config.json", f"{run}/adapter_model.safetensors"],
)
PY
  local dir="${WEIGHTS_DIR}/${LORA_RUN}"
  if [[ ! -f "${dir}/adapter_model.safetensors" ]]; then
    # Same reasoning as the detector: refuse rather than quietly serve the
    # base model under a configuration that says the adapter is on.
    echo "No adapter under ${dir} after download. Check LORA_RUN=${LORA_RUN}." >&2
    exit 1
  fi
  LORA_ARGS=(--enable-lora --max-lora-rank "${LORA_RANK:-16}" --lora-modules "${LORA_NAME}=${dir}")
  export VLM_FAULT_MODEL="${LORA_NAME}"
  log "Adapter ${LORA_RUN} served as ${LORA_NAME}"
}

start_vllm() {
  log "Starting Qwen (${MODEL}) on port ${VLM_PORT}, ${GPU_FRACTION} of the card"
  python3 -m vllm.entrypoints.openai.api_server \
    --model "${MODEL}" \
    --served-model-name "${MODEL}" \
    --host 127.0.0.1 \
    --port "${VLM_PORT}" \
    --gpu-memory-utilization "${GPU_FRACTION}" \
    --max-model-len "${MAX_LEN}" "${MODEL_ARGS[@]}" "${LORA_ARGS[@]}" &
  VLM_PID=$!
  trap 'kill ${VLM_PID} 2>/dev/null || true' EXIT
}

wait_for_vllm() {
  log "Waiting for the model to load"
  for _ in $(seq 1 180); do
    if curl --fail --silent "http://127.0.0.1:${VLM_PORT}/v1/models" >/dev/null 2>&1; then
      log "Qwen is answering"
      return
    fi
    if ! kill -0 "${VLM_PID}" 2>/dev/null; then
      echo "vLLM exited before becoming ready. Its error is above." >&2
      exit 1
    fi
    sleep 5
  done
  echo "vLLM did not become ready within 15 minutes." >&2
  exit 1
}

start_api() {
  export VLM_BASE_URL="http://127.0.0.1:${VLM_PORT}"
  export VLM_MODEL_NAME="${MODEL}"
  log "Starting the API on port ${API_PORT}"
  log "  detector: ${YOLO_WEIGHTS_PATH:-stub}"
  log "  vlm:      ${VLM_BASE_URL}"
  log "  adapter:  ${VLM_FAULT_MODEL:-none}"
  log "  engine:   ${AI_ENGINE}"
  exec python3 -m uvicorn app.main:app --host 0.0.0.0 --port "${API_PORT}"
}

case "${1:-serve}" in
  serve)
    fetch_weights
    fetch_adapter
    start_vllm
    wait_for_vllm
    start_api
    ;;
  shell) exec /bin/bash ;;
  *) echo "Unknown command: $1 (expected serve or shell)" >&2; exit 2 ;;
esac
