#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIR="${TMPDIR:-/tmp}/cew-smoke"

rm -rf "$WORK_DIR"
mkdir -p "$WORK_DIR"

run_export() {
  local provider="$1"
  local input="$2"
  local fmt="$3"
  local out
  if [[ "$fmt" == "html" ]]; then
    out="$WORK_DIR/$provider"
  else
    out="$WORK_DIR/$provider-$fmt"
  fi

  python3 "$ROOT_DIR/format_conversations.py" \
    --input "$ROOT_DIR/$input" \
    --format "$fmt" \
    --output "$out" \
    --yes

  if ! compgen -G "$out/*.$fmt" > /dev/null; then
    echo "Smoke test failed: no .$fmt files written for $provider ($input)" >&2
    exit 1
  fi
}

run_export deepseek sample_data/deepseek-convo.json html
run_export claude sample_data/claude-convo.json html
run_export chatgpt sample_data/chatgpt-convo.json html
run_export chatgpt sample_data/chatgpt-convo.json json

python3 "$ROOT_DIR/generate_spa.py" --output "$WORK_DIR" --yes

if [[ ! -f "$WORK_DIR/index.html" ]]; then
  echo "Smoke test failed: SPA index not generated" >&2
  exit 1
fi

echo "Smoke test passed: exports + SPA generation succeeded ($WORK_DIR)"
