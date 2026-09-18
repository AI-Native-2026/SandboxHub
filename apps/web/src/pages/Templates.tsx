import { useState } from "react";
import { Button, Card, Form, Input, Modal, Popconfirm, Space, Table, Tag, message } from "antd";
import { PlusOutlined } from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createTemplate, deleteTemplate, listTemplates, updateTemplate } from "../api";
import { hasRole } from "../auth";
import {tr,  useI18n } from "../i18n";

export default function Templates() {
  const { t } = useI18n();
  const qc = useQueryClient();
  const isAdmin = hasRole("platform-admin");
  const [open, setOpen] = useState(false);
  const [editing, setEditing] = useState<any>(null);
  const [form] = Form.useForm();

  const { data, isLoading } = useQuery({ queryKey: ["templates"], queryFn: listTemplates });

  const save = useMutation({
    mutationFn: (v: any) =>
      editing ? updateTemplate(editing.id, v) : createTemplate(v),
    onSuccess: () => {
      message.success(tr("已保存"));
      setOpen(false);
      setEditing(null);
      qc.invalidateQueries({ queryKey: ["templates"] });
    },
    onError: (e: any) => message.error(e?.response?.data?.error?.message || tr("保存失败")),
  });
  const del = useMutation({
    mutationFn: (id: string) => deleteTemplate(id),
    onSuccess: () => {
      message.success(tr("已删除"));
      qc.invalidateQueries({ queryKey: ["templates"] });
    },
  });
  const openEdit = (t: any) => {
    setEditing(t);
    form.setFieldsValue(t);
    setOpen(true);
  };
  return (
    <div>
      <Space style={{ marginBottom: 16, width: "100%", justifyContent: "space-between" }}>
        <h2 style={{ margin: 0 }}>{t("templates.title")}</h2>
        {isAdmin && (
          <Button
            type="primary"
            icon={<PlusOutlined />}
            onClick={() => {
              setEditing(null);
              form.resetFields();
              setOpen(true);
            }}
          >{tr("新建模板")}</Button>
        )}
      </Space>
      <Table
        rowKey="id"
        loading={isLoading}
        dataSource={data || []}
        pagination={false}
        columns={[
          { title: tr("名称"), dataIndex: "name" },
          { title: tr("镜像"), dataIndex: "image", ellipsis: true },
          { title: "CPU", dataIndex: "default_cpu", width: 80 },
          { title: tr("内存"), dataIndex: "default_memory", width: 90 },
          {
            title: tr("标签"),
            dataIndex: "tags",
            render: (t: string[]) => (t || []).map((x) => <Tag key={x}>{x}</Tag>),
          },
          {
            title: tr("操作"),
            width: 160,
            render: (_: any, r: any) =>
              isAdmin ? (
                <Space>
                  <a onClick={() => openEdit(r)}>{tr("编辑")}</a>
                  <Popconfirm title={tr("删除该模板？")} onConfirm={() => del.mutate(r.id)}>
                    <a style={{ color: "var(--bad)" }}>{tr("删除")}</a>
                  </Popconfirm>
                </Space>
                ) : (
                 <span style={{ color: "var(--text-faint)" }}>—</span>
               ),
          },
        ]}
      />

      <Modal
        open={open}
        title={editing ? tr("编辑模板") : tr("新建模板")}
        onCancel={() => setOpen(false)}
        onOk={() => form.validateFields().then((v) => save.mutate(v))}
        confirmLoading={save.isPending}
        width={640}
      >
        <Form form={form} layout="vertical">
          <Form.Item label={tr("名称")} name="name" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item label={tr("镜像")} name="image" rules={[{ required: true }]}>
            <Input placeholder="python:3.12" />
          </Form.Item>
          <Form.Item label={tr("描述")} name="description">
            <Input />
          </Form.Item>
          <Space>
            <Form.Item label={tr("默认 CPU")} name="default_cpu">
              <Input style={{ width: 120 }} />
            </Form.Item>
            <Form.Item label={tr("默认内存")} name="default_memory">
              <Input style={{ width: 120 }} />
            </Form.Item>
            <Form.Item label={tr("默认超时(秒)")} name="default_timeout_seconds">
              <Input style={{ width: 140 }} />
            </Form.Item>
          </Space>
        </Form>
      </Modal>
    </div>
  );
}
