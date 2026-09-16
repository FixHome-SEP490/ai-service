#!/usr/bin/env bash
# Entry point for a rented GPU box.
#
# A rental is disposable: it appears, does one job, and is destroyed. So the
# container pulls the dataset in at the start and pushes results out at the end,
# and keeps nothing important on local disk. Losing the machine then costs
# nothing but the minutes since the last run.
#
#   docker run --gpus all --rm \
#     -e HF_TOKEN=... -e HF_DATASET_REPO=user/fixhome-devices \
#     -e HF_WEIGHTS_REPO=user/fixhome-detector \
#     <user>/fixhome-trainer:1.0 train
#
# Commands: train (default), evaluate, shell.

set -euo pipefail

DATA_DIR="${DATA_DIR:-/workspace/datasets/fixhome}"
RUNS_DIR="${RUNS_DIR:-/workspace/runs}"
MODEL="${MODEL:-yolov8n.pt}"
EPOCHS="${EPOCHS:-100}"
IMAGE_SIZE="${IMAGE_SIZE:-640}"
BATCH="${BATCH:-16}"
SEED="${SEED:-20260915}"
RUN_NAME="${RUN_NAME:-detector-$(date +%Y%m%d-%H%M%S)}"

log() { printf '\n== %s\n' "$*"; }

require_gpu() {
  if ! python -c "import torch, sys; sys.exit(0 if torch.cuda.is_available() else 1)"; then
    echo "No CUDA device visible. Did you pass --gpus all?" >&2
    exit 1
  fi
  python - <<'PY'
import torch
print(f"GPU: {torch.cuda.get_device_name(0)}")
print(f"VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
print(f"torch {torch.__version__}, CUDA {torch.version.cuda}")
PY
}

fetch_dataset() {
  if [[ -f "${DATA_DIR}/data.yaml" ]]; then
    log "Dataset already present at ${DATA_DIR}"
    return
  fi
  if [[ -z "${HF_DATASET_REPO:-}" ]]; then
    echo "No dataset at ${DATA_DIR} and HF_DATASET_REPO is unset." >&2
    echo "Either mount a dataset volume or set HF_DATASET_REPO." >&2
    exit 1
  fi
  log "Downloading dataset ${HF_DATASET_REPO}"
  huggingface-cli download "${HF_DATASET_REPO}" \
    --repo-type dataset --local-dir "${DATA_DIR}"

  # The dataset travels as one archive. Uploading it as loose files hit the
  # Hub's limit of 128 commits an hour partway through and left images without
  # their labels, which trains quietly on the wrong thing.
  local archive="${DATA_DIR}/fixhome-dataset.tar.gz"
  if [[ -f "${archive}" ]]; then
    log "Unpacking $(du -h "${archive}" | cut -f1)"
    tar -xzf "${archive}" -C "${DATA_DIR}"
    rm -f "${archive}"
  fi

  [[ -f "${DATA_DIR}/data.yaml" ]] || {
    echo "No data.yaml in ${DATA_DIR} after download." >&2
    exit 1
  }

  local images labels
  images=$(find "${DATA_DIR}/images" -type f | wc -l)
  labels=$(find "${DATA_DIR}/labels" -type f | wc -l)
  log "${images} images, ${labels} labels"
  if [[ "${images}" -ne "${labels}" ]]; then
    # Ultralytics skips an image with no label beside it and says nothing, so
    # a partial download would train on less data and still look healthy.
    echo "Counts differ; the dataset did not arrive intact." >&2
    exit 1
  fi
}

fix_dataset_root() {
  # data.yaml ships with a relative root, because the machine that exports the
  # dataset is not the machine that trains on it. Ultralytics resolves a
  # relative `path` against its own configured datasets directory rather than
  # against the yaml, so leaving it alone fails with a "dataset not found" that
  # names a directory nobody chose. Point it at where the files actually landed.
  local yaml="${DATA_DIR}/data.yaml"
  [[ -f "${yaml}" ]] || { echo "No data.yaml in ${DATA_DIR}" >&2; exit 1; }

  python - "${yaml}" "${DATA_DIR}" <<'PYEOF'
import sys
from pathlib import Path

yaml_path, root = Path(sys.argv[1]), sys.argv[2]
lines = yaml_path.read_text(encoding="utf-8").splitlines()
out = [f"path: {root}" if line.startswith("path:") else line for line in lines]
if not any(line.startswith("path: ") for line in out):
    out.insert(0, f"path: {root}")
yaml_path.write_text("\n".join(out) + "\n", encoding="utf-8")
print(f"dataset root set to {root}")
PYEOF
}

publish_weights() {
  local run_dir="$1"
  if [[ -z "${HF_WEIGHTS_REPO:-}" || -z "${HF_TOKEN:-}" ]]; then
    log "HF_WEIGHTS_REPO or HF_TOKEN unset; weights stay in ${run_dir}"
    log "Copy them out before destroying this machine."
    return
  fi
  log "Uploading weights and metrics to ${HF_WEIGHTS_REPO}"
  huggingface-cli upload "${HF_WEIGHTS_REPO}" "${run_dir}" "${RUN_NAME}" \
    --repo-type model --commit-message "${RUN_NAME}"
}

DONE_MARKER="${RUNS_DIR}/${RUN_NAME}.done"

refuse_if_already_done() {
  # vast.ai restarts a container that exits, so a finished run starts over:
  # it retrains, overwrites its own published weights, and bills for as long
  # as nobody is watching. Observed on the first real rental, which was two
  # epochs into a second identical run before anyone noticed.
  #
  # /workspace survives the restart, so a marker written on success is the
  # thing that distinguishes "started again" from "started".
  if [[ -f "${DONE_MARKER}" ]]; then
    log "Run ${RUN_NAME} already finished on this machine:"
    cat "${DONE_MARKER}"
    log "Not training again. Destroy the instance to stop being charged."
    # Sleep rather than exit, because exiting is what triggers the restart
    # this guard exists to break.
    while true; do sleep 3600; done
  fi
}

cmd_train() {
  refuse_if_already_done
  require_gpu
  fetch_dataset
  fix_dataset_root
  log "Training ${MODEL} for ${EPOCHS} epochs at ${IMAGE_SIZE}px, batch ${BATCH}"
  yolo detect train \
    model="${MODEL}" \
    data="${DATA_DIR}/data.yaml" \
    epochs="${EPOCHS}" \
    imgsz="${IMAGE_SIZE}" \
    batch="${BATCH}" \
    seed="${SEED}" \
    deterministic=True \
    project="${RUNS_DIR}" \
    name="${RUN_NAME}" \
    exist_ok=True \
    plots=True

  local run_dir="${RUNS_DIR}/${RUN_NAME}"
  log "Evaluating on the held-out test split"
  # Reported on test, never on the split used to pick the checkpoint.
  yolo detect val \
    model="${run_dir}/weights/best.pt" \
    data="${DATA_DIR}/data.yaml" \
    split=test \
    project="${RUNS_DIR}" \
    name="${RUN_NAME}-test" \
    exist_ok=True \
    plots=True

  cp -r "${RUNS_DIR}/${RUN_NAME}-test" "${run_dir}/test" 2>/dev/null || true
  publish_weights "${run_dir}"

  {
    echo "run:     ${RUN_NAME}"
    echo "epochs:  ${EPOCHS}"
    echo "weights: ${run_dir}/weights/best.pt"
    echo "pushed:  ${HF_WEIGHTS_REPO:-not uploaded}"
    echo "at:      $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  } > "${DONE_MARKER}"

  log "Done. Results in ${run_dir}"
  log "This machine has nothing left to do; destroy it."
}

cmd_evaluate() {
  require_gpu
  fetch_dataset
  fix_dataset_root
  local weights="${WEIGHTS:-${RUNS_DIR}/${RUN_NAME}/weights/best.pt}"
  log "Evaluating ${weights} on the test split"
  yolo detect val \
    model="${weights}" \
    data="${DATA_DIR}/data.yaml" \
    split=test \
    project="${RUNS_DIR}" \
    name="eval-$(date +%Y%m%d-%H%M%S)" \
    plots=True
}

case "${1:-train}" in
  train) cmd_train ;;
  evaluate) cmd_evaluate ;;
  shell) exec /bin/bash ;;
  *) echo "Unknown command: $1 (expected train, evaluate or shell)" >&2; exit 2 ;;
esac
