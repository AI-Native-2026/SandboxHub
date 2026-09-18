import { useState } from "react";
import { Button, Card, Form, Input, Modal, Popconfirm, Select, Space, Table, Tag, message } from "antd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createRole, deleteRole, getRbac } from "../api";
import { hasRole } from "../auth";
import { useI18n } from "../i18n";
import PageHeader from "../components/PageHeader";

const RESOURCES = ["sandbox", "template", "credential", "policy", "tenant", "audit", "recording"];
const ACTIONS = ["view", "create", "update", "delete"];
const PERMISSION_OPTIONS = RESOURCES.flatMap((r) =>
  ACTIONS.map((a) => ({ value: `${r}:${a}`, label: `${r}:${a}` }))
);

export default function Rbac() {
  const { t } = useI18n();
  const qc = useQueryClient();
  const isAdmin = hasRole("platform-admin");
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();
  const { data } = useQuery({ queryKey: ["rbac"], queryFn: getRbac });

  const create = useMutation({
    mutationFn: (v: any) => createRole({ name: v.name, permissions: v.permissions }),
    onSuccess: () => {
      message.success(t("common.save"));
      setOpen(false);
      qc.invalidateQueries({ queryKey: ["rbac"] });
    },
  });
  const del = useMutation({
    mutationFn: (id: string) => deleteRole(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["rbac"] }),
  });

  return (
    <div>
      <PageHeader
        eyebrow="Security"
        title={t("rbac.title")}
        subtitle={t("rbac.subtitle")}
        actions={isAdmin ? <Button type="primary" onClick={() => setOpen(true)}>{t("rbac.new")}</Button> : null}
      />
      <Card title={t("rbac.custom")}>
        <Table
          rowKey="id"
          size="small"
          dataSource={data?.custom || []}
          pagination={false}
          columns={[
            { title: t("common.name"), dataIndex: "name" },
            {
              title: "Permissions",
              dataIndex: "permissions",
              render: (p: string[]) => (
                <Space wrap>
                  {(p || []).map((x) => (
                    <Tag key={x}>{x}</Tag>
                  ))}
                </Space>
              ),
            },
            {
              title: t("common.actions"),
              width: 100,
              render: (_: any, r: any) =>
                isAdmin ? (
                  <Popconfirm title={`${t("common.delete")}?`} onConfirm={() => del.mutate(r.id)}>
                    <a style={{ color: "var(--bad)" }}>{t("common.delete")}</a>
                  </Popconfirm>
                ) : null,
            },
          ]}
        />
      </Card>
      <Modal
        open={open}
        title={t("rbac.new")}
        onCancel={() => setOpen(false)}
        onOk={() => form.validateFields().then((v) => create.mutate(v))}
        confirmLoading={create.isPending}
        width={620}
      >
        <Form form={form} layout="vertical">
          <Form.Item label={t("common.name")} name="name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label="Permissions" name="permissions" rules={[{ required: true, message: "select at least one" }]}>
            <Select
              mode="multiple"
              allowClear
              placeholder="sandbox:view, sandbox:create ..."
              options={PERMISSION_OPTIONS}
              optionFilterProp="label"
              maxTagCount="responsive"
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
