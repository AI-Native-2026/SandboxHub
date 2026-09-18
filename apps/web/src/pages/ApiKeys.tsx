import { useState } from "react";
import {
  Alert, Button, Card, Empty, Form, Input, InputNumber, Modal, Popconfirm, Space, Table, Tag, Tooltip, Typography, message,
} from "antd";
import { CopyOutlined, PlusOutlined, ReloadOutlined } from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createApiKey, listApiKeys, revokeApiKey } from "../api";
import {tr,  useI18n } from "../i18n";
import PageHeader from "../components/PageHeader";

function Copyable({ text }: { text: string }) {
  return (
    <Space size={4}>
      <Typography.Text code>{text}</Typography.Text>
      <Tooltip title="Copy">
        <Button
          size="small"
          type="text"
          icon={<CopyOutlined />}
          onClick={() => {
            navigator.clipboard.writeText(text);
            message.success("copied");
          }}
        />
      </Tooltip>
    </Space>
  );
}

export default function ApiKeys() {
  const { t } = useI18n();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [newKey, setNewKey] = useState<string | null>(null);
  const [form] = Form.useForm();
  const { data, isLoading, refetch } = useQuery({ queryKey: ["api-keys"], queryFn: listApiKeys });

  const create = useMutation({
    mutationFn: (v: any) => createApiKey(v.name, v.expires_in_days ?? null),
    onSuccess: (d) => {
      setNewKey(d.api_key);
      setOpen(false);
      form.resetFields();
      qc.invalidateQueries({ queryKey: ["api-keys"] });
    },
    onError: (e: any) => message.error(e?.response?.data?.error?.message || "failed"),
  });

  const revoke = useMutation({
    mutationFn: (id: string) => revokeApiKey(id),
    onSuccess: () => {
      message.success(t("common.save"));
      qc.invalidateQueries({ queryKey: ["api-keys"] });
    },
  });

  return (
    <div>
      <PageHeader
        eyebrow="Developer"
        title={t("apikeys.title")}
        subtitle={t("apikeys.subtitle")}
        actions={
          <Space>
            <Button icon={<ReloadOutlined />} onClick={() => refetch()}>{t("common.refresh")}</Button>
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>{t("apikeys.new")}</Button>
          </Space>
        }
      />

      <Alert
        type="warning"
        showIcon
        style={{ marginBottom: 16 }}
        message={t("apikeys.subtitle")}
      />

      {newKey && (
        <Alert
          type="success"
          showIcon
          style={{ marginBottom: 16 }}
          message={tr("密钥已生成（仅显示一次）")}
          description={<Copyable text={newKey} />}
          closable
          onClose={() => setNewKey(null)}
        />
      )}

      <Card title={t("apikeys.mine")}>
        {(!data || data.length === 0) && !isLoading ? (
          <Empty description={t("common.none")} />
        ) : (
          <Table
            rowKey="id"
            loading={isLoading}
            dataSource={data || []}
            pagination={false}
            columns={[
              { title: t("common.name"), dataIndex: "name" },
              { title: "Prefix", dataIndex: "prefix", render: (v: string) => <Typography.Text code>{v}…</Typography.Text> },
              {
                title: t("common.status"),
                dataIndex: "status",
                render: (s: string) => <Tag color={s === "active" ? "green" : "default"}>{s}</Tag>,
              },
              { title: t("common.createdAt"), dataIndex: "created_at", render: (v) => (v ? new Date(v).toLocaleString() : "-") },
              {
                title: "Expires",
                dataIndex: "expires_at",
                render: (v: string | null) => (v ? new Date(v).toLocaleDateString() : tr("永久 / never")),
              },
              { title: "Last used", dataIndex: "last_used_at", render: (v) => (v ? new Date(v).toLocaleString() : "-") },
              {
                title: t("common.actions"),
                width: 100,
                render: (_: any, r: any) =>
                  r.status === "active" ? (
                    <Popconfirm title={`${t("common.delete")}?`} onConfirm={() => revoke.mutate(r.id)}>
                      <a style={{ color: "var(--bad)" }}>Revoke</a>
                    </Popconfirm>
                  ) : null,
              },
            ]}
          />
        )}
      </Card>

      <Modal
        open={open}
        title={t("apikeys.new")}
        onCancel={() => setOpen(false)}
        onOk={() => form.validateFields().then((v) => create.mutate(v))}
        confirmLoading={create.isPending}
        okText={t("common.create")}
      >
        <Form form={form} layout="vertical">
          <Form.Item label={t("common.name")} name="name" rules={[{ required: true, message: "required" }]}>
            <Input placeholder="ci-runner / local-dev" maxLength={64} />
          </Form.Item>
          <Form.Item label={tr("有效期（天，留空为永久）")} name="expires_in_days">
            <InputNumber min={1} max={3650} style={{ width: 200 }} placeholder={tr("永久")} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
