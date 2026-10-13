"use client";

import { useEffect, useRef } from "react";

export type StageTheme = "dark" | "light";

type Twinkle = { x: number; y: number; r: number; phase: number; speed: number; hue: number };
type Shooter = { x: number; y: number; vx: number; vy: number; tail: number; width: number; hue: number; age: number; life: number };

const PALETTE = {
  dark: { sat: 92, light: 82, tailLight: 78, alphaScale: 1 },
  light: { sat: 82, light: 38, tailLight: 42, alphaScale: 0.9 },
};

function makeTwinkle(): Twinkle {
  const roll = Math.random();
  return { x: Math.random(), y: Math.random(), r: 0.5 + Math.random() * (roll > 0.93 ? 2.2 : 1.1), phase: Math.random() * Math.PI * 2, speed: 0.6 + Math.random() * 2.6, hue: roll > 0.8 ? 262 : roll > 0.4 ? 176 : 194 };
}

function makeShooter(width: number, height: number): Shooter {
  const angle = 2.25 + Math.random() * 0.4;
  const speed = 900 + Math.random() * 900;
  const bright = Math.random() > 0.8;
  return {
    x: width * (0.15 + Math.random() * 1.0),
    y: -40 + Math.random() * height * 0.55,
    vx: Math.cos(angle) * speed,
    vy: Math.sin(angle) * speed,
    tail: (bright ? 260 : 120) + Math.random() * 160,
    width: bright ? 2.6 : 1.4 + Math.random() * 0.8,
    hue: Math.random() > 0.35 ? 175 : 258,
    age: 0,
    life: 0,
  };
}

export function ShootingStarField({ theme, className = "" }: { theme: StageTheme; className?: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const themeRef = useRef(theme);
  themeRef.current = theme;

  useEffect(() => {
    const canvas = canvasRef.current;
    const context = canvas?.getContext("2d");
    if (!canvas || !context) return;
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let width = 0;
    let height = 0;
    let twinkles: Twinkle[] = [];
    let shooters: Shooter[] = [];
    let nextSpawn = 0;
    let frame = 0;
    let last = performance.now();
    let clock = 0;

    const resize = () => {
      const bounds = canvas.getBoundingClientRect();
      const scale = Math.min(window.devicePixelRatio || 1, 2);
      width = bounds.width;
      height = bounds.height;
      canvas.width = Math.floor(width * scale);
      canvas.height = Math.floor(height * scale);
      context.setTransform(scale, 0, 0, scale, 0, 0);
      const target = Math.max(90, Math.floor((width * height) / 4200));
      twinkles = Array.from({ length: target }, makeTwinkle);
    };

    const drawTwinkles = (p: (typeof PALETTE)["dark"]) => {
      for (const t of twinkles) {
        const wave = 0.5 + 0.5 * Math.sin(clock * t.speed + t.phase);
        const alpha = (0.08 + 0.92 * wave ** 3) * p.alphaScale;
        const x = t.x * width;
        const y = t.y * height;
        context.fillStyle = `hsla(${t.hue}, ${p.sat}%, ${p.light}%, ${alpha})`;
        context.beginPath();
        context.arc(x, y, t.r, 0, Math.PI * 2);
        context.fill();
        if (t.r > 1.5 && wave > 0.82) {
          const glint = t.r * 7 * (wave - 0.8) * 5;
          context.strokeStyle = `hsla(${t.hue}, ${p.sat}%, ${p.light}%, ${alpha * 0.8})`;
          context.lineWidth = 0.8;
          context.beginPath();
          context.moveTo(x - glint, y); context.lineTo(x + glint, y);
          context.moveTo(x, y - glint); context.lineTo(x, y + glint);
          context.stroke();
        }
      }
    };

    const drawShooters = (p: (typeof PALETTE)["dark"], dt: number) => {
      shooters = shooters.filter((s) => s.x > -400 && s.y < height + 400 && s.age < 3);
      for (const s of shooters) {
        s.age += dt;
        s.x += s.vx * dt;
        s.y += s.vy * dt;
        const speed = Math.hypot(s.vx, s.vy);
        const tx = s.x - (s.vx / speed) * s.tail;
        const ty = s.y - (s.vy / speed) * s.tail;
        const gradient = context.createLinearGradient(s.x, s.y, tx, ty);
        gradient.addColorStop(0, `hsla(${s.hue}, ${p.sat}%, ${p.tailLight}%, 0.95)`);
        gradient.addColorStop(1, `hsla(${s.hue}, ${p.sat}%, ${p.tailLight}%, 0)`);
        context.strokeStyle = gradient;
        context.lineWidth = s.width;
        context.lineCap = "round";
        context.beginPath();
        context.moveTo(s.x, s.y);
        context.lineTo(tx, ty);
        context.stroke();
        context.fillStyle = `hsla(${s.hue}, ${p.sat}%, ${Math.min(96, p.tailLight + 14)}%, 1)`;
        context.shadowColor = `hsla(${s.hue}, 100%, ${p.tailLight}%, 0.9)`;
        context.shadowBlur = 14;
        context.beginPath();
        context.arc(s.x, s.y, s.width * 1.2, 0, Math.PI * 2);
        context.fill();
        context.shadowBlur = 0;
      }
    };

    const render = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      clock += dt;
      const p = PALETTE[themeRef.current];
      context.clearRect(0, 0, width, height);
      drawTwinkles(p);
      if (!reduceMotion) {
        if (clock >= nextSpawn) {
          const burst = Math.random() > 0.82 ? 2 + Math.floor(Math.random() * 2) : 1;
          for (let i = 0; i < burst; i++) shooters.push(makeShooter(width, height));
          nextSpawn = clock + 0.3 + Math.random() * 0.9;
        }
        drawShooters(p, dt);
        frame = requestAnimationFrame(render);
      }
    };

    const observer = new ResizeObserver(resize);
    observer.observe(canvas);
    resize();
    frame = requestAnimationFrame(render);
    return () => { observer.disconnect(); cancelAnimationFrame(frame); };
  }, []);

  return <canvas ref={canvasRef} className={`shooting-star-field ${className}`} aria-hidden="true" />;
}
