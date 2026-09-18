import { useEffect, useState } from "react";
import { Card, Col, Row, Statistic } from "antd";
import { useQuery } from "@tanstack/react-query";
import { getMetrics } from "../api";
import { useI18n } from "../i18n";
import TrendChart from "./TrendChart";

interface Sample {
  t: string;
  cpu: number;
  mem: number;
  memUsed: number;
}

export default function Metrics({ sandboxId }: { sandboxId: string }) {
  const { t } = useI18n();
  const { data } = useQuery({
    queryKey: ["metrics", sandboxId],
    queryFn: () => getMetrics(sandboxId),
    refetchInterval: 3000,
  });
  const [samples, setSamples] = useState<Sample[]>([]);

  useEffect(() => {
    if (!data) return;
    const cpu = Number(data.cpu_used_pct ?? 0);
    const memTotal = Number(data.mem_total_mib ?? 0);
    const memUsed = Number(data.mem_used_mib ?? 0);
    const mem = memTotal > 0 ? (memUsed / memTotal) * 100 : 0;
    const t = new Date().toLocaleTimeString();
    setSamples((prev) => [...prev, { t, cpu, mem, memUsed }].slice(-60));
  }, [data]);

  const latest = samples[samples.length - 1];

  return (
    <div>
      <Row gutter={16}>
        <Col span={6}>
          <Card><Statistic title="CPU cores" value={data?.cpu_count ?? "-"} /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="CPU %" value={latest ? latest.cpu.toFixed(1) : "-"} suffix="%" /></Card>
        </Col>
        <Col span={6}>
          <Card><Statistic title="Memory %" value={latest ? latest.mem.toFixed(1) : "-"} suffix="%" /></Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Memory"
              value={latest ? latest.memUsed.toFixed(0) : "-"}
              suffix={`/ ${(data?.mem_total_mib ?? 0).toFixed(0)} MiB`}
            />
          </Card>
        </Col>
      </Row>

      <Card title="CPU / Memory (%)" style={{ marginTop: 16 }}>
        {samples.length < 2 ? (
          <div style={{ color: "var(--text-faint)", padding: 24, textAlign: "center" }}>
            {t("common.none")}
          </div>
        ) : (
          <TrendChart
            x={samples.map((s) => s.t)}
            series={[
              { name: "CPU %", data: samples.map((s) => Number(s.cpu.toFixed(2))) },
              { name: "Memory %", data: samples.map((s) => Number(s.mem.toFixed(2))) },
            ]}
            height={280}
          />
        )}
      </Card>

      <Card title="Memory used (MiB)" style={{ marginTop: 16 }}>
        {samples.length < 2 ? (
          <div style={{ color: "var(--text-faint)", padding: 24, textAlign: "center" }}>
            {t("common.none")}
          </div>
        ) : (
          <TrendChart
            x={samples.map((s) => s.t)}
            series={[{ name: "MiB", data: samples.map((s) => Number(s.memUsed.toFixed(1))) }]}
            height={220}
          />
        )}
      </Card>
    </div>
  );
}
