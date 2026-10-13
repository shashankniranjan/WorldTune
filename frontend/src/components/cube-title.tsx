"use client";

import { useEffect, useRef } from "react";

type Cube = {
  hx: number; hy: number; size: number; line: number; shade: number;
  sx: number; sy: number; sz: number;
  x: number; y: number; z: number; vx: number; vy: number; vz: number;
};

const PAD = 70;
const SHADES = 10;

function palette(line: number, shade: number) {
  const t = shade / (SHADES - 1);
  const [h, s, lo, hi] = line === 0 ? [195, 14, 58, 97] : [172, 62, 44, 86];
  const l = lo + (hi - lo) * t;
  return [`hsl(${h} ${s}% ${Math.min(99, l + 9)}%)`, `hsl(${h} ${s}% ${l}%)`, `hsl(${h} ${s}% ${l - 20}%)`];
}
const COLORS = [0, 1].map((line) => Array.from({ length: SHADES }, (_, i) => palette(line, i)));

function build(wrap: HTMLElement, h1: HTMLElement) {
  const wr = wrap.getBoundingClientRect();
  const W = Math.ceil(wr.width + PAD * 2);
  const H = Math.ceil(wr.height + PAD * 2);
  const ox = wr.left - PAD;
  const oy = wr.top - PAD;
  const off = document.createElement("canvas");
  off.width = W; off.height = H;
  const octx = off.getContext("2d", { willReadFrequently: true })!;
  const cubes: Cube[] = [];
  const spans = Array.from(h1.children) as HTMLElement[];
  const fontSize = parseFloat(getComputedStyle(h1).fontSize);
  const step = Math.max(4, Math.round(fontSize / 22));

  spans.forEach((span, line) => {
    const cs = getComputedStyle(span);
    const range = document.createRange();
    range.selectNodeContents(span);
    const rect = range.getBoundingClientRect();
    const probe = document.createElement("i");
    probe.style.cssText = "display:inline-block;width:0;height:0;vertical-align:baseline";
    span.appendChild(probe);
    const baseline = probe.getBoundingClientRect().bottom;
    probe.remove();

    octx.clearRect(0, 0, W, H);
    octx.font = `${cs.fontWeight} ${cs.fontSize} ${cs.fontFamily}`;
    octx.letterSpacing = cs.letterSpacing === "normal" ? "0px" : cs.letterSpacing;
    octx.textBaseline = "alphabetic";
    octx.fillStyle = "#000";
    octx.fillText(span.textContent ?? "", rect.left - ox, baseline - oy);
    const data = octx.getImageData(0, 0, W, H).data;

    for (let y = step / 2; y < H; y += step) {
      for (let x = step / 2; x < W; x += step) {
        if (data[((y | 0) * W + (x | 0)) * 4 + 3] < 120) continue;
        const r = Math.random();
        cubes.push({
          hx: x, hy: y, line, size: step * (0.8 + Math.random() * 0.55) * (r > 0.96 ? 1.7 : 1),
          shade: Math.floor(Math.random() * SHADES),
          sx: (Math.random() - 0.5) * step * 2.6, sy: (Math.random() - 0.5) * step * 2.6, sz: Math.random() * 5 - 1,
          x: 0, y: 0, z: 0, vx: 0, vy: 0, vz: 0,
        });
      }
    }
  });
  cubes.sort(() => Math.random() - 0.5);
  return { cubes, W, H, ox, oy, radius: fontSize * 0.5 };
}

export function CubeTitle({ children }: { children: React.ReactNode }) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const h1Ref = useRef<HTMLHeadingElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const state = useRef({ hover: false, mx: -1e5, my: -1e5, raf: 0, timers: [] as number[], scene: null as ReturnType<typeof build> | null, size: "" });

  useEffect(() => {
    const wrap = wrapRef.current!, h1 = h1Ref.current!, canvas = canvasRef.current!;
    if (window.matchMedia("(prefers-reduced-motion: reduce), (pointer: coarse)").matches) return;
    const ctx = canvas.getContext("2d")!;
    const s = state.current;

    const frame = () => {
      const sc = s.scene;
      if (!sc) return;
      const k = s.hover ? 1 : 0;
      ctx.setTransform(canvas.width / sc.W, 0, 0, canvas.height / sc.H, 0, 0);
      ctx.clearRect(0, 0, sc.W, sc.H);
      const R = sc.radius;
      for (const c of sc.cubes) {
        const px = c.hx + c.x, py = c.hy + c.y;
        const dx = px - s.mx, dy = py - s.my, d = Math.hypot(dx, dy);
        if (d < R) {
          const f = (1 - d / R) ** 2;
          c.vx += (dx / (d || 1)) * f * 5; c.vy += (dy / (d || 1)) * f * 5; c.vz += f * 2.2;
        }
        c.vx += (c.sx * k - c.x) * 0.07; c.vy += (c.sy * k - c.y) * 0.07; c.vz += (c.sz * k - c.z) * 0.07;
        c.vx *= 0.82; c.vy *= 0.82; c.vz *= 0.82;
        c.x += c.vx; c.y += c.vy; c.z += c.vz;
        const u = (c.size * (1 + c.z * 0.06)) / 2, w = u * 0.87, X = c.hx + c.x, Y = c.hy + c.y;
        const [top, left, right] = COLORS[c.line][c.shade];
        ctx.fillStyle = top;
        ctx.beginPath(); ctx.moveTo(X, Y - u); ctx.lineTo(X + w, Y - u / 2); ctx.lineTo(X, Y); ctx.lineTo(X - w, Y - u / 2); ctx.fill();
        ctx.fillStyle = left;
        ctx.beginPath(); ctx.moveTo(X - w, Y - u / 2); ctx.lineTo(X, Y); ctx.lineTo(X, Y + u); ctx.lineTo(X - w, Y + u / 2); ctx.fill();
        ctx.fillStyle = right;
        ctx.beginPath(); ctx.moveTo(X + w, Y - u / 2); ctx.lineTo(X, Y); ctx.lineTo(X, Y + u); ctx.lineTo(X + w, Y + u / 2); ctx.fill();
      }
      s.raf = requestAnimationFrame(frame);
    };

    const setup = () => {
      const r = wrap.getBoundingClientRect();
      const key = `${Math.round(r.width)}x${Math.round(r.height)}x${getComputedStyle(h1).fontSize}`;
      if (s.scene && key === s.size) return;
      s.size = key;
      s.scene = build(wrap, h1);
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      canvas.width = s.scene.W * dpr; canvas.height = s.scene.H * dpr;
      canvas.style.cssText = `left:${-PAD}px;top:${-PAD}px;width:${s.scene.W}px;height:${s.scene.H}px`;
    };
    const clearTimers = () => { s.timers.forEach(clearTimeout); s.timers = []; };
    const track = (e: PointerEvent) => {
      if (!s.scene) return;
      const r = canvas.getBoundingClientRect();
      s.mx = e.clientX - r.left; s.my = e.clientY - r.top;
    };
    const enter = (e: PointerEvent) => {
      clearTimers();
      if (!s.hover) {
        setup();
        for (const c of s.scene?.cubes ?? []) { c.vx += (Math.random() - 0.5) * 8; c.vy += (Math.random() - 0.5) * 8; c.vz += Math.random() * 3; }
      }
      s.hover = true;
      track(e);
      h1.classList.add("is-cubed");
      canvas.style.opacity = "1";
      if (!s.raf) s.raf = requestAnimationFrame(frame);
    };
    const leave = () => {
      s.hover = false; s.mx = s.my = -1e5;
      clearTimers();
      s.timers.push(window.setTimeout(() => { h1.classList.remove("is-cubed"); canvas.style.opacity = "0"; }, 320));
      s.timers.push(window.setTimeout(() => { cancelAnimationFrame(s.raf); s.raf = 0; }, 800));
    };
    wrap.addEventListener("pointerenter", enter);
    wrap.addEventListener("pointermove", track);
    wrap.addEventListener("pointerleave", leave);
    return () => {
      wrap.removeEventListener("pointerenter", enter);
      wrap.removeEventListener("pointermove", track);
      wrap.removeEventListener("pointerleave", leave);
      clearTimers(); cancelAnimationFrame(s.raf); s.raf = 0;
    };
  }, []);

  return <div className="cube-title" ref={wrapRef}>
    <h1 ref={h1Ref}>{children}</h1>
    <canvas ref={canvasRef} aria-hidden="true" />
  </div>;
}
