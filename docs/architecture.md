# SandboxHub 系统架构

## 1. 总览

```
Browser ──HTTP──> nginx(8081) ──/api, /ws──> SandboxHub BFF(8001) ──> OpenSandbox Server(8090) ──> 沙箱容器(gVisor)
                      └─ 静态资源                    │
                                                     ├─ Keycloak(8180)  OIDC/JWKS
                                                     ├─ PostgreSQL(5433) 元数据/审计/租户
                                                     └─ Redis(6380)  缓存/限流
```

## 2. 关键原则
- **BFF 是唯一出口**：UI 只对接 BFF；BFF 统一鉴权、授权、租户作用域、审计、聚合
- **零改动核心**：不改 OpenSandbox；通过其 REST API + SDK 对接
- **密钥边界**：上游 `OPEN-SANDBOX-API-KEY` / `X-EXECD-ACCESS-TOKEN` 仅在 BFF（ADR-012）
- **逻辑多租户**：平台 DB 的 `tenant_id` 强作用域；上游单 Key + metadata 打标

## 3. 组件职责

### 3.1 Web（apps/web）
React SPA：路由/权限、设计系统、页面与组件、实时通道客户端。

### 3.2 BFF（apps/bff）
| 模块 | 职责 |
|---|---|
| auth | 校验 Keycloak JWT（JWKS）、解析用户 |
| rbac | 角色/租户授权、作用域过滤 |
| tenants | 租户/成员/配额 |
| sandboxes | 封装 lifecycle API、平台索引、编排 |
| terminal/exec | 代理 execd（PTY WS、命令 SSE、code） |
| files | 代理 execd files/directories、上传下载 |
| metrics | 代理 execd metrics / watch |
| policies | egress policy 读写 |
| templates/snapshots | 模板目录、快照索引 |
| quota/usage | 配额校验、用量采样 |
| audit | 写操作审计落库 |
| admin | 管理端聚合 |
| overview | 概览聚合 |

### 3.3 上游 OpenSandbox
lifecycle `/v1/*`、execd `/command|/code|/files|/metrics`、egress `/policy`、diagnostic `/diagnostics/*`。

## 4. 关键流程

### 4.1 创建沙箱
1. Web → BFF `POST /sandboxes`（tenant 作用域）
2. BFF 校验配额/权限 → 调 OpenSandbox `POST /v1/sandboxes`
3. BFF 写 `sandbox_records`（tenant/owner/template）+ 审计
4. 返回 sandbox_id/状态；前端轮询或订阅状态

### 4.2 终端
1. Web → BFF `WS /sandboxes/{id}/terminal`
2. BFF 校验租户/权限 → 解析 execd 端点（端口 44772）
3. BFF 与 execd `/pty/{session}/ws` 建立 WS，双向透传二进制帧
4. viewer 只读模式支持

### 4.3 命令（SSE）
BFF 调 execd `POST /command`，将 SSE 事件流原样转发（经鉴权）。

### 4.4 文件
BFF 调 execd `/files/*`、`/directories/*`；上传 multipart、下载流式（支持 Range）。

### 4.5 出网策略
BFF 调 lifecycle `/sandboxes/{id}/networkpolicy`（或 egress sidecar `/policy`）。

## 5. 实时通道
| 通道 | 协议 | 端点 |
|---|---|---|
| 终端 | WS | `WS /api/v1/sandboxes/{id}/terminal` |
| 命令/代码 | SSE | `POST /api/v1/sandboxes/{id}/commands` |
| 指标 | SSE | `GET /api/v1/sandboxes/{id}/metrics/watch` |
| 事件 | SSE | `GET /api/v1/sandboxes/{id}/events` |

## 6. 安全
- 浏览器仅持 Keycloak JWT（短时）；BFF 校验签名/受众/过期
- 所有写操作审计；敏感字段脱敏
- 端点代理经 BFF，不暴露沙箱端口给浏览器直连

## 7. 部署（见 ops.md）
Docker Compose：postgres · redis · keycloak · bff · web(nginx)；复用 opensandbox-server。
