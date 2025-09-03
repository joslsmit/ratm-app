#!/usr/bin/env bash
set -euo pipefail

# Requires env vars: BASE, TOKEN, LEAGUE_KEY, TEAM_KEY
: "${BASE:?Set BASE}" "${TOKEN:?Set TOKEN}" "${LEAGUE_KEY:?Set LEAGUE_KEY}" "${TEAM_KEY:?Set TEAM_KEY}"

ppjson() { if command -v jq >/dev/null 2>&1; then jq .; else python3 -m json.tool 2>/dev/null || cat; fi; }

echo "==[ Waiver Pool (A) ]=="
BODY="$(curl -sk -H "Authorization: Bearer $TOKEN" "$BASE/api/yahoo/waiver_pool?league_key=$LEAGUE_KEY&status=A&max=200")"
printf "%s\n" "$BODY" | ppjson >/dev/null
if command -v jq >/dev/null 2>&1; then
  echo "$BODY" | jq -r '{pool_total: .total_count, sample_name: (.available_players[0].name // "N/A"), weekly_points: (.available_players[0].weekly_points // "N/A")} '
fi

echo "==[ Recommendations V2 ]=="
read -r -d '' PAYLOAD <<JSON || true
{"league_key":"$LEAGUE_KEY","team_key":"$TEAM_KEY","status":"A","top_n":10}
JSON
RSP="$(curl -sk -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d "$PAYLOAD" "$BASE/api/yahoo/waiver_recommendations_v2")"
printf "%s\n" "$RSP" | ppjson >/dev/null
if command -v jq >/dev/null 2>&1; then
  echo "$RSP" | jq -r '{rec_count: (.recommendations|length), first_add: (.recommendations[0].add_player.name // "N/A"), delta: (.recommendations[0].delta_points // "N/A")} '
fi
