import { Card, Col, Progress, Row, Statistic } from "antd";
import { useQuery } from "@tanstack/react-query";
import { getQuota } from "../api";
import PageHeader from "../components/PageHeader";
import {tr,  useI18n } from "../i18n";

export default function Quota() {
  const { t } = useI18n();
  const { data } = useQuery({ queryKey: ["quota"], queryFn: getQuota, refetchInterval: 15000 });
  const q = data?.quota || {};
  const u = data?.usage || {};
  const pct = q.sandboxes ? Math.min(100, Math.round(((u.running || 0) / q.sandboxes) * 100)) : 0;

  return (
    <div>
      <PageHeader eyebrow="Governance" title={t("quota.title")} subtitle={t("quota.subtitle")} />
      <Row gutter={16}>
        <Col span={8}>
          <Card title={tr("CPU 配额")}><Statistic value={q.cpu ?? "-"} suffix={tr("核")} /></Card>
        </Col>
        <Col span={8}>
          <Card title={tr("内存配额")}><Statistic value={q.memory ?? "-"} /></Card>
        </Col>
        <Col span={8}>
          <Card title={tr("并发沙箱")}>
            <Progress percent={pct} status={pct > 90 ? "exception" : "active"} />
            <div style={{ color: "var(--text-faint)", fontSize: 12 }}>
              {u.running ?? 0} / {q.sandboxes ?? "-"}
            </div>
          </Card>
        </Col>
      </Row>
      <Card title={tr("说明")} style={{ marginTop: 16 }}>
        <p style={{ color: "var(--text-dim)" }}>{tr("配额由平台管理员在「管理端 · 租户」中设置；超过并发上限的创建请求将被拒绝（HTTP 429 QUOTA_EXCEEDED）。")}</p>
      </Card>
    </div>
  );
}
