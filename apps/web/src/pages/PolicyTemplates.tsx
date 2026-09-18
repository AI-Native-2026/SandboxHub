import { useState } from "react";
import { Button, Card, Form, Input, Modal, Popconfirm, Select, Table, Tag, message } from "antd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createPolicyTemplate, deletePolicyTemplate, listPolicyTemplates } from "../api";
import { hasRole } from "../auth";
import PageHeader from "../components/PageHeader";
import {tr,  useI18n } from "../i18n";

export default function PolicyTemplates() {
  const { t } = useI18n();
  const qc = useQueryClient();
  const isAdmin = hasRole("platform-admin");
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();
  const { data, isLoading } = useQuery({ queryKey: ["policy-templates"], queryFn: listPolicyTemplates });

  const create = useMutation({
    mutationFn: (v: any) => createPolicyTemplate({ name: v.name, default_action: v.default_action, rules: v.rules }),
    onSuccess: () => {
      message.success(tr("已创建"));
      setOpen(false);
      qc.invalidateQueries({ queryKey: ["policy-templates"] });
    },
  });
  const del = useMutation({
    mutationFn: (id: string) => deletePolicyTemplate(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["policy-templates"] }),
  });

  return (
    <div>
      <PageHeader
        eyebrow="Governance"
        title={t("policy.title")}
        subtitle={t("policy.subtitle")}
        actions={isAdmin ? <Button type="primary" onClick={() => setOpen(true)}>{t("policy.new")}</Button> : null}
      />
      <Card>
        <Table
          rowKey="id"
          loading={isLoading}
          dataSource={data || []}
          pagination={false}
          columns={[
            { title: tr("名称"), dataIndex: "name" },
            { title: tr("默认动作"), dataIndex: "default_action", render: (v) => <Tag color={v === "deny" ? "red" : "green"}>{v}</Tag> },
            { title: tr("规则"), dataIndex: "rules", render: (r: any[]) => (r || []).map((x, i) => <Tag key={i}>{`${x.action} ${x.target}`}</Tag>) },
            {
              title: tr("操作"),
              render: (_: any, r: any) =>
                isAdmin ? (
                  <Popconfirm title={tr("删除？")} onConfirm={() => del.mutate(r.id)}>
                    <a style={{ color: "var(--bad)" }}>{tr("删除")}</a>
                  </Popconfirm>
                ) : null,
            },
          ]}
        />
      </Card>
      <Modal open={open} title={tr("新建策略模板")} onCancel={() => setOpen(false)} onOk={() => form.validateFields().then((v) => {
        const action = v.default_action === "allow" ? "deny" : "allow";
        const rules = (v.rulesText || "").split("\n").map((s: string) => s.trim()).filter(Boolean).map((target: string) => ({ action, target }));
        create.mutate({ name: v.name, default_action: v.default_action, rules });
      })}>
        <Form form={form} layout="vertical" initialValues={{ default_action: "deny" }}>
          <Form.Item label={tr("名称")} name="name" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item label={tr("默认动作")} name="default_action" rules={[{ required: true }]}>
            <Select
              options={[
                { value: "deny", label: tr("deny（默认拒绝，仅放行白名单）") },
                { value: "allow", label: tr("allow（默认放行，按规则拦截）") },
              ]}
            />
          </Form.Item>
          <Form.Item label={tr("规则目标（每行一个，支持 *.example.com）")} name="rulesText" extra={tr("deny 模板填放行域名；allow 模板填拦截域名")}>
            <Input.TextArea rows={4} placeholder={"*.pythonhosted.org\nexample.com"} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
