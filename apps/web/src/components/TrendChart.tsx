import ReactECharts from "echarts-for-react";
import { useTheme } from "../theme";

export default function TrendChart({
  x,
  series,
  height = 240,
  area = true,
}: {
  x: string[];
  series: { name: string; data: number[]; color?: string }[];
  height?: number;
  area?: boolean;
}) {
  const { resolved } = useTheme();
  const dark = resolved === "dark";
  const axisColor = dark ? "#7b88a3" : "#6b7794";
  const splitColor = dark ? "rgba(255,255,255,.06)" : "rgba(15,23,42,.08)";
  const palette = dark
    ? ["#6ea8fe", "#5fd3b0", "#c0a4ff", "#ffb86b", "#f87171"]
    : ["#2563eb", "#0d9488", "#7c3aed", "#d97706", "#dc2626"];

  const option = {
    grid: { left: 40, right: 16, top: 28, bottom: 28 },
    tooltip: {
      trigger: "axis",
      backgroundColor: dark ? "#141b29" : "#ffffff",
      borderColor: splitColor,
      textStyle: { color: dark ? "#e8ecf4" : "#1a2233" },
    },
    legend: { top: 0, textStyle: { color: axisColor }, icon: "roundRect" },
    xAxis: {
      type: "category",
      boundaryGap: false,
      data: x,
      axisLine: { lineStyle: { color: splitColor } },
      axisLabel: { color: axisColor },
    },
    yAxis: {
      type: "value",
      axisLine: { show: false },
      splitLine: { lineStyle: { color: splitColor } },
      axisLabel: { color: axisColor },
    },
    series: series.map((s, i) => ({
      name: s.name,
      type: "line",
      smooth: true,
      showSymbol: false,
      data: s.data,
      lineStyle: { width: 2, color: s.color || palette[i % palette.length] },
      itemStyle: { color: s.color || palette[i % palette.length] },
      areaStyle: area
        ? {
            opacity: 0.15,
            color: s.color || palette[i % palette.length],
          }
        : undefined,
    })),
  };
  return <ReactECharts option={option} style={{ height }} notMerge lazyUpdate />;
}
