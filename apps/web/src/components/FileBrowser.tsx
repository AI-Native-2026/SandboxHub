import { useState } from "react";
import { Breadcrumb, Button, Input, Modal, Space, Table, Tag, Upload, message } from "antd";
import { DownloadOutlined, FolderAddOutlined, ReloadOutlined, UploadOutlined } from "@ant-design/icons";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { deleteFiles, downloadFile, listFiles, makeDirs, writeFile } from "../api";
import { keycloak } from "../auth";
import { tr } from "../i18n";

export default function FileBrowser({ sandboxId }: { sandboxId: string }) {
  const [path, setPath] = useState("/tmp");
  const [editPath, setEditPath] = useState<string | null>(null);
  const [editContent, setEditContent] = useState("");
  const [newDir, setNewDir] = useState("");
  const qc = useQueryClient();

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["files", sandboxId, path],
    queryFn: () => listFiles(sandboxId, path, 1),
  });

  const join = (p: string, name: string) => (p.endsWith("/") ? p + name : p + "/" + name);

  const save = async () => {
    if (!editPath) return;
    await writeFile(sandboxId, editPath, editContent);
    message.success(tr("已保存"));
    setEditPath(null);
    refetch();
  };
  const openEdit = async (filePath: string) => {
    const blob = await downloadFile(sandboxId, filePath);
    const text = await blob.text();
    setEditContent(text);
    setEditPath(filePath);
  };
  const doDownload = async (filePath: string) => {
    const blob = await downloadFile(sandboxId, filePath);
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filePath.split("/").pop() || "file";
    a.click();
    URL.revokeObjectURL(url);
  };
  const del = useMutation({
    mutationFn: (p: string) => deleteFiles(sandboxId, [p]),
    onSuccess: () => refetch(),
  });

  const mkdir = useMutation({
    mutationFn: (p: string) => makeDirs(sandboxId, p),
    onSuccess: () => {
      setNewDir("");
      refetch();
    },
  });

  const upload = async (file: File) => {
    const target = join(path, file.name);
    const url = `/api/v1/sandboxes/${sandboxId}/files/upload?path=${encodeURIComponent(target)}`;
    const resp = await fetch(url, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${keycloak.token}`,
        "X-Tenant-Id": localStorage.getItem("tenantId") || "",
        "Content-Type": "application/octet-stream",
      },
      body: file,
    });
    if (resp.ok) {
      message.success(tr("上传成功"));
      refetch();
    } else {
      message.error(tr("上传失败"));
    }
  };
  const parent = path === "/" ? "/" : path.replace(/\/[^/]+$/, "") || "/";

  return (
    <div>
      <Space style={{ marginBottom: 12, width: "100%", justifyContent: "space-between" }}>
        <Space>
          <Breadcrumb
            items={path
              .split("/")
              .filter(Boolean)
              .map((seg, i, arr) => ({
                title: <a onClick={() => setPath("/" + arr.slice(0, i + 1).join("/"))}>{seg}</a>,
              }))
              .concat([{ title: <a onClick={() => setPath("/")}>/</a> }])}
          />
          <Button size="small" onClick={() => setPath(parent)}>{tr("上级")}</Button>
          <Button size="small" icon={<ReloadOutlined />} onClick={() => refetch()}>{tr("刷新")}</Button>
        </Space>
        <Space>
          <Input
            size="small"
            placeholder={tr("新目录名")}
            value={newDir}
            onChange={(e) => setNewDir(e.target.value)}
            style={{ width: 140 }}
          />
          <Button size="small" icon={<FolderAddOutlined />} onClick={() => newDir && mkdir.mutate(join(path, newDir))}>{tr("新建目录")}</Button>
          <Upload showUploadList={false} beforeUpload={(f) => { upload(f as File); return false; }}>
            <Button size="small" icon={<UploadOutlined />}>{tr("上传")}</Button>
          </Upload>
        </Space>
      </Space>

      <Table
        rowKey="path"
        size="small"
        loading={isLoading}
        dataSource={(data || []).filter((e: any) => e.path !== path)}
        pagination={false}
        columns={[
          {
            title: tr("名称"),
            dataIndex: "path",
            render: (v: string, r: any) => {
              const name = v.split("/").filter(Boolean).pop();
              if (r.type === "directory") return <a onClick={() => setPath(v)}>📁 {name}</a>;
              return <span>📄 {name}</span>;
            },
          },
          { title: tr("类型"), dataIndex: "type", width: 100 },
          { title: tr("大小"), dataIndex: "size", width: 100 },
          {
            title: tr("操作"),
            width: 200,
            render: (_: any, r: any) =>
              r.type === "directory" ? null : (
                <Space size="small">
                  <a onClick={() => openEdit(r.path)}>{tr("编辑")}</a>
                  <a onClick={() => doDownload(r.path)}>
                    <DownloadOutlined />{tr("下载")}</a>
                  <a style={{ color: "var(--bad)" }} onClick={() => del.mutate(r.path)}>{tr("删除")}</a>
                </Space>
              ),
          },
        ]}
      />

      <Modal open={!!editPath} title={editPath} onCancel={() => setEditPath(null)} onOk={save} width={800}>
        <Input.TextArea
          value={editContent}
          onChange={(e) => setEditContent(e.target.value)}
          autoSize={{ minRows: 16, maxRows: 24 }}
          style={{ fontFamily: "monospace" }}
        />
      </Modal>
    </div>
  );
}
