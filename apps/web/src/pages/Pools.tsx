import { useState } from "react";
import { Alert, Button, Card, Col, Form, Input, InputNumber, Modal, Popconfirm, Row, Select, Space, Statistic, Table, Tag, message } from "antd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createPool, deletePool, listPoolProviders, listPools, observability } from "../api";
import { hasRole } from "../auth";
import { useI18n } from "../i18n";
import PageHeader from "../components/PageHeader";
import TrendChart from "../components/TrendChart";

export default function Pools() {
  const { t } = useI18n();
  const qc = useQueryClient();
  const isAdmin = hasRole("platform-admin");
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();
  const pools = useQuery({ queryKey: ["pools"], queryFn: listPools });
  const providers = useQuery({ queryKey: ["pool-providers"], queryFn: listPoolProviders });
  const obs = useQuery({ queryKey: ["observability"], queryFn: () => observability(7), refetchInterval: 15000 });

  const create = useMutation({
    mutationFn: (v: any) =>
      createPool({ name: v.name, provider: v.provider, image: v.image, capacity: { min: v.min, max: v.max } }),
    onSuccess: () => {
      message.success(t("common.save"));
      setOpen(false);
      qc.invalidateQueries({ queryKey: ["pools"] });
    },
  });
  const del = useMutation({
    mutationFn: (id: string) => deletePool(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["pools"] }),
  });

  const byState = obs.data?.sandboxes?.by_state || {};
  const ts = obs.data?.timeseries || [];

  return (
    <div>
      <PageHeader
        eyebrow="Scale"
        title={t("pools.title")}
        subtitle={t("pools.subtitle")}
        actions={isAdmin ? <Button type="primary" onClick={() => setOpen(true)}>{t("pools.new")}</Button> : null}
      />
      <Row gutter={16}>
        <Col span={6}><Card className="sh-stat"><Statistic title={t("header.tenant")} value={obs.data?.tenants ?? 0} /></Card></Col>
        <Col span={6}><Card className="sh-stat"><Statistic title="Users" value={obs.data?.users ?? 0} /></Card></Col>
        <Col span={6}><Card className="sh-stat"><Statistic title={t("nav.sandboxes")} value={obs.data?.sandboxes?.total ?? 0} /></Card></Col>
        <Col span={6}><Card className="sh-stat"><Statistic title="Running" value={obs.data?.sandboxes?.running ?? 0} /></Card></Col>
      </Row>

      <Card title="Usage trend" style={{ marginTop: 16 }}>
        {ts.length === 0 ? (
          <div style={{ color: "var(--text-faint)", padding: 24, textAlign: "center" }}>{t("common.none")}</div>
        ) : (
          <TrendChart
            x={ts.map((d: any) => d.date)}
            series={[
              { name: t("usage.cpuHours"), data: ts.map((d: any) => d.cpu_hours) },
              { name: t("usage.memGbHours"), data: ts.map((d: any) => d.mem_gb_hours) },
            ]}
          />
        )}
      </Card>

      <Card title={t("common.status")} style={{ marginTop: 16 }}>
        {Object.entries(byState).map(([k, v]) => (
          <Tag key={k} style={{ marginBottom: 4 }} color={k === "Running" ? "green" : k === "Failed" ? "red" : "blue"}>
            {k}: {v as number}
          </Tag>
        ))}
        {Object.keys(byState).length === 0 && <span style={{ color: "var(--text-faint)" }}>{t("common.none")}</span>}
      </Card>

      <Card title={t("pools.title")} style={{ marginTop: 16 }}>
        <Alert type="info" showIcon style={{ marginBottom: 12 }} message={t("pools.assocHint")} />
        <Table
          rowKey="id"
          size="small"
          loading={pools.isLoading}
          dataSource={pools.data || []}
          pagination={false}
          columns={[
            { title: t("common.name"), dataIndex: "name" },
            { title: "Provider", dataIndex: "provider", render: (v) => <Tag>{v}</Tag> },
            { title: t("common.image"), dataIndex: "image", ellipsis: true },
            { title: t("pools.warm"), dataIndex: "capacity", render: (c: any) => c?.min ?? 0 },
            { title: t("pools.usage"), dataIndex: "used", render: (used: number, r: any) => `${used ?? 0} / ${r.capacity?.max ?? "-"}` },
            { title: t("common.status"), dataIndex: "status" },
            {
              title: t("common.actions"),
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
        title={t("pools.new")}
        onCancel={() => setOpen(false)}
        onOk={() => form.validateFields().then((v) => create.mutate(v))}
        confirmLoading={create.isPending}
      >
        <Form form={form} layout="vertical" initialValues={{ provider: "docker", min: 0, max: 5 }}>
          <Form.Item label={t("common.name")} name="name" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item label="Provider" name="provider" rules={[{ required: true }]}>
            <Select
              options={(providers.data || []).map((p: any) => ({
                value: p.value,
                label: `${p.label} — ${p.description}`,
              }))}
            />
          </Form.Item>
          <Form.Item label={t("common.image")} name="image"><Input placeholder="python:3.12" /></Form.Item>
          <Space>
            <Form.Item label="Min warm" name="min"><InputNumber /></Form.Item>
            <Form.Item label="Max capacity" name="max"><InputNumber /></Form.Item>
          </Space>
        </Form>
      </Modal>
    </div>
  );
}
