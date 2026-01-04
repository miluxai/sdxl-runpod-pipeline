#!/usr/bin/env bash
set -euo pipefail

echo "==> Bootstrapping RunPod ComfyUI + SDXL pipeline..."

# --- Settings (NO ENV REQUIRED) ---
COMFY_DIR="/workspace/ComfyUI"
CKPT_DIR="$COMFY_DIR/models/checkpoints"
JOBS_DIR="/workspace/jobs"
SCRIPTS_DIR="/workspace/scripts"

# Default SDXL base checkpoint (can be overridden by env, but not required)
SDXL_NAME="${SDXL_NAME:-sd_xl_base_1.0.safetensors}"
SDXL_URL="${SDXL_URL:-https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors}"

# --- Validate ComfyUI template ---
if [[ ! -d "$COMFY_DIR" ]]; then
  echo "ERROR: ComfyUI not found at $COMFY_DIR."
  echo "Use RunPod template: Stable Diffusion – ComfyUI."
  exit 1
fi

# --- System packages (idempotent) ---
echo "==> Installing system packages..."
if command -v sudo >/dev/null 2>&1; then SUDO="sudo"; else SUDO=""; fi
$SUDO apt-get update -y
$SUDO apt-get install -y --no-install-recommends \
  curl wget git python3 python3-pip unzip zip netcat-openbsd
$SUDO apt-get clean
$SUDO rm -rf /var/lib/apt/lists/* || true

# --- Python deps for batch script ---
echo "==> Installing Python deps..."
python3 -m pip install --upgrade pip >/dev/null
python3 -m pip install "requests>=2.31.0" >/dev/null

# --- Copy repo assets to /workspace (idempotent overwrite) ---
echo "==> Copying workflow/scripts/jobs to /workspace..."
mkdir -p "$JOBS_DIR" "$SCRIPTS_DIR"

if [[ ! -f "./workflows/day_night_workflow_api.json" ]]; then
  echo "ERROR: Missing workflows/day_night_workflow_api.json in repo."
  exit 1
fi
cp -f "./workflows/day_night_workflow_api.json" "$JOBS_DIR/day_night_workflow_api.json"

if [[ ! -f "./scripts/batch_day_night.py" ]]; then
  echo "ERROR: Missing scripts/batch_day_night.py in repo."
  exit 1
fi
cp -f "./scripts/batch_day_night.py" "$SCRIPTS_DIR/batch_day_night.py"

if [[ -f "./jobs/prompts.txt" ]]; then
  cp -f "./jobs/prompts.txt" "$JOBS_DIR/prompts.txt"
else
  echo "WARN: jobs/prompts.txt not found in repo. Create it before running batch."
fi

# --- Download SDXL checkpoint (idempotent) ---
echo "==> Ensuring SDXL checkpoint exists..."
mkdir -p "$CKPT_DIR"
MODEL_PATH="$CKPT_DIR/$SDXL_NAME"
if [[ ! -f "$MODEL_PATH" ]]; then
  echo "==> Downloading: $SDXL_NAME"
  wget -O "$MODEL_PATH" "$SDXL_URL"
else
  echo "==> Checkpoint already present: $SDXL_NAME"
fi

# --- Start ComfyUI if not running ---
echo "==> Ensuring ComfyUI is running on :8188..."
if nc -z 127.0.0.1 8188 >/dev/null 2>&1; then
  echo "==> ComfyUI already running."
else
  echo "==> Starting ComfyUI..."
  cd "$COMFY_DIR"
  # Start in background; logs to /workspace/comfyui.log
  nohup python3 main.py --listen 127.0.0.1 --port 8188 > /workspace/comfyui.log 2>&1 &
  cd - >/dev/null

  # Wait up to 60s
  for i in {1..60}; do
    if nc -z 127.0.0.1 8188 >/dev/null 2>&1; then
      echo "==> ComfyUI is up."
      break
    fi
    sleep 1
  done

  if ! nc -z 127.0.0.1 8188 >/dev/null 2>&1; then
    echo "ERROR: ComfyUI did not start. Check /workspace/comfyui.log"
    exit 1
  fi
fi

echo "==> Bootstrap complete."
echo "Next: python3 /workspace/scripts/batch_day_night.py"