#!/usr/bin/env zsh
# Quick tester for Waiver v4 endpoints (deterministic and AI) with Yahoo token
# Usage:
#   TOKEN='{"access_token":"..."}' LEAGUE_KEY='461.l.12345' TEAM_KEY='461.l.12345.t.8' ./scripts/test_waiver_v4.zsh
# Optional:
#   API_BASE_URL='https://localhost:5000/api' GEMINI_KEY='...' INSECURE=1 STATUS='A' TOP_N=10 ALTS=0 MINB=0

set -euo pipefail

: ${API_BASE_URL:=${API_BASE_URL:-"https://localhost:5000/api"}}
: ${TOKEN:?"Set TOKEN to the JSON string with access_token"}
: ${LEAGUE_KEY:?"Set LEAGUE_KEY"}
: ${TEAM_KEY:?"Set TEAM_KEY"}

AUTH="Bearer $(echo "$TOKEN" | python3 -c 'import sys,json;print(json.load(sys.stdin)["access_token"])')"
STATUS=${STATUS:-A}
TOP_N=${TOP_N:-10}
ALTS=${ALTS:-0}
MINB=${MINB:-0}
GEMINI_KEY=${GEMINI_KEY:-}

curl_common=(
  -sS \
  -H "Authorization: $AUTH" \
  -H 'Content-Type: application/json'
)
[[ ${INSECURE:-0} == 1 ]] && curl_common+=(-k)

echo "== Roster =="
curl "${curl_common[@]}" "${API_BASE_URL}/yahoo/roster?team_key=${TEAM_KEY}" | jq '{count:length, names: [.[].name]}' || true

echo "\n== Waiver Pool (sample 10) =="
curl "${curl_common[@]}" "${API_BASE_URL}/yahoo/waiver_pool?league_key=${LEAGUE_KEY}&status=${STATUS}" | jq '{total_count, sample: (.available_players[:10] | map({name, position, team}))}' || true

body=$(jq -n --arg lk "$LEAGUE_KEY" --arg tk "$TEAM_KEY" --arg st "$STATUS" --argjson tn "$TOP_N" --argjson al "$ALTS" --argjson mb "$MINB" '{league_key:$lk, team_key:$tk, status:$st, top_n:$tn, include_alternatives:($al==1), min_benefit:$mb, exclude_positions:["K","DEF"]}')

echo "\n== Deterministic v2 Recommendations =="
curl "${curl_common[@]}" -X POST -d "$body" "${API_BASE_URL}/yahoo/waiver_recommendations_v2" | tee /tmp/waiver_v2.json | jq '{count:(.recommendations|length), recs: [.recommendations[] | {add: (.add_player.name//.add.name), drop:(.drop_player.name//.drop.name), benefit:.estimated_benefit}]}' || true

if [[ -n "$GEMINI_KEY" ]]; then
  echo "\n== AI Recommendations (with debug) =="
  curl "${curl_common[@]}" -H "X-API-Key: $GEMINI_KEY" -X POST -d "$body" "${API_BASE_URL}/yahoo/waiver_recommendations_ai?debug=1" | tee /tmp/waiver_ai.json | jq '{moves_count:(.moves|length), summary, moves, debug: {pool_coverage, roster_coverage, error}}' || true
else
  echo "\n(GEMINI_KEY not set; skipping AI endpoint)"
fi

echo "\n== Self-add guard check (Rashee Rice) =="
name="Rashee Rice"
jq -r --arg n "$name" '.recommendations[]? | select((.add_player.name // .add.name) == $n) | "FOUND: add \(.add_player.name // .add.name) -> drop \(.drop_player.name // .drop.name) benefit=\(.estimated_benefit)"' /tmp/waiver_v2.json || true

echo "Done."

