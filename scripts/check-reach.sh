#!/usr/bin/env bash
# Create a sandbox and test execd reachability from host and from the BFF container.
set -uo pipefail
OSB=http://127.0.0.1:8090
KEY=osb-course-key-2026
H=(-H "Content-Type: application/json" -H "OPEN-SANDBOX-API-KEY: $KEY")

RESP=$(curl -s "${H[@]}" -X POST "$OSB/v1/sandboxes" -d '{
  "image": {"uri": "python:3.12"}, "entrypoint": ["sleep", "infinity"],
  "timeout": 300, "metadata": {"name": "sh-reach"}}')
SID=$(echo "$RESP" | jq -r .id)
EP=$(curl -s "${H[@]}" "$OSB/v1/sandboxes/$SID/endpoints/44772" | jq -r .endpoint)
echo "sandbox=$SID endpoint=$EP"
echo "docker0=$(ip -4 addr show docker0 2>/dev/null | grep -oP 'inet \K[0-9.]+')"

echo "=== host -> endpoint /ping ==="
curl -s -o /dev/null -w '%{http_code}\n' --max-time 6 "http://$EP/ping"

echo "=== bff container -> endpoint /ping ==="
docker exec sandboxhub-bff python -c "
import urllib.request,sys
try:
    print(urllib.request.urlopen('http://$EP/ping', timeout=6).read().decode()[:100])
except Exception as e:
    print('ERR', type(e).__name__, e)
"

echo "=== bff container -> host.docker.internal:8090/health ==="
docker exec sandboxhub-bff python -c "
import urllib.request
try:
    print(urllib.request.urlopen('http://host.docker.internal:8090/health', timeout=6).read().decode()[:100])
except Exception as e:
    print('ERR', type(e).__name__, e)
"

curl -s -o /dev/null "${H[@]}" -X DELETE "$OSB/v1/sandboxes/$SID"
echo "deleted"
