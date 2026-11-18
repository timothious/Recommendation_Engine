#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -x "$ROOT/.venv/bin/streamlit" ]]; then
  exec "$ROOT/.venv/bin/streamlit" run test_ui/app.py --server.headless true
fi

exec streamlit run test_ui/app.py --server.headless true
