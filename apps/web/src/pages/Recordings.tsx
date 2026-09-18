import { useCallback, useEffect, useRef, useState } from "react";
import { Button, Card, Modal, Popconfirm, Space, Table, message } from "antd";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Terminal as XTerm } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import "@xterm/xterm/css/xterm.css";
import { deleteRecording, getRecording, listRecordings } from "../api";
import PageHeader from "../components/PageHeader";
import {tr,  useI18n } from "../i18n";

function b64ToBytes(b64: string): Uint8Array {
  const bin = atob(b64);
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i += 1) out[i] = bin.charCodeAt(i);
  return out;
}

function Playback({ id, onClose }: { id: string | null; onClose: () => void }) {
  const { data } = useQuery({ queryKey: ["recording", id], queryFn: () => getRecording(id as string), enabled: !!id });
  const termRef = useRef<XTerm | null>(null);
  const timer = useRef<any>(null);
  const [playing, setPlaying] = useState(false);

  // Callback ref: AntD mounts the modal body after the first effect pass, so a
  // plain useEffect would see a null node and never initialize the terminal.
  const attach = useCallback((node: HTMLDivElement | null) => {
    if (!node) {
      termRef.current?.dispose();
      termRef.current = null;
      return;
    }
    if (termRef.current) return;
    const term = new XTerm({
      fontSize: 12.5,
      fontFamily: "SFMono-Regular, Consolas, Menlo, monospace",
      theme: { background: "#05070c", foreground: "#e8ecf4", cursor: "#6ea8fe" },
      cursorBlink: false,
      scrollback: 5000,
      convertEol: false,
    });
    const fit = new FitAddon();
    term.loadAddon(fit);
    term.open(node);
    termRef.current = term;
    setTimeout(() => {
      try {
        fit.fit();
      } catch {
        /* ignore */
      }
    }, 60);
  }, []);

  useEffect(() => {
    termRef.current?.reset();
    setPlaying(false);
    clearTimeout(timer.current);
    return () => clearTimeout(timer.current);
  }, [id, data]);

  const play = () => {
    const term = termRef.current;
    if (!term || !data?.data) return;
    term.reset();
    setPlaying(true);
    const chunks = data.data as any[];
    let i = 0;
    let last = 0;
    const step = () => {
      if (i >= chunks.length) {
        setPlaying(false);
        return;
      }
      const c = chunks[i];
      const at = typeof c.t === "number" ? c.t : i * 60;
      const delay = Math.min(Math.max(at - last, 0), 400);
      last = at;
      try {
        term.write(b64ToBytes(c.b));
      } catch {
        /* ignore */
      }
      i += 1;
      timer.current = setTimeout(step, delay);
    };
    step();
  };

  return (
    <Modal open={!!id} title={tr("会话回放")} onCancel={onClose} footer={null} width={880} destroyOnClose>
      <Space style={{ marginBottom: 10 }}>
        <Button type="primary" onClick={play} disabled={playing || !data}>
          {playing ? tr("回放中…") : tr("播放")}
        </Button>
        <span style={{ color: "var(--text-faint)" }}>
          {data?.chunks ?? 0} {tr("帧")} · {data?.size_bytes ?? 0} bytes
        </span>
      </Space>
      <div className="sh-terminal" ref={attach} style={{ height: 440 }} />
    </Modal>
  );
}

export default function Recordings() {
  const { t } = useI18n();
  const qc = useQueryClient();
  const [playId, setPlayId] = useState<string | null>(null);
  const { data, isLoading } = useQuery({ queryKey: ["recordings"], queryFn: listRecordings });
  const del = useMutation({
    mutationFn: (id: string) => deleteRecording(id),
    onSuccess: () => {
      message.success(tr("已删除"));
      qc.invalidateQueries({ queryKey: ["recordings"] });
    },
  });
  return (
    <div>
      <PageHeader
        eyebrow="Security"
        title={t("recordings.title")}
        subtitle={t("recordings.subtitle")}
      />
      <Card>
        <Table
          rowKey="id"
          loading={isLoading}
          dataSource={data || []}
          pagination={false}
          columns={[
            { title: tr("名称"), dataIndex: "name" },
            { title: tr("沙箱"), dataIndex: "sandbox_id", ellipsis: true },
            { title: tr("帧数"), dataIndex: "chunks" },
            { title: tr("大小"), dataIndex: "size_bytes", render: (v) => `${v} B` },
            { title: tr("结束时间"), dataIndex: "ended_at", render: (v) => (v ? new Date(v).toLocaleString() : "-") },
            {
              title: tr("操作"),
              render: (_: any, r: any) => (
                <Space>
                  <a onClick={() => setPlayId(r.id)}>{t("recordings.play")}</a>
                  <Popconfirm title={tr("删除录制？")} onConfirm={() => del.mutate(r.id)}>
                    <a style={{ color: "var(--bad)" }}>{tr("删除")}</a>
                  </Popconfirm>
                </Space>
              ),
            },
          ]}
        />
      </Card>
      <Playback id={playId} onClose={() => setPlayId(null)} />
    </div>
  );
}
