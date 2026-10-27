#!/usr/bin/env bash
# Start Qwen, wait until it can actually answer, then start the API.
#
# The order matters and so does the waiting. The API degrades a failed model
# call into "ask the customer a question", which is right when the model is
# down and wrong during startup: every request in the first two minutes would
# come back as a clarification, the service would look healthy, and nobody
# would know the difference.
#
# Both share one GPU, so vLLM is told to leave room. At 0.85 of a 12GB card it
# takes 9.9GB and the detector has 1.6GB to live in, which is where CUDA runs
# out partway through a request rather than at startup.

set -euo pipefail

VLM_PORT="${VLM_PORT:-8001}"
API_PORT="${API_PORT:-8000}"
MODEL="${VLM_MODEL_NAME:-Qwen/Qwen2.5-VL-3B-Instruct-AWQ}"
GPU_FRACTION="${GPU_FRACTION:-0.70}"
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
    --max-model-len "${MAX_LEN}"     "${LORA_ARGS[@]}" &
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
