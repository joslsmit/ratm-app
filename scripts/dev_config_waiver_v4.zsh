#!/usr/bin/env zsh
# Configure dev runner with your Yahoo token, league, team, and optional Gemini key
# Usage:
#   RATM_DEV=1 TOKEN='{"access_token":"..."}' LEAGUE_KEY='461.l.42889' TEAM_KEY='461.l.42889.t.8' GEMINI_KEY='...' ./scripts/dev_config_waiver_v4.zsh

set -euo pipefail

: ${API_BASE_URL:=${API_BASE_URL:-"https://localhost:5000/api"}}
: ${TOKEN:?"Set TOKEN to the JSON string or raw access token"}
: ${LEAGUE_KEY:?"Set LEAGUE_KEY"}
: ${TEAM_KEY:?"Set TEAM_KEY"}

body=$(jq -n --arg t "$TOKEN" --arg lk "$LEAGUE_KEY" --arg tk "$TEAM_KEY" --arg g "${GEMINI_KEY:-}" '{token:$t, league_key:$lk, team_key:$tk, gemini_key: ( $g | select(length>0) ) }')

curl -sS -k -H 'Content-Type: application/json' -X POST -d "$body" "$API_BASE_URL/dev/configure" | jq .

