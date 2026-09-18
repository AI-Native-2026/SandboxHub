#!/usr/bin/env bash
# Inspect OpenSandbox lifecycle API response shapes (grounding for BFF).
set -uo pipefail
OSB=http://127.0.0.1:8090
KEY=osb-course-key-2026
H=(-H "Content-Type: application/json" -H "OPEN-SANDBOX-API-KEY: $KEY")

echo "=== create ==="
RESP=$(curl -s "${H[@]}" -X POST "$OSB/v1/sandboxes" -d '{
  "image": {"uri": "python:3.12"},
  "entrypoint": ["sleep", "infinity"],
  "timeout": 300,
  "resourceLimits": {"cpu": "1", "memory": "1Gi"},
  "metadata": {"name": "sh-probe", "tenant": "demo"}
}')
echo "$RESP" | jq -c '{id, status, entrypoint, expiresAt}'
SID=$(echo "$RESP" | jq -r .id)
echo "sandbox id: $SID"

echo "=== get ==="
curl -s "${H[@]}" "$OSB/v1/sandboxes/$SID" | jq -c '{id, status, metadata, resourceLimits}'

echo "=== endpoint 44772 ==="
curl -s "${H[@]}" "$OSB/v1/sandboxes/$SID/endpoints/44772" | jq -c .

echo "=== list (first item) ==="
curl -s "${H[@]}" "$OSB/v1/sandboxes?page=1&pageSize=2" | jq -c '.items[0] // .[0] // .' 2>/dev/null | head -c 400; echo

echo "=== delete ==="
curl -s -o /dev/null -w '%{http_code}\n' "${H[@]}" -X DELETE "$OSB/v1/sandboxes/$SID"
