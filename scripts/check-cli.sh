#!/usr/bin/env bash
# Test the SandboxHub CLI end-to-end + API key expiry.
set -uo pipefail
WEB=http://127.0.0.1:8081
KC=$WEB/realms/sandboxhub
export PATH="$HOME/.local/bin:$PATH"

DT=$(curl -s -X POST "$KC/protocol/openid-connect/token" -d grant_type=password -d client_id=sandboxhub-web -d username=dev1 -d password='Passw0rd!' | jq -r .access_token)
DTEN=$(curl -s -H "Authorization: Bearer $DT" "$WEB/api/v1/me" | jq -r '.tenants[0].id')
D=(-H "Authorization: Bearer $DT" -H "X-Tenant-Id: $DTEN" -H "Content-Type: application/json")

echo "== create API key with 30-day expiry =="
KR=$(curl -s "${D[@]}" -X POST "$WEB/api/v1/api-keys" -d '{"name":"cli-key","expires_in_days":30}')
echo "$KR" | jq -c '{name,prefix,expires_at}'
KEY=$(echo "$KR" | jq -r .api_key)

echo "== CLI login =="
sandboxhub login --domain 127.0.0.1:8081 --api-key "$KEY"
echo "== CLI whoami =="
sandboxhub whoami | jq -c '{user:.user.username, tenant:.tenant}'
echo "== CLI config =="
sandboxhub config

echo "== CLI sandbox list =="
sandboxhub sandbox list | head -5

echo "== CLI create =="
CREATE=$(sandboxhub sandbox create --image python:3.12 --name cli-demo)
echo "$CREATE" | jq -c '{sandbox_id,name,state}'
SID=$(echo "$CREATE" | jq -r .sandbox_id)

echo "== CLI exec =="
sandboxhub exec "$SID" python --version

echo "== CLI files ls =="
sandboxhub files ls "$SID" /tmp | head -4

echo "== CLI delete =="
sandboxhub sandbox delete "$SID"

echo "== API key expiry enforcement =="
# force the key to be expired in the DB, then try to use it
docker exec sandboxhub-postgres psql -U sandboxhub -d sandboxhub -c \
  "UPDATE api_keys SET expires_at = now() - interval '1 day' WHERE prefix = '$(echo "$KEY" | cut -c1-10)';" >/dev/null
code=$(curl -s -o /dev/null -w '%{http_code}' -H "X-API-Key: $KEY" "$WEB/api/v1/me")
echo "expired key /me -> HTTP $code (expect 401)"

echo "== cleanup run expires keys =="
AT=$(curl -s -X POST "$KC/protocol/openid-connect/token" -d grant_type=password -d client_id=sandboxhub-web -d username=admin -d password='Passw0rd!' | jq -r .access_token)
ATEN=$(curl -s -H "Authorization: Bearer $AT" "$WEB/api/v1/me" | jq -r '.tenants[0].id')
curl -s -H "Authorization: Bearer $AT" -H "X-Tenant-Id: $ATEN" -X POST "$WEB/api/v1/admin/cleanup" | jq -c .
