#!/usr/bin/env bash
# OmniVoice Studio — start the server
set -e
cd "$(dirname "$0")"
source .venv/bin/activate
exec uvicorn main:app --host 0.0.0.0 --port 8000 --reload
