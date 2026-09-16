#!/usr/bin/env bash
# Serve Qwen2.5-VL on a rented GPU.
#
# Run this on the vast.ai box, not locally. It starts vLLM with an
# OpenAI-compatible API on port 8000, which is what app/services/pipeline/
# qwen_client.py speaks.
#
#   curl -sL https://raw.githubusercontent.com/FixHome-SEP490/ai-service/main/docker/serve/vllm.sh | bash
#
# Then point the service at it:
#   VLM_BASE_URL=https://<your-tunnel-host>
#
# A rented instance gets a new IP every time it starts, so the last step opens
# a Cloudflare tunnel and prints a stable HTTPS address. Backend then holds one
# address forever instead of being reconfigured after every rental.

set -euo pipefail

MODEL="${MODEL:-Qwen/Qwen2.5-VL-3B-Instruct-AWQ}"
PORT="${PORT:-8000}"
# vLLM reserves this fraction of VRAM up front. The default of 0.9 leaves no
# room for YOLO on the same card; 0.55 of a 12GB card is comfortable for a 3B
# AWQ model plus its KV cache.
GPU_FRACTION="${GPU_FRACTION:-0.55}"
MAX_LEN="${MAX_LEN:-8192}"

log() { printf '\n== %s\n' "$*"; }

log "GPU"
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || {
  echo "No GPU visible. This script is for a rented GPU instance." >&2
  exit 1
}

log "Installing vLLM"
pip install --quiet --upgrade pip
# Pinned: an unpinned vLLM changes sampling defaults and model support between
# rentals, and results stop being comparable with the previous run.
#
# 0.6 was the original pin and would never have worked: Qwen2.5-VL support
# arrived in 0.7.2, so the install would have succeeded and the model would
# then have been refused, which is a slow way to learn it.
#
# Prefer `python tools/rent_gpu.py serve`, which runs the official
# vllm/vllm-openai image instead and skips this install entirely. This script
# is for a box that already exists.
pip install --quiet "vllm==0.29.*" "qwen-vl-utils"

log "Starting vLLM for ${MODEL}"
python -m vllm.entrypoints.openai.api_server \
  --model "${MODEL}" \
  --served-model-name "${MODEL}" \
  --port "${PORT}" \
  --gpu-memory-utilization "${GPU_FRACTION}" \
  --max-model-len "${MAX_LEN}" \
  --limit-mm-per-prompt image=1 \
  --trust-remote-code &

SERVER_PID=$!
trap 'kill ${SERVER_PID} 2>/dev/null || true' EXIT

log "Waiting for the model to load, this takes a few minutes on first run"
for attempt in $(seq 1 120); do
  if curl --fail --silent "http://127.0.0.1:${PORT}/v1/models" >/dev/null 2>&1; then
    log "Ready"
    curl --silent "http://127.0.0.1:${PORT}/v1/models"
    break
  fi
  if ! kill -0 "${SERVER_PID}" 2>/dev/null; then
    echo "vLLM exited before becoming ready. Scroll up for its error." >&2
    exit 1
  fi
  sleep 5
done

log "Smoke test"
curl --silent "http://127.0.0.1:${PORT}/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d "{\"model\":\"${MODEL}\",\"messages\":[{\"role\":\"user\",\"content\":\"Trả lời đúng một từ: xin chào\"}],\"temperature\":0,\"max_tokens\":16}" \
  | head -c 400
echo

if command -v cloudflared >/dev/null 2>&1; then
  log "Opening a public HTTPS address"
  echo "Copy the trycloudflare.com URL below into VLM_BASE_URL."
  cloudflared tunnel --url "http://127.0.0.1:${PORT}"
else
  log "cloudflared not installed"
  echo "The API is on port ${PORT} of this instance only."
  echo "Install cloudflared for a stable HTTPS address, or map the port in the"
  echo "vast.ai instance settings and use its host:port directly."
  wait "${SERVER_PID}"
fi
