"""Measure recording persistence delay (runs in BFF container)."""
import asyncio
import base64
import json
import os
import time
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
    sb = req("POST", "/sandboxes", {"image": "python:3.12", "name": "rec-t", "cpu": "1", "memory": "1Gi", "timeout_seconds": 600})
    sid = sb["sandbox_id"]
    pty = req("POST", f"/sandboxes/{sid}/pty", {"cwd": "/tmp"})
    sess = pty["session_id"]
    url = (f"ws://127.0.0.1:8001/api/v1/sandboxes/{sid}/terminal"
           f"?session_id={sess}&token={TOK}&tenant={TEN}&record=1&name=rec-t")
    async with websockets.connect(url, max_size=None) as ws:
        await asyncio.sleep(1)
        await ws.send(b"\x00echo T-MARKER\n")
        await asyncio.sleep(2)
    closed = time.time()
    print("ws closed at t=0")
    found = None
    for i in range(60):
        await asyncio.sleep(0.5)
        recs = req("GET", "/recordings")
        mine = [r for r in recs if r["name"] == "rec-t"]
        if mine:
            found = mine[0]
            print("persisted after %.1fs" % (time.time() - closed))
            break
    if found:
        full = req("GET", f"/recordings/{found['id']}")
        txt = "".join(base64.b64decode(c["b"]).decode("utf-8", "replace") for c in full["data"])
        print("MARKER present:", "T-MARKER" in txt)
        print("sample:", txt[:160].replace("\n", "\\n"))
    else:
        print("NOT persisted within 30s")
    req("DELETE", f"/sandboxes/{sid}")


asyncio.run(main())
