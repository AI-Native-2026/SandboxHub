#!/usr/bin/env bash
# Verify Keycloak realm, users, roles via direct access grant.
set -uo pipefail
KC=http://127.0.0.1:8180/realms/sandboxhub

echo "=== openid-config ==="
curl -s -o /dev/null -w '%{http_code}\n' "$KC/.well-known/openid-configuration"

for u in admin tenantadmin dev1 viewer; do
  echo "=== user: $u ==="
  RESP=$(curl -s -X POST "$KC/protocol/openid-connect/token" \
    -d grant_type=password -d client_id=sandboxhub-web \
    -d username="$u" -d password='Passw0rd!')
  echo "$RESP" | python3 -c '
import sys, json, base64
try:
    d = json.load(sys.stdin)
except Exception:
    print("  parse error"); sys.exit()
if "access_token" not in d:
    print("  LOGIN FAILED:", d.get("error"), d.get("error_description")); sys.exit()
t = d["access_token"]; p = t.split(".")[1]; p += "=" * (-len(p) % 4)
payload = json.loads(base64.urlsafe_b64decode(p))
print("  user:", payload.get("preferred_username"))
print("  roles:", payload.get("realm_access", {}).get("roles"))
'
done

echo "=== clients ==="
ADMIN_TOKEN=$(curl -s -X POST "$KC/protocol/openid-connect/token" \
  -d grant_type=password -d client_id=admin-cli \
  -d username=admin -d password="${KEYCLOAK_ADMIN_PASSWORD:-sh_kc_2026}" \
  | python3 -c 'import sys,json; print(json.load(sys.stdin).get("access_token",""))')
curl -s -H "Authorization: Bearer $ADMIN_TOKEN" \
  "http://127.0.0.1:8180/admin/realms/sandboxhub/clients" \
  | python3 -c 'import sys,json; print([c["clientId"] for c in json.load(sys.stdin)])'
