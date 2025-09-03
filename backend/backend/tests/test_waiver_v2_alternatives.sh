#!/usr/bin/env bash
set -euo pipefail

# Requires env vars: BASE, TOKEN, LEAGUE_KEY, TEAM_KEY
: "${BASE:?Set BASE}" "${TOKEN:?Set TOKEN}" "${LEAGUE_KEY:?Set LEAGUE_KEY}" "${TEAM_KEY:?Set TEAM_KEY}"

# Optional: MIN benefit threshold for alternatives (default -1.0)
MIN=${MIN:-"-1.0"}
TOP_N=${TOP_N:-"10"}

read -r -d '' PAYLOAD <<JSON || true
{
  "league_key": "${LEAGUE_KEY}",
  "team_key": "${TEAM_KEY}",
  "status": "A",
  "top_n": ${TOP_N},
  "include_alternatives": true,
  "min_benefit": ${MIN}
}
JSON

RSP="$(curl -sk -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d "$PAYLOAD" "$BASE/api/yahoo/waiver_recommendations_v2")"

if command -v jq >/dev/null 2>&1; then
  echo "$RSP" | jq '{count:(.recommendations|length), first:(.recommendations[0]//{}), baseline_overall:(.metadata.baseline_overall)}'
else
  printf '%s\n' "$RSP"
fi

