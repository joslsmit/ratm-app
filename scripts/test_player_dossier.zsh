#!/usr/bin/env zsh

# Zsh smoketest for the Player Dossier endpoint (local-first)
#
# Quick start:
#   export GEMINI_KEY=your_api_key
#   zsh scripts/test_player_dossier.zsh "Lamar Jackson" "Amon-Ra St. Brown"
#
# Optional:
#   export API_BASE_URL=...     # overrides auto-detect
#   export CURL_FLAGS="-v"       # extra curl flags

set -e
set -u
set -o pipefail

typeset -a PLAYERS
PLAYERS=(${@})

if [[ ${#PLAYERS[@]} -eq 0 ]]; then
  PLAYERS=("Amon-Ra St. Brown" "Lamar Jackson")
fi

if [[ -z "${GEMINI_KEY:-}" ]]; then
  echo "Error: GEMINI_KEY env var not set."
  echo "Set it with: export GEMINI_KEY=your_api_key"
  exit 1
fi

# Resolve API_BASE_URL
API_BASE_URL_RESOLVED="${API_BASE_URL:-}"
USE_K=0

function try_url() {
  local url="$1"
  local use_k="$2"
  local code
  if [[ "$use_k" == "1" ]]; then
    code=$(curl -k -sS -o /dev/null -w "%{http_code}" "$url/all_player_names_with_data" || echo "000")
  else
    code=$(curl -sS -o /dev/null -w "%{http_code}" "$url/all_player_names_with_data" || echo "000")
  fi
  echo "$code"
}

if [[ -z "$API_BASE_URL_RESOLVED" ]]; then
  # Try local HTTPS first (mkcert typical)
  code=$(try_url "https://localhost:5000/api" 1)
  if [[ "$code" == "200" ]]; then
    API_BASE_URL_RESOLVED="https://localhost:5000/api"
    USE_K=1
  else
    # Try local HTTP
    code=$(try_url "http://localhost:5000/api" 0)
    if [[ "$code" == "200" ]]; then
      API_BASE_URL_RESOLVED="http://localhost:5000/api"
      USE_K=0
    else
      # Fallback to production
      API_BASE_URL_RESOLVED="https://ratm-app.onrender.com/api"
      USE_K=0
    fi
  fi
fi

echo "API_BASE_URL=${API_BASE_URL_RESOLVED}"
echo "Players: ${#PLAYERS[@]}"

# Build curl flags
typeset -a CF
CF=()
if [[ "$USE_K" == "1" ]]; then
  CF+=(-k)
fi
if [[ -n "${CURL_FLAGS:-}" ]]; then
  CF+=(${=CURL_FLAGS})
fi

failures=0
for name in "${PLAYERS[@]}"; do
  echo "\n— Testing dossier for: ${name}"
  payload=$(printf '{"player_name":"%s"}' "$name")
  resp=$(curl ${CF[@]} -sS -X POST "${API_BASE_URL_RESOLVED}/player_dossier" \
    -H 'Content-Type: application/json' \
    -H "X-API-Key: ${GEMINI_KEY}" \
    -d "${payload}" || true)

  if [[ -z "$resp" ]]; then
    echo "❌ Empty response (connection or server error)"
    failures=$((failures+1))
    continue
  fi

  if command -v jq >/dev/null 2>&1; then
    # If server returns non-JSON, jq will fail; catch it
    if ! echo "$resp" | jq . >/dev/null 2>&1; then
      echo "❌ Non-JSON response (possible error page)"
      failures=$((failures+1))
      continue
    fi

    if echo "$resp" | jq -e '.error' >/dev/null 2>&1; then
      echo "❌ API error: $(echo "$resp" | jq -r '.error')"
      failures=$((failures+1))
      continue
    fi

    if ! echo "$resp" | jq -e '.player_data and .analysis' >/dev/null; then
      echo "❌ Invalid shape: missing player_data or analysis"
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

