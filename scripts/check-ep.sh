#!/usr/bin/env bash
# Determine the working execd base URL from the BFF container.
set -uo pipefail
OSB=http://127.0.0.1:8090
KEY=osb-course-key-2026
H=(-H "Content-Type: application/json" -H "OPEN-SANDBOX-API-KEY: $KEY")

RESP=$(curl -s "${H[@]}" -X POST "$OSB/v1/sandboxes" -d '{"image":{"uri":"python:3.12"},"entrypoint":["sleep","infinity"],"timeout":300,"resourceLimits":{"cpu":"1","memory":"1Gi"},"metadata":{"name":"sh-ep"}}')
SID=$(echo "$RESP" | jq -r .id)
EP=$(curl -s "${H[@]}" "$OSB/v1/sandboxes/$SID/endpoints/44772" | jq -r .endpoint)
IP=$(echo "$EP" | cut -d: -f1); PORT=$(echo "$EP" | cut -d: -f2 | cut -d/ -f1)
echo "sid=$SID ep=$EP ip=$IP port=$PORT"

docker exec -i sandboxhub-bff python - <<PY
import urllib.request
urls = [
  "http://host.docker.internal:$PORT/ping",
  "http://host.docker.internal:$PORT/proxy/44772/ping",
  "http://$IP:$PORT/ping",
  "http://$IP:$PORT/proxy/44772/ping",
]
for u in urls:
    try:
        r = urllib.request.urlopen(u, timeout=6)
        print("OK ", r.status, u, repr(r.read()[:40]))
    except Exception as e:
        print("ERR", type(e).__name__, u, str(e)[:60])
PY

curl -s -o /dev/null "${H[@]}" -X DELETE "$OSB/v1/sandboxes/$SID"
echo "deleted"
