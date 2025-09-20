#!/usr/bin/env bash
set -euo pipefail

# Trade Suggestions tester (no prompts by default)
# Env:
#   TOKEN (required)   - Yahoo OAuth access token
#   BACKEND (optional) - e.g., https://localhost:5000 or http://localhost:5000
#   LEAGUE (optional)  - defaults to 461.l.42889
#   MY_TEAM_KEY (opt)  - auto-detected if not set (via /api/yahoo/leagues)

LEAGUE="${LEAGUE:-461.l.42889}"
if [[ -z "${TOKEN:-}" ]]; then
  echo "ERROR: TOKEN not set. Run: export TOKEN='your_yahoo_token'" >&2
  exit 1
fi

# Choose backend: prefer https then http if BACKEND not provided
if [[ -z "${BACKEND:-}" ]]; then
  CANDIDATES=("https://localhost:5000" "http://localhost:5000")
else
  CANDIDATES=("${BACKEND}")
fi

HDR_AUTH="Authorization: Bearer ${TOKEN}"
HDR_CT="Content-Type: application/json"
CURL_OPTS="-sS"
BACKEND_CHOSEN=""
for cand in "${CANDIDATES[@]}"; do
  EXTRA=""
  [[ "$cand" == https://* ]] && EXTRA="-k"
  if curl -sS $EXTRA -H "$HDR_AUTH" "$cand/" >/dev/null 2>&1; then
    BACKEND_CHOSEN="$cand"; CURL_OPTS="-sS $EXTRA"; break
  fi
done
if [[ -z "$BACKEND_CHOSEN" ]]; then
  echo "ERROR: Could not reach backend at: ${CANDIDATES[*]}" >&2
  exit 1
fi
echo "Using BACKEND=${BACKEND_CHOSEN} (curl opts: ${CURL_OPTS})" >&2

# Auto-detect MY_TEAM_KEY if not provided
if [[ -z "${MY_TEAM_KEY:-}" ]]; then
  LEAGUES_JSON=$(curl ${CURL_OPTS} -H "$HDR_AUTH" "$BACKEND_CHOSEN/api/yahoo/leagues" || true)
  MY_TEAM_KEY=$(python3 - <<'PY' 2>/dev/null || true
import json,sys,os
try:
  data=json.loads(sys.stdin.read())
  league=os.getenv('LEAGUE')
  if isinstance(data, list):
    for l in data:
      if l.get('league_key')==league:
        t=l.get('team',{})
        print(t.get('team_key') or '')
        break
except Exception:
  pass
PY
<<<"$LEAGUES_JSON")
fi
if [[ -z "${MY_TEAM_KEY:-}" ]]; then
  echo "ERROR: MY_TEAM_KEY not set and auto-detect failed. Set: export MY_TEAM_KEY='league.t.team'" >&2
  exit 1
fi

echo "Generating trade suggestions..." >&2
REQ=$(printf '{"league_key":"%s","my_team_key":"%s","bench_first":true,"include_injured":false,"max_package_size":2,"top_k":12,"debug":1}' "$LEAGUE" "$MY_TEAM_KEY")
RESP=$(curl ${CURL_OPTS} -H "$HDR_AUTH" -H "$HDR_CT" -X POST -d "$REQ" "$BACKEND_CHOSEN/api/trade_suggestions" || true)

# Print summary
echo "$RESP" | python3 - <<'PY'
import json,sys
data=sys.stdin.read()
try:
  r=json.loads(data)
  ps=r.get('proposals',[])
  print("Proposals:", len(ps))
  for p in ps[:10]:
    print(f"* {p.get('trade_id')} | myΔ {p.get('my_delta_points')} | theirΔ {p.get('their_delta_points')} | parity {p.get('value_parity_pct')}% | acc {p.get('acceptance_prob')}")
except Exception as e:
  print("ERROR parsing suggestions JSON:", e)
  print("RAW:")
  print(data[:400])
PY

# Capture first_id
FIRST_ID=$(echo "$RESP" | python3 - <<'PY'
import json,sys
try:
  r=json.load(sys.stdin)
  ps=r.get('proposals',[])
  print(ps[0]['trade_id'] if ps else '')
except Exception:
  print('')
PY
)

# Debug first proposal if present
if [[ -n "$FIRST_ID" && "$FIRST_ID" != ERROR* ]]; then
  echo "Debugging first proposal: $FIRST_ID" >&2
  DBG=$(curl ${CURL_OPTS} -H "$HDR_AUTH" "$BACKEND_CHOSEN/api/trade_suggestions/debug?league_key=$LEAGUE&my_team_key=$MY_TEAM_KEY&trade_id=$FIRST_ID" || true)
  echo "$DBG" | python3 - <<'PY'
import json,sys
try:
  d=json.load(sys.stdin)
  keep={k:d.get(k) for k in ['trade_id','my_delta_points','their_delta_points','value_parity_pct','acceptance_prob']}
  print(keep)
except Exception as e:
  print('ERROR parsing debug JSON:', e)
  print('RAW:')
  print(sys.stdin.read()[:400])
PY
fi

exit 0
