#!/usr/bin/env bash
# Run the recording test inside the BFF container.
set -uo pipefail
WEB=http://127.0.0.1:8081
KC=$WEB/realms/sandboxhub
DT=$(curl -s -X POST "$KC/protocol/openid-connect/token" -d grant_type=password -d client_id=sandboxhub-web -d username=dev1 -d password='Passw0rd!' | jq -r .access_token)
DTEN=$(curl -s -H "Authorization: Bearer $DT" "$WEB/api/v1/me" | jq -r '.tenants[0].id')
docker cp /home/ubuntu/SandboxHub/rec_test.py sandboxhub-bff:/tmp/rec_test.py >/dev/null
docker exec -i -e TOK="$DT" -e TEN="$DTEN" sandboxhub-bff python /tmp/rec_test.py
