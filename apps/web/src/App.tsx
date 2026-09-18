import React from "react";
import { Avatar, Button, Dropdown, Layout, Menu, Select, Space, Typography } from "antd";
import {
  AppstoreAddOutlined,
  AppstoreOutlined,
  DashboardOutlined,
  FundOutlined,
  KeyOutlined,
  MoonOutlined,
  ReadOutlined,
  SafetyCertificateOutlined,
  SettingOutlined,
  SunOutlined,
  ThunderboltOutlined,
  TranslationOutlined,
  UserOutlined,
} from "@ant-design/icons";
import { Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { getMe } from "./api";
import { keycloak, hasRole, canWrite } from "./auth";
import { useI18n } from "./i18n";
import { useTheme } from "./theme";
import Dashboard from "./pages/Dashboard";
import SandboxList from "./pages/SandboxList";
import SandboxDetail from "./pages/SandboxDetail";
import Templates from "./pages/Templates";
import ApiKeys from "./pages/ApiKeys";
import Admin from "./pages/Admin";
import Guide from "./pages/Guide";
import Usage from "./pages/Usage";
import Quota from "./pages/Quota";
import Approvals from "./pages/Approvals";
import Credentials from "./pages/Credentials";
import PolicyTemplates from "./pages/PolicyTemplates";
import Recordings from "./pages/Recordings";
import Rbac from "./pages/Rbac";
import Pools from "./pages/Pools";
import Tasks from "./pages/Tasks";
import Artifacts from "./pages/Artifacts";
import Agents from "./pages/Agents";
import NotificationCenter from "./components/NotificationCenter";

const { Sider, Header, Content } = Layout;

export default function App() {
  const nav = useNavigate();
  const loc = useLocation();
  const { t, lang, setLang } = useI18n();
  const { resolved, setMode } = useTheme();
  const me = useQuery({ queryKey: ["me"], queryFn: getMe });

  React.useEffect(() => {
    if (me.data && !localStorage.getItem("tenantId") && me.data.tenants.length) {
      localStorage.setItem("tenantId", me.data.tenants[0].id);
    }
  }, [me.data]);

  const path = loc.pathname;
  const selected = path === "/" ? "overview"
    : path.startsWith("/sandboxes") ? "sandboxes"
    : path.startsWith("/templates") ? "templates"
    : path.startsWith("/api-keys") ? "apikeys"
    : path.startsWith("/guide") ? "guide"
    : path.startsWith("/admin") ? "admin"
    : path.slice(1) || "overview";

  type Item = { key: string; icon?: React.ReactNode; label: string };
  const groups: { group: string; items: Item[] }[] = [
    {
      group: t("nav.workbench"),
      items: [
        { key: "overview", icon: <DashboardOutlined />, label: t("nav.overview") },
        { key: "sandboxes", icon: <AppstoreOutlined />, label: t("nav.sandboxes") },
        { key: "tasks", icon: <ThunderboltOutlined />, label: t("nav.tasks") },
        { key: "artifacts", icon: <AppstoreAddOutlined />, label: t("nav.artifacts") },
        { key: "agents", icon: <ThunderboltOutlined />, label: t("nav.agents") },
      ],
    },
    {
      group: t("nav.resources"),
      items: [
        { key: "templates", icon: <AppstoreAddOutlined />, label: t("nav.templates") },
        { key: "guide", icon: <ReadOutlined />, label: t("nav.guide") },
        { key: "apikeys", icon: <KeyOutlined />, label: t("nav.apikeys") },
      ],
    },
  ];
  if (hasRole("platform-admin") || hasRole("tenant-admin")) {
    groups.push({
      group: t("nav.governance"),
      items: [
        { key: "cost", icon: <FundOutlined />, label: t("nav.cost") },
        { key: "quota", icon: <FundOutlined />, label: t("nav.quota") },
        { key: "approval", icon: <SafetyCertificateOutlined />, label: t("nav.approval") },
        { key: "vault", icon: <KeyOutlined />, label: t("nav.vault") },
        { key: "policy", icon: <SafetyCertificateOutlined />, label: t("nav.policy") },
      ],
    });
  }
  if (hasRole("platform-admin")) {
    groups.push({
      group: t("nav.admin"),
      items: [
        { key: "admin", icon: <SettingOutlined />, label: t("nav.admincenter") },
        { key: "pools", icon: <FundOutlined />, label: t("nav.pools") },
        { key: "recordings", icon: <ReadOutlined />, label: t("nav.recording") },
        { key: "rbac", icon: <SafetyCertificateOutlined />, label: t("nav.rbac") },
      ],
    });
  }

  const go = (key: string) => {
    const map: Record<string, string> = {
      overview: "/", sandboxes: "/sandboxes", templates: "/templates", apikeys: "/api-keys",
      guide: "/guide", admin: "/admin", tasks: "/tasks", artifacts: "/artifacts", agents: "/agents",
      cost: "/cost", quota: "/quota", approval: "/approval", vault: "/vault", policy: "/policy",
      pools: "/pools", recordings: "/recordings", rbac: "/rbac",
    };
    nav(map[key] || "/");
  };
  const menuItems = groups.flatMap((g) => [
    { type: "group" as const, label: g.group, children: g.items.map((i) => ({ key: i.key, icon: i.icon, label: i.label })) },
  ]);

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider width={244} theme={resolved === "dark" ? "dark" : "light"} style={{ background: resolved === "dark" ? "#0d1320" : "#ffffff" }}>
        <div className="sh-logo">
          <span className="dot">SH</span> SandboxHub
        </div>
        <Menu
          theme={resolved === "dark" ? "dark" : "light"}
          mode="inline"
          selectedKeys={[selected]}
          style={{ background: "transparent", borderInlineEnd: "none" }}
          onClick={(e) => go(e.key)}
          items={menuItems}
        />
      </Sider>
      <Layout>
        <Header className="sh-topbar">
          <Typography.Text strong>{t("header.title")}</Typography.Text>
          <Space size={10}>
            <NotificationCenter />
            <Select
              size="small"
              style={{ minWidth: 168 }}
              value={localStorage.getItem("tenantId") || undefined}
              placeholder={t("header.tenant")}
              onChange={(v) => {
                localStorage.setItem("tenantId", v);
                window.location.reload();
              }}
              options={(me.data?.tenants || []).map((x) => ({ value: x.id, label: `${x.name} (${x.role})` }))}
            />
            <Button
              type="text"
              className="sh-theme-toggle"
              aria-label={t("header.theme")}
              icon={resolved === "dark" ? <SunOutlined /> : <MoonOutlined />}
              onClick={() => setMode(resolved === "dark" ? "light" : "dark")}
            />
            <Button
              type="text"
              className="sh-lang-toggle"
              aria-label={t("header.language")}
              icon={<TranslationOutlined />}
              onClick={() => setLang(lang === "zh" ? "en" : "zh")}
            >
              {lang === "zh" ? "中" : "EN"}
            </Button>
            <Dropdown
              menu={{ items: [{ key: "logout", label: t("header.logout"), onClick: () => keycloak.logout() }] }}
            >
              <Space style={{ cursor: "pointer" }}>
                <Avatar size="small" icon={<UserOutlined />} />
                <span style={{ color: "var(--text-dim)" }}>
                  {me.data?.user?.display_name || me.data?.user?.username}
                </span>
              </Space>
            </Dropdown>
          </Space>
        </Header>
        <Content style={{ padding: 24 }}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/sandboxes" element={<SandboxList />} />
            <Route path="/sandboxes/new" element={<Navigate to="/sandboxes" />} />
            <Route path="/sandboxes/:id" element={<SandboxDetail />} />
            <Route path="/templates" element={<Templates />} />
            <Route path="/api-keys" element={<ApiKeys />} />
            <Route path="/guide" element={<Guide />} />
            <Route path="/tasks" element={<Tasks />} />
            <Route path="/artifacts" element={<Artifacts />} />
            <Route path="/agents" element={<Agents />} />
            <Route path="/cost" element={<Usage />} />
            <Route path="/quota" element={<Quota />} />
            <Route path="/approval" element={<Approvals />} />
            <Route path="/vault" element={<Credentials />} />
            <Route path="/policy" element={<PolicyTemplates />} />
            <Route path="/pools" element={<Pools />} />
            <Route path="/recordings" element={<Recordings />} />
            <Route path="/rbac" element={<Rbac />} />
            <Route path="/admin" element={hasRole("platform-admin") ? <Admin /> : <Navigate to="/" />} />
            <Route path="*" element={<Navigate to="/" />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  );
}
