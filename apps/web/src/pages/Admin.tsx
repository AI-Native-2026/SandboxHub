import { useState } from "react";
import { Button, Card, Col, Form, Input, InputNumber, Modal, Popconfirm, Row, Space, Statistic, Table, Tabs, Tag, message } from "antd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  adminAddMember, adminAudit, adminCleanup, adminCreateTenant, adminMembers, adminMetrics, adminPatchTenant, adminRemoveMember, adminTenants,
} from "../api";
import {tr,  useI18n } from "../i18n";

function Tenants() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({ queryKey: ["admin-tenants"], queryFn: adminTenants });
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();
  const [memberTenant, setMemberTenant] = useState<any>(null);
  const [memberForm] = Form.useForm();

  const create = useMutation({
    mutationFn: (v: any) => adminCreateTenant(v),
    onSuccess: () => {
      message.success(tr("已创建"));
      setOpen(false);
      qc.invalidateQueries({ queryKey: ["admin-tenants"] });
    },
    onError: (e: any) => message.error(e?.response?.data?.error?.message || tr("创建失败")),
  });
  const patch = useMutation({
    mutationFn: ({ id, body }: any) => adminPatchTenant(id, body),
    onSuccess: () => {
      message.success(tr("已更新"));
      qc.invalidateQueries({ queryKey: ["admin-tenants"] });
    },
  });
  return (
    <div>
      <Space style={{ marginBottom: 16, justifyContent: "space-between", width: "100%" }}>
        <b>{tr("租户管理")}</b>
        <Button type="primary" onClick={() => setOpen(true)}>{tr("新建租户")}</Button>
      </Space>
      <Table
        rowKey="id"
        loading={isLoading}
        dataSource={data || []}
        pagination={false}
        columns={[
          { title: "Slug", dataIndex: "slug" },
          { title: tr("名称"), dataIndex: "name" },
          { title: tr("状态"), dataIndex: "status", render: (s) => <Tag color={s === "active" ? "green" : "red"}>{s}</Tag> },
          { title: tr("沙箱数"), dataIndex: "sandbox_count" },
          { title: tr("成员数"), dataIndex: "member_count" },
          { title: tr("配额"), render: (_: any, r: any) => `${r.quota.cpu} / ${r.quota.memory} / ${r.quota.sandboxes}` },
          {
            title: tr("操作"),
            render: (_: any, r: any) => (
              <Space>
                <a onClick={() => setMemberTenant(r)}>{tr("成员")}</a>
                {r.status === "active" ? (
                  <a onClick={() => patch.mutate({ id: r.id, body: { status: "suspended" } })}>{tr("停用")}</a>
                ) : (
                  <a onClick={() => patch.mutate({ id: r.id, body: { status: "active" } })}>{tr("启用")}</a>
                )}
              </Space>
            ),
          },
        ]}
      />
      <Modal open={open} title={tr("新建租户")} onCancel={() => setOpen(false)} onOk={() => form.validateFields().then((v) => create.mutate(v))}>
        <Form form={form} layout="vertical" initialValues={{ quota_cpu: "16", quota_memory: "32Gi", quota_sandboxes: 20 }}>
          <Form.Item label="Slug" name="slug" rules={[{ required: true }]}>
            <Input placeholder="team-a" />
          </Form.Item>
          <Form.Item label={tr("名称")} name="name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Space>
            <Form.Item label={tr("CPU 配额")} name="quota_cpu"><Input style={{ width: 110 }} /></Form.Item>
            <Form.Item label={tr("内存配额")} name="quota_memory"><Input style={{ width: 110 }} /></Form.Item>
            <Form.Item label={tr("沙箱上限")} name="quota_sandboxes"><InputNumber /></Form.Item>
          </Space>
        </Form>
      </Modal>
      <MemberModal tenant={memberTenant} form={memberForm} onClose={() => setMemberTenant(null)} />
    </div>
  );
}

function MemberModal({ tenant, form, onClose }: any) {
  const qc = useQueryClient();
  const { data } = useQuery({
    queryKey: ["members", tenant?.id],
    queryFn: () => adminMembers(tenant.id),
    enabled: !!tenant,
  });
  const add = useMutation({
    mutationFn: (v: any) => adminAddMember(tenant.id, v),
    onSuccess: () => {
      message.success(tr("已添加"));
      qc.invalidateQueries({ queryKey: ["members", tenant.id] });
    },
    onError: (e: any) => message.error(e?.response?.data?.error?.message || tr("添加失败")),
  });
  const remove = useMutation({
    mutationFn: (uid: string) => adminRemoveMember(tenant.id, uid),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["members", tenant.id] }),
  });
  return (
    <Modal open={!!tenant} title={`${tr("成员")} · ${tenant?.name || ""}`} onCancel={onClose} footer={null} width={680}>
      <Space style={{ marginBottom: 12 }}>
        <Form form={form} layout="inline" onFinish={(v) => add.mutate(v)} initialValues={{ role: "developer" }}>
          <Form.Item name="email" rules={[{ required: true, message: tr("邮箱") }]}>
            <Input placeholder="user@example.com" style={{ width: 240 }} />
          </Form.Item>
          <Form.Item name="role">
            <Input placeholder="role" style={{ width: 140 }} />
          </Form.Item>
          <Button type="primary" htmlType="submit">{tr("添加")}</Button>
        </Form>
      </Space>
      <Table
        rowKey="user_id"
        size="small"
        dataSource={data || []}
        pagination={false}
        columns={[
          { title: tr("邮箱"), dataIndex: "email" },
          { title: tr("名称"), dataIndex: "display_name" },
          { title: tr("角色"), dataIndex: "role" },
          {
            title: tr("操作"),
            render: (_: any, r: any) => (
              <Popconfirm title={tr("移除？")} onConfirm={() => remove.mutate(r.user_id)}>
                <a style={{ color: "var(--bad)" }}>{tr("移除")}</a>
              </Popconfirm>
            ),
          },
        ]}
      />
    </Modal>
  );
}

function Audit() {
  const [action, setAction] = useState("");
  const { data, isLoading, refetch } = useQuery({
    queryKey: ["admin-audit", action],
    queryFn: () => adminAudit({ action: action || undefined, limit: 200 }),
  });
  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Input.Search placeholder={tr("按 action 过滤")} allowClear onSearch={setAction} style={{ width: 260 }} />
        <Button onClick={() => refetch()}>{tr("刷新")}</Button>
      </Space>
      <Table
        rowKey={(r: any) => `${r.ts}-${r.action}-${r.resource_id}`}
        size="small"
        loading={isLoading}
        dataSource={data || []}
        pagination={{ pageSize: 20 }}
        columns={[
          { title: tr("时间"), dataIndex: "ts", render: (v) => (v ? new Date(v).toLocaleString() : "-"), width: 180 },
          { title: tr("动作"), dataIndex: "action", width: 200 },
          { title: tr("资源"), dataIndex: "resource_id", ellipsis: true },
          { title: tr("结果"), dataIndex: "result", width: 90 },
          { title: "IP", dataIndex: "ip", width: 140 },
        ]}
      />
    </div>
  );
}

function Metrics() {
  const { data } = useQuery({ queryKey: ["admin-metrics"], queryFn: adminMetrics, refetchInterval: 5000 });
  const cleanup = useMutation({
    mutationFn: () => adminCleanup(),
    onSuccess: (r: any) => message.success(`${tr("对账并清理")}: ${tr("标记")} ${r.marked}, ${tr("清理")} ${r.purged}`),
  });
  return (
    <div>
      <Space style={{ marginBottom: 12 }}>
        <Button loading={cleanup.isPending} onClick={() => cleanup.mutate()}>{tr("立即对账并清理已终止沙箱")}</Button>
      </Space>
      <Row gutter={16}>
        <Col span={6}><Card><Statistic title={tr("租户")} value={data?.tenants ?? 0} /></Card></Col>
        <Col span={6}><Card><Statistic title={tr("用户")} value={data?.users ?? 0} /></Card></Col>
        <Col span={6}><Card><Statistic title={tr("沙箱总数")} value={data?.sandboxes ?? 0} /></Card></Col>
        <Col span={6}><Card><Statistic title={tr("运行中")} value={data?.active_sandboxes ?? 0} valueStyle={{ color: "var(--ok)" }} /></Card></Col>
      </Row>
    </div>
  );
}

export default function Admin() {
  const { t } = useI18n();
  return (
    <Card>
      <Tabs
        items={[
          { key: "tenants", label: t("admin.tenants"), children: <Tenants /> },
          { key: "audit", label: t("admin.audit"), children: <Audit /> },
          { key: "metrics", label: t("admin.metrics"), children: <Metrics /> },
        ]}
      />
    </Card>
  );
}
