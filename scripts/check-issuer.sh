#!/usr/bin/env bash
# Verify Keycloak issuer and a demo login through the /auth path.
set -uo pipefail
KC=http://127.0.0.1:8180/realms/sandboxhub
echo "=== issuer ==="
curl -s "$KC/.well-known/openid-configuration" | python3 -c 'import sys,json; d=json.load(sys.stdin); print("issuer:", d["issuer"]); print("jwks_uri:", d["jwks_uri"])'
echo "=== dev1 login ==="
curl -s -X POST "$KC/protocol/openid-connect/token" \
  -d grant_type=password -d client_id=sandboxhub-web \
  -d username=dev1 -d password='Passw0rd!' \
  | python3 -c 'import sys,json,base64; d=json.load(sys.stdin); t=d.get("access_token");
p=t.split(".")[1] if t else ""; p+="="*(-len(p)%4);
pay=json.loads(base64.urlsafe_b64decode(p)) if p else {};
print("iss:", pay.get("iss")); print("roles:", pay.get("realm_access",{}).get("roles"))' 2>/dev/null || echo "login failed"
