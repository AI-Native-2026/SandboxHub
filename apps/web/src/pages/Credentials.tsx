import { useState } from "react";
import { Button, Card, Form, Input, Modal, Popconfirm, Table, Tag, message } from "antd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createCredential, deleteCredential, listCredentials } from "../api";
import { hasRole } from "../auth";
import PageHeader from "../components/PageHeader";
import {tr,  useI18n } from "../i18n";

export default function Credentials() {
  const { t } = useI18n();
  const qc = useQueryClient();
  const isAdmin = hasRole("platform-admin");
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();
  const { data, isLoading } = useQuery({ queryKey: ["credentials"], queryFn: listCredentials });

  const create = useMutation({
    mutationFn: (v: any) => createCredential(v),
    onSuccess: () => {
      message.success(tr("已创建（密钥仅存引用，不回显）"));
      setOpen(false);
      qc.invalidateQueries({ queryKey: ["credentials"] });
    },
    onError: (e: any) => message.error(e?.response?.data?.error?.message || tr("创建失败")),
  });
  const del = useMutation({
    mutationFn: (id: string) => deleteCredential(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["credentials"] }),
  });

  return (
    <div>
      <PageHeader
        eyebrow="Governance"
        title={t("credentials.title")}
        subtitle={t("credentials.subtitle")}
        actions={isAdmin ? <Button type="primary" onClick={() => setOpen(true)}>{t("credentials.new")}</Button> : null}
      />
      <Card>
        <Table
          rowKey="id"
          loading={isLoading}
          dataSource={data || []}
          pagination={false}
          columns={[
            { title: tr("名称"), dataIndex: "name" },
            { title: tr("类型"), dataIndex: "type", render: (t) => <Tag>{t}</Tag> },
            { title: tr("引用"), dataIndex: "secret_ref", render: (v) => v || "—" },
            { title: tr("创建时间"), dataIndex: "created_at", render: (v) => (v ? new Date(v).toLocaleString() : "-") },
            {
              title: tr("操作"),
              render: (_: any, r: any) =>
                isAdmin ? (
                  <Popconfirm title={tr("删除该凭据？")} onConfirm={() => del.mutate(r.id)}>
                    <a style={{ color: "var(--bad)" }}>{tr("删除")}</a>
                  </Popconfirm>
                ) : null,
            },
          ]}
        />
      </Card>
      <Modal open={open} title={tr("新建凭据")} onCancel={() => setOpen(false)} onOk={() => form.validateFields().then((v) => create.mutate(v))}>
        <Form form={form} layout="vertical" initialValues={{ type: "bearer" }}>
          <Form.Item label={tr("名称")} name="name" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item label={tr("类型")} name="type"><Input placeholder="bearer / basic / apiKey" /></Form.Item>
          <Form.Item label={tr("密钥（仅存储引用，不回显）")} name="secret"><Input.Password /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
