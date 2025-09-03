#!/usr/bin/env bash
set -euo pipefail

# Requires BASE and TOKEN
: "${BASE:?Set BASE}" "${TOKEN:?Set TOKEN}"

echo "==[ Trigger Refresh ]=="
curl -sk -X POST -H "Authorization: Bearer $TOKEN" "$BASE/api/admin/refresh_data" | jq '.'

