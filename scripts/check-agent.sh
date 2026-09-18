#!/usr/bin/env bash
# Verify agent launch installs the agent (opencode).
set -uo pipefail
WEB=http://127.0.0.1:8081
KC=$WEB/realms/sandboxhub
DT=$(curl -s -X POST "$KC/protocol/openid-connect/token" -d grant_type=password -d client_id=sandboxhub-web -d username=dev1 -d password='Passw0rd!' | jq -r .access_token)
DTEN=$(curl -s -H "Authorization: Bearer $DT" "$WEB/api/v1/me" | jq -r '.tenants[0].id')
D=(-H "Authorization: Bearer $DT" -H "X-Tenant-Id: $DTEN" -H "Content-Type: application/json")

echo "== launch opencode agent =="
L=$(curl -s "${D[@]}" -X POST "$WEB/api/v1/agents/opencode/launch" -d '{"cpu":"2","memory":"2Gi","timeout_seconds":1800}')
echo "$L" | jq -c .
SID=$(echo "$L" | jq -r .sandbox_id)

echo "== wait for install (up to 150s) =="
for i in $(seq 1 30); do
  sleep 5
  OUT=$(curl -s "${D[@]}" -X POST "$WEB/api/v1/sandboxes/$SID/commands" -d '{"command":"which opencode && opencode --version || echo NOT_YET"}' | grep -o '"text":"[^"]*"' | tail -2 | tr '\n' ' ')
  echo "  t=$((i*5))s: $OUT"
  if echo "$OUT" | grep -qv "NOT_YET"; then echo "INSTALLED"; break; fi
done
echo "sandbox=$SID"
