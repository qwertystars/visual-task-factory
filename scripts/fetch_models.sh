#!/usr/bin/env bash
# Download llama.cpp CPU build and small vision GGUFs into runs/.
set -euo pipefail
cd "$(dirname "$0")/.."
B=b12757
M=runs/models
rm -f runs/fetch.DONE runs/fetch.FAIL
trap 'touch runs/fetch.FAIL' ERR
if [ ! -x runs/llama/bin/llama-server ] && [ -z "$(find runs/llama -name llama-server -type f 2>/dev/null)" ]; then
  curl -fL -o runs/llama.tgz "https://github.com/ggml-org/llama.cpp/releases/download/$B/llama-$B-bin-ubuntu-x64.tar.gz"
  tar -xzf runs/llama.tgz -C runs/llama
fi
get() { [ -s "$M/$2" ] || curl -fL -o "$M/$2.part" "https://huggingface.co/$1/resolve/main/$2" && mv -f "$M/$2.part" "$M/$2" 2>/dev/null || true; }
get ggml-org/Qwen2.5-VL-3B-Instruct-GGUF Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf
get ggml-org/Qwen2.5-VL-3B-Instruct-GGUF mmproj-Qwen2.5-VL-3B-Instruct-Q8_0.gguf
get ggml-org/SmolVLM2-2.2B-Instruct-GGUF SmolVLM2-2.2B-Instruct-Q4_K_M.gguf
get ggml-org/SmolVLM2-2.2B-Instruct-GGUF mmproj-SmolVLM2-2.2B-Instruct-Q8_0.gguf
get ggml-org/gemma-3-4b-it-GGUF gemma-3-4b-it-Q4_K_M.gguf
get ggml-org/gemma-3-4b-it-GGUF mmproj-model-f16.gguf
ls -la $M
touch runs/fetch.DONE
