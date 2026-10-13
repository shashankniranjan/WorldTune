"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ArrowLeft, Maximize, Minimize, Moon, Sun } from "lucide-react";
import { ShootingStarField, type StageTheme } from "@/components/shooting-star-field";

const IDLE_MS = 2800;

export function LogoStage({ initialTheme = "dark" }: { initialTheme?: StageTheme }) {
  const [theme, setTheme] = useState<StageTheme>(initialTheme);
  const [idle, setIdle] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);

  const toggleTheme = useCallback(() => setTheme((current) => (current === "dark" ? "light" : "dark")), []);
  const toggleFullscreen = useCallback(() => {
    if (document.fullscreenElement) void document.exitFullscreen();
    else void document.documentElement.requestFullscreen?.();
  }, []);

  useEffect(() => {
    let timer = 0;
    const wake = () => {
      setIdle(false);
      window.clearTimeout(timer);
      timer = window.setTimeout(() => setIdle(true), IDLE_MS);
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.metaKey || event.ctrlKey || event.altKey) return;
      const key = event.key.toLowerCase();
      if (key === "t") toggleTheme();
      if (key === "f") toggleFullscreen();
      wake();
    };
    const onFullscreen = () => setFullscreen(Boolean(document.fullscreenElement));
    wake();
    window.addEventListener("pointermove", wake);
    window.addEventListener("pointerdown", wake);
    window.addEventListener("keydown", onKey);
    document.addEventListener("fullscreenchange", onFullscreen);
    return () => {
      window.clearTimeout(timer);
      window.removeEventListener("pointermove", wake);
      window.removeEventListener("pointerdown", wake);
      window.removeEventListener("keydown", onKey);
      document.removeEventListener("fullscreenchange", onFullscreen);
    };
  }, [toggleTheme, toggleFullscreen]);

  return <main className="logo-stage" data-theme={theme} data-idle={idle}>
    <div className="logo-glow" aria-hidden="true" />
    <ShootingStarField theme={theme} />
    <h1 className="logo-mark" aria-label="WorldTune"><span>WORLD</span><span>TUNE</span></h1>
    <nav className="logo-controls" aria-label="Logo page controls">
      <Link href="/" className="logo-ctl" aria-label="Back to landing page" title="Back to landing page"><ArrowLeft size={18} /></Link>
      <span className="logo-ctl-spacer" />
      <button type="button" className="logo-ctl" onClick={toggleTheme} aria-label={theme === "dark" ? "Switch to white background" : "Switch to dark background"} title="Toggle background (T)">{theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}</button>
      <button type="button" className="logo-ctl" onClick={toggleFullscreen} aria-label={fullscreen ? "Exit full screen" : "Enter full screen"} title="Full screen (F)">{fullscreen ? <Minimize size={18} /> : <Maximize size={18} />}</button>
    </nav>
    <p className="logo-hint">T &nbsp;background &nbsp;·&nbsp; F &nbsp;full screen</p>
  </main>;
}
