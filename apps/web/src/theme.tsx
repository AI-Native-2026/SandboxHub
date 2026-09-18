import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { theme as antdTheme } from "antd";

export type ThemeMode = "dark" | "light" | "auto";

interface ThemeCtx {
  mode: ThemeMode;
  resolved: "dark" | "light";
  setMode: (m: ThemeMode) => void;
  algorithm: typeof antdTheme.darkAlgorithm;
}

const Ctx = createContext<ThemeCtx>({
  mode: "dark",
  resolved: "dark",
  setMode: () => {},
  algorithm: antdTheme.darkAlgorithm,
});

function resolve(mode: ThemeMode): "dark" | "light" {
  if (mode === "auto") {
    return window.matchMedia?.("(prefers-color-scheme: light)").matches ? "light" : "dark";
  }
  return mode;
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [mode, setMode] = useState<ThemeMode>(() => (localStorage.getItem("sh-theme") as ThemeMode) || "dark");
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const mq = window.matchMedia?.("(prefers-color-scheme: light)");
    const onChange = () => setTick((t) => t + 1);
    mq?.addEventListener?.("change", onChange);
    return () => mq?.removeEventListener?.("change", onChange);
  }, []);

  const resolved = useMemo(() => resolve(mode), [mode, tick]);

  useEffect(() => {
    localStorage.setItem("sh-theme", mode);
    document.documentElement.setAttribute("data-theme", resolved);
  }, [mode, resolved]);

  const algorithm = resolved === "dark" ? antdTheme.darkAlgorithm : antdTheme.defaultAlgorithm;
  return <Ctx.Provider value={{ mode, resolved, setMode, algorithm }}>{children}</Ctx.Provider>;
}

export const useTheme = () => useContext(Ctx);
