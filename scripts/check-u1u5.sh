#!/usr/bin/env bash
# U1-U5 endpoint checks.
set -uo pipefail
WEB=http://127.0.0.1:8081
KC=$WEB/realms/sandboxhub
tok() { curl -s -X POST "$KC/protocol/openid-connect/token" -d grant_type=password -d client_id=sandboxhub-web -d username="$1" -d password='Passw0rd!' | jq -r .access_token; }

AT=$(tok admin); DT=$(tok dev1)
ATEN=$(curl -s -H "Authorization: Bearer $AT" "$WEB/api/v1/me" | jq -r '.tenants[0].id')
DTEN=$(curl -s -H "Authorization: Bearer $DT" "$WEB/api/v1/me" | jq -r '.tenants[0].id')
A=(-H "Authorization: Bearer $AT" -H "X-Tenant-Id: $ATEN" -H "Content-Type: application/json")
D=(-H "Authorization: Bearer $DT" -H "X-Tenant-Id: $DTEN" -H "Content-Type: application/json")

echo "== U1 usage/summary ==";   curl -s "${A[@]}" "$WEB/api/v1/usage/summary?days=7" | jq -c .
echo "== U1 quota ==";           curl -s "${A[@]}" "$WEB/api/v1/quota" | jq -c .
echo "== U1 approval create =="; curl -s "${A[@]}" -X POST "$WEB/api/v1/approvals" -d '{"kind":"quota","reason":"test","payload":{}}' | jq -c '{id,kind,status}'
echo "== U1 credential create =="; curl -s "${A[@]}" -X POST "$WEB/api/v1/credentials" -d '{"name":"gh","type":"bearer","secret":"s3cr3t"}' | jq -c '{name,type,secret_ref}'
echo "== U1 policy template create =="; curl -s "${A[@]}" -X POST "$WEB/api/v1/policy-templates" -d '{"name":"pypi","rules":[{"action":"allow","target":"*.pythonhosted.org"}]}' | jq -c '{name,default_action}'
echo "== U3 rbac ==";            curl -s "${A[@]}" "$WEB/api/v1/rbac/roles" | jq -c '{roles:(.matrix.roles|keys), custom:(.custom|length)}'
echo "== U3 recordings ==";      curl -s "${A[@]}" "$WEB/api/v1/recordings" | jq -c 'length'
echo "== U4 pool create ==";     curl -s "${A[@]}" -X POST "$WEB/api/v1/pools" -d '{"name":"warm-python","image":"python:3.12","capacity":{"min":1,"max":3}}' | jq -c '{name,provider,capacity}'
echo "== U4 observability ==";   curl -s "${A[@]}" "$WEB/api/v1/observability" | jq -c '{tenants,users,sandboxes:.sandboxes.total}'
echo "== U5 agents ==";          curl -s "${D[@]}" "$WEB/api/v1/agents" | jq -c '[.[].id]'
echo "== U5 task create ==";     TID=$(curl -s "${D[@]}" -X POST "$WEB/api/v1/tasks" -d '{"name":"batch","image":"python:3.12","command":"python -c \"print(1+1)\"","replicas":2}' | jq -r .id); echo "task=$TID"
echo "== U5 task get (after 20s) =="; sleep 20; curl -s "${D[@]}" "$WEB/api/v1/tasks/$TID" | jq -c '{status,succeeded,failed,items:(.items|length)}'
echo "== U5 artifacts ==";       curl -s "${D[@]}" "$WEB/api/v1/artifacts" | jq -c 'length'
