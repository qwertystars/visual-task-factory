#!/usr/bin/env bash
# Start a local llama.cpp vision server (CPU) for one model.
# Usage: scripts/serve.sh qwen2.5-vl-3b|smolvlm2-2.2b|gemma3-4b [port]
set -euo pipefail
cd "$(dirname "$0")/.."
M=runs/models
case "$1" in
  qwen2.5-vl-3b) m=Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf; p=mmproj-Qwen2.5-VL-3B-Instruct-Q8_0.gguf ;;
  smolvlm2-2.2b) m=SmolVLM2-2.2B-Instruct-Q4_K_M.gguf; p=mmproj-SmolVLM2-2.2B-Instruct-Q8_0.gguf ;;
  gemma3-4b)     m=gemma-3-4b-it-Q4_K_M.gguf;         p=mmproj-model-f16.gguf ;;
  *) echo "unknown model $1" >&2; exit 2 ;;
esac
BIN=$(find runs/llama -name llama-server -type f | head -n1)
exec "$BIN" -m "$M/$m" --mmproj "$M/$p" --host 127.0.0.1 --port "${2:-8090}" \
  -t "${THREADS:-12}" -c 8192 -np 1 --load-mode none --temp 0 --alias "$1" --no-webui
