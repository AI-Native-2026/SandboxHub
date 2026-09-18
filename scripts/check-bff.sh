#!/usr/bin/env bash
# Verify BFF auth + seed: login as dev1, call /api/v1/me and /overview.
set -uo pipefail
KC=http://127.0.0.1:8180/realms/sandboxhub
BFF=http://127.0.0.1:8001

token() {
  curl -s -X POST "$KC/protocol/openid-connect/token" \
    -d grant_type=password -d client_id=sandboxhub-web \
    -d username="$1" -d password='Passw0rd!' | jq -r .access_token
}

for u in admin tenantadmin dev1 viewer; do
  T=$(token "$u")
  echo "=== $u ==="
  curl -s -H "Authorization: Bearer $T" "$BFF/api/v1/me" | jq -c '{user:.user.username, roles:.roles, tenants:[.tenants[].slug]}'
done

echo "=== dev1 /overview ==="
T=$(token dev1)
TENANT=$(curl -s -H "Authorization: Bearer $T" "$BFF/api/v1/me" | jq -r '.tenants[0].id')
curl -s -H "Authorization: Bearer $T" -H "X-Tenant-Id: $TENANT" "$BFF/api/v1/overview" | jq -c '{tenant:.tenant.slug, sandboxes:.sandboxes, templates:.templates}'

echo "=== no token (expect 401) ==="
curl -s -o /dev/null -w '%{http_code}\n' "$BFF/api/v1/me"

echo "=== viewer write denied check (overview ok, but writer-only later) ==="
TV=$(token viewer)
TENV=$(curl -s -H "Authorization: Bearer $TV" "$BFF/api/v1/me" | jq -r '.tenants[0].id')
curl -s -H "Authorization: Bearer $TV" -H "X-Tenant-Id: $TENV" "$BFF/api/v1/overview" | jq -c '{role:.tenant.role}'
