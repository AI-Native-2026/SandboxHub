import { useEffect, useRef, useState } from "react";
import {
  Button, Card, Descriptions, Empty, Input, Popconfirm, Space, Table, Tabs, Tag, Timeline, message, Alert,
} from "antd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate, useParams } from "react-router-dom";
import { api, getSandbox, sandboxAction, listSnapshots, createSnapshot, deleteSnapshot } from "../api";
import { canWrite } from "../auth";
import {tr,  useI18n } from "../i18n";
import { keycloak } from "../auth";
import Terminal from "../components/Terminal";
import CommandRunner from "../components/CommandRunner";
import FileBrowser from "../components/FileBrowser";
import Metrics from "../components/Metrics";

const stateColor: Record<string, string> = {
  Running: "green", Paused: "orange", Pending: "blue", Terminated: "default", Failed: "red",
};
function useSandboxEvents(id: string, onStatus: (s: any) => void) {
  const ref = useRef<AbortController | null>(null);
  useEffect(() => {
    const ctrl = new AbortController();
    ref.current = ctrl;
    (async () => {
      try {
        const resp = await fetch(`/api/v1/sandboxes/${id}/events`, {
          headers: {
            Authorization: `Bearer ${keycloak.token}`,
            "X-Tenant-Id": localStorage.getItem("tenantId") || "",
          },
          signal: ctrl.signal,
        });
        if (!resp.body) return;
        const reader = resp.body.getReader();
        const dec = new TextDecoder();
        let buf = "";
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buf += dec.decode(value, { stream: true });
          const lines = buf.split(/\r?\n/);
          buf = lines.pop() || "";
          for (const raw of lines) {
            const line = raw.trim();
            if (!line.startsWith("data:")) continue;
            try {
              onStatus(JSON.parse(line.slice(5).trim()));
            } catch {
              /* ignore */
            }
          }
        }
      } catch {
        /* aborted */
      }
    })();
    return () => ctrl.abort();
  }, [id]);
}

function Snapshots({ id, writable }: { id: string; writable: boolean }) {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["snapshots"], queryFn: listSnapshots });
  return (
    <Card>
      <Space style={{ marginBottom: 12 }}>
        <Button
          type="primary"
          disabled={!writable}
          onClick={async () => {
            try {
              await createSnapshot(id, `snap-${Date.now()}`);
              message.success(tr("快照创建中"));
              qc.invalidateQueries({ queryKey: ["snapshots"] });
            } catch (e: any) {
              message.error(e?.response?.data?.error?.message || tr("创建失败（Docker 运行时可能不支持）"));
            }
          }}
        >{tr("创建快照")}</Button>
      </Space>
      <Table
        rowKey="id"
        size="small"
        loading={isLoading}
        dataSource={data || []}
        pagination={false}
        columns={[
          { title: tr("名称"), dataIndex: "name" },
          { title: tr("状态"), dataIndex: "state" },
          { title: tr("来源沙箱"), dataIndex: "sandboxId", ellipsis: true },
          {
            title: tr("操作"),
            render: (_: any, r: any) => (
              <a
                style={{ color: "var(--bad)" }}
                onClick={async () => {
                  await deleteSnapshot(r.id);
                  qc.invalidateQueries({ queryKey: ["snapshots"] });
                }}
              >{tr("删除")}</a>
            ),
          },
        ]}
      />
    </Card>
  );
}

export default function SandboxDetail() {
  const { id = "" } = useParams();
  const { t } = useI18n();
  const nav = useNavigate();
  const qc = useQueryClient();
  const writable = canWrite();
  const [liveState, setLiveState] = useState<string | null>(null);
  const [events, setEvents] = useState<any[]>([]);

  const { data, isLoading } = useQuery({
    queryKey: ["sandbox", id],
    queryFn: () => getSandbox(id),
    refetchInterval: 10000,
  });

  useSandboxEvents(id, (e) => {
    if (e.type === "status") {
      setLiveState(e.state);
      setEvents((prev) => [{ ...e, ts: Date.now() }, ...prev].slice(0, 50));
    }
  });

  const state = liveState || data?.state;

  const { data: policy, refetch: refetchPolicy } = useQuery({
    queryKey: ["policy", id],
    queryFn: async () => (await api.get(`/sandboxes/${id}/networkpolicy`)).data,
  });
  const { data: execdEndpoint } = useQuery({
    queryKey: ["endpoint", id],
    queryFn: async () => (await api.get(`/sandboxes/${id}/endpoints/44772`)).data,
    retry: false,
  });

  const act = useMutation({
    mutationFn: ({ action, body }: any) => sandboxAction(id, action, body),
    onSuccess: () => {
      message.success(tr("操作成功"));
      qc.invalidateQueries({ queryKey: ["sandbox", id] });
    },
    onError: (e: any) => message.error(e?.response?.data?.error?.message || tr("操作失败")),
  });
  const del = useMutation({
    mutationFn: () => api.delete(`/sandboxes/${id}`),
    onSuccess: () => {
      message.success(tr("已销毁"));
      nav("/sandboxes");
    },
  });
  const [allowText, setAllowText] = useState("");
  const savePolicy = useMutation({
    mutationFn: () => {
      const egress = allowText
        .split("\n")
        .map((s) => s.trim())
        .filter(Boolean)
        .map((target) => ({ action: "allow", target }));
      return api.put(`/sandboxes/${id}/networkpolicy`, { defaultAction: "deny", egress });
    },
    onSuccess: () => {
      message.success(tr("策略已应用"));
      refetchPolicy();
    },
    onError: (e: any) => message.error(e?.response?.data?.error?.message || tr("应用失败")),
  });
  return (
    <div>
      {data?.lost && (
        <Alert
          type="warning"
          showIcon
          style={{ marginBottom: 12 }}
          message={tr("该沙箱在上游已不存在（可能已过期或被回收），仅保留平台记录。终端/命令将不可用。")}
        />
      )}
      <Space style={{ marginBottom: 16, width: "100%", justifyContent: "space-between" }}>
        <Space>
          <h2 style={{ margin: 0 }}>{data?.name || id.slice(0, 8)}</h2>
          <Tag color={stateColor[state] || "default"}>{state}</Tag>
        </Space>
        <Space>
          {writable && state === "Running" && <Button onClick={() => act.mutate({ action: "pause" })}>{t("sandbox.pause")}</Button>}
          {writable && state === "Paused" && <Button onClick={() => act.mutate({ action: "resume" })}>{t("sandbox.resume")}</Button>}
          {writable && (
            <Button onClick={() => act.mutate({ action: "renew", body: { timeout_seconds: 1800 } })}>{t("sandbox.renew")}</Button>
          )}
          {writable && (
            <Popconfirm title={tr("确认销毁？")} onConfirm={() => del.mutate()}>
              <Button danger>{t("sandbox.destroy")}</Button>
            </Popconfirm>
          )}
        </Space>
      </Space>

      <Tabs
        items={[
          {
            key: "overview",
            label: t("detail.overview"),
            children: (
              <Card loading={isLoading}>
                <Descriptions column={2} bordered size="small">
                  <Descriptions.Item label="Sandbox ID">{data?.sandbox_id}</Descriptions.Item>
                  <Descriptions.Item label={tr("状态")}>{state}</Descriptions.Item>
                  <Descriptions.Item label={tr("镜像")}>{data?.image}</Descriptions.Item>
                  <Descriptions.Item label={tr("CPU / 内存")}>{data?.cpu} / {data?.memory}</Descriptions.Item>
                  <Descriptions.Item label={tr("到期")}>
                    {data?.expires_at ? new Date(data.expires_at).toLocaleString() : "-"}
                  </Descriptions.Item>
                  <Descriptions.Item label={tr("创建")}>
                    {data?.created_at ? new Date(data.created_at).toLocaleString() : "-"}
                  </Descriptions.Item>
                  <Descriptions.Item label={tr("execd 端点")} span={2}>
                    {execdEndpoint?.endpoint || "-"}
                  </Descriptions.Item>
                </Descriptions>
              </Card>
            ),
          },
          {
            key: "runtime",
            label: t("detail.runtime"),
            children: (
              <Tabs
                items={[
                  { key: "terminal", label: t("detail.terminal"), children: <Terminal sandboxId={id} /> },
                  { key: "command", label: t("detail.command"), children: <CommandRunner sandboxId={id} /> },
                ]}
              />
            ),
          },
          { key: "data", label: t("detail.data"), children: <FileBrowser sandboxId={id} /> },
          {
            key: "network",
            label: t("detail.network"),
            children: (
              <Card>
                <p style={{ color: "var(--text-dim)" }}>{tr("当前策略：")}<code>{JSON.stringify(policy?.policy ?? policy)}</code>
                </p>
                <p style={{ color: "var(--warn, #fbbf24)" }}>{tr("注意：gVisor 运行时与 networkPolicy 不兼容（无 nat 表），应用可能失败。")}</p>
                <Input.TextArea
                  rows={5}
                  placeholder={"放行域名，每行一个\n*.pythonhosted.org"}
                  value={allowText}
                  onChange={(e) => setAllowText(e.target.value)}
                />
                <Button
                  type="primary"
                  style={{ marginTop: 12 }}
                  loading={savePolicy.isPending}
                  onClick={() => savePolicy.mutate()}
                >{tr("应用（默认拒绝 + 上述放行）")}</Button>
              </Card>
            ),
          },
          {
            key: "observe",
            label: t("detail.observe"),
            children: (
              <div>
                <Metrics sandboxId={id} />
                <Card title={tr("状态事件（实时）")} style={{ marginTop: 16 }}>
                  {events.length === 0 ? (
                    <Empty description={tr("等待事件…")} />
                   ) : (
                    <Timeline
                      items={events.map((e) => ({
                        color: e.state === "Running" ? "green" : e.state === "Failed" ? "red" : "blue",
                        children: (
                          <span>
                            <b>{e.state}</b> {e.reason ? `· ${e.reason}` : ""}
                            <span style={{ color: "var(--text-faint)", marginLeft: 8 }}>
                              {new Date(e.ts).toLocaleTimeString()}
                            </span>
                          </span>
                        ),
                      }))}
                    />
                  )}
                </Card>
              </div>
            ),
          },
          { key: "snapshots", label: t("detail.snapshot"), children: <Snapshots id={id} writable={writable} /> },
          {
            key: "security",
            label: t("detail.security"),
            children: (
              <Card>
                <Empty description={tr("凭据注入 / 会话录制将在 U1/U3 阶段交付")} />
              </Card>
            ),
          },
        ]}
      />
    </div>
  );
}
