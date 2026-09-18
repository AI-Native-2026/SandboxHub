#!/usr/bin/env bash
# Verify the web container (nginx) single-port entry: static, keycloak, api.
set -uo pipefail
WEB=http://127.0.0.1:8081

echo "=== index.html ==="
curl -s -o /dev/null -w '%{http_code}\n' "$WEB/"
curl -s "$WEB/" | grep -o '<title>[^<]*</title>'

echo "=== keycloak via /realms ==="
curl -s -o /dev/null -w '%{http_code}\n' "$WEB/realms/sandboxhub/.well-known/openid-configuration"
curl -s "$WEB/realms/sandboxhub/.well-known/openid-configuration" | jq -r .issuer

echo "=== api via /api (no token expect 401) ==="
curl -s -o /dev/null -w '%{http_code}\n' "$WEB/api/v1/me"

echo "=== api via /api with token ==="
T=$(curl -s -X POST "$WEB/realms/sandboxhub/protocol/openid-connect/token" \
  -d grant_type=password -d client_id=sandboxhub-web -d username=dev1 -d password='Passw0rd!' | jq -r .access_token)
curl -s -H "Authorization: Bearer $T" "$WEB/api/v1/me" | jq -c '{user:.user.username, tenants:[.tenants[].slug]}'
