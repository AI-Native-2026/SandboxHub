#!/usr/bin/env bash
# M3 end-to-end: create sandbox via BFF, run command, metrics, files, delete.
set -uo pipefail
KC=http://127.0.0.1:8180/realms/sandboxhub
BFF=http://127.0.0.1:8001

T=$(curl -s -X POST "$KC/protocol/openid-connect/token" -d grant_type=password -d client_id=sandboxhub-web -d username=dev1 -d password='Passw0rd!' | jq -r .access_token)
TENANT=$(curl -s -H "Authorization: Bearer $T" "$BFF/api/v1/me" | jq -r '.tenants[0].id')
AUTH=(-H "Authorization: Bearer $T" -H "X-Tenant-Id: $TENANT" -H "Content-Type: application/json")

echo "=== create sandbox ==="
CREATE=$(curl -s "${AUTH[@]}" -X POST "$BFF/api/v1/sandboxes" -d '{"image":"python:3.12","name":"m3-test","cpu":"1","memory":"1Gi","timeout_seconds":600}')
echo "$CREATE" | jq -c '{id, sandbox_id, state, image}'
SID=$(echo "$CREATE" | jq -r .sandbox_id)
[ "$SID" = "null" ] && { echo "create failed"; exit 1; }

echo "=== list ==="
curl -s "${AUTH[@]}" "$BFF/api/v1/sandboxes" | jq -c '{total, items:[.items[]|{sandbox_id,state}]}'

echo "=== get ==="
curl -s "${AUTH[@]}" "$BFF/api/v1/sandboxes/$SID" | jq -c '{sandbox_id,state}'

echo "=== command (SSE) ==="
curl -s --max-time 20 "${AUTH[@]}" -X POST "$BFF/api/v1/sandboxes/$SID/commands" -d '{"command":"echo bff-hello; python --version"}' | head -c 600; echo

echo "=== metrics ==="
curl -s "${AUTH[@]}" "$BFF/api/v1/sandboxes/$SID/metrics" | head -c 300; echo

echo "=== files: write then read ==="
curl -s "${AUTH[@]}" -X POST "$BFF/api/v1/sandboxes/$SID/files/write" -d '{"path":"/tmp/bff.txt","content":"written-via-bff"}' | jq -c .
curl -s "${AUTH[@]}" "$BFF/api/v1/sandboxes/$SID/files/download?path=/tmp/bff.txt"; echo

echo "=== files: list /tmp ==="
curl -s "${AUTH[@]}" "$BFF/api/v1/sandboxes/$SID/files/list?path=/tmp&depth=1" | jq -c '.entries[0:3]'

echo "=== delete ==="
curl -s -o /dev/null -w '%{http_code}\n' "${AUTH[@]}" -X DELETE "$BFF/api/v1/sandboxes/$SID"
