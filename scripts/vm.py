#!/usr/bin/env python3
"""Tiny SSH helper for the OpenSandbox course test VM.

Usage:
  python env/vm.py run  "uname -a"
  python env/vm.py sudo "apt-get update"
  python env/vm.py put  <local> <remote>
  python env/vm.py get  <remote> <local>
  python env/vm.py setup-key
  python env/vm.py audit

Auth: uses secrets/vm_key if present, otherwise the password from .env.
Secrets live in opensandbox-course/.env (gitignored).
"""
from __future__ import annotations

import os
import sys
import stat
from pathlib import Path

import paramiko

ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
KEY_FILE = ROOT / "secrets" / "vm_key"


def load_env() -> dict[str, str]:
    env: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    for k in ("VM_HOST", "VM_USER", "VM_PASS", "DEEPSEEK_API_KEY", "DEEPSEEK_BASE_URL", "DEEPSEEK_MODEL"):
        if os.environ.get(k):
            env[k] = os.environ[k]
    return env


def connect(env: dict[str, str]) -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    kwargs = dict(hostname=env["VM_HOST"], username=env["VM_USER"], timeout=20, banner_timeout=30, auth_timeout=30)
    if KEY_FILE.exists():
        client.connect(key_filename=str(KEY_FILE), **kwargs)
    else:
        client.connect(password=env["VM_PASS"], **kwargs)
    return client


def run(client: paramiko.SSHClient, cmd: str, timeout: int = 600) -> int:
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout, get_pty=False)
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    rc = stdout.channel.recv_exit_status()
    if out:
        sys.stdout.write(out)
    if err:
        sys.stderr.write(err)
    return rc


def sudo(client: paramiko.SSHClient, cmd: str, password: str, timeout: int = 1800) -> int:
    wrapped = "sudo -S -p '' bash -lc " + shlex_quote(cmd)
    stdin, stdout, stderr = client.exec_command(wrapped, timeout=timeout, get_pty=False)
    stdin.write(password + "\n")
    stdin.flush()
    out = stdout.read().decode("utf-8", "replace")
    err = stderr.read().decode("utf-8", "replace")
    rc = stdout.channel.recv_exit_status()
    if out:
        sys.stdout.write(out)
    if err:
        sys.stderr.write(err)
    return rc


def shlex_quote(s: str) -> str:
    return "'" + s.replace("'", "'\\''") + "'"


def _mkdirs(sftp: paramiko.SFTPClient, remote_dir: str) -> None:
    parts = remote_dir.strip("/").split("/")
    cur = ""
    for part in parts:
        cur += "/" + part
        try:
            sftp.stat(cur)
        except IOError:
            sftp.mkdir(cur)


def sync_dir(client: paramiko.SSHClient, local_dir: str, remote_dir: str) -> None:
    sftp = client.open_sftp()
    local = Path(local_dir).resolve()
    count = 0
    for p in sorted(local.rglob("*")):
        if any(seg in (".git", "__pycache__", ".uv-cache") for seg in p.parts):
            continue
        rel = p.relative_to(local).as_posix()
        rp = remote_dir.rstrip("/") + "/" + rel
        if p.is_dir():
            _mkdirs(sftp, rp)
        else:
            _mkdirs(sftp, str(Path(rp).parent.as_posix()))
            sftp.put(str(p), rp)
            count += 1
    sftp.close()
    print(f"SYNC {local} -> {remote_dir} ({count} files)")


def setup_key(client: paramiko.SSHClient) -> None:
    KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not KEY_FILE.exists():
        key = paramiko.Ed25519Key.generate() if hasattr(paramiko.Ed25519Key, "generate") else None
        if key is None:
            key = paramiko.RSAKey.generate(3072)
        key.write_private_key_file(str(KEY_FILE))
        try:
            os.chmod(KEY_FILE, stat.S_IRUSR | stat.S_IWUSR)
        except Exception:
            pass
    pub = None
    for cls in (paramiko.Ed25519Key, paramiko.RSAKey, paramiko.ECDSAKey):
        try:
            k = cls.from_private_key_file(str(KEY_FILE))
            pub = f"{k.get_name()} {k.get_base64()}"
            break
        except Exception:
            continue
    if pub is None:
        raise SystemExit("could not derive public key")
    cmd = (
        "mkdir -p ~/.ssh && chmod 700 ~/.ssh && "
        f"grep -qxF {shlex_quote(pub)} ~/.ssh/authorized_keys 2>/dev/null || echo {shlex_quote(pub)} >> ~/.ssh/authorized_keys; "
        "chmod 600 ~/.ssh/authorized_keys && echo KEY_INSTALLED"
    )
    rc = run(client, cmd)
    if rc != 0:
        raise SystemExit("failed to install key")


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    env = load_env()
    action = sys.argv[1]
    client = connect(env)
    try:
        if action == "run":
            return run(client, sys.argv[2])
        if action == "sudo":
            return sudo(client, sys.argv[2], env["VM_PASS"])
        if action == "put":
            sftp = client.open_sftp()
            sftp.put(sys.argv[2], sys.argv[3])
            sftp.close()
            print(f"PUT {sys.argv[2]} -> {sys.argv[3]}")
            return 0
        if action == "get":
            sftp = client.open_sftp()
            sftp.get(sys.argv[2], sys.argv[3])
            sftp.close()
            print(f"GET {sys.argv[2]} -> {sys.argv[3]}")
            return 0
        if action == "sync":
            sync_dir(client, sys.argv[2], sys.argv[3])
            return 0
        if action == "setup-key":
            setup_key(client)
            return 0
        if action == "audit":
            script = (ROOT / "env" / "audit.sh").read_text(encoding="utf-8")
            return run(client, "bash -s <<'OSB_AUDIT_EOF'\n" + script + "\nOSB_AUDIT_EOF")
        print(f"unknown action: {action}")
        return 2
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())
