# SandboxHub 架构决策记录（ADR）

> 状态：均已 Accepted。任何变更需追加新 ADR 并标注取代关系。

| ID | 背景 | 决策 | 影响 |
|---|---|---|---|
| ADR-001 定位 | 需要一个对内平台承载 AI 代码执行 | **内部 PaaS**，服务公司内 AI 应用/团队 | 不做商业化计费；配额与成本用于内部治理 |
| ADR-002 底座 | 自研沙箱成本高、风险大 | 基于 **OpenSandbox**，**零改动核心** | 定制全部收敛在平台层；升级跟随上游 Release（cosign 校验） |
| ADR-003 多租户 | 上游 `[tenants]` 仅 K8s（C1），单 VM 无 K8s | **平台层逻辑多租户**（`tenant_id` 强作用域） | BFF 强制租户过滤与授权；上游用单一 Key + metadata 打标 |
| ADR-004 认证 | 需企业级 SSO | **Keycloak（OIDC，Auth Code + PKCE）** | 认证在 Keycloak，**授权/租户归属以平台 DB 为准** |
| ADR-005 运行时 | 仅一台 VM | **Docker 运行时 + gVisor** | 上游原生 Pool / Pause-Resume 快照（K8s）不可用；后续可选 k3d 进阶轨 |
| ADR-006 前端 | 面向开发者友好 + 运维管理 | **React 18 + TS + Vite + Ant Design 5** | 暗色主题；企业级表格/表单/权限组件齐全 |
| ADR-007 BFF | UI 需统一鉴权/审计/聚合 | **Python FastAPI + SQLAlchemy + Alembic** | 与上游同栈，可复用官方 SDK |
| ADR-008 部署 | 单 VM | **Docker Compose，HTTP 内网** | 端口规划见 ADR-011；生产化再叠加 TLS |
| ADR-009 数据 | 平台元数据 | **PostgreSQL + Redis** | 上游 server 自身仍用 SQLite（C3，不改） |
| ADR-010 VM 约束 | 已有 discoveryx 项目 | **允许停服务，禁止删文件** | 复用/错开端口；必要时停非必要服务 |
| ADR-011 端口 | 避免与 8000/8080/6379 冲突 | web **8081** · bff **8001** · keycloak **8180** · pg **5433** · redis **6380** · osb **8090** · 沙箱 **40000–60000** | 见 `ops.md` |
| ADR-012 密钥边界 | 上游密钥敏感 | 上游 `OPEN-SANDBOX-API-KEY` / `X-EXECD-ACCESS-TOKEN` **仅 BFF 内部持有** | 绝不透传浏览器；浏览器只持有 Keycloak JWT |
| ADR-013 授权模型 | 角色 + 租户 | 角色 `platform-admin`/`tenant-admin`/`developer`/`viewer`；租户归属在平台 `memberships` | 前端按角色渲染，后端二次校验 |
| ADR-014 实时通道 | 终端/日志/指标 | 终端 **WebSocket(PTY)**；日志/事件/指标 **SSE** | 统一经 BFF 代理鉴权 |
| ADR-015 模板 | 降低上手成本 | 平台级**模板目录**（python/code-interpreter/playwright/chrome/desktop/vscode） | 向导一键带出默认配置 |

## 上游硬约束（贯穿设计）

| 编号 | 约束 | 来源 |
|---|---|---|
| C1 | 多租户仅 K8s；Docker 配 `[tenants]` 拒绝启动 | `docs/guides/multi-tenancy.md` |
| C2 | 启用 `[tenants]` 必须移除 `server.api_key` | 同上 |
| C3 | Server 持久化仅 SQLite → 单活 | `server/configuration.md` |
| C4 | Pool API 非租户隔离 | `docs/guides/multi-tenancy.md` |
| C5 | `gvisor + networkPolicy` 不兼容（无 nat 表，400） | `docs/guides/secure-container.md` |
| C6 | Ingress 面向 K8s；Docker 仅 direct | `server/configuration.md` |
