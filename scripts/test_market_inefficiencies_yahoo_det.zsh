#!/usr/bin/env zsh
# Deterministic Yahoo league inefficiency test runner
# Requirements:
#   TOKEN       - Yahoo OAuth token (raw token string or JSON with access_token)
#   GEMINI_KEY  - Google Gemini API key (still required by backend for some AI tasks)
#   LEAGUE_KEY  - Yahoo league key (e.g., 461.l.42889)
#   TEAM_KEY    - Yahoo team key (e.g., 461.l.42889.t.8)
# Optional:
#   API_BASE    - API base URL (default: https://localhost:5000/api)

set -euo pipefail

API_BASE=${API_BASE:-https://localhost:5000/api}

if [[ -z "${TOKEN:-}" || -z "${GEMINI_KEY:-}" || -z "${LEAGUE_KEY:-}" || -z "${TEAM_KEY:-}" ]]; then
  echo "Usage: TOKEN=... GEMINI_KEY=... LEAGUE_KEY=... TEAM_KEY=... ${0}" >&2
  exit 1
fi

# Extract raw access token if a JSON blob is provided
ACCESS_TOKEN="$TOKEN"
if echo "$TOKEN" | grep -q 'access_token'; then
  ACCESS_TOKEN=$(echo "$TOKEN" | sed -n 's/.*"access_token"\s*:\s*"\([^"]*\)".*/\1/p')
fi

hdr_yahoo=( -H "Authorization: Bearer $ACCESS_TOKEN" )
hdr_json=( -H 'Content-Type: application/json' -H "X-API-Key: $GEMINI_KEY" )

echo "Fetching league context ..." >&2
LC=$(curl -sS -k "${hdr_yahoo[@]}" "$API_BASE/yahoo/league_context?league_key=$LEAGUE_KEY")

echo "Fetching available player pools (FA + W) ..." >&2
PFA=$(curl -sS -k "${hdr_yahoo[@]}" "$API_BASE/yahoo/waiver_pool?league_key=$LEAGUE_KEY&status=FA")
PW=$(curl -sS -k "${hdr_yahoo[@]}" "$API_BASE/yahoo/waiver_pool?league_key=$LEAGUE_KEY&status=W")

AP=$(jq -n --argjson a "$PFA" --argjson b "$PW" '{available_players: ((($a.available_players // []) + ($b.available_players // [])))}')

echo "Running deterministic league inefficiency analysis ..." >&2
REQ=$(jq -n \
  --arg lk "$LEAGUE_KEY" \
  --arg tk "$TEAM_KEY" \
  --argjson lc "$LC" \
  --argjson ap "$AP" \
  '{league_key:$lk, team_key:$tk, position:"all", league_context:$lc, available_players:$ap.available_players}')

RES=$(curl -sS -k "${hdr_json[@]}" -d "$REQ" "$API_BASE/yahoo/league_inefficiencies")

echo "Counts:" >&2
echo "$RES" | jq '{sleepers: (.sleepers|length), busts: (.busts|length)}'

echo "Top sleepers (names + flags):" >&2
echo "$RES" | jq -r '.sleepers[0:5][] | "- \(.name) [\(.availability_type // "?")] score=\(.score // 0)"'

echo "Top busts (names + edge vs FA):" >&2
echo "$RES" | jq -r '.busts[0:5][] | "- \(.name) edge_vs_FA=\(.edge_vs_best_fa // 0)"'

