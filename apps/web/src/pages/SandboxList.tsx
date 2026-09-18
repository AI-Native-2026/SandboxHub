import { useState } from "react";
import { Button, Input, Popconfirm, Select, Space, Table, Tag, message } from "antd";
import { ReloadOutlined, PlusOutlined } from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { deleteSandbox, listSandboxes, sandboxAction } from "../api";
import { canWrite } from "../auth";
import { useI18n } from "../i18n";
import PageHeader from "../components/PageHeader";
import CreateSandboxModal from "../components/CreateSandboxModal";

const stateColor: Record<string, string> = {
  Running: "green",
  Paused: "orange",
  Pending: "blue",
  Terminated: "default",
  Failed: "red",
};
const STATE_OPTIONS = ["Running", "Paused", "Pending", "Terminated", "Failed"];

export default function SandboxList() {
  const { t } = useI18n();
  const [q, setQ] = useState("");
  const [states, setStates] = useState<string[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [createOpen, setCreateOpen] = useState(false);
  const qc = useQueryClient();
  const nav = useNavigate();
  const writable = canWrite();

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["sandboxes", q, states],
    queryFn: () => listSandboxes({ q: q || undefined, state: states.join(",") || undefined, page: 1, size: 50 }),
  });

  const invalidate = () => qc.invalidateQueries({ queryKey: ["sandboxes"] });

  const act = useMutation({
    mutationFn: ({ id, action, body }: any) => sandboxAction(id, action, body),
    onSuccess: () => {
      message.success(t("common.save"));
      invalidate();
    },
    onError: (e: any) => message.error(e?.response?.data?.error?.message || "failed"),
  });

  const del = useMutation({
    mutationFn: (id: string) => deleteSandbox(id),
    onSuccess: () => {
      message.success(t("sandbox.destroy"));
      invalidate();
    },
    onError: (e: any) => message.error(e?.response?.data?.error?.message || "failed"),
  });

  const batch = async (action: "pause" | "resume" | "renew" | "delete") => {
    let ok = 0;
    let fail = 0;
    for (const id of selected) {
      try {
        if (action === "delete") await deleteSandbox(id);
        else if (action === "renew") await sandboxAction(id, "renew", { timeout_seconds: 1800 });
        else await sandboxAction(id, action);
        ok += 1;
      } catch {
        fail += 1;
      }
    }
    message.success(`${ok} ok / ${fail} failed`);
    setSelected([]);
    invalidate();
  };
  return (
    <div>
      <PageHeader eyebrow="Sandboxes" title={t("sandbox.title")} subtitle={t("sandbox.subtitle")} />
      <Space style={{ marginBottom: 12, width: "100%" }} wrap>
        <Input.Search placeholder={t("sandbox.searchPlaceholder")} allowClear onSearch={setQ} style={{ width: 220 }} />
        <Select
          mode="multiple"
          allowClear
          placeholder={t("sandbox.statusFilter")}
          style={{ minWidth: 260 }}
          value={states}
          onChange={setStates}
          options={STATE_OPTIONS.map((s) => ({ value: s, label: s }))}
          maxTagCount="responsive"
        />
        <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
          {t("common.refresh")}
        </Button>
        {writable && (
          <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateOpen(true)}>
            {t("sandbox.create")}
          </Button>
        )}
      </Space>

      {writable && selected.length > 0 && (
        <div className="sh-batchbar">
          <span>
            {t("sandbox.selected")} {selected.length}
          </span>
          <Space>
            <Button size="small" onClick={() => batch("pause")}>{t("sandbox.batchPause")}</Button>
            <Button size="small" onClick={() => batch("renew")}>{t("sandbox.batchRenew")}</Button>
            <Popconfirm title={`${t("sandbox.batchDestroy")}?`} onConfirm={() => batch("delete")}>
              <Button size="small" danger>{t("sandbox.batchDestroy")}</Button>
            </Popconfirm>
            <Button size="small" type="text" onClick={() => setSelected([])}>{t("sandbox.clearSelection")}</Button>
          </Space>
        </div>
      )}

      <Table
        rowKey="sandbox_id"
        loading={isLoading}
        dataSource={data?.items || []}
        pagination={{ pageSize: 20, total: data?.total }}
        rowSelection={writable ? { selectedRowKeys: selected, onChange: (keys) => setSelected(keys as string[]) } : undefined}
        columns={[
          {
            title: t("common.name"),
            dataIndex: "name",
            render: (v, r: any) => <Link to={`/sandboxes/${r.sandbox_id}`}>{v || r.sandbox_id.slice(0, 8)}</Link>,
          },
          { title: t("common.status"), dataIndex: "state", render: (s) => <Tag color={stateColor[s] || "default"}>{s}</Tag> },
          { title: t("common.image"), dataIndex: "image", ellipsis: true },
          { title: t("common.cpu"), dataIndex: "cpu", width: 80 },
          { title: t("common.memory"), dataIndex: "memory", width: 90 },
          { title: t("common.expires"), dataIndex: "expires_at", render: (v) => (v ? new Date(v).toLocaleString() : "-") },
          {
            title: t("common.actions"),
            width: 260,
            render: (_, r: any) => (
              <Space size="small">
                <Link to={`/sandboxes/${r.sandbox_id}`}>{t("common.detail")}</Link>
                {writable && r.state === "Running" && <a onClick={() => act.mutate({ id: r.sandbox_id, action: "pause" })}>{t("sandbox.pause")}</a>}
                {writable && r.state === "Paused" && <a onClick={() => act.mutate({ id: r.sandbox_id, action: "resume" })}>{t("sandbox.resume")}</a>}
                {writable && <a onClick={() => act.mutate({ id: r.sandbox_id, action: "renew", body: { timeout_seconds: 1800 } })}>{t("sandbox.renew")}</a>}
                {writable && (
                  <Popconfirm title={`${t("sandbox.destroy")}?`} onConfirm={() => del.mutate(r.sandbox_id)}>
                    <a style={{ color: "var(--bad)" }}>{t("sandbox.destroy")}</a>
                  </Popconfirm>
                )}
              </Space>
            ),
          },
        ]}
      />

      <CreateSandboxModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        onCreated={(sid) => {
          invalidate();
          nav(`/sandboxes/${sid}`);
        }}
      />
    </div>
  );
}
