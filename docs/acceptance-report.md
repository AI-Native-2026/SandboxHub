# SandboxHub 验收报告（v0.1）

- 环境：单台 Linux VM（`43.135.120.107`），Docker Compose 部署，HTTP
- 入口：`http://43.135.120.107:8081`
- 验收方式：Playwright E2E（`scripts/e2e-suite.py`）+ API 契约检查（`scripts/check-*.sh`）

## 1. E2E 结果（对齐用户旅程）

| 用例 | 旅程 | 结果 |
|---|---|---|
| E2E-D1 | 登录 / 租户切换 | ✅ PASS |
| E2E-D2 | 从模板创建沙箱 | ✅ PASS |
| E2E-D3 | 终端（PTY）+ 命令（流式） | ✅ PASS |
| E2E-D4 | 文件浏览 / 收发 / 编辑 | ✅ PASS |
| E2E-D6 | 指标（CPU/内存） | ✅ PASS |
| E2E-D7 | 模板市场 | ✅ PASS |
| E2E-D10 | 个人 API Key | ✅ PASS |
| E2E-P1 | 管理端 / 全局审计 | ✅ PASS |
| E2E-A1 | 只读角色无写入口 | ✅ PASS |

**合计：PASS=9 FAIL=0**

## 1.1 U2 体验阶段（新增）

| 用例 | 内容 | 结果 |
|---|---|---|
| E2E-U2 | 命令面板（⌘K） | ✅ PASS |
| E2E-U2 | 主题切换（暗/亮/跟随） | ✅ PASS |

**U2 回归合计：PASS=11 FAIL=0**（含原有 9 项）

U2 交付：四组导航（工作台/资源/治理/管理）、暗/亮/跟随主题、中英双语、命令面板、通知中心、批量操作、详情页 7 Tab 重组、实时状态 SSE、接入指南页、设计规范（`docs/design/ui-spec.html`）。

## 1.2 U1–U5 全量交付（新增）

| 阶段 | 模块 | 实现 | 验证 |
|---|---|---|---|
| U1 | 用量与成本 | 后台采样器（60s）记录 CPU/内存秒数 → 汇总/趋势/Top + 成本 | API ✓ |
| U1 | 配额管理 | 租户配额用量视图（CPU/内存/并发） | API ✓ |
| U1 | 审批中心 | 申请 / 待审 / 批准 / 驳回 | API ✓ |
| U1 | 凭据库 | 凭据引用存储（不回显） | API ✓ |
| U1 | 网络策略模板 | 可复用 allow/deny 模板 | API ✓ |
| U3 | 会话录制 | 终端 PTY 录制 + 回放 | API ✓ |
| U3 | 审计导出 | CSV 导出 | API ✓ |
| U3 | 角色与权限 | 内置权限矩阵 + 自定义角色 | API ✓ |
| U4 | 资源池与可观测 | 资源池登记 + 平台用量大盘 | API ✓ |
| U5 | 任务 | 批量创建沙箱执行命令（实测 2 副本成功 2/失败 0） | API ✓ |
| U5 | 产物 | 从沙箱收集文件并下载 | API ✓ |
| U5 | Agent 托管 | Claude Code / OpenCode / Codex 一键创建 | API ✓ |

**E2E 回归：PASS=11 FAIL=0**（无回归）

## 1.3 PM 评审修复（v0.3）

| 问题 | 修复 |
|---|---|
| 创建沙箱不应独立成页 | 改为**沙箱列表页内的弹窗**（`CreateSandboxModal`），移除独立路由与导航项 |
| API Key 设计肤浅 | 重做：安全告警、创建表单、前缀/状态/创建时间/最近使用、一次性密钥展示 + 复制、吊销确认 |
| 深/浅主题下部分内容不显示 | 补齐应用层 CSS 变量（`--text/--text-dim/--text-faint/...`）+ 浅色覆盖；页头/Logo 颜色改用变量；ConfigProvider token 按主题切换 |
| 主题切换控件冗余 | 合并为**单个图标按钮**（暗↔亮） |
| 语言切换控件冗余 | 合并为**单个按钮**（中↔EN） |
| Agent 启动后 opencode 未安装 | 镜像本身不含 Agent；启动时**后台自动安装**（实测 10s 后 `opencode 1.18.31` 可用），Agents 页增加说明 |

## 1.4 第二轮 PM 评审修复（v0.4）

| 问题 | 修复 | 验证 |
|---|---|---|
| 销毁报 404 `SANDBOX_NOT_FOUND` | 删除改为**幂等**：上游 404 视为成功，记录标记 Terminated | 连续两次删除均返回 204 |
| 新建角色权限需手填 | 改为**多选下拉**（`resource:action`），移除权限矩阵展示（设计细节见手册） | E2E-P1 |
| 会话录制无入口 | 终端工具栏新增**录制开关**，开启后写入录制，可到「会话录制」回放 | — |
| 资源池 provider 需手填 | 改为**下拉可选**（Docker / Kubernetes，含说明），新增 `/pools/providers` | — |
| 成本趋势/观测非时序图 | 引入 **ECharts**，用量与成本、资源池与可观测改为**时序折线/面积图** | 截图 51/53 |
| 搜索跳转无意义 | **移除**命令面板与 ⌘K 入口 | — |
| 状态筛选需手填 | 改为**多选下拉**（Running/Paused/Pending/Terminated/Failed），后端支持逗号分隔多状态 | — |
| 选模板后镜像仍可改 | 选择模板后**镜像置为只读**并提示「由模板决定」；不选模板则自定义镜像 | 截图 41 |
| 英文界面残留中文 | 补全 i18n 词典并接入全部页面（导航/详情 Tab/标题/按钮/列），新增中英切换 E2E 校验 | E2E-U2 中英切换 PASS |
| 缺少使用手册 | 新增 `docs/user-manual.md`（概念 + 功能原理 + 使用示例 + FAQ） | — |

**E2E 回归：PASS=11 FAIL=0**

## 1.6 状态对账与自动清理（v0.6）

| 需求 | 实现 | 验证 |
|---|---|---|
| 刷新时主动检查最新状态 | 列表接口每次调用都会拉取上游并**对账**：记录在上游不存在则标记 `Terminated`；「刷新」按钮触发重新请求即完成对账 | stale 沙箱返回 `Terminated` |
| 后台每 15 分钟清理已终止沙箱 | 新增 `services/cleanup.py`：`run_cleanup` 每 900s 执行「对账 + 清理」，删除所有 `Terminated` 记录（BFF 启动即执行一次） | 启动时 `purged` 生效 |
| 被清理的沙箱不得出现在列表 | 清理为**硬删除**记录，列表自然不再返回 | 删除后触发清理 → `purged=2` → 列表不再包含该沙箱 |
| 运维手动清理 | 新增 `POST /admin/cleanup`（平台管理员）；管理端「平台指标」提供「立即对账并清理」按钮 | `purged=2, presentAfter=false` |

## 1.7 沙箱观测时序图（v0.7）

| 需求 | 实现 | 验证 |
|---|---|---|
| 观测的 CPU 使用率与内存用时序图表 | `Metrics` 组件按 3s 采样累积最近 60 个点，用 ECharts 渲染 **CPU / Memory (%)** 双序列面积折线图与 **Memory used (MiB)** 折线图；同时保留当前值卡片 | E2E-D6 指标时序图 PASS（截图 70） |

**E2E 回归：PASS=11 FAIL=0**

## 1.8 构建稳定性与 i18n 加固（v0.8）

| 问题 | 修复 | 验证 |
|---|---|---|
| i18n 批量替换导致前端构建失败（括号损坏） | 新增 `scripts/lint-web.sh`（容器内 esbuild 一次性枚举全部 TSX 语法错误），逐条精确修复：函数/对象闭合 `});`→`};`、补齐丢失的 `)`/`}`；`vite build` 通过 | esbuild 零错误 + web 镜像重建成功 |
| 语言切换后按钮 `aria-label` 被翻译，E2E 选择器失效 | 主题/语言按钮加稳定 class `sh-theme-toggle` / `sh-lang-toggle`，E2E 改用 class 定位 | E2E-U2 中英切换 PASS |
| 品牌名统一 | `header.title` 统一为「AI智能体沙箱平台」（英文 AI Agent Sandbox Platform） | E2E-D1 PASS |

**E2E 回归：PASS=11 FAIL=0**

## 1.5 第三轮优化（v0.5）

| 问题 | 修复 | 验证 |
|---|---|---|
| 创建沙箱按钮与刷新不在同一行 | 「创建沙箱」按钮移到筛选行，**紧挨「刷新」右侧** | 截图 60 |
| 「我的 API Key」命名与创建方式 | 导航与页面标题改为 **API Key**；「创建新密钥」改为**弹窗表单** | 截图 61 / E2E-D10 |
| 打开运行中沙箱报 404 `SANDBOX_NOT_FOUND` | 记录与上游不同步时**优雅降级**：列表/详情检测到上游已无该沙箱则标记为 `Terminated`；详情返回 `lost=true` 并给出提示；端点接口 404 返回不可用而非报错 | 实测 stale 沙箱返回 `{status: Terminated, lost: true}` |





## 1.9 反馈修复：品牌 / 录制 / 策略模板 / 资源池（v0.9）

| 反馈 | 修复 | 验证 |
|---|---|---|
| 品牌名应为「AI智能体沙箱平台」 | 前端 i18n、README（中/英）、用户手册、UI 规范、E2E 断言统一改名；英文名 `AI Agent Sandbox Platform` | E2E-D1 PASS |
| 会话录制"没法用" | ① 录制开关不再重连终端，改为控制帧动态开启；② 断开即落库（原等 `websockets` 默认 `close_timeout=10s`，改 `close_timeout=1` + `FIRST_COMPLETED` 取消） | 落库延迟 **10.2s → 0.5s**，内容含命令输出；E2E 无回归 |
| 策略模板默认动作应可选 | 「新建策略模板」的默认动作改为**下拉**（deny/allow），规则目标随默认动作自动 allow/deny | 截图 91 |
| 策略模板用在哪里 | **接入创建沙箱**：新增「网络策略模板（可选）」下拉，选用后 BFF 按模板下发 `networkPolicy`（上游据此创建 egress sidecar） | 截图 92；上游日志见 `create/start egress sidecar` |
| 资源池如何关联用户资源 | 按**镜像**关联：`list_pools` 统计 Running 且镜像匹配的沙箱数作为「已用」，上限取池 Max capacity，列表展示「已用 / 上限」 | 截图 93（used=1/max=3） |

**E2E 回归：PASS=11 FAIL=0**

> 已知上游限制：本部署 `GET/PUT /v1/sandboxes/{id}/networkpolicy` 恒返回 404，详情·网络页显示 BFF 兜底值；创建时下发的策略仍会创建 egress sidecar。

## 1.10 交互与主题优化（v0.10）

| 反馈 | 修复 | 验证 |
|---|---|---|
| Agent 托管点击一个按钮，多个一起转圈 | 加载态按卡片隔离：`loading={launch.isPending && launch.variables?.id === a.id}`，仅被点击的卡片显示动画 | 截图 97 |
| 明/暗主题整体优化（清晰、配色协调） | ① 主色分主题（暗 `#6ea8fe` / 亮 `#2563eb`），补 Menu/Table/Card 组件 token；② 新增语义变量（`--accent-soft/--stat-a/--stat-b/--code-*/--shadow`），统计渐变、代码块、批量条、卡片阴影随主题切换；③ 页面内硬编码色（`#f87171/#6b7794/#9aa6bd/#4ade80`）统一改为 `var(--bad/--text-faint/--text-dim/--ok)`；④ 图表轴色/调色板/提示框按主题切换，提升浅色对比度 | 截图 95–98（明/暗） |

**E2E 回归：PASS=11 FAIL=0**

## 1.11 录制回放修复（v0.11）

| 反馈 | 修复 | 验证 |
|---|---|---|
| 运行 opencode 后，录制回放乱码 | 回放由 `atob`+`<pre>` 改为 **xterm.js 渲染原始字节**：正确解码 UTF-8（中文/框线/制表符）并渲染 ANSI（光标/清屏/alt-screen/颜色）；按 chunk 时间戳回放。终端用回调 ref 初始化以适配 Modal 挂载时机 | 截图 99：opencode TUI 正常显示（框线/颜色/`Hello, World!`），无 U+FFFD、无转义残留 |

## 2. 部署组件

| 组件 | 端口 | 状态 |
|---|---|---|
| web（nginx + React SPA） | 8081 | 运行 |
| bff（FastAPI） | 8001 | 运行 |
| keycloak（realm `sandboxhub`） | 8180 | 运行 |
| postgres / redis | 5433 / 6380 | 运行 |
| opensandbox-server（复用） | 8090 | 运行 |

## 3. 功能覆盖

- **身份**：Keycloak SSO；4 角色（platform-admin/tenant-admin/developer/viewer）；平台层逻辑多租户；个人 API Key（`X-API-Key`）
- **沙箱**：列表/详情/创建向导/暂停/恢复/续期/销毁/元数据/快照
- **执行**：Web 终端（PTY，经 BFF WS 代理）、命令（流式）、代码执行
- **文件**：目录浏览、上传、下载、在线编辑、删除、新建目录、搜索
- **网络**：出网策略读取/编辑（默认拒绝 + FQDN 白名单）
- **观测**：沙箱指标（CPU/内存/进程）、审计活动、平台指标
- **管理端**：租户 CRUD、成员管理、配额、全局审计、平台指标、系统设置

## 4. 已知限制

1. Docker 运行时不支持上游原生多租户/Pool（用平台层逻辑多租户替代）。
2. 快照恢复（pause/resume 持久化）在 Docker 下能力有限，K8s 才完整。
3. `gvisor + networkPolicy` 不兼容（上游约束 C5）。
4. 单 VM 单活 BFF；HA 需多实例 + 外部会话（后续）。

## 5. 质量与工程

- BFF：FastAPI + SQLAlchemy(async) + Pydantic；所有写操作审计落库
- 前端：React 18 + TS + Vite + Ant Design 5（暗色主题、统一 token）
- 部署：Docker Compose 一键；nginx 单端口（静态 + `/api` + Keycloak `/realms`）
- 测试：Playwright E2E 套件 + API 检查脚本

## 6. 结论

**通过**。SandboxHub v0.1 在单 VM 上完成前后端设计、开发、部署与端到端验收，核心用户旅程全部可运行。
