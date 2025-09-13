#!/usr/bin/env zsh

# Zsh smoketest for Sit/Start Optimizer (Yahoo + Traditional)
# Usage examples:
#   export GEMINI_KEY=your_key
#   export API_BASE_URL=https://localhost:5000/api   # optional; auto-detect if not set
#   # Yahoo mode (requires yahoo_token in localStorage when using the app; here, pass token directly)
#   export YAHOO_BEARER="Bearer <token>"
#   zsh scripts/test_lineup_optimizer.zsh --yahoo --team "461.l.12345.t.8" --league "461.l.12345" --week 1
#   # Traditional mode
#   zsh scripts/test_lineup_optimizer.zsh --traditional --week 1 --roster QB="Josh Allen" RB1="Saquon Barkley" RB2="James Cook" WR1="Tyreek Hill" WR2="Amon-Ra St. Brown" TE="Sam LaPorta" W_T="" W_R_T="" K="Justin Tucker" DEF="49ers"

set -euo pipefail

if [[ -z "${GEMINI_KEY:-}" ]]; then
  echo "Error: GEMINI_KEY not set"; exit 1
fi

API_BASE="${API_BASE_URL:-}"
USE_K=0

try_ping() {
  local base="$1"; local usek="$2"; local code
  if [[ "$usek" == "1" ]]; then
    code=$(curl -k -sS -o /dev/null -w "%{http_code}" "$base/all_player_names_with_data" || echo 000)
  else
    code=$(curl -sS -o /dev/null -w "%{http_code}" "$base/all_player_names_with_data" || echo 000)
  fi
  echo "$code"
}

if [[ -z "$API_BASE" ]]; then
  if [[ "$(try_ping https://localhost:5000/api 1)" == "200" ]]; then API_BASE=https://localhost:5000/api; USE_K=1
  elif [[ "$(try_ping http://localhost:5000/api 0)" == "200" ]]; then API_BASE=http://localhost:5000/api; USE_K=0
  else API_BASE=https://ratm-app.onrender.com/api; USE_K=0; fi
fi

echo "API_BASE=${API_BASE}"

mode=""
week=""
team_key=""
league_key=""
typeset -A roster

while [[ $# -gt 0 ]]; do
  case "$1" in
    --yahoo) mode=yahoo; shift ;;
    --traditional) mode=traditional; shift ;;
    --team) team_key="$2"; shift 2 ;;
    --league) league_key="$2"; shift 2 ;;
    --week) week="$2"; shift 2 ;;
    --roster) shift; while [[ $# -gt 0 && "$1" == *=* ]]; do k="${1%%=*}"; v="${1#*=}"; k=${k//_//}; roster[$k]="$v"; shift; done ;;
    *) echo "Unknown arg: $1"; exit 2 ;;
  esac
done

if [[ -z "$mode" ]]; then echo "Pick --yahoo or --traditional"; exit 2; fi

typeset -a CF
[[ "$USE_K" == "1" ]] && CF+=(-k)

payload='{}'
headers=(-H 'Content-Type: application/json' -H "X-API-Key: ${GEMINI_KEY}")

if [[ "$mode" == "yahoo" ]]; then
  if [[ -z "${YAHOO_BEARER:-}" ]]; then echo "Error: YAHOO_BEARER not set"; exit 1; fi
  headers+=(-H "Authorization: ${YAHOO_BEARER}")
  payload=$(jq -n --arg team "$team_key" --arg league "$league_key" --arg w "$week" '{mode:"yahoo", team_key:$team, league_key: ($league|select(.!="")), week: ($w|tonumber?)}')
else
  # Traditional: build roster object
  echo "Traditional roster slots: ${(@k)roster}"
  payload=$(jq -n --arg w "$week" '{mode:"traditional", week: ($w|tonumber?), roster:{}}')
  for k in ${(k)roster}; do
    payload=$(jq --arg k "$k" --arg v "${roster[$k]}" '.roster[$k]=$v' <<< "$payload")
  done
fi

echo "Payload: $payload"
resp=$(curl ${CF[@]} -sS -X POST "${API_BASE}/optimize_lineup" ${headers[@]} -d "$payload" || true)

if command -v jq >/dev/null 2>&1; then
  if ! echo "$resp" | jq . >/dev/null 2>&1; then
    echo "❌ Non-JSON response"; echo "$resp" | head -c 500; exit 1
  fi
  if echo "$resp" | jq -e '.error' >/dev/null; then
    echo "❌ API error: $(echo "$resp" | jq -r '.error')"; exit 1
  fi
  echo "✅ OK: $(echo "$resp" | jq -r '.ai_note_json.headline // "(no headline)"')"
  echo "   total: $(echo "$resp" | jq -r '.total_projected_points // 0')"
else
  echo "Raw length: ${#resp}"
fi

