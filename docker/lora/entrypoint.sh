#!/usr/bin/env bash
# Rented box for the fault adapter: pull the data, train, measure, push, done.
#
#   train   (default) download lora/${DATA_RUN}/ from HF_DATASET_REPO, train on
#           train.jsonl, evaluate on val and test with vLLM (served AWQ model +
#           adapter), upload the adapter and results to HF_WEIGHTS_REPO under
#           ${RUN_NAME}/, then write ${RUN_NAME}/DONE (or FAILED) last.
#           PUSH_FAILED instead of DONE when an upload did not go through.
#   evaluate  the same evaluation for an adapter already at ${RUN_NAME}/
#   shell
#
# The box then sleeps instead of exiting, and is destroyed by whoever rented it
# once DONE or FAILED appears; after PUSH_FAILED read its log first, the
# adapter is still on it.

set -uo pipefail

DATA_RUN="${DATA_RUN:-fault-v1}"
RUN_NAME="${RUN_NAME:-lora-${DATA_RUN}-$(date +%Y%m%d-%H%M)}"
export DATA_DIR="${DATA_DIR:-/workspace/data}"
export OUT_DIR="${OUT_DIR:-/workspace/adapter}"
LOG="/workspace/run.log"
mkdir -p /workspace "${OUT_DIR}"
export PYTORCH_CUDA_ALLOC_CONF="${PYTORCH_CUDA_ALLOC_CONF:-expandable_segments:True}" PYTHONUNBUFFERED=1

log() { printf '\n== %s\n' "$*" | tee -a "$LOG"; }

# Uploads one file at a time, three tries each, and says why one failed.
# lora-fault-v1b trained and measured, then lost everything: the folder upload
# failed, `|| true` swallowed the reason and DONE went up anyway.
push() {
  HF_HUB_DISABLE_PROGRESS_BARS=1 python3 - "$@" <<'PY' 2>&1 | tee -a "$LOG"
import os, sys, time, traceback
from huggingface_hub import HfApi
api = HfApi(token=os.environ["HF_TOKEN"])
repo, run = os.environ["HF_WEIGHTS_REPO"], os.environ["RUN_NAME"]
api.create_repo(repo, exist_ok=True, private=True)
failed = 0
for path in sys.argv[1:]:
    name = os.path.basename(path)
    for attempt in range(3):
        try:
            api.upload_file(repo_id=repo, path_or_fileobj=path, path_in_repo=f"{run}/{name}", commit_message=f"{run}: {name}")
            print(f"pushed {name} ({os.path.getsize(path)} bytes)", flush=True)
            break
        except Exception:
            print(f"push {name} attempt {attempt + 1} failed:", flush=True)
            traceback.print_exc(file=sys.stdout)
            time.sleep(20 * (attempt + 1))
    else:
        failed += 1
sys.exit(1 if failed else 0)
PY
  return "${PIPESTATUS[0]}"
}

# Small files first, so the numbers survive even when the adapter does not;
# the log last, so it carries every upload error. DONE only when all of it is
# up; otherwise PUSH_FAILED and the box stays up to be read and copied from.
finish() {
  local status="$1" ok=0 f
  mkdir -p "${OUT_DIR}"
  local small=() big=()
  for f in results.json predictions.jsonl train_log.json adapter_config.json; do
    [[ -f "${OUT_DIR}/$f" ]] && small+=("${OUT_DIR}/$f")
  done
  for f in "${OUT_DIR}"/*; do
    [[ -f "$f" && ! " ${small[*]} " == *" $f "* && "$(basename "$f")" != run.log ]] && big+=("$f")
  done
  ((${#small[@]})) && { push "${small[@]}" || ok=1; }
  ((${#big[@]})) && { push "${big[@]}" || ok=1; }
  [[ "$status" == DONE && $ok -ne 0 ]] && status=PUSH_FAILED
  log "${status}"
  cp "$LOG" "${OUT_DIR}/run.log" 2>/dev/null || true
  push "${OUT_DIR}/run.log" || true
  echo "$status $(date -u +%FT%TZ)" > "/workspace/${status}"
  push "/workspace/${status}" || true
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
    fetch 2>&1 | tee -a "$LOG" || { finish FAILED; exec sleep infinity; }
    log "Training ${RUN_NAME}"
    python3 /opt/lora/train_lora.py 2>&1 | tee -a "$LOG"
    [[ ${PIPESTATUS[0]} -eq 0 ]] || { finish FAILED; exec sleep infinity; }
    log "Evaluating ${RUN_NAME} with vLLM"
    python3 /opt/lora/eval_lora.py 2>&1 | tee -a "$LOG"
    [[ ${PIPESTATUS[0]} -eq 0 ]] || { finish FAILED; exec sleep infinity; }
    finish DONE
    # Exiting makes vast.ai restart the container, which trains all over again
    # on the same bill. Wait to be destroyed instead.
    exec sleep infinity
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
    [[ ${PIPESTATUS[0]} -eq 0 ]] || { finish FAILED; exec sleep infinity; }
    finish DONE
    exec sleep infinity
    ;;
  shell) exec bash ;;
  *) echo "unknown command $1" >&2; exit 2 ;;
esac
