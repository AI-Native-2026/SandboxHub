# SandboxHub 运维与部署

## 1. 环境
| 环境 | 说明 |
|---|---|
| dev | 本地/VM 开发，HTTP |
| staging | VM 预发，HTTP |
| prod | 内网，后续叠加 TLS |

本期在单 VM（`43.135.120.107`）以 HTTP 部署。

## 2. 端口规划（ADR-011）
| 服务 | 端口 |
|---|---|
| web (nginx) | 8081 |
| bff | 8001 |
| keycloak | 8180 |
| postgres | 5433 |
| redis | 6380 |
| opensandbox-server | 8090 |
| 沙箱端口段 | 40000–60000 |
| 既有 discoveryx | 8000/8080/6379（保持，必要时停） |

## 3. 部署拓扑（Docker Compose）
```
compose network: sandboxhub
  postgres  (volume: pgdata)
  redis
  keycloak  (import deploy/keycloak/realm.json)
  bff       (depends_on: postgres, redis, keycloak)
  web       (nginx: 静态资源 + /api 反代 bff)
```
OpenSandbox server 复用宿主既有部署（8090，挂载 docker.sock）。

## 4. 配置与密钥
- `.env`（gitignore）：数据库口令、Keycloak admin、上游 API Key 等
- `.env.example` 提供占位
- 浏览器不持有上游密钥（ADR-012）

## 5. CI/CD
- CI：lint（ruff/eslint）、单测（pytest/vitest）、构建、镜像扫描
- CD：构建镜像 → 推送 Harbor → `docker compose up -d` → 健康检查 → 回滚策略
- 迁移：Alembic 自动升级

## 6. 可观测
- BFF：结构化日志、OTel 指标（请求/沙箱创建）、健康端点 `/healthz`
- OpenSandbox：`[otel]` 导出、Controller Prometheus（K8s 轨）
- 平台大盘：租户/沙箱用量、错误率、延迟

## 7. 备份
- PostgreSQL 定时 dump + 恢复演练
- 关键配置（realm、.env 模板、compose）纳入版本库

## 8. 应急预案
| 场景 | 处置 |
|---|---|
| BFF 不可用 | 重启容器；查日志；回滚镜像 |
| Keycloak 不可用 | 已签发 JWT 在有效期内可继续；恢复 Keycloak |
| OpenSandbox server 故障 | 重启；存量沙箱 TTL 定时器自动恢复（C3 单活） |
| 沙箱资源耗尽 | 调低租户配额；清理孤儿沙箱 |
| 端口冲突 | 按 ADR-011 调整并记录 |

## 9. SLO（单 VM 基线）
- BFF 可用性 ≥ 99.5%
- 创建 API P95 < 3s（不含镜像拉取）
- 审计落库成功率 100%
