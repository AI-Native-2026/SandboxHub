import { Card, Col, Row, Select, Statistic, Table } from "antd";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { usageSummary, usageTimeseries, usageTop } from "../api";
import PageHeader from "../components/PageHeader";
import TrendChart from "../components/TrendChart";
import {tr,  useI18n } from "../i18n";

export default function Usage() {
  const { t } = useI18n();
  const [days, setDays] = useState(7);
  const summary = useQuery({ queryKey: ["usage-summary", days], queryFn: () => usageSummary(days) });
  const series = useQuery({ queryKey: ["usage-series", days], queryFn: () => usageTimeseries(days) });
  const top = useQuery({ queryKey: ["usage-top", days], queryFn: () => usageTop(days) });

  return (
    <div>
      <PageHeader
        eyebrow="Governance"
        title={t("usage.title")}
        subtitle={t("usage.subtitle")}
        actions={
          <Select
            value={days}
            onChange={setDays}
            options={[7, 14, 30].map((d) => ({ value: d, label: `${tr("近")} ${d} ${tr("天")}` }))}
          />
        }
      />
      <Row gutter={16}>
        <Col span={6}><Card className="sh-stat"><Statistic title={t("usage.cpuHours")} value={summary.data?.cpu_hours ?? 0} /></Card></Col>
        <Col span={6}><Card className="sh-stat"><Statistic title={t("usage.memGbHours")} value={summary.data?.mem_gb_hours ?? 0} /></Card></Col>
        <Col span={6}><Card className="sh-stat"><Statistic title={t("usage.cost")} value={summary.data?.cost ?? 0} prefix="¥" /></Card></Col>
        <Col span={6}><Card className="sh-stat"><Statistic title={t("usage.activeSandboxes")} value={summary.data?.active_sandboxes ?? 0} /></Card></Col>
      </Row>

      <Card title={t("usage.costTrend")} style={{ marginTop: 16 }}>
        {(series.data || []).length === 0 ? (
          <div style={{ color: "var(--text-faint)", padding: 24, textAlign: "center" }}>{t("common.none")}</div>
        ) : (
          <TrendChart
            x={(series.data || []).map((d: any) => d.date)}
            series={[
              { name: t("usage.cpuHours"), data: (series.data || []).map((d: any) => d.cpu_hours) },
              { name: t("usage.memGbHours"), data: (series.data || []).map((d: any) => d.mem_gb_hours) },
              { name: t("usage.cost"), data: (series.data || []).map((d: any) => d.cost) },
            ]}
          />
        )}
      </Card>

      <Card title={t("usage.topSandboxes")} style={{ marginTop: 16 }}>
        <Table
          rowKey="sandbox_id"
          size="small"
          loading={top.isLoading}
          dataSource={top.data || []}
          pagination={false}
          columns={[
            { title: "Sandbox ID", dataIndex: "sandbox_id", ellipsis: true },
            { title: tr("CPU·小时"), dataIndex: "cpu_hours" },
            { title: tr("内存·GB·小时"), dataIndex: "mem_gb_hours" },
            { title: tr("成本"), dataIndex: "cost", render: (v) => `¥${v}` },
          ]}
        />
      </Card>
    </div>
  );
}
