import { Button, Card, Col, Row, Space, Tag, Typography, message } from "antd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { launchAgent, listAgents } from "../api";
import PageHeader from "../components/PageHeader";
import {tr,  useI18n } from "../i18n";

export default function Agents() {
  const { t } = useI18n();
  const nav = useNavigate();
  const qc = useQueryClient();
  const { data } = useQuery({ queryKey: ["agents"], queryFn: listAgents });

  const launch = useMutation({
    mutationFn: (a: any) => launchAgent(a.id, { cpu: "2", memory: "2Gi", timeout_seconds: 3600 }),
    onSuccess: (d) => {
      message.success(tr("沙箱已创建，正在后台安装 Agent（约 30-90 秒）"));
      qc.invalidateQueries({ queryKey: ["sandboxes"] });
      nav(`/sandboxes/${d.sandbox_id}`);
    },
    onError: (e: any) => message.error(e?.response?.data?.error?.message || tr("启动失败")),
  });
  return (
    <div>
      <PageHeader
        eyebrow="Intelligence"
        title={t("agents.title")}
        subtitle={t("agents.subtitle")}
      />
      <Card style={{ marginBottom: 16 }}>
        <Typography.Paragraph type="secondary" style={{ margin: 0 }}>
          {tr("说明：基础镜像（code-interpreter）")}<b>{tr("不含")}</b>{tr("编码 Agent。点击「创建并安装」后，平台会在沙箱内执行安装命令；")}
          {tr("安装完成后在沙箱详情「运行 → 终端」中执行运行命令即可。")}
        </Typography.Paragraph>
      </Card>
      <Row gutter={16}>
        {(data || []).map((a: any) => (
          <Col span={8} key={a.id} style={{ marginBottom: 16 }}>
            <Card title={a.name} extra={<Tag color="blue">{a.image.split(":")[0]}</Tag>}>
              <Typography.Paragraph type="secondary" style={{ fontSize: 12 }}>{tr("安装：")}<code>{a.install}</code>
              </Typography.Paragraph>
              <Typography.Paragraph type="secondary" style={{ fontSize: 12 }}>{tr("运行：")}<code>{a.run}</code>
              </Typography.Paragraph>
              <Space>
                <Button
                  type="primary"
                  loading={launch.isPending && launch.variables?.id === a.id}
                  onClick={() => launch.mutate(a)}
                >
                  {t("agents.launch")}
                </Button>
                <a href={a.docs} target="_blank" rel="noopener">{tr("官方示例")}</a>
              </Space>
            </Card>
          </Col>
        ))}
      </Row>
    </div>
  );
}
