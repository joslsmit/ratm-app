#!/usr/bin/env bash
set -euo pipefail

# Requires: BASE, TOKEN, LEAGUE_KEY, TEAM_KEY
: "${BASE:?Set BASE}" "${TOKEN:?Set TOKEN}" "${LEAGUE_KEY:?Set LEAGUE_KEY}" "${TEAM_KEY:?Set TEAM_KEY}"

PAYLOAD=$(cat <<JSON
{"league_key":"$LEAGUE_KEY","team_key":"$TEAM_KEY","status":"A","top_n":10}
JSON
)

RSP="$(curl -sk -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d "$PAYLOAD" "$BASE/api/yahoo/waiver_recommendations_v2")"
if command -v jq >/dev/null 2>&1; then
  echo "$RSP" | jq '{roster_cov:(.metadata.roster_projection_coverage), pool_cov:(.metadata.pool_projection_coverage), unmatched_roster:(.metadata.unmatched_roster), unmatched_pool:(.metadata.unmatched_pool)}'
else
  printf '%s\n' "$RSP"
fi

