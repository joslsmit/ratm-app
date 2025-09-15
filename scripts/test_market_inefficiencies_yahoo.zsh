#!/usr/bin/env zsh
# Simple tester for Yahoo League Market Inefficiency endpoint
# Requires env vars:
#   TOKEN        - Yahoo OAuth access token (raw JSON string or raw token); if JSON, it extracts access_token
#   GEMINI_KEY   - Google Gemini API key
#   LEAGUE_KEY   - Yahoo league key (e.g., 461.l.42889)
# Optional:
#   API_BASE     - API base URL (default: https://localhost:5000/api)

set -euo pipefail

API_BASE=${API_BASE:-https://localhost:5000/api}

if [[ -z "${TOKEN:-}" || -z "${GEMINI_KEY:-}" || -z "${LEAGUE_KEY:-}" ]]; then
  echo "Usage: TOKEN=... GEMINI_KEY=... LEAGUE_KEY=... ${0}" >&2
  exit 1
fi

# Derive Bearer token if a JSON blob was supplied
ACCESS_TOKEN="$TOKEN"
if echo "$TOKEN" | grep -q 'access_token'; then
  ACCESS_TOKEN=$(echo "$TOKEN" | sed -n 's/.*"access_token"\s*:\s*"\([^"]*\)".*/\1/p')
fi

echo "Fetching league context for $LEAGUE_KEY ..." >&2
LEAGUE_CONTEXT=$(curl -sS -k \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  "$API_BASE/yahoo/league_context?league_key=$LEAGUE_KEY")

echo "Running league inefficiency analysis ..." >&2
RESULT=$(curl -sS -k -X POST "$API_BASE/yahoo/league_inefficiencies" \
  -H 'Content-Type: application/json' \
  -H "X-API-Key: $GEMINI_KEY" \
  -d @- <<EOF
{
  "league_key": "${LEAGUE_KEY}",
  "position": "all",
  "league_context": ${LEAGUE_CONTEXT}
}
EOF
)

echo "$RESULT" | jq -e '.sleepers, .busts' >/dev/null 2>&1 && {
  echo "Structured output detected. Counts:" >&2
  echo "$RESULT" | jq '{sleepers: (.sleepers|length), busts: (.busts|length)}'
} || {
  echo "No structured arrays; showing first 20 lines of markdown result (if present)." >&2
  echo "$RESULT" | jq -r '.result' | sed -n '1,20p'
}

