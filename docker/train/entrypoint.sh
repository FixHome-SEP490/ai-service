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
RESUME_FROM="${RESUME_FROM:-}"
LR0="${LR0:-}"
WARMUP="${WARMUP:-}"

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

fetch_resume_weights() {
  # Buying more epochs for a model that already exists.
  #
  # A rental is destroyed the minute it finishes, so the only copy of the
  # weights it produced is the one publish_weights pushed to the Hub.
  # Without a way to fetch that back, the only route to more epochs was to
  # train from scratch and pay a second time for the epochs already bought.
  #
  # RESUME_FROM is a path inside HF_WEIGHTS_REPO, laid out the way
  # publish_weights leaves it: detector-v2/weights/best.pt.
  #
  # Call this what it is: not a resume. Ultralytics resumes only from a run
  # directory it wrote itself, with the optimiser state and the place in the
  # schedule still in it, and that directory died with the machine. What
  # happens here is a fresh run of EPOCHS epochs starting from trained
  # weights - new warmup, new decay, a new schedule from its beginning.
  #
  # That distinction decides the learning rate. The weights handed in have
  # already been annealed to the bottom of a schedule; hitting them with the
  # default lr0 of 0.01 and three epochs of warmup pulls them apart again,
  # and the first several epochs read as a regression before they recover.
  # So when RESUME_FROM is set and nothing was said about the rate, start
  # low and warm up briefly.
  [[ -n "${RESUME_FROM}" ]] || return 0
  if [[ -z "${HF_WEIGHTS_REPO:-}" || -z "${HF_TOKEN:-}" ]]; then
    echo "RESUME_FROM needs HF_WEIGHTS_REPO and HF_TOKEN to fetch from." >&2
    exit 1
  fi

  log "Continuing from ${RESUME_FROM} in ${HF_WEIGHTS_REPO}"
  local dir="/workspace/resume"
  huggingface-cli download "${HF_WEIGHTS_REPO}" "${RESUME_FROM}" \
    --repo-type model --local-dir "${dir}"

  local weights="${dir}/${RESUME_FROM}"
  [[ -f "${weights}" ]] || {
    echo "${RESUME_FROM} is not in ${HF_WEIGHTS_REPO}." >&2
    echo "Check the run name; publish_weights uploads under RUN_NAME." >&2
    exit 1
  }
  MODEL="${weights}"
  LR0="${LR0:-0.002}"
  WARMUP="${WARMUP:-1.0}"
  log "Starting from ${MODEL} at lr0=${LR0}, warmup ${WARMUP} epoch(s)"
}

cmd_train() {
  refuse_if_already_done
  require_gpu
  fetch_dataset
  fix_dataset_root
  fetch_resume_weights

  # Kept out of the command line when unset: yolo reads an empty lr0= as
  # the string "" and stops with a parse error rather than using its own
  # default.
  # Written as if-blocks, not `[[ test ]] && append`, because this file runs
  # under `set -e` on a machine that bills by the second. Whether a bare
  # AND-list whose test fails ends the script is a question with a
  # version-dependent answer, and the cost of being wrong is a run that dies
  # at the first line of training with nothing in the log to explain it.
  local tuning=()
  if [[ -n "${LR0}" ]]; then
    tuning+=("lr0=${LR0}")
  fi
  if [[ -n "${WARMUP}" ]]; then
    tuning+=("warmup_epochs=${WARMUP}")
  fi

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
    plots=True \
    ${tuning[@]+"${tuning[@]}"}

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
