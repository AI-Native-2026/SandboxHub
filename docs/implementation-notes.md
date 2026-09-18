# SandboxHub 实现要点（踩坑与结论）

> 开发过程中对 OpenSandbox 上游 API 的实测结论，供后续维护参考。

## 1. 创建沙箱必须带 resourceLimits
`POST /v1/sandboxes` 在未提供 `poolRef` 时 **必须提供 `resourceLimits`**，否则返回 422：
`"resourceLimits is required when poolRef is not provided."`
→ BFF 始终注入 `resourceLimits`（默认 cpu=1, memory=1Gi）。

## 2. execd 端点形态与可达性
- 端点返回形如 `172.19.0.16:58040/proxy/44772`（host:port + 代理路径）。
- BFF 容器内访问：把 host 替换为 `host.docker.internal`，保留端口与路径：
  `http://host.docker.internal:58040/proxy/44772/<execd-path>`。
- 由 `app/services/execd.py:normalize_endpoint` 统一处理（`OSB_ENDPOINT_HOST` 可配）。

## 3. 文件上传是「两段式 multipart」
execd `/files/upload` 要求：
- `metadata` 部分：**必须带文件名**的 JSON 部分（`("metadata.json", json, "application/json")`），否则报 `INVALID_FILE_METADATA: metadata file is missing`。
- `file` 部分：二进制。
→ `api/exec.py` 的 `write_file` / `upload_file` 按此构造。

## 4. 命令/代码执行返回 NDJSON（非标准 SSE）
execd `/command`、`/code` 的输出是**逐行 JSON**（`{"type":"stdout",...}`），并非带 `data:` 前缀的 SSE。
→ 前端 `CommandRunner` 同时兼容 SSE（`data:`）与 NDJSON 两种格式。

## 5. PTY 终端协议
- `POST /pty {cwd}` → `{session_id}`。
- `ws /pty/{session_id}/ws`：holder 收 `0x01`(stdout)/`0x02`(stderr)，发 `0x00`+stdin；`{"type":"resize"|"signal"|"ping"}` 为 JSON 文本帧。
- BFF 以 WebSocket 代理透传；浏览器通过 `?token=<jwt>&tenant=<id>` 鉴权（浏览器 WS 不便带 Header）。
- **WS 租户解析需同时支持 id 与 slug**（前端传的是 tenant UUID）。

## 6. Keycloak 单端口访问
- 为让浏览器只经 8081，Keycloak 通过 nginx 代理 `/realms`、`/resources`。
- Keycloak 配置 `KC_HOSTNAME=http://<vm>:8081`（固定 issuer），BFF 校验 `BFF_TOKEN_ISSUER` 与之一致。
- 关键：**不要**设置 `KC_HTTP_RELATIVE_PATH=/auth`（会导致 issuer 与路径不一致）。

## 7. 未设置 networkPolicy 时上游返回 404
`GET /v1/sandboxes/{id}/networkpolicy` 在未设置策略时返回 404。
→ BFF 捕获并返回默认 `{"defaultAction":"deny","egress":[]}`。

## 8. 单 VM 逻辑多租户
上游 Docker 运行时不支持 `[tenants]`。SandboxHub 用平台 `sandbox_records.tenant_id` 强作用域；
沙箱 metadata 打标 `tenant=<slug>`、`owner=<user_id>` 便于追溯。

## 9. 端口与网络
- BFF 需 `extra_hosts: host.docker.internal:host-gateway` 才能访问宿主上的 OpenSandbox server 与沙箱端口。
- 沙箱端口段 40000–60000 由上游分配，BFF 经 host.docker.internal 访问。

## 10. 终端录制的两个坑（已修）
- **开关不应重连终端**：原先 `record` 进入 `useEffect` 依赖，切换开关会重建 WS。改为前端用 `recordRef` + 控制帧 `{"type":"record","on":bool}`，BFF 拦截该文本帧设置录制标志，开关即时生效且不中断会话。
- **落库延迟 ~10s**：断开时 `await upstream.close()` 等 websockets 默认 `close_timeout=10s` 才返回，导致录制迟迟不入库。改为 `asyncio.wait(FIRST_COMPLETED)` + 取消另一任务 + `close_timeout=1`，断开即落库（实测 0.5s）。
- 录制仅采集 `0x01/0x03` 输出帧，内容含输入回显与命令输出。

## 11. 网络策略模板的落点
- 模板（`policy_templates`）在**创建沙箱**时通过 `policy_template_id` 使用：BFF 读取模板并生成 `networkPolicy={defaultAction, egress:rules}` 下发给上游；不选模板时用创建弹窗的自定义策略。
- 上游 `GET/PUT /v1/sandboxes/{id}/networkpolicy` 在本部署**恒返回 404**（即使已下发策略、egress sidecar 已创建）；BFF 捕获后返回兜底 `{"defaultAction":"deny","egress":[]}`。因此详情·网络页不反映创建时的策略。

## 12. 资源池与用户资源的关联
- 资源池（`pool_registry`）按 `image` 与用户沙箱关联：`list_pools` 统计本租户 **Running 且 image 匹配** 的沙箱数作为 `used`，`max` 取自池的 `capacity.max`。
- 这是"登记 + 用量观测"语义，不改变上游调度（上游 Docker 无 Pool）；后续接 K8s 时可将池映射为真实预热池。

## 13. 会话回放改用 xterm.js（修 TUI 乱码）
- 录制存的是 PTY 原始字节（base64）。旧回放用 `atob` 拼进 `<pre>`，两个问题：① `atob` 返回 Latin-1 字符串，UTF-8 多字节（中文/框线/制表符）→ **乱码**；② 不解析 ANSI 转义，运行 opencode 等全屏 TUI 时 → 满屏转义序列乱码。
- 改为 xterm.js 回放：`atob` → `Uint8Array` → `term.write(bytes)`，xterm 内部按 UTF-8 解码并渲染 ANSI（光标/清屏/alt-screen/颜色）。按 chunk 的 `t` 时间戳回放，单步延迟上限 400ms。
- **坑**：AntD `Modal` 首次打开时内容挂载晚于 effect，普通 `useEffect` 拿到 `ref.current === null`；终端需用**回调 ref** 初始化。
