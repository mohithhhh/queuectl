#!/usr/bin/env bash
set -euo pipefail

# Create virtual env and install deps
python3 -m venv .venv
source .venv/bin/activate
pip install --quiet click

# Show status before
python queuectl.py status || true 

# Enqueue jobs
python queuectl.py enqueue '{"id":"job1","command":"echo Hello"}'
python queuectl.py enqueue '{"id":"job2","command":"sleep 2"}'
python queuectl.py enqueue '{"id":"job3","command":"not-a-real-binary"}'

# Start workers (in foreground; stop after ~6s)
( timeout 6s python queuectl.py worker start --count 2 ) || true

# Show status and lists
python queuectl.py status
python queuectl.py list --state completed
python queuectl.py list --state pending
python queuectl.py dlq list

# Retry DLQ job if exists
# shellcheck disable=SC2046
DLQ_ID=$(python - <<'PY'
from job_queue import _connect
rows=_connect().execute("SELECT id FROM dlq").fetchall()
print(rows[0]["id"] if rows else "", end="")
PY
)
if [ -n "$DLQ_ID" ]; then
  python queuectl.py dlq retry "$DLQ_ID"
  ( timeout 5s python queuectl.py worker start --count 1 ) || true
fi

python queuectl.py status
