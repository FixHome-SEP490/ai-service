#!/usr/bin/env bash
# Rented box for the fault adapter: pull the data, train, measure, push, done.
#
#   train   (default) download lora/${DATA_RUN}/ from HF_DATASET_REPO, train on
#           train.jsonl, evaluate on val and test with vLLM (served AWQ model +
#           adapter), upload the adapter and results to HF_WEIGHTS_REPO under
#           ${RUN_NAME}/, then write ${RUN_NAME}/DONE (or FAILED) last.
#   evaluate  the same evaluation for an adapter already at ${RUN_NAME}/
#   shell
#
# The box is destroyed by whoever rented it once DONE or FAILED appears.

set -uo pipefail

DATA_RUN="${DATA_RUN:-fault-v1}"
RUN_NAME="${RUN_NAME:-lora-${DATA_RUN}-$(date +%Y%m%d-%H%M)}"
export DATA_DIR="${DATA_DIR:-/workspace/data}"
export OUT_DIR="${OUT_DIR:-/workspace/adapter}"
LOG="/workspace/run.log"

log() { printf '\n== %s\n' "$*" | tee -a "$LOG"; }

push() {
  python3 - "$@" <<'PY'
import os, sys
from huggingface_hub import HfApi
api = HfApi(token=os.environ["HF_TOKEN"])
repo, run, path = os.environ["HF_WEIGHTS_REPO"], os.environ["RUN_NAME"], sys.argv[1]
api.create_repo(repo, exist_ok=True, private=True)
if os.path.isdir(path):
    api.upload_folder(repo_id=repo, folder_path=path, path_in_repo=run, commit_message=f"{run}: adapter and results")
else:
    api.upload_file(repo_id=repo, path_or_fileobj=path, path_in_repo=f"{run}/{os.path.basename(path)}", commit_message=f"{run}: {os.path.basename(path)}")
PY
}

finish() {
  local status="$1"
  cp "$LOG" "${OUT_DIR}/run.log" 2>/dev/null || true
  mkdir -p "${OUT_DIR}"
  push "${OUT_DIR}" || true
  echo "$status $(date -u +%FT%TZ)" > "/workspace/${status}"
  push "/workspace/${status}" || true
  log "${status}"
}

fetch() {
  log "Downloading lora/${DATA_RUN} from ${HF_DATASET_REPO}"
  python3 - <<'PY'
import os, shutil
from huggingface_hub import snapshot_download
d = snapshot_download(os.environ["HF_DATASET_REPO"], repo_type="dataset", token=os.environ["HF_TOKEN"],
                      allow_patterns=[f"lora/{os.environ['DATA_RUN']}/*"], local_dir="/workspace/hfdata")
src = os.path.join(d, "lora", os.environ["DATA_RUN"])
os.makedirs(os.environ["DATA_DIR"], exist_ok=True)
for name in os.listdir(src):
    shutil.copy(os.path.join(src, name), os.environ["DATA_DIR"])
print(sorted(os.listdir(os.environ["DATA_DIR"])))
PY
}

export RUN_NAME DATA_RUN
case "${1:-train}" in
  train)
    nvidia-smi | tee -a "$LOG"
    fetch 2>&1 | tee -a "$LOG" || { finish FAILED; exit 1; }
    log "Training ${RUN_NAME}"
    python3 /opt/lora/train_lora.py 2>&1 | tee -a "$LOG"
    [[ ${PIPESTATUS[0]} -eq 0 ]] || { finish FAILED; exit 1; }
    log "Evaluating ${RUN_NAME} with vLLM"
    python3 /opt/lora/eval_lora.py 2>&1 | tee -a "$LOG"
    [[ ${PIPESTATUS[0]} -eq 0 ]] || { finish FAILED; exit 1; }
    finish DONE
    ;;
  evaluate)
    fetch 2>&1 | tee -a "$LOG"
    python3 - <<'PY'
import os
from huggingface_hub import snapshot_download
d = snapshot_download(os.environ["HF_WEIGHTS_REPO"], token=os.environ["HF_TOKEN"], allow_patterns=[f"{os.environ['RUN_NAME']}/*"], local_dir="/workspace/hfw")
import shutil; shutil.copytree(os.path.join(d, os.environ["RUN_NAME"]), os.environ["OUT_DIR"], dirs_exist_ok=True)
PY
    python3 /opt/lora/eval_lora.py 2>&1 | tee -a "$LOG"
    finish DONE
    ;;
  shell) exec bash ;;
  *) echo "unknown command $1" >&2; exit 2 ;;
esac
