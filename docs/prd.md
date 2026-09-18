# SandboxHub 产品需求（PRD）

## 1. 背景
AI 应用进入"真执行"阶段，AI 生成代码不可信。团队自建沙箱重复且不安全。需要一个统一、隔离、可审计的内部沙箱平台。

## 2. 用户与权限
| 角色 | 能力 |
|---|---|
| platform-admin | 全部；租户/模板/策略/凭据/审计/设置 |
| tenant-admin | 本租户成员/配额/Key；本租户全部沙箱 |
| developer | 自助创建/使用/销毁自己的沙箱 |
| viewer | 只读 |

授权模型：Keycloak 认证 + 平台 `memberships` 决定租户与角色（ADR-004/013）。

## 3. 功能需求（FR）

### 3.1 身份与租户
- FR-1 SSO 登录/登出（Keycloak OIDC PKCE）
- FR-2 租户列表与切换
- FR-3 成员与角色管理（T）
- FR-4 租户生命周期（P）

### 3.2 沙箱
- FR-10 列表（搜索/筛选/分页/排序）
- FR-11 创建向导（模板/镜像、entrypoint、env、资源、超时、网络策略、挂载）
- FR-12 详情概览（状态、元数据、到期、端点）
- FR-13 生命周期：pause / resume / renew / delete
- FR-14 元数据 patch

### 3.3 执行与文件
- FR-20 Web 终端（PTY，多会话，viewer 只读）
- FR-21 命令执行（SSE 流式，退出码）
- FR-22 文件浏览器（列表/上传/下载/编辑/删除/移动/搜索）
- FR-23 端点访问（经 BFF 代理）

### 3.4 网络与安全
- FR-30 出网策略编辑（defaultAction + allow/deny，FQDN/CIDR/通配）
- FR-31 `gvisor+networkPolicy` 组合禁用提示（C5）
- FR-32 凭据库（P）

### 3.5 模板与快照
- FR-40 模板目录与一键创建
- FR-41 模板管理（P）
- FR-42 快照创建/列表/删除（标注 Docker 限制）

### 3.6 配额与审计
- FR-50 配额设置与用量（T）
- FR-51 审计全量落库与检索（P）
- FR-52 个人 API Key（D）

### 3.7 观测
- FR-60 沙箱指标（CPU/内存/进程）
- FR-61 事件/诊断
- FR-62 平台大盘（P）

## 4. 非功能需求（NFR）
- NFR-1 鉴权：所有写操作经 BFF 鉴权 + 审计
- NFR-2 租户隔离：任何查询/操作强作用域
- NFR-3 密钥边界：上游密钥不出 BFF（ADR-012）
- NFR-4 实时：终端 WS、日志/指标 SSE
- NFR-5 可用性：加载/空/错/无权限 四态齐全
- NFR-6 可访问性：语义 HTML、键盘可达、对比度达标
- NFR-7 i18n：zh/en
- NFR-8 性能：列表虚拟滚动、大输出虚拟列表

## 5. 验收
以 `docs/user-journeys.md` 的 E2E 用例为准（`E2E-D*`、`E2E-T*`、`E2E-P*`、`E2E-A1`）。
