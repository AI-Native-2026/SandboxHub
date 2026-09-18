#!/usr/bin/env bash
# Run a python script inside the BFF container with TOK/TEN env set.
# Usage: bash run-in-bff.sh /path/to/script.py
set -uo pipefail
SCRIPT="${1:?usage: run-in-bff.sh <script.py>}"
WEB=http://127.0.0.1:8081
KC=$WEB/realms/sandboxhub
DT=$(curl -s -X POST "$KC/protocol/openid-connect/token" \
  -d grant_type=password -d client_id=sandboxhub-web \
  -d username=dev1 -d password='Passw0rd!' | jq -r .access_token)
DTEN=$(curl -s -H "Authorization: Bearer $DT" "$WEB/api/v1/me" | jq -r '.tenants[0].id')
docker cp "$SCRIPT" sandboxhub-bff:/tmp/_run.py >/dev/null
docker exec -i -e TOK="$DT" -e TEN="$DTEN" sandboxhub-bff python /tmp/_run.py
