# SandboxHub 数据模型

## 1. ER 概览

```
users ──< memberships >── tenants ──< sandbox_records
                              │              │
                              ├─< api_keys    └─< snapshots_index
                              ├─< templates
                              ├─< network_policy_templates
                              ├─< credential_refs
                              ├─< usage_snapshots
                              └─< pools
audit_logs (actor_user_id, tenant_id, ...)
settings (key,value)
```

## 2. 表定义

### users
| 列 | 类型 | 说明 |
|---|---|---|
| id | uuid pk | |
| keycloak_sub | text unique | Keycloak `sub` |
| email | text | |
| display_name | text | |
| status | text | active/disabled |
| created_at | timestamptz | |

### tenants
| 列 | 类型 | 说明 |
|---|---|---|
| id | uuid pk | |
| slug | text unique | 短标识 |
| name | text | |
| status | text | active/suspended |
| quota_cpu | text | 如 `16` |
| quota_memory | text | 如 `32Gi` |
| quota_sandboxes | int | 并发上限 |
| osb_metadata_key | text | 上游打标键 |
| created_at | timestamptz | |

### memberships
| 列 | 类型 | 说明 |
|---|---|---|
| user_id | uuid fk | |
| tenant_id | uuid fk | |
| role | text | platform-admin/tenant-admin/developer/viewer |
| created_at | timestamptz | |
| PK | (user_id, tenant_id) | |

### api_keys
| 列 | 类型 | 说明 |
|---|---|---|
| id | uuid pk | |
| tenant_id | uuid fk null | 租户 Key |
| user_id | uuid fk null | 个人 Key |
| name | text | |
| prefix | text | 展示用前缀 |
| key_hash | text | 哈希存储 |
| scopes | jsonb | |
| status | text | active/revoked |
| last_used_at | timestamptz | |
| expires_at | timestamptz null | |
| created_at | timestamptz | |

### sandbox_records
| 列 | 类型 | 说明 |
|---|---|---|
| id | uuid pk | 平台 ID |
| tenant_id | uuid fk | |
| owner_user_id | uuid fk | |
| osb_sandbox_id | text unique | 上游 ID |
| name | text | |
| image | text | |
| template_id | uuid fk null | |
| status | text | Pending/Running/Paused/... |
| cpu | text | |
| memory | text | |
| expires_at | timestamptz null | |
| metadata | jsonb | |
| created_at / updated_at | timestamptz | |

### templates
| 列 | 类型 | 说明 |
|---|---|---|
| id | uuid pk | |
| tenant_id | uuid fk null | null=全局 |
| name / description | text | |
| image | text | |
| entrypoint | jsonb | |
| env | jsonb | |
| default_cpu / default_memory | text | |
| default_timeout_seconds | int | |
| network_policy | jsonb null | |
| icon / tags | text / jsonb | |
| visibility | text | public/tenant |
| status | text | |
| created_at | timestamptz | |

### snapshots_index
`id, tenant_id, osb_snapshot_id, sandbox_id, name, state, created_at`

### network_policy_templates
`id, tenant_id null, name, default_action, rules jsonb, created_at`

### credential_refs
`id, tenant_id, name, type, secret_ref, created_at`（+ bindings 可扩展 jsonb）

### pools
`id, tenant_id, name, capacity jsonb, provider, created_at`（K8s 进阶轨使用）

### usage_snapshots
`id, tenant_id, sandbox_id, ts, cpu_seconds, mem_gb_seconds`

### audit_logs
| 列 | 类型 | 说明 |
|---|---|---|
| id | uuid pk | |
| ts | timestamptz | |
| actor_user_id | uuid null | |
| tenant_id | uuid null | |
| action | text | sandbox.create / sandbox.kill ... |
| resource_type / resource_id | text | |
| result | text | success/failure |
| ip / user_agent | text | |
| detail | jsonb | 脱敏后参数 |

### settings
`key text pk, value jsonb, updated_at`
