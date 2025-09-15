#!/usr/bin/env zsh
# Tester for general Market Inefficiency endpoint (non‑Yahoo)
# Requires env vars:
#   GEMINI_KEY   - Google Gemini API key
# Optional:
#   API_BASE     - API base URL (default: https://localhost:5000/api)
#   POSITION     - Position filter (all|QB|RB|WR|TE), default: all

set -euo pipefail

API_BASE=${API_BASE:-https://localhost:5000/api}
POSITION=${POSITION:-all}

if [[ -z "${GEMINI_KEY:-}" ]]; then
  echo "Usage: GEMINI_KEY=... ${0}" >&2
  exit 1
fi

echo "Requesting market inefficiencies (position=$POSITION) ..." >&2

RESULT=$(curl -sS -k -X POST "$API_BASE/find_market_inefficiencies" \
  -H 'Content-Type: application/json' \
  -H "X-API-Key: $GEMINI_KEY" \
  -d '{"position":"'"$POSITION"'"}')

echo "$RESULT" | jq '{sleepers: (.sleepers|length), busts: (.busts|length)}'

