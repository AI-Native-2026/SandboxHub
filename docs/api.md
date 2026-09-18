# SandboxHub BFF API 契约

- 前缀：`/api/v1`
- 鉴权：`Authorization: Bearer <Keycloak JWT>`
- 契约由 BFF 生成 OpenAPI，前端用 orval 生成类型（`packages/api-client`）
- 上游密钥仅 BFF 内部使用（ADR-012）

## 身份
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/me` | 当前用户、角色、可访问租户 |
| GET | `/tenants` | 我的租户列表 |
| POST | `/auth/logout` | 登出（前端清 token） |

## 概览
| GET | `/overview` | 沙箱状态分布、配额用量、最近活动 |

## 沙箱
| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/sandboxes` | 列表（`?tenant=&state=&q=&page=&size=`） |
| POST | `/sandboxes` | 创建（template/image、entrypoint、env、resource、timeout、networkPolicy、volumes） |
| GET | `/sandboxes/{id}` | 详情 |
| DELETE | `/sandboxes/{id}` | 销毁 |
| POST | `/sandboxes/{id}/pause` | 暂停 |
| POST | `/sandboxes/{id}/resume` | 恢复 |
| POST | `/sandboxes/{id}/renew` | 续期（body: timeout） |
| PATCH | `/sandboxes/{id}/metadata` | 元数据合并 |
| GET | `/sandboxes/{id}/endpoints/{port}` | 端点 |
| GET | `/sandboxes/{id}/proxy/{port}/{path}` | 经 BFF 代理访问沙箱服务 |
| GET/PUT/PATCH/DELETE | `/sandboxes/{id}/networkpolicy` | 出网策略 |
| GET | `/sandboxes/{id}/events` | SSE 状态/事件 |
| GET | `/sandboxes/{id}/metrics/watch` | SSE 指标 |
| GET | `/sandboxes/{id}/diagnostics/logs\|events` | 诊断 |
| POST | `/sandboxes/{id}/snapshots` | 创建快照 |

## 执行
| POST | `/sandboxes/{id}/commands` | 执行命令（SSE 流式） |
| POST | `/sandboxes/{id}/code` | 执行代码（SSE 流式） |
| WS | `/sandboxes/{id}/terminal` | PTY 终端 |

## 文件
| GET | `/sandboxes/{id}/files` | 列目录 |
| GET | `/sandboxes/{id}/files/download` | 下载（Range） |
| POST | `/sandboxes/{id}/files/upload` | 上传（multipart） |
| POST | `/sandboxes/{id}/directories` | 建目录 |
| DELETE | `/sandboxes/{id}/files` | 删除 |
| POST | `/sandboxes/{id}/files/mv` | 移动/重命名 |
| POST | `/sandboxes/{id}/files/replace` | 内容替换 |

## 模板 / 快照
| GET/POST | `/templates` | 模板列表/创建（P） |
| GET/PUT/DELETE | `/templates/{id}` | 模板详情/更新/删除（P） |
| GET | `/snapshots` | 快照列表 |
| DELETE | `/snapshots/{id}` | 删除快照 |

## 个人 Key
| GET/POST | `/api-keys` | 我的 Key 列表/创建 |
| DELETE | `/api-keys/{id}` | 吊销 |

## 管理端（P / T）
| GET/POST | `/admin/tenants` | 租户列表/创建 |
| GET/PATCH | `/admin/tenants/{id}` | 租户详情/更新（含配额、状态） |
| GET/POST/DELETE | `/admin/tenants/{id}/members` | 成员管理 |
| GET/POST/DELETE | `/admin/tenants/{id}/keys` | 租户 Key 管理 |
| GET | `/admin/pools` | 资源池 |
| GET | `/admin/audit` | 审计检索（`?tenant=&actor=&action=&from=&to=`） |
| GET/PATCH | `/admin/settings` | 系统设置 |
| GET/POST | `/admin/credentials` | 凭据库 |
| GET | `/admin/metrics` | 平台大盘 |

## 错误约定
```json
{ "error": { "code": "QUOTA_EXCEEDED", "message": "租户沙箱数已达上限", "detail": {} } }
```
常用 code：`UNAUTHENTICATED` `FORBIDDEN` `NOT_FOUND` `QUOTA_EXCEEDED` `UPSTREAM_ERROR` `VALIDATION_ERROR` `CONFLICT`。

## 上游映射
| BFF | 上游 |
|---|---|
| `/sandboxes*` | lifecycle `/v1/sandboxes*` |
| `/sandboxes/{id}/commands` | execd `POST /command` |
| `/sandboxes/{id}/code` | execd `POST /code` |
| `/sandboxes/{id}/terminal` | execd `/pty/{session}/ws` |
| `/sandboxes/{id}/files*` | execd `/files*`,`/directories*` |
| `/sandboxes/{id}/metrics/watch` | execd `/metrics/watch` |
| `/sandboxes/{id}/networkpolicy` | lifecycle `/networkpolicy` 或 egress `/policy` |
