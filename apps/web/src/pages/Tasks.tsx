import { useState } from "react";
import { Button, Card, Drawer, Form, Input, InputNumber, Modal, Popconfirm, Space, Table, Tag, message } from "antd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { createTask, deleteTask, getTask, listTasks } from "../api";
import PageHeader from "../components/PageHeader";
import {tr,  useI18n } from "../i18n";

const statusColor: Record<string, string> = { pending: "default", running: "blue", completed: "green" };

export default function Tasks() {
  const { t } = useI18n();
  const qc = useQueryClient();
  const [open, setOpen] = useState(false);
  const [detailId, setDetailId] = useState<string | null>(null);
  const [form] = Form.useForm();
  const { data, isLoading } = useQuery({ queryKey: ["tasks"], queryFn: listTasks, refetchInterval: 5000 });
  const detail = useQuery({ queryKey: ["task", detailId], queryFn: () => getTask(detailId as string), enabled: !!detailId, refetchInterval: 3000 });

  const create = useMutation({
    mutationFn: (v: any) => createTask(v),
    onSuccess: () => {
      message.success(tr("任务已创建，正在后台执行"));
      setOpen(false);
      qc.invalidateQueries({ queryKey: ["tasks"] });
    },
    onError: (e: any) => message.error(e?.response?.data?.error?.message || tr("创建失败")),
  });
  const del = useMutation({
    mutationFn: (id: string) => deleteTask(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["tasks"] }),
  });

  return (
    <div>
      <PageHeader
        eyebrow="Intelligence"
        title={t("tasks.title")}
        subtitle={t("tasks.subtitle")}
        actions={<Button type="primary" onClick={() => setOpen(true)}>{t("tasks.new")}</Button>}
      />
      <Card>
        <Table
          rowKey="id"
          loading={isLoading}
          dataSource={data || []}
          pagination={false}
          columns={[
            { title: tr("名称"), dataIndex: "name", render: (v, r: any) => <a onClick={() => setDetailId(r.id)}>{v}</a> },
            { title: tr("镜像"), dataIndex: "image", ellipsis: true },
            { title: tr("命令"), dataIndex: "command", ellipsis: true },
            { title: tr("副本"), dataIndex: "replicas", width: 70 },
            { title: tr("状态"), dataIndex: "status", render: (s) => <Tag color={statusColor[s]}>{s}</Tag> },
            { title: tr("成功/失败"), render: (_: any, r: any) => `${r.succeeded} / ${r.failed}` },
            {
              title: tr("操作"),
              render: (_: any, r: any) => (
                <Space>
                  <a onClick={() => setDetailId(r.id)}>{tr("详情")}</a>
                  <Popconfirm title={tr("删除任务记录？")} onConfirm={() => del.mutate(r.id)}>
                    <a style={{ color: "var(--bad)" }}>{tr("删除")}</a>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      </Card>

      <Modal open={open} title={tr("新建任务")} onCancel={() => setOpen(false)} onOk={() => form.validateFields().then((v) => create.mutate(v))}>
        <Form form={form} layout="vertical" initialValues={{ image: "python:3.12", command: "echo hello", replicas: 2 }}>
          <Form.Item label={tr("名称")} name="name" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item label={tr("镜像")} name="image" rules={[{ required: true }]}><Input /></Form.Item>
          <Form.Item label={tr("命令")} name="command" rules={[{ required: true }]}><Input.TextArea rows={2} /></Form.Item>
          <Form.Item label={tr("副本数")} name="replicas"><InputNumber min={1} max={20} /></Form.Item>
        </Form>
      </Modal>

      <Drawer open={!!detailId} title={detail.data?.name || tr("任务详情")} width={720} onClose={() => setDetailId(null)}>
        <Table
          rowKey="id"
          size="small"
          loading={detail.isLoading}
          dataSource={detail.data?.items || []}
          pagination={false}
          columns={[
            { title: tr("沙箱"), dataIndex: "sandbox_id", ellipsis: true },
            { title: tr("状态"), dataIndex: "status", render: (s) => <Tag color={s === "succeeded" ? "green" : "red"}>{s}</Tag> },
            { title: tr("退出码"), dataIndex: "exit_code", width: 80 },
            { title: tr("输出"), dataIndex: "output", ellipsis: true },
          ]}
        />
      </Drawer>
    </div>
  );
}
