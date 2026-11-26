#!/usr/bin/env bash
# One-command demo: build a small dataset, prove it is valid, grade baselines (and a model if given).
# Usage: scripts/demo.sh [openai-compatible base URL] [model name]
#   e.g. scripts/demo.sh http://127.0.0.1:8090 qwen2.5-vl-3b
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=runs/demo
uv sync -q
rm -rf "$OUT"
echo "== 1. generate 72 items (8 families x 3 difficulties x 3)"
uv run vtf generate "$OUT" --per-cell 3 --seed 42 > /dev/null
echo "== 2. validate: regenerate, re-derive, re-probe, grader self-test"
uv run vtf validate "$OUT" --seed 42
echo "== 3. baselines"
uv run vtf run "$OUT" oracle > /dev/null
uv run vtf run "$OUT" random > /dev/null
MODELS="oracle random"
if [ $# -ge 2 ]; then
  echo "== 4. model $2 at $1"
  uv run vtf run "$OUT" "openai:$1:$2"
  MODELS="$MODELS $2"
fi
echo "== 5. report"
uv run vtf report "$OUT" $MODELS
cat "$OUT/report/REPORT.md"
echo "HTML report: $OUT/report/index.html"
