import { useEffect, useState } from "react";
import { Form, Input, InputNumber, Modal, Select, Space, Switch, message } from "antd";
import { useMutation, useQuery } from "@tanstack/react-query";
import { createSandbox, listPolicyTemplates, listTemplates } from "../api";
import { tr } from "../i18n";

export default function CreateSandboxModal({
  open,
  onClose,
  onCreated,
}: {
  open: boolean;
  onClose: () => void;
  onCreated?: (sandboxId: string) => void;
}) {
  const [form] = Form.useForm();
  const [denyAll, setDenyAll] = useState(true);
  const [tplSelected, setTplSelected] = useState(false);
  const { data: templates } = useQuery({ queryKey: ["templates"], queryFn: listTemplates, enabled: open });
  const { data: policyTpls } = useQuery({ queryKey: ["policy-templates"], queryFn: listPolicyTemplates, enabled: open });
  const policyTplId = Form.useWatch("policy_template_id", form);

  useEffect(() => {
    if (open) form.resetFields();
  }, [open]);

  const create = useMutation({
    mutationFn: (body: any) => createSandbox(body),
    onSuccess: (d) => {
      message.success(tr("沙箱创建成功"));
      onClose();
      onCreated?.(d.sandbox_id);
    },
    onError: (e: any) => message.error(e?.response?.data?.error?.message || tr("创建失败")),
  });
  const onTemplate = (id: string) => {
    if (!id) {
      setTplSelected(false);
      return;
    }
    const t = (templates || []).find((x: any) => x.id === id);
    if (!t) return;
    setTplSelected(true);
    form.setFieldsValue({
      template_id: id,
      image: t.image,
      cpu: t.default_cpu,
      memory: t.default_memory,
      timeout_seconds: t.default_timeout_seconds,
    });
  };
  const submit = () => {
    form.validateFields().then((values) => {
      const allow = (values.allow || "")
        .split("\n")
        .map((s: string) => s.trim())
        .filter(Boolean)
        .map((target: string) => ({ action: "allow", target }));
      const body: any = {
        template_id: values.template_id || undefined,
        image: values.image,
        name: values.name,
        cpu: values.cpu,
        memory: values.memory,
        timeout_seconds: values.timeout_seconds,
      };
      if (values.policy_template_id) {
        body.policy_template_id = values.policy_template_id;
      } else if (denyAll) {
        body.network_policy = { defaultAction: "deny", egress: allow };
      }
      create.mutate(body);
    });
  };
  return (
    <Modal
      open={open}
      title={tr("创建沙箱")}
      onCancel={onClose}
      onOk={submit}
      confirmLoading={create.isPending}
      okText={tr("创建")}
      width={640}
      destroyOnClose
    >
      <Form
        form={form}
        layout="vertical"
        initialValues={{ cpu: "1", memory: "1Gi", timeout_seconds: 1800 }}
      >
        <Form.Item label={tr("模板（可选，选择后自动带出配置）")} name="template_id">
          <Select
            allowClear
            placeholder={tr("选择模板")}
            onChange={onTemplate}
            options={(templates || []).map((t: any) => ({ value: t.id, label: `${t.name} — ${t.image}` }))}
          />
        </Form.Item>
        <Space size="large" style={{ display: "flex" }}>
          <Form.Item label={tr("名称")} name="name" rules={[{ required: true, message: tr("请输入名称") }]} style={{ flex: 1 }}>
            <Input placeholder="my-sandbox" />
          </Form.Item>
          <Form.Item
            label={tplSelected ? tr("镜像（由模板决定，不可修改）") : tr("镜像")}
            name="image"
            rules={[{ required: true, message: tr("请输入镜像") }]}
            style={{ flex: 1 }}
          >
            <Input placeholder="python:3.12" disabled={tplSelected} />
          </Form.Item>
        </Space>
        <Space size="large">
          <Form.Item label="CPU" name="cpu">
            <Input style={{ width: 110 }} />
          </Form.Item>
          <Form.Item label={tr("内存")} name="memory">
            <Input style={{ width: 110 }} />
          </Form.Item>
          <Form.Item label={tr("超时(秒)")} name="timeout_seconds">
            <InputNumber min={60} max={86400} />
          </Form.Item>
        </Space>
        <Form.Item
          label={tr("网络策略模板（可选）")}
          name="policy_template_id"
          extra={tr("选用后按模板统一出网 allow/deny；不选用则使用下方自定义策略")}
        >
          <Select
            allowClear
            placeholder={tr("选择网络策略模板")}
            options={(policyTpls || []).map((p: any) => ({ value: p.id, label: `${p.name} — ${p.default_action}` }))}
          />
        </Form.Item>
        {!policyTplId && (
          <Form.Item label={tr("出网策略：默认拒绝所有出网")}>
            <Switch checked={denyAll} onChange={setDenyAll} />
          </Form.Item>
        )}
        {!policyTplId && denyAll && (
          <Form.Item label={tr("放行域名（每行一个，支持 *.example.com）")} name="allow">
            <Input.TextArea rows={3} placeholder={"example.com\n*.pythonhosted.org"} />
          </Form.Item>
        )}
      </Form>
    </Modal>
  );
}
