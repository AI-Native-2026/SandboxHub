import { Card, Col, Empty, List, Row, Statistic, Tag } from "antd";
import { useQuery } from "@tanstack/react-query";
import { getOverview } from "../api";
import PageHeader from "../components/PageHeader";
import {tr,  useI18n } from "../i18n";

export default function Dashboard() {
  const { t } = useI18n();
  const { data, isLoading } = useQuery({ queryKey: ["overview"], queryFn: getOverview });
  const byState: Record<string, number> = data?.sandboxes?.by_state || {};

  return (
    <div>
      <PageHeader eyebrow="Overview" title={t("nav.overview")} />
      <Row gutter={16}>
        <Col span={6} className="sh-stat">
          <Card loading={isLoading}>
            <Statistic title={t("usage.activeSandboxes")} value={data?.sandboxes?.total ?? 0} />
          </Card>
        </Col>
        <Col span={6} className="sh-stat">
          <Card loading={isLoading}>
            <Statistic title={t("common.status")} value={byState["Running"] ?? 0} />
          </Card>
        </Col>
        <Col span={6} className="sh-stat">
          <Card loading={isLoading}>
            <Statistic title={t("nav.quota")} value={data?.sandboxes?.quota ?? "-"} />
          </Card>
        </Col>
        <Col span={6} className="sh-stat">
          <Card loading={isLoading}>
            <Statistic title={t("nav.templates")} value={data?.templates ?? 0} />
          </Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col span={10}>
          <Card title={t("common.status")} loading={isLoading}>
            {Object.keys(byState).length === 0 ? (
              <Empty description={tr("暂无沙箱")} />
            ) : (
              Object.entries(byState).map(([k, v]) => (
                <div key={k} style={{ marginBottom: 8 }}>
                  <Tag color={k === "Running" ? "green" : k === "Paused" ? "orange" : "blue"}>{k}</Tag>
                  <b>{v}</b>
                </div>
              ))
            )}
          </Card>
        </Col>
        <Col span={14}>
          <Card title={t("common.actions")} loading={isLoading}>
            <List
              size="small"
              dataSource={data?.recent_activity || []}
              locale={{ emptyText: tr("暂无活动") }}
              renderItem={(a: any) => (
                <List.Item>
                  <span style={{ color: "var(--text-faint)", width: 170, display: "inline-block" }}>
                    {a.ts ? new Date(a.ts).toLocaleString() : ""}
                  </span>
                  <Tag>{a.action}</Tag>
                  <span style={{ color: "var(--text-dim)" }}>{a.resource_id}</span>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
}
