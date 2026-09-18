import { useEffect, useRef, useState } from "react";
import { Alert, Button, Space, Switch } from "antd";
import { Terminal as XTerm } from "@xterm/xterm";
import { FitAddon } from "@xterm/addon-fit";
import "@xterm/xterm/css/xterm.css";
import { keycloak } from "../auth";
import { api } from "../api";
import { useI18n, tr } from "../i18n";

export default function Terminal({ sandboxId }: { sandboxId: string }) {
  const { t } = useI18n();
  const ref = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [record, setRecord] = useState(false);
  const recordRef = useRef(false);
  const termRef = useRef<XTerm | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let disposed = false;
    const term = new XTerm({
      fontSize: 13,
      fontFamily: "SFMono-Regular, Consolas, Menlo, monospace",
      theme: { background: "#05070c", foreground: "#e8ecf4", cursor: "#6ea8fe" },
      cursorBlink: true,
    });
    const fit = new FitAddon();
    term.loadAddon(fit);
    termRef.current = term;

    async function start() {
      if (!ref.current) return;
      term.open(ref.current);
      fit.fit();
      setStatus(t("terminal.creating"));
      try {
        const { data } = await api.post(`/sandboxes/${sandboxId}/pty`, { cwd: "/tmp" });
        const sessionId = data.session_id;
        const tenant = localStorage.getItem("tenantId") || "";
        const proto = window.location.protocol === "https:" ? "wss" : "ws";
        const url = `${proto}://${window.location.host}/api/v1/sandboxes/${sandboxId}/terminal?session_id=${sessionId}&token=${encodeURIComponent(keycloak.token || "")}&tenant=${encodeURIComponent(tenant)}&record=0&name=${encodeURIComponent("session-" + Date.now())}`;
        const ws = new WebSocket(url);
        ws.binaryType = "arraybuffer";
        wsRef.current = ws;
        ws.onopen = () => {
          setStatus(t("terminal.connected"));
          term.focus();
          ws.send(JSON.stringify({ type: "resize", cols: term.cols, rows: term.rows }));
          ws.send(JSON.stringify({ type: "record", on: recordRef.current }));
        };
        ws.onmessage = (ev) => {
          if (typeof ev.data === "string") {
            try {
              const msg = JSON.parse(ev.data);
              if (msg.type === "exit") {
                term.writeln(`\r\n[${tr("会话结束")} exit=${msg.exit_code}]`);
                setStatus(t("terminal.ended"));
              }
            } catch {
              term.write(ev.data);
            }
            return;
          }
          const buf = new Uint8Array(ev.data as ArrayBuffer);
          const kind = buf[0];
          const payload = buf.slice(1);
          if (kind === 0x01 || kind === 0x02 || kind === 0x03) {
            term.write(new TextDecoder().decode(payload));
          } else {
            term.write(new TextDecoder().decode(buf));
          }
        };
        ws.onclose = () => setStatus(t("terminal.disconnected"));
        ws.onerror = () => setError(t("terminal.error"));
        term.onData((d) => {
          if (ws.readyState === WebSocket.OPEN) {
            const enc = new TextEncoder().encode(d);
            const out = new Uint8Array(enc.length + 1);
            out[0] = 0x00;
            out.set(enc, 1);
            ws.send(out);
          }
        });
        term.onResize(({ cols, rows }) => {
          if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: "resize", cols, rows }));
        });
        window.addEventListener("resize", () => fit.fit());
      } catch (e: any) {
        setError(e?.response?.data?.error?.message || String(e));
        setStatus(t("terminal.failed"));
      }
    }
    start();
    return () => {
      disposed = true;
      try {
        wsRef.current?.close();
      } catch {
        /* ignore */
      }
      term.dispose();
    };
  }, [sandboxId]);

  const toggleRecord = (v: boolean) => {
    setRecord(v);
    recordRef.current = v;
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "record", on: v }));
    }
  };

  return (
    <div>
      <Space style={{ marginBottom: 8 }}>
        <span style={{ color: "var(--text-dim)" }}>{status || t("terminal.connecting")}</span>
        <Button size="small" onClick={() => wsRef.current?.send(JSON.stringify({ type: "signal", signal: "SIGINT" }))}>
          {t("terminal.sendCtrlC")}
        </Button>
        <Space size={4}>
          <Switch size="small" checked={record} onChange={toggleRecord} />
          <span style={{ color: record ? "var(--bad)" : "var(--text-dim)", fontSize: 12 }}>
            {t("detail.record")}
          </span>
        </Space>
        {record && <span style={{ color: "var(--text-faint)", fontSize: 12 }}>{t("terminal.recordingHint")}</span>}
      </Space>
      {error && <Alert type="error" showIcon message={error} style={{ marginBottom: 8 }} />}
      <div className="sh-terminal" ref={ref} />
    </div>
  );
}
