"""List and clean up sandboxes created during testing."""
import json
import os
import urllib.parse
import urllib.request

WEB = "http://host.docker.internal:8081"
API = "http://127.0.0.1:8001/api/v1"
PREFIXES = ("suite-", "rec-", "policy-test", "pol-", "agent-opencode")


def token(user):
    data = urllib.parse.urlencode(
        {"grant_type": "password", "client_id": "sandboxhub-web", "username": user, "password": "Passw0rd!"}
    ).encode()
    req = urllib.request.Request(
        WEB + "/realms/sandboxhub/protocol/openid-connect/token", data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    return json.loads(urllib.request.urlopen(req, timeout=30).read())["access_token"]


def call(tok, ten, method, path, body=None):
    data = json.dumps(body).encode() if body is not None else None
    h = {"Authorization": "Bearer " + tok, "Content-Type": "application/json"}
    if ten:
        h["X-Tenant-Id"] = ten
    req = urllib.request.Request(API + path, data=data, method=method, headers=h)
    raw = urllib.request.urlopen(req, timeout=120).read()
    return json.loads(raw) if raw else None


TOK = token("admin")
TEN = call(TOK, None, "GET", "/me")["tenants"][0]["id"]
items = call(TOK, TEN, "GET", "/sandboxes?size=200").get("items", [])
print("total sandboxes:", len(items))
for it in items:
    print(" -", it["name"], it["sandbox_id"][:8], it["state"])
for it in items:
    if it["name"].startswith(PREFIXES):
        try:
            call(TOK, TEN, "DELETE", f"/sandboxes/{it['sandbox_id']}")
            print("deleted", it["name"], it["sandbox_id"][:8])
        except Exception as e:
            print("delete failed", it["name"], str(e)[:80])
print("DONE")
