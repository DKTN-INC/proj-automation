#!/usr/bin/env bash
set -euo pipefail
echo "=== Run all checks for proj-automation ==="

if [ -f "./scripts/setup_local_env.sh" ]; then
  ./scripts/setup_local_env.sh
fi

if [ -f ".venv/bin/activate" ]; then
  source .venv/bin/activate
fi

echo "Running smoke tests..."
python scripts/run_smoke_tests.py

echo "Running pytest full suite..."
python -m pytest -q

echo "All checks completed."
