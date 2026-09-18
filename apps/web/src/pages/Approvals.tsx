import { useState } from "react";
import { Button, Card, Form, Input, Modal, Space, Table, Tabs, Tag, message } from "antd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createApproval, decideApproval, listApprovals } from "../api";
import { hasRole } from "../auth";
import PageHeader from "../components/PageHeader";
import {tr,  useI18n } from "../i18n";

const statusColor: Record<string, string> = { pending: "orange", approved: "green", rejected: "red" };

export default function Approvals() {
  const { t } = useI18n();
  const qc = useQueryClient();
  const [tab, setTab] = useState("mine");
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();
  const isApprover = hasRole("platform-admin") || hasRole("tenant-admin");

  const mine = useQuery({ queryKey: ["approvals", "mine"], queryFn: () => listApprovals("mine") });
  const pending = useQuery({
    queryKey: ["approvals", "pending"],
    queryFn: () => listApprovals("pending"),
    enabled: isApprover,
  });

  const create = useMutation({
    mutationFn: (v: any) => createApproval({ kind: v.kind, reason: v.reason, payload: { detail: v.detail } }),
    onSuccess: () => {
      message.success(tr("已提交申请"));
      setOpen(false);
      qc.invalidateQueries({ queryKey: ["approvals"] });
    },
  });
  const decide = useMutation({
    mutationFn: ({ id, approve }: any) => decideApproval(id, approve),
    onSuccess: () => {
      message.success(tr("已处理"));
      qc.invalidateQueries({ queryKey: ["approvals"] });
    },
  });
  const columns = (approvable: boolean) => [
    { title: tr("类型"), dataIndex: "kind" },
    { title: tr("理由"), dataIndex: "reason", ellipsis: true },
    { title: tr("状态"), dataIndex: "status", render: (s: string) => <Tag color={statusColor[s]}>{s}</Tag> },
    { title: tr("提交时间"), dataIndex: "created_at", render: (v: string) => (v ? new Date(v).toLocaleString() : "-") },
    ...(approvable
      ? [{
          title: tr("操作"),
          render: (_: any, r: any) =>
            r.status === "pending" ? (
              <Space>
                <a onClick={() => decide.mutate({ id: r.id, approve: true })}>{tr("批准")}</a>
                <a style={{ color: "var(--bad)" }} onClick={() => decide.mutate({ id: r.id, approve: false })}>{tr("驳回")}</a>
              </Space>
            ) : null,
        }]
      : []),
  ];

  return (
    <div>
      <PageHeader
        eyebrow="Governance"
        title={t("approval.title")}
        subtitle={t("approval.subtitle")}
        actions={<Button type="primary" onClick={() => setOpen(true)}>{t("approval.new")}</Button>}
      />
      <Card>
        <Tabs
          activeKey={tab}
          onChange={setTab}
          items={[
            { key: "mine", label: t("approval.mine"), children: <Table rowKey="id" size="small" loading={mine.isLoading} dataSource={mine.data || []} columns={columns(false) as any} pagination={false} /> },
            ...(isApprover
              ? [{ key: "pending", label: t("approval.pending"), children: <Table rowKey="id" size="small" loading={pending.isLoading} dataSource={pending.data || []} columns={columns(true) as any} pagination={false} /> }]
              : []),
          ]}
        />
      </Card>
      <Modal open={open} title={tr("发起申请")} onCancel={() => setOpen(false)} onOk={() => form.validateFields().then((v) => create.mutate(v))}>
        <Form form={form} layout="vertical" initialValues={{ kind: "quota" }}>
          <Form.Item label={tr("类型")} name="kind" rules={[{ required: true }]}>
            <Input placeholder="quota / allowlist / template" />
          </Form.Item>
          <Form.Item label={tr("详情")} name="detail"><Input /></Form.Item>
          <Form.Item label={tr("理由")} name="reason" rules={[{ required: true }]}><Input.TextArea rows={3} /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
