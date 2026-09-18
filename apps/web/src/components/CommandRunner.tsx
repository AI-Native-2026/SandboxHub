import { useRef, useState } from "react";
import { Button, Input, Space } from "antd";
import { keycloak } from "../auth";
import { tr } from "../i18n";

export default function CommandRunner({ sandboxId }: { sandboxId: string }) {
  const [cmd, setCmd] = useState("echo hello; python --version");
  const [out, setOut] = useState("");
  const [running, setRunning] = useState(false);
  const outRef = useRef<HTMLPreElement>(null);

  const run = async () => {
    setOut("");
    setRunning(true);
    const tenant = localStorage.getItem("tenantId") || "";
    try {
      const resp = await fetch(`/api/v1/sandboxes/${sandboxId}/commands`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${keycloak.token}`,
          "X-Tenant-Id": tenant,
        },
        body: JSON.stringify({ command: cmd }),
      });
      if (!resp.body) throw new Error("no stream");
      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split(/\r?\n/);
        buf = lines.pop() || "";
        for (const raw of lines) {
          let line = raw.trim();
          if (!line) continue;
          if (line.startsWith("data:")) line = line.slice(5).trim();
          if (!line) continue;
          try {
            const evt = JSON.parse(line);
            if (evt.type === "stdout" || evt.type === "stderr") {
              setOut((p) => p + evt.text + "\n");
            } else if (evt.type === "execution_complete") {
              setOut((p) => p + `\n[${tr("完成")} exit=${evt.exit_code ?? 0}]\n`);
            } else if (evt.type === "error") {
              setOut((p) => p + `[error] ${evt.text}\n`);
            }
          } catch {
            /* ignore non-json */
          }
        }
        if (outRef.current) outRef.current.scrollTop = outRef.current.scrollHeight;
      }
    } catch (e: any) {
      setOut((p) => p + `\n[${tr("异常")}] ${e.message}\n`);
    } finally {
      setRunning(false);
    }
  };
  return (
    <div>
      <Space.Compact style={{ width: "100%", marginBottom: 10 }}>
        <Input
          value={cmd}
          onChange={(e) => setCmd(e.target.value)}
          onPressEnter={run}
          placeholder={tr("输入 shell 命令")}
        />
        <Button type="primary" onClick={run} loading={running}>{tr("执行")}</Button>
      </Space.Compact>
      <pre className="sh-mono sh-out" ref={outRef}>
        {out || tr("（输出将显示在这里）")}
      </pre>
    </div>
  );
}
