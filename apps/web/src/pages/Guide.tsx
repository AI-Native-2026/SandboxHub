import { Card, Tabs, Typography } from "antd";
import PageHeader from "../components/PageHeader";
import { tr, useI18n } from "../i18n";

const BASE = "http://43.135.120.107:8081";

function restSnippet() {
  return `# 1) ${tr("# 1) 获取访问令牌（Keycloak 密码模式，仅演示）").replace("# 1) ", "")}
TOKEN=$(curl -s -X POST ${BASE}/realms/sandboxhub/protocol/openid-connect/token \\
  -d grant_type=password -d client_id=sandboxhub-web \\
  -d username=dev1 -d password='Passw0rd!' | jq -r .access_token)

# 2) ${tr("# 2) 用个人 API Key（推荐，脚本场景）").replace("# 2) ", "")}
#    Header: X-API-Key: <your-key>

# 3) ${tr("# 3) 创建沙箱").replace("# 3) ", "")}
curl -s -X POST ${BASE}/api/v1/sandboxes \\
  -H "Authorization: Bearer $TOKEN" -H "X-Tenant-Id: <tenant-id>" \\
  -H "Content-Type: application/json" \\
  -d '{"image":"python:3.12","name":"my-box","cpu":"1","memory":"1Gi","timeout_seconds":1800}'

# 4) ${tr("# 4) 执行命令（流式）").replace("# 4) ", "")}
curl -N -X POST ${BASE}/api/v1/sandboxes/<id>/commands \\
  -H "Authorization: Bearer $TOKEN" -H "X-Tenant-Id: <tenant-id>" \\
  -H "Content-Type: application/json" -d '{"command":"echo hi"}'`;
}

function pySnippet() {
  return `import httpx

BASE = "${BASE}/api/v1"
HEADERS = {"X-API-Key": "<your-key>", "X-Tenant-Id": "<tenant-id>"}

# ${tr("# 创建沙箱").replace("# ", "")}
sb = httpx.post(f"{BASE}/sandboxes", headers=HEADERS, json={
    "image": "python:3.12", "name": "sdk-demo",
    "cpu": "1", "memory": "1Gi", "timeout_seconds": 1800,
}).json()
sid = sb["sandbox_id"]

# ${tr("# 执行命令（流式）").replace("# ", "")}
with httpx.stream("POST", f"{BASE}/sandboxes/{sid}/commands",
                  headers=HEADERS, json={"command": "python --version"}) as r:
    for line in r.iter_lines():
        if line:
            print(line)

# ${tr("# 销毁").replace("# ", "")}
httpx.delete(f"{BASE}/sandboxes/{sid}", headers=HEADERS)`;
}

export default function Guide() {
  const { t } = useI18n();
  return (
    <div>
      <PageHeader eyebrow="Developer" title={t("guide.title")} subtitle={t("guide.subtitle")} />
      <Card>
        <Typography.Paragraph type="secondary">
          {tr("所有接口前缀")} <code>/api/v1</code>{tr("，鉴权二选一：")}<code>Authorization: Bearer &lt;jwt&gt;</code> {tr("或")}
          <code> X-API-Key: &lt;key&gt;</code>{tr("；多租户请求需带")} <code>X-Tenant-Id</code>。
        </Typography.Paragraph>
        <Tabs
          items={[
            { key: "rest", label: "REST / CLI", children: <pre className="sh-mono sh-out">{restSnippet()}</pre> },
            { key: "py", label: "Python", children: <pre className="sh-mono sh-out">{pySnippet()}</pre> },
          ]}
        />
      </Card>
    </div>
  );
}
