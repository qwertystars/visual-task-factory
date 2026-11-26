#!/usr/bin/env bash
# Run every local model over a dataset, one llama.cpp server at a time.
# Usage: scripts/run_models.sh <dataset> [model ...]   (writes <dataset>/models.DONE or .FAIL)
set -uo pipefail
cd "$(dirname "$0")/.."
DS=$1; shift
MODELS=${*:-qwen2.5-vl-3b gemma3-4b smolvlm2-2.2b}
PORT=8091
rm -f "$DS/models.DONE" "$DS/models.FAIL"
for m in $MODELS; do
  echo "== $m $(date -u +%T)"
  scripts/serve.sh "$m" $PORT > "runs/server-$m.log" 2>&1 &
  pid=$!
  until curl -sf "localhost:$PORT/health" > /dev/null; do
    kill -0 $pid 2>/dev/null || { echo "server for $m died"; touch "$DS/models.FAIL"; exit 1; }
    sleep 5
  done
  echo "server up $(date -u +%T)"
  uv run vtf run "$DS" "openai:http://127.0.0.1:$PORT:$m" || echo "run $m had errors"
  kill $pid; wait $pid 2>/dev/null
done
touch "$DS/models.DONE"
