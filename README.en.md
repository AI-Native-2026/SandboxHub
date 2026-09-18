# SandboxHub

**An AI agent sandbox platform** built on [OpenSandbox](https://github.com/alibaba/OpenSandbox) with **zero changes to the upstream core**. A single PaaS for **developer self-service** and **ops / tenant governance**: create sandboxes, run commands, manage files, host agents, govern quotas, audit and observe — all from one entry point.

[简体中文](README.md) · **English**

---

## Preview

Install and run the OpenCode coding agent inside a sandbox terminal with one click (Agent Hosting):

![SandboxHub · OpenCode Agent hosting](imgs/Agent.png)

> The sandbox detail page has seven tabs: **Overview / Runtime / Data / Network / Observability / Snapshots / Security**. The screenshot shows the embedded web terminal on the **Runtime** tab with the OpenCode coding agent installed and running inside the sandbox.

---

## Live Demo

- Entry point: **http://43.135.120.107:8081** (single HTTP port; nginx proxies the SPA plus `/api` and `/realms`)
- Test accounts (password `Passw0rd!` for all):

| Account | Role | Description |
|---|---|---|
| `admin` | platform-admin | Platform admin; sees governance & admin menus |
| `tenantadmin` | tenant-admin | Manages tenant members and quotas |
| `dev1` | developer | Self-service sandbox create/operate |
| `viewer` | viewer | Read-only; no write entry points |

> The top bar offers single-button toggles for **theme (dark/light)** and **language (中 / EN)**. Multi-tenancy is switched via the **tenant** dropdown.

---

## Capabilities

### Developer self-service
- **Sandbox lifecycle**: create (templates / custom images / resource limits), pause, renew, destroy; batch operations in the list.
- **Runtime**: embedded web terminal (PTY over WebSocket with session recording & replay), streaming command execution (NDJSON), file browse / upload / download / inline edit.
- **Template marketplace**: built-in Python / Node images, one-click parameterized creation.
- **Getting started / API keys**: personal API keys (with expiry) for scripts and SDKs.
- **Tasks & artifacts**: batch-create sandboxes and run commands (eval / batch); collect and download artifacts.
- **Agent hosting**: one-click sandbox with a coding agent installed and running (e.g. OpenCode).

### Ops & governance
- **Multi-tenancy & RBAC**: logical multi-tenancy at the platform layer with enforced scoping in the BFF; custom roles and permissions.
- **Quotas & approvals**: tenant resource limits and usage; large quotas / egress allowlists / privileged templates go through the approval center.
- **Credential vault**: store outbound credential references, injected into sandboxes without exposing plaintext.
- **Network policy templates**: reusable egress allow/deny rule templates.
- **Audit & observability**: operation audit, real-time status event stream, CPU / memory time series, resource pools and platform usage overview.
- **Session recording**: terminal sessions persisted and replayed on a timeline.

### CLI
`apps/cli` provides the `sandboxhub` command. Log in with an API key and manage sandboxes, exec, files, templates, agents and tasks.

---

## Architecture

```
Browser → nginx(8081) ─┬─ /            → web (React SPA)
                       └─ /api,/realms → BFF(8001) ─→ OpenSandbox Server(8090) → sandbox (gVisor)
                                           ├─ Keycloak(8180)   auth / OIDC
                                           ├─ PostgreSQL(5433) platform metadata
                                           └─ Redis(6380)      session / cache
```

| Component | Port | Notes |
|---|---|---|
| web | 8081 | nginx + React 18 + Vite + Ant Design 5 + ECharts |
| bff | 8001 | FastAPI: auth, RBAC, tenants, audit, sandboxes, terminal, exec, files, metrics, templates, snapshots, API keys, approvals, credentials, policies, recordings, pools, tasks, artifacts, agents |
| keycloak | 8180 | OIDC (realm `sandboxhub`) |
| postgres | 5433 | Platform metadata |
| redis | 6380 | Session & cache |
| opensandbox-server | 8090 | Upstream sandbox control plane (unchanged) |
| sandboxes | 40000–60000 | Running isolated sandbox instances |

---

## Layout

```
apps/web/      React frontend (~20 pages, four nav groups)
apps/bff/      FastAPI backend (BFF + platform services)
apps/cli/      sandboxhub command-line tool
packages/      api-client (generated) / ui (design system)
deploy/        docker-compose / nginx / keycloak / sandbox.toml
docs/          Formal docs (decisions / PRD / architecture / data model / API / UI / ops / test / acceptance)
scripts/       Dev & ops scripts (vm.py SSH helper, e2e-suite.py, ...)
imgs/          README screenshots
```

---

## Quick Start (Deploy)

Prerequisites: a Linux VM with Docker and Compose, SSH access, and a configured `.env`.

```bash
# 1) Sync code to the VM (use the scripts/vm.py helper locally)
python scripts/vm.py sync apps deploy /home/ubuntu/SandboxHub

# 2) Build and start the full stack
cd deploy
docker compose up -d --build

# 3) Open
#    http://<VM_IP>:8081
```

See [docs/ops.md](docs/ops.md) for detailed deploy, upgrade and troubleshooting.

---

## CLI Usage

```bash
# Install (on the VM or locally)
uv tool install ./apps/cli        # or: pip install ./apps/cli

# Log in and verify
sandboxhub login --domain http://<VM_IP>:8081 --api-key <API_KEY>
sandboxhub whoami

# Common commands
sandboxhub sandbox list
sandboxhub exec <sandbox-id> python -c "print('hello')"
sandboxhub files put <sandbox-id> ./local.txt /tmp/local.txt
sandboxhub templates
sandboxhub agents
```

---

## Documentation

| Doc | Content |
|---|---|
| [docs/decisions.md](docs/decisions.md) | Architecture decision records (ADRs) and upstream hard constraints |
| [docs/user-journeys.md](docs/user-journeys.md) | User journeys and acceptance cases (E2E-aligned) |
| [docs/charter.md](docs/charter.md) | Project charter |
| [docs/prd.md](docs/prd.md) | Product requirements |
| [docs/architecture.md](docs/architecture.md) | System architecture |
| [docs/data-model.md](docs/data-model.md) | Data model |
| [docs/api.md](docs/api.md) | BFF API contract |
| [docs/ui.md](docs/ui.md) | UI design spec |
| [docs/ops.md](docs/ops.md) | Deploy & operations |
| [docs/test.md](docs/test.md) | Test & acceptance strategy |
| [docs/implementation-notes.md](docs/implementation-notes.md) | Key implementation notes and upstream constraints |
| [docs/acceptance-report.md](docs/acceptance-report.md) | Acceptance report |
| [docs/user-manual.md](docs/user-manual.md) | User manual |

---

## Design Principles

- **Zero changes to the upstream core** (ADR-002): all platform capabilities live in the BFF.
- **Logical multi-tenancy, enforced scoping in the BFF** (ADR-003): tenant isolation is enforced at the application layer.
- **Upstream secrets never leave the BFF** (ADR-012): credentials are injected into sandboxes, never exposed to the frontend.
- **Every milestone is accepted by passing user-journey E2E** ([docs/test.md](docs/test.md)).

---

## Acceptance Status

- Version: **v0.1** — designed, developed, deployed and accepted on a single Linux VM.
- E2E: **PASS=11 FAIL=0** (`scripts/e2e-suite.py`). See [docs/acceptance-report.md](docs/acceptance-report.md).
