#!/usr/bin/env bash

# Simple smoke test for the Player Dossier endpoint
# Requirements:
#   - curl
#   - jq (brew install jq) — optional but recommended for parsing
#
# Usage:
#   export GEMINI_KEY=your_api_key
#   export API_BASE_URL=https://ratm-app.onrender.com/api   # or https://localhost:5000/api
#   bash scripts/test_player_dossier.sh "Amon-Ra St. Brown" "Lamar Jackson" "Sam LaPorta"

set -euo pipefail

API_BASE_URL="${API_BASE_URL:-https://localhost:5000/api}"
GEMINI_KEY="${GEMINI_KEY:-}"

if [[ -z "${GEMINI_KEY}" ]]; then
  echo "Error: GEMINI_KEY env var not set."
  echo "Set it with: export GEMINI_KEY=your_api_key"
  exit 1
fi

if ! command -v curl >/dev/null 2>&1; then
  echo "Error: curl is required."
  exit 1
fi

PLAYERS=("${@}")
if [[ ${#PLAYERS[@]} -eq 0 ]]; then
  PLAYERS=("Amon-Ra St. Brown" "Lamar Jackson")
fi

echo "API_BASE_URL=${API_BASE_URL}"
echo "Testing ${#PLAYERS[@]} player(s)..."

failures=0
for name in "${PLAYERS[@]}"; do
  echo "\n— Testing dossier for: ${name}"
  payload=$(printf '{"player_name":"%s"}' "$name")
  resp=$(curl -sS -X POST "${API_BASE_URL}/player_dossier" \
    -H 'Content-Type: application/json' \
    -H "X-API-Key: ${GEMINI_KEY}" \
    -d "${payload}") || { echo "curl failed"; failures=$((failures+1)); continue; }

  # If jq is available, validate shape; otherwise print raw length
  if command -v jq >/dev/null 2>&1; then
    if echo "$resp" | jq -e '.error' >/dev/null 2>&1; then
      echo "❌ Error from API: $(echo "$resp" | jq -r '.error')"
      failures=$((failures+1))
      continue
    fi

    # Validate core keys exist
    if ! echo "$resp" | jq -e '.player_data and .analysis' >/dev/null; then
      echo "❌ Invalid response: missing player_data or analysis"
      failures=$((failures+1))
      continue
    fi

    pname=$(echo "$resp" | jq -r '.player_data.name // "N/A"')
    proj=$(echo "$resp" | jq -r '.player_data.projected_points // "N/A"')
    own=$(echo "$resp" | jq -r '.player_data.weekly_ownership // "N/A"')
    echo "✅ OK | name=${pname} | proj=${proj} | owned=${own}%"
  else
    echo "(jq not found) Raw response length: ${#resp} bytes"
  fi
done

echo "\nDone. Failures: ${failures}"
exit ${failures}
