#!/usr/bin/env bash
# M7/M8 checks: api-keys, snapshots, admin endpoints + RBAC.
set -uo pipefail
WEB=http://127.0.0.1:8081
KC=$WEB/realms/sandboxhub

tok() { curl -s -X POST "$KC/protocol/openid-connect/token" -d grant_type=password -d client_id=sandboxhub-web -d username="$1" -d password='Passw0rd!' | jq -r .access_token; }

DT=$(tok dev1); AT=$(tok admin)
DTENANT=$(curl -s -H "Authorization: Bearer $DT" "$WEB/api/v1/me" | jq -r '.tenants[0].id')
ATENANT=$(curl -s -H "Authorization: Bearer $AT" "$WEB/api/v1/me" | jq -r '.tenants[0].id')
DAUTH=(-H "Authorization: Bearer $DT" -H "X-Tenant-Id: $DTENANT")
AAUTH=(-H "Authorization: Bearer $AT" -H "X-Tenant-Id: $ATENANT")

echo "=== M7: personal api key create ==="
KEYRESP=$(curl -s "${DAUTH[@]}" -H "Content-Type: application/json" -X POST "$WEB/api/v1/api-keys" -d '{"name":"cli-key"}')
echo "$KEYRESP" | jq -c '{id,name,prefix,has_key:(.api_key!=null)}'
RAWKEY=$(echo "$KEYRESP" | jq -r .api_key)
echo "=== use api key to authenticate ==="
curl -s -H "X-API-Key: $RAWKEY" -H "X-Tenant-Id: $DTENANT" "$WEB/api/v1/me" | jq -c '{user:.user.username, roles:.roles}'
echo "=== list keys ==="
curl -s "${DAUTH[@]}" "$WEB/api/v1/api-keys" | jq -c '[.[]|{name,status}]'

echo "=== M7: snapshots list ==="
curl -s "${DAUTH[@]}" "$WEB/api/v1/snapshots" | head -c 200; echo

echo "=== M8: admin tenants (as admin) ==="
curl -s "${AAUTH[@]}" "$WEB/api/v1/admin/tenants" | jq -c '[.[]|{slug,name,sandbox_count,member_count}]'

echo "=== M8: admin audit (as admin) ==="
curl -s "${AAUTH[@]}" "$WEB/api/v1/admin/audit?limit=5" | jq -c '[.[]|{action,resource_id}]'

echo "=== M8: admin metrics ==="
curl -s "${AAUTH[@]}" "$WEB/api/v1/admin/metrics" | jq -c .

echo "=== M8: admin denied for dev1 (expect 403) ==="
curl -s -o /dev/null -w '%{http_code}\n' "${DAUTH[@]}" "$WEB/api/v1/admin/tenants"
