"""SandboxHub CLI.

Usage:
  sandboxhub login --domain 43.135.120.107:8081 --api-key <key> [--tenant <id|slug>]
  sandboxhub whoami
  sandboxhub sandbox list [--state Running]
  sandboxhub sandbox create --image python:3.12 --name demo [--cpu 1] [--memory 1Gi] [--timeout 1800]
  sandboxhub sandbox get <sandbox-id>
  sandboxhub sandbox delete <sandbox-id>
  sandboxhub sandbox pause|resume|renew <sandbox-id> [--timeout 1800]
  sandboxhub exec <sandbox-id> <command...>
  sandboxhub files ls <sandbox-id> [path]
  sandboxhub files cat <sandbox-id> <path>
  sandboxhub files put <sandbox-id> <local> <remote>
  sandboxhub files get <sandbox-id> <remote> <local>
  sandboxhub templates
  sandboxhub agents
  sandboxhub task create --name t --image python:3.12 --command "echo hi" --replicas 2

Config is stored at ~/.sandboxhub/config.json (domain, api_key, tenant_id, tenant_name).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

CONFIG_DIR = Path.home() / ".sandboxhub"
CONFIG_FILE = CONFIG_DIR / "config.json"


def load_config() -> dict:
    if not CONFIG_FILE.exists():
        print("未登录：请先执行 `sandboxhub login --domain <host:port> --api-key <key>`", file=sys.stderr)
        sys.exit(2)
    return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))


def save_config(cfg: dict) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    try:
        os.chmod(CONFIG_FILE, 0o600)
    except Exception:  # noqa: BLE001
        pass


def _request(cfg: dict, method: str, path: str, body: dict | None = None, stream: bool = False):
    url = f"http://{cfg['domain']}/api/v1{path}"
    headers = {"X-API-Key": cfg["api_key"]}
    if cfg.get("tenant_id"):
        headers["X-Tenant-Id"] = cfg["tenant_id"]
    data = json.dumps(body).encode() if body is not None else None
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        resp = urllib.request.urlopen(req, timeout=120)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", "replace")
        print(f"HTTP {exc.code}: {detail}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as exc:
        print(f"连接失败: {exc}", file=sys.stderr)
        sys.exit(1)
    if stream:
        return resp
    raw = resp.read().decode("utf-8", "replace")
    return json.loads(raw) if raw else None


# ---------------------------------------------------------------- commands

def cmd_login(args) -> None:
    cfg = {"domain": args.domain, "api_key": args.api_key}
    me = _request(cfg, "GET", "/me")
    tenants = me.get("tenants", [])
    if not tenants:
        print("该 API Key 无可用租户", file=sys.stderr)
        sys.exit(1)
    chosen = None
    if args.tenant:
        chosen = next((t for t in tenants if t["id"] == args.tenant or t["slug"] == args.tenant), None)
    if chosen is None:
        chosen = tenants[0]
    cfg["tenant_id"] = chosen["id"]
    cfg["tenant_name"] = chosen["name"]
    save_config(cfg)
    print(f"已登录：{me['user'].get('username')} @ {cfg['domain']}")
    print(f"租户：{chosen['name']} ({chosen['slug']})  角色：{chosen['role']}")
    print(f"配置已保存到 {CONFIG_FILE}")


def cmd_whoami(args) -> None:
    cfg = load_config()
    me = _request(cfg, "GET", "/me")
    print(json.dumps({"user": me["user"], "roles": me["roles"], "tenant": cfg.get("tenant_name")}, ensure_ascii=False, indent=2))


def cmd_sandbox_list(args) -> None:
    cfg = load_config()
    params = "?size=100"
    if args.state:
        params += f"&state={args.state}"
    data = _request(cfg, "GET", f"/sandboxes{params}")
    print(f"{'NAME':22} {'STATE':12} {'IMAGE':28} {'ID'}")
    for s in data.get("items", []):
        print(f"{(s.get('name') or '-'):22} {s.get('state',''):12} {(s.get('image') or ''):28} {s.get('sandbox_id')}")


def cmd_sandbox_create(args) -> None:
    cfg = load_config()
    body = {
        "image": args.image,
        "name": args.name,
        "cpu": args.cpu,
        "memory": args.memory,
        "timeout_seconds": args.timeout,
    }
    if args.network_policy == "deny":
        body["network_policy"] = {"defaultAction": "deny", "egress": [{"action": "allow", "target": t} for t in (args.allow or [])]}
    data = _request(cfg, "POST", "/sandboxes", body)
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_sandbox_get(args) -> None:
    cfg = load_config()
    print(json.dumps(_request(cfg, "GET", f"/sandboxes/{args.id}"), ensure_ascii=False, indent=2))


def cmd_sandbox_delete(args) -> None:
    cfg = load_config()
    _request(cfg, "DELETE", f"/sandboxes/{args.id}")
    print(f"已销毁 {args.id}")


def cmd_sandbox_action(args, action: str) -> None:
    cfg = load_config()
    body = {"timeout_seconds": args.timeout} if action == "renew" else {}
    print(json.dumps(_request(cfg, "POST", f"/sandboxes/{args.id}/{action}", body), ensure_ascii=False))


def cmd_exec(args) -> None:
    cfg = load_config()
    command = " ".join(args.command)
    resp = _request(cfg, "POST", f"/sandboxes/{args.id}/commands", {"command": command}, stream=True)
    for raw in resp:
        line = raw.decode("utf-8", "replace").strip()
        if not line:
            continue
        if line.startswith("data:"):
            line = line[5:].strip()
        if not line:
            continue
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue
        if evt.get("type") in ("stdout", "stderr"):
            text = evt.get("text", "")
            sys.stdout.write(text)
            if not text.endswith("\n"):
                sys.stdout.write("\n")
        elif evt.get("type") == "execution_complete":
            print(f"[exit={evt.get('exit_code', 0)}]")


def cmd_files_ls(args) -> None:
    cfg = load_config()
    data = _request(cfg, "GET", f"/sandboxes/{args.id}/files/list?path={args.path}&depth=1")
    for e in data.get("entries", []):
        print(f"{e.get('type',''):10} {e.get('size',0):>10} {e.get('path')}")


def cmd_files_cat(args) -> None:
    cfg = load_config()
    resp = _request(cfg, "GET", f"/sandboxes/{args.id}/files/download?path={args.path}", stream=True)
    sys.stdout.write(resp.read().decode("utf-8", "replace"))


def cmd_files_put(args) -> None:
    cfg = load_config()
    content = Path(args.local).read_bytes()
    import urllib.parse

    q = urllib.parse.quote(args.remote)
    url = f"http://{cfg['domain']}/api/v1/sandboxes/{args.id}/files/upload?path={q}"
    req = urllib.request.Request(
        url, data=content, method="POST",
        headers={"X-API-Key": cfg["api_key"], "X-Tenant-Id": cfg["tenant_id"], "Content-Type": "application/octet-stream"},
    )
    urllib.request.urlopen(req, timeout=120)
    print(f"已上传 {args.local} -> {args.remote}")


def cmd_files_get(args) -> None:
    cfg = load_config()
    resp = _request(cfg, "GET", f"/sandboxes/{args.id}/files/download?path={args.remote}", stream=True)
    Path(args.local).write_bytes(resp.read())
    print(f"已下载 {args.remote} -> {args.local}")


def cmd_templates(args) -> None:
    cfg = load_config()
    for t in _request(cfg, "GET", "/templates"):
        print(f"{t['name']:22} {t['image']:40} cpu={t.get('default_cpu')} mem={t.get('default_memory')}")


def cmd_agents(args) -> None:
    cfg = load_config()
    for a in _request(cfg, "GET", "/agents"):
        print(f"{a['id']:14} {a['name']:18} install: {a['install']}")


def cmd_task_create(args) -> None:
    cfg = load_config()
    data = _request(cfg, "POST", "/tasks", {"name": args.name, "image": args.image, "command": args.command, "replicas": args.replicas})
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_config_show(args) -> None:
    cfg = load_config()
    masked = dict(cfg)
    if masked.get("api_key"):
        masked["api_key"] = masked["api_key"][:10] + "…"
    print(json.dumps(masked, ensure_ascii=False, indent=2))


# ---------------------------------------------------------------- parser

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="sandboxhub", description="SandboxHub CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    lp = sub.add_parser("login", help="使用 API Key 登录并保存配置")
    lp.add_argument("--domain", required=True)
    lp.add_argument("--api-key", required=True)
    lp.add_argument("--tenant", default=None)
    lp.set_defaults(func=cmd_login)

    sub.add_parser("whoami").set_defaults(func=cmd_whoami)
    sub.add_parser("config").set_defaults(func=cmd_config_show)

    sb = sub.add_parser("sandbox").add_subparsers(dest="sub", required=True)
    sl = sb.add_parser("list"); sl.add_argument("--state", default=None); sl.set_defaults(func=cmd_sandbox_list)
    sc = sb.add_parser("create")
    sc.add_argument("--image", required=True)
    sc.add_argument("--name", default=None)
    sc.add_argument("--cpu", default="1")
    sc.add_argument("--memory", default="1Gi")
    sc.add_argument("--timeout", type=int, default=1800)
    sc.add_argument("--network-policy", choices=["none", "deny"], default="none")
    sc.add_argument("--allow", action="append", default=[])
    sc.set_defaults(func=cmd_sandbox_create)
    sg = sb.add_parser("get"); sg.add_argument("id"); sg.set_defaults(func=cmd_sandbox_get)
    sd = sb.add_parser("delete"); sd.add_argument("id"); sd.set_defaults(func=cmd_sandbox_delete)
    for act in ("pause", "resume", "renew"):
        ap = sb.add_parser(act); ap.add_argument("id")
        ap.add_argument("--timeout", type=int, default=1800)
        ap.set_defaults(func=lambda a, act=act: cmd_sandbox_action(a, act))

    ex = sub.add_parser("exec", help="在沙箱中执行命令"); ex.add_argument("id"); ex.add_argument("command", nargs=argparse.REMAINDER); ex.set_defaults(func=cmd_exec)

    fl = sub.add_parser("files").add_subparsers(dest="sub", required=True)
    f1 = fl.add_parser("ls"); f1.add_argument("id"); f1.add_argument("path", nargs="?", default="/"); f1.set_defaults(func=cmd_files_ls)
    f2 = fl.add_parser("cat"); f2.add_argument("id"); f2.add_argument("path"); f2.set_defaults(func=cmd_files_cat)
    f3 = fl.add_parser("put"); f3.add_argument("id"); f3.add_argument("local"); f3.add_argument("remote"); f3.set_defaults(func=cmd_files_put)
    f4 = fl.add_parser("get"); f4.add_argument("id"); f4.add_argument("remote"); f4.add_argument("local"); f4.set_defaults(func=cmd_files_get)

    sub.add_parser("templates").set_defaults(func=cmd_templates)
    sub.add_parser("agents").set_defaults(func=cmd_agents)

    tk = sub.add_parser("task").add_subparsers(dest="sub", required=True)
    tc = tk.add_parser("create")
    tc.add_argument("--name", required=True)
    tc.add_argument("--image", default="python:3.12")
    tc.add_argument("--command", default="echo hi")
    tc.add_argument("--replicas", type=int, default=1)
    tc.set_defaults(func=cmd_task_create)

    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
