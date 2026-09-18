# SandboxHub UI 设计规格

## 1. 技术栈
React 18 · TypeScript · Vite · Ant Design 5（暗色主题）· TanStack Query · Zustand · React Router 6 · xterm.js · Monaco Editor · ECharts · react-i18next · react-hook-form + zod。

## 2. 设计原则
- 面向开发者：键盘可达、终端体验优先、少点击
- 面向运维：信息密度可控、表格强大、操作可审计
- 四态齐全：加载 / 空 / 错 / 无权限
- 暗色优先，支持亮色与跟随系统

## 3. 信息架构

```
登录(Keycloak)
工作台
├─ 概览
├─ 沙箱
│   ├─ 列表
│   ├─ 创建向导
│   └─ 详情（概览/终端/命令/文件/端点/指标/网络/事件）
├─ 模板市场
├─ 我的 API Key
└─ 我的活动
管理端
├─ 租户管理
├─ 资源池
├─ 模板与镜像
├─ 网络策略模板
├─ 凭据库
├─ 全局审计
├─ 可观测大盘
└─ 系统设置
```

## 4. 页面规格（要点）

### 4.1 沙箱列表
- 列：名称、状态徽标、镜像/模板、租户、所有者、CPU/内存、到期倒计时、创建时间、操作
- 交互：搜索、状态筛选、分页、排序、批量 kill/renew、行内 pause/resume
- 状态：加载骨架、空态（引导创建）、错误重试

### 4.2 创建向导（Steps）
1. 选择来源：模板 / 镜像（模板带出默认）
2. 配置：entrypoint、env、工作目录
3. 资源与超时：CPU/内存、timeout、renew
4. 网络策略：defaultAction、allow/deny 规则（FQDN/CIDR/通配）
5. 挂载：host/PVC（白名单内）
6. 确认：摘要 + 提交 → 进度（Pending→Running）→ 跳详情

### 4.3 沙箱详情
- 顶部：名称、状态徽标、操作（暂停/恢复/续期/销毁）、到期倒计时
- Tab：
  - 概览：元数据、限额、端点、来源、审计摘要
  - 终端：xterm.js（多会话、resize、复制粘贴；viewer 只读）
  - 命令：命令输入 + SSE 流式输出 + 退出码 + 历史
  - 文件：目录树 + 上传/下载/新建/删除/移动 + Monaco 编辑 + 搜索
  - 端点：列表 + 复制 + 经 BFF 代理打开
  - 指标：CPU/内存/进程 实时曲线（ECharts）
  - 网络：出网策略编辑（`gvisor+networkPolicy` 禁用提示）
  - 事件：状态迁移时间线 + 诊断

### 4.4 管理端
- 租户：列表/详情、成员与角色、配额、Key 轮换、状态
- 资源池：容量与分配（K8s 进阶）
- 模板与镜像：CRUD、可见性、白名单
- 网络策略模板：全局 allow/deny
- 凭据库：credentials + bindings
- 全局审计：多条件检索 + 导出
- 可观测大盘：集群/租户用量与趋势
- 系统设置：功能开关、默认策略

## 5. 设计系统（packages/ui）
- Tokens：颜色/间距/圆角/阴影/字体（暗/亮/跟随系统）
- 基础组件：Button、Input、Select、Table(虚拟滚动)、Tabs、Drawer、Modal、Toast、Badge、Tooltip、Empty、Skeleton、CodeBlock、Terminal、MetricChart、PolicyEditor、StatusBadge
- 业务组件：SandboxStatusBadge、SandboxCard、CreateWizard、EndpointList、FileTree、AuditTable、QuotaBar、TenantSwitcher
- Storybook：组件文档 + 视觉回归

## 6. 权限渲染
- `<Can action="sandbox:kill">` 包裹敏感操作
- 路由守卫按角色
- 后端二次校验（前端仅体验优化）

## 7. 无障碍与 i18n
- 语义 HTML、键盘可达、焦点管理、对比度达标
- zh/en 文案集中管理

## 8. 实时
- 终端 WS；命令/指标/事件 SSE
- 断线重连、错误提示、回放（终端）
