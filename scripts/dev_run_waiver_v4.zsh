#!/usr/bin/env zsh
# Run the dev waiver v4 test using stored config (token/league/team/gemini)
# Usage:
#   RATM_DEV=1 ./scripts/dev_run_waiver_v4.zsh
# Optional overrides:
#   API_BASE_URL, STATUS=A|FA|W, TOP_N=10, ALTS=0|1, MINB=0, USE_AI=1|0

set -euo pipefail

: ${API_BASE_URL:=${API_BASE_URL:-"https://localhost:5000/api"}}
STATUS=${STATUS:-A}
TOP_N=${TOP_N:-10}
ALTS=${ALTS:-0}
MINB=${MINB:-0}
USE_AI=${USE_AI:-1}

body=$(jq -n --arg st "$STATUS" --argjson tn "$TOP_N" --argjson al "$ALTS" --argjson mb "$MINB" --argjson ua "$USE_AI" '{status:$st, top_n:$tn, include_alternatives:($al==1), min_benefit:$mb, use_ai: ($ua==1)}')

curl -sS -k -H 'Content-Type: application/json' -X POST -d "$body" "$API_BASE_URL/dev/run_waiver_v4_test" | jq '{roster, v2: {count:(.v2.recommendations|length), recs: (.v2.recommendations // [] | map({add: (.add_player.name // .add.name), drop:(.drop_player.name // .drop.name), benefit:.estimated_benefit}))}, ai: {summary, moves_count:(.ai.moves|length), debug: {pool_coverage, roster_coverage, error}}}'

