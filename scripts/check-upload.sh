#!/usr/bin/env bash
# Debug execd /files/upload multipart format.
set -uo pipefail
OSB=http://127.0.0.1:8090
KEY=osb-course-key-2026
H=(-H "Content-Type: application/json" -H "OPEN-SANDBOX-API-KEY: $KEY")

RESP=$(curl -s "${H[@]}" -X POST "$OSB/v1/sandboxes" -d '{"image":{"uri":"python:3.12"},"entrypoint":["sleep","infinity"],"timeout":300,"resourceLimits":{"cpu":"1","memory":"1Gi"},"metadata":{"name":"sh-up"}}')
SID=$(echo "$RESP" | jq -r .id)
EP=$(curl -s "${H[@]}" "$OSB/v1/sandboxes/$SID/endpoints/44772" | jq -r .endpoint)
BASE="http://$EP"
echo "base=$BASE"
echo "hello-upload" > /tmp/up.txt

echo "=== A: metadata + file (curl -F) ==="
curl -s -X POST "$BASE/files/upload" \
  -F 'metadata={"path":"/tmp/up.txt","mode":644};type=application/json;filename=metadata.json' \
  -F 'file=@/tmp/up.txt;type=application/octet-stream'
echo
echo "--- read back ---"
curl -s "$BASE/files/download?path=/tmp/up.txt"; echo

echo "=== B: python httpx multipart ==="
python3 - <<PY
import httpx, json
files = {
  "metadata": (None, json.dumps({"path": "/tmp/up2.txt", "mode": 644}), "application/json"),
  "file": ("up2.txt", b"hello-httpx\n", "application/octet-stream"),
}
r = httpx.post("$BASE/files/upload", files=files, timeout=20)
print("status", r.status_code, r.text[:200])
PY

curl -s -o /dev/null "${H[@]}" -X DELETE "$OSB/v1/sandboxes/$SID"
echo "deleted"
