#!/usr/bin/env bash
# Generate the same seed twice into two folders, validate both, and compare every PNG and
# JSON file byte for byte. Usage: scripts/determinism.sh OUT_DIR [SEED] [PER_CELL]
set -euo pipefail
out=${1:?out dir}; seed=${2:-7}; per=${3:-10}
rm -rf "$out/a" "$out/b"; mkdir -p "$out"
for d in a b; do
  uv run --frozen vtf generate "$out/$d" --seed "$seed" --per-cell "$per" > "$out/generate-$d.json"
  uv run --frozen vtf validate "$out/$d" --seed "$seed" > "$out/validate-$d.txt"
done
for d in a b; do
  (cd "$out/$d" && find . -type f \( -name '*.png' -o -name '*.json' -o -name '*.jsonl' \) -print0 \
     | sort -z | xargs -0 sha256sum) > "$out/sha-$d.txt"
done
if cmp -s "$out/sha-a.txt" "$out/sha-b.txt"; then
  echo "IDENTICAL $(wc -l < "$out/sha-a.txt") files" | tee "$out/determinism.txt"
else
  echo "DIFFERENT" | tee "$out/determinism.txt"; diff "$out/sha-a.txt" "$out/sha-b.txt" | tee -a "$out/determinism.txt"; exit 1
fi
