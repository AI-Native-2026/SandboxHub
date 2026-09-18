#!/usr/bin/env bash
# Diagnose sandbox endpoint networking.
set -uo pipefail
OSB=http://127.0.0.1:8090
KEY=osb-course-key-2026
H=(-H "Content-Type: application/json" -H "OPEN-SANDBOX-API-KEY: $KEY")

RESP=$(curl -s "${H[@]}" -X POST "$OSB/v1/sandboxes" -d '{"image":{"uri":"python:3.12"},"entrypoint":["sleep","infinity"],"timeout":300,"resourceLimits":{"cpu":"1","memory":"1Gi"},"metadata":{"name":"sh-diag"}}')
SID=$(echo "$RESP" | jq -r .id)
echo "create: $RESP" | head -c 200; echo
EP=$(curl -s "${H[@]}" "$OSB/v1/sandboxes/$SID/endpoints/44772" | jq -r .endpoint)
HOSTPORT=$(echo "$EP" | cut -d: -f2 | cut -d/ -f1)
IP=$(echo "$EP" | cut -d: -f1)
echo "sid=$SID ep=$EP ip=$IP hostport=$HOSTPORT"

echo "=== networks ==="
docker network ls
echo "--- sandbox container ip ---"
docker ps --format '{{.Names}} {{.Image}}' | grep -i "$SID" || docker ps --format '{{.Names}} {{.Image}}' | head -5

echo "=== host -> 127.0.0.1:$HOSTPORT/ping ==="
curl -s -o /dev/null -w '%{http_code}\n' --max-time 6 "http://127.0.0.1:$HOSTPORT/ping"
echo "=== host -> $EP/ping ==="
curl -s -o /dev/null -w '%{http_code}\n' --max-time 6 "http://$EP/ping"
echo "=== bff -> host.docker.internal:$HOSTPORT/ping ==="
docker exec sandboxhub-bff python -c "
import urllib.request
for url in ['http://host.docker.internal:$HOSTPORT/ping','http://$IP:$HOSTPORT/ping']:
    try: print(url, '->', urllib.request.urlopen(url, timeout=6).read().decode()[:60])
    except Exception as e: print(url, '-> ERR', type(e).__name__, e)
"
curl -s -o /dev/null "${H[@]}" -X DELETE "$OSB/v1/sandboxes/$SID"
echo "deleted $SID"
