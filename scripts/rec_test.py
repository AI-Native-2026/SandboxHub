"""Recording test — runs inside the BFF container (has websockets).

Env: TOK (Keycloak JWT), TEN (tenant id)
"""
import asyncio
import base64
import json
import os
import urllib.request

import websockets

BASE = "http://127.0.0.1:8001/api/v1"
TOK = os.environ["TOK"]
TEN = os.environ["TEN"]


def req(method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(
        BASE + path, data=data, method=method,
        headers={"Authorization": "Bearer " + TOK, "X-Tenant-Id": TEN, "Content-Type": "application/json"},
    )
    raw = urllib.request.urlopen(r, timeout=60).read()
    return json.loads(raw) if raw else None


async def main():
    sb = req("POST", "/sandboxes", {"image": "python:3.12", "name": "rec-test", "cpu": "1", "memory": "1Gi", "timeout_seconds": 600})
    sid = sb["sandbox_id"]
    print("sandbox:", sid)
    pty = req("POST", f"/sandboxes/{sid}/pty", {"cwd": "/tmp"})
    sess = pty["session_id"]
    url = (f"ws://127.0.0.1:8001/api/v1/sandboxes/{sid}/terminal"
           f"?session_id={sess}&token={TOK}&tenant={TEN}&record=1&name=rectest")
    async with websockets.connect(url, max_size=None) as ws:
        await asyncio.sleep(2)
        await ws.send(b"\x00echo rec-test-123\n")
        end = asyncio.get_event_loop().time() + 5
        while asyncio.get_event_loop().time() < end:
            try:
                await asyncio.wait_for(ws.recv(), timeout=1)
            except asyncio.TimeoutError:
                pass
    await asyncio.sleep(4)  # allow the recording to be persisted
    recs = req("GET", "/recordings")
    print("recordings:", len(recs))
    ok = False
    if recs:
        r = req("GET", f"/recordings/{recs[0]['id']}")
        txt = "".join(base64.b64decode(c["b"]).decode("utf-8", "replace") for c in r["data"])
        ok = "rec-test-123" in txt
        print("replay contains rec-test-123:", ok)
        print("sample:", txt[:160].replace("\n", "\\n"))
    req("DELETE", f"/sandboxes/{sid}")
    print("RECORDING_OK" if ok else "RECORDING_FAIL")


asyncio.run(main())
