import { Badge, Button, Drawer, List, Popover, Tag } from "antd";
import { BellOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { getOverview } from "../api";
import { tr } from "../i18n";

export default function NotificationCenter() {
  const [open, setOpen] = useState(false);
  const { data } = useQuery({ queryKey: ["overview"], queryFn: getOverview, refetchInterval: 15000 });
  const items = data?.recent_activity || [];

  const content = (
    <div style={{ width: 360, maxHeight: 420, overflow: "auto" }}>
      <List
        size="small"
        dataSource={items}
        locale={{ emptyText: tr("暂无通知") }}
        renderItem={(a: any) => (
          <List.Item>
            <div style={{ width: "100%" }}>
              <Tag>{a.action}</Tag>
              <span style={{ color: "var(--text-dim)", fontSize: 12 }}>{a.resource_id}</span>
              <div style={{ color: "var(--text-faint)", fontSize: 11 }}>
                {a.ts ? new Date(a.ts).toLocaleString() : ""}
              </div>
            </div>
          </List.Item>
        )}
      />
    </div>
  );
  return (
    <Popover content={content} title={tr("通知")} trigger="click" placement="bottomRight" open={open} onOpenChange={setOpen}>
      <Badge count={items.length ? Math.min(items.length, 9) : 0} size="small">
        <Button type="text" icon={<BellOutlined />} aria-label={tr("通知")} />
      </Badge>
    </Popover>
  );
}
