import { useState } from "react";
import { Button, Card, Form, Input, Modal, Popconfirm, Select, Space, Table, message } from "antd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { collectArtifact, deleteArtifact, listArtifacts, listSandboxes } from "../api";
import { keycloak } from "../auth";
import PageHeader from "../components/PageHeader";
import {tr,  useI18n } from "../i18n";

export default function Artifacts() {
  const { t } = useI18n();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [form] = Form.useForm();
  const { data, isLoading } = useQuery({ queryKey: ["artifacts"], queryFn: listArtifacts });
  const sandboxes = useQuery({
    queryKey: ["sandboxes-for-artifact"],
    queryFn: () => listSandboxes({ page: 1, size: 200 }),
    enabled: open,
  });

  const collect = useMutation({
    mutationFn: (v: any) => collectArtifact(v),
    onSuccess: () => {
      message.success(tr("已收集产物"));
      setOpen(false);
      qc.invalidateQueries({ queryKey: ["artifacts"] });
    },
    onError: (e: any) => message.error(e?.response?.data?.error?.message || tr("收集失败")),
  });
  const del = useMutation({
    mutationFn: (id: string) => deleteArtifact(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["artifacts"] }),
  });

  const download = async (a: any) => {
    const resp = await fetch(`/api/v1/artifacts/${a.id}/download`, {
      headers: {
        Authorization: `Bearer ${keycloak.token}`,
        "X-Tenant-Id": localStorage.getItem("tenantId") || "",
      },
    });
    const blob = await resp.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = a.name;
    link.click();
    URL.revokeObjectURL(url);
  };
  return (
    <div>
      <PageHeader
        eyebrow="Intelligence"
        title={t("artifacts.title")}
        subtitle={t("artifacts.subtitle")}
        actions={<Button type="primary" onClick={() => setOpen(true)}>{t("artifacts.collect")}</Button>}
      />
      <Card>
        <Table
          rowKey="id"
          loading={isLoading}
          dataSource={data || []}
          pagination={false}
          columns={[
            { title: tr("名称"), dataIndex: "name" },
            { title: tr("沙箱"), dataIndex: "sandbox_id", ellipsis: true },
            { title: tr("路径"), dataIndex: "path", ellipsis: true },
            { title: tr("大小"), dataIndex: "size", render: (v) => `${v} B` },
            { title: tr("类型"), dataIndex: "content_type", ellipsis: true },
            {
              title: tr("操作"),
              render: (_: any, r: any) => (
                <Space>
                  <a onClick={() => download(r)}>{tr("下载")}</a>
                  <Popconfirm title={tr("删除？")} onConfirm={() => del.mutate(r.id)}>
                    <a style={{ color: "var(--bad)" }}>{tr("删除")}</a>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      </Card>
      <Modal open={open} title={tr("从沙箱收集产物")} onCancel={() => setOpen(false)} onOk={() => form.validateFields().then((v) => collect.mutate(v))}>
        <Form form={form} layout="vertical">
          <Form.Item label="Sandbox" name="sandbox_id" rules={[{ required: true, message: tr("请选择沙箱") }]}>
            <Select
              showSearch
              optionFilterProp="label"
              placeholder={tr("请选择沙箱")}
              loading={sandboxes.isLoading}
              options={(sandboxes.data?.items || []).map((s: any) => ({
                value: s.sandbox_id,
                label: `${s.name || s.sandbox_id.slice(0, 8)} · ${s.state}`,
              }))}
            />
          </Form.Item>
          <Form.Item label={tr("文件路径")} name="path" rules={[{ required: true }]}><Input placeholder="/workspace/squares.csv" /></Form.Item>
          <Form.Item label={tr("名称（可选）")} name="name"><Input /></Form.Item>
        </Form>
      </Modal>
    </div>
  );
}
