# SandboxHub 测试与验收策略

## 1. 分层测试
| 层 | 工具 | 范围 |
|---|---|---|
| BFF 单测 | pytest | services/validators/rbac/quota |
| BFF 集成 | pytest + httpx | 路由 + DB（testcontainers 或 sqlite/pg） |
| 契约测试 | pytest + 上游 OpenAPI | BFF↔OpenSandbox 字段一致性 |
| 前端组件 | Vitest + Testing Library | 组件/状态/权限渲染 |
| E2E | Playwright | 用户旅程（见下） |
| 性能 | k6 / locust | 创建并发、终端并发、大文件 |
| 安全 | 手工 + 用例 | 越权、注入、密钥不透传、CORS |

## 2. E2E 与用户旅程对齐
每个 `E2E-*` 用例对应 `docs/user-journeys.md` 的旅程 ID，是里程碑完成判据。

| 用例 | 旅程 | 关键断言 |
|---|---|---|
| E2E-D1 | J-D1 | 登录后 `/me` 与租户切换器可见 |
| E2E-D2 | J-D2 | 模板创建→Running→详情含 id/端点 |
| E2E-D3 | J-D3 | 终端输出 `Python`；命令 SSE 含退出码 |
| E2E-D4 | J-D4 | 上传→编辑→下载内容一致 |
| E2E-D5 | J-D5 | 代理端点返回 200 |
| E2E-D6 | J-D6 | 指标刷新；事件时间线非空 |
| E2E-D7 | J-D7 | allow 可达 / deny 不可达；gvisor 组合禁用 |
| E2E-D8 | J-D8 | pause→Paused→resume→Running→kill |
| E2E-D9 | J-D9 | 快照创建成功并可查 |
| E2E-D10 | J-D10 | 个人 Key 可用并记录 last_used |
| E2E-D11 | J-D11 | 越权返回 403；错误可读 |
| E2E-T1..4 | J-T1..4 | 成员/配额/用量/Key 轮换 |
| E2E-P1..7 | J-P1..7 | 租户/模板/策略/凭据/审计/大盘/设置 |
| E2E-A1 | J-A1 | 只读角色无写入口 |

## 3. 质量门禁
- 每个里程碑 PR 必须：lint 通过、单测通过、对应 E2E 通过
- 关键旅程回归：每次部署后跑全套 E2E
- 覆盖率目标：BFF ≥ 70%，前端关键组件 ≥ 60%

## 4. 测试数据
- 固定测试租户 `demo`、测试用户（Keycloak 预置）
- 测试模板（python:3.12 等）
- 清理：用例结束销毁沙箱

## 5. 验收报告模板
- 版本/时间/环境
- 用例通过矩阵（E2E-*）
- 已知问题与豁免
- 结论（通过/不通过）
