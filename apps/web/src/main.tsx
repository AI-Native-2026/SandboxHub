import React from "react";
import ReactDOM from "react-dom/client";
import { ConfigProvider, Spin, theme as antdTheme } from "antd";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import { initAuth } from "./auth";
import App from "./App";
import { ThemeProvider, useTheme } from "./theme";
import { I18nProvider, tr } from "./i18n";
import "antd/dist/reset.css";
import "./styles.css";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
});

function Themed({ children }: { children: React.ReactNode }) {
  const { algorithm, resolved } = useTheme();
  const dark = resolved === "dark";
  const accent = dark ? "#6ea8fe" : "#2563eb";
  return (
    <ConfigProvider
      theme={{
        algorithm,
        token: {
          colorPrimary: accent,
          colorInfo: accent,
          colorLink: accent,
          colorLinkHover: dark ? "#8bbcff" : "#1d4ed8",
          borderRadius: 12,
          colorBgLayout: dark ? "#0b0f17" : "#f4f7fc",
          colorBgContainer: dark ? "#111826" : "#ffffff",
          colorBgElevated: dark ? "#141b29" : "#ffffff",
          colorBorder: dark ? "#222b39" : "rgba(15,23,42,.12)",
          colorBorderSecondary: dark ? "#1b2432" : "rgba(15,23,42,.08)",
          colorText: dark ? "#e8ecf4" : "#1a2233",
          colorTextSecondary: dark ? "#9aa6bd" : "#4b5875",
          colorTextTertiary: dark ? "#7b88a3" : "#6b7794",
          fontFamily:
            "-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',Roboto,sans-serif",
        },
        components: {
          Menu: {
            itemSelectedBg: dark ? "rgba(110,168,254,.16)" : "rgba(37,99,235,.10)",
            itemSelectedColor: dark ? "#e8ecf4" : "#1d4ed8",
            itemBorderRadius: 10,
          },
          Layout: { headerBg: "transparent", siderBg: "transparent", bodyBg: "transparent" },
          Table: {
            headerBg: dark ? "#151d2c" : "#f5f8fc",
            headerColor: dark ? "#c7d0e0" : "#334155",
            rowHoverBg: dark ? "rgba(110,168,254,.06)" : "rgba(37,99,235,.04)",
            borderColor: dark ? "#1b2432" : "rgba(15,23,42,.08)",
          },
          Card: { colorBorderSecondary: dark ? "#1b2432" : "rgba(15,23,42,.08)" },
        },
      }}
    >
      {children}
    </ConfigProvider>
  );
}

function Root() {
  const [ready, setReady] = React.useState(false);
  React.useEffect(() => {
    initAuth().then(() => setReady(true));
  }, []);
  if (!ready) {
    return (
      <div style={{ display: "grid", placeItems: "center", height: "100vh" }}>
        <Spin size="large" tip={tr("正在登录…")} />
      </div>
    );
  }
  return (
    <ThemeProvider>
      <I18nProvider>
        <Themed>
          <QueryClientProvider client={queryClient}>
            <BrowserRouter>
              <App />
            </BrowserRouter>
          </QueryClientProvider>
        </Themed>
      </I18nProvider>
    </ThemeProvider>
  );
}

ReactDOM.createRoot(document.getElementById("root")!).render(<Root />);
