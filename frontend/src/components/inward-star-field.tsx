"use client";

import { useEffect, useRef } from "react";

type Star = { x: number; y: number; speed: number; size: number; hue: number; alpha: number };

function createStar(width: number, height: number, velocity: number): Star {
  const angle = Math.random() * Math.PI * 2;
  const radius = Math.max(width, height) * (0.55 + Math.random() * 0.55);
  return { x: Math.cos(angle) * radius, y: Math.sin(angle) * radius, speed: (0.0018 + Math.random() * 0.004) * velocity, size: 0.55 + Math.random() * 2.15, hue: Math.random() > 0.84 ? 260 : Math.random() > 0.42 ? 175 : 192, alpha: 0.32 + Math.random() * 0.68 };
}

export function InwardStarField({ className = "", density, velocity = 1 }: { className?: string; density?: number; velocity?: number }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const context = canvas.getContext("2d");
    if (!context) return;
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let animationFrame = 0;
    let width = 0;
    let height = 0;
    let stars: Star[] = [];
    let advancing = true;
    const count = () => density ?? Math.max(72, Math.floor((width * height) / 5200));
    const paint = () => {
      context.clearRect(0, 0, width, height);
      const centerX = width * 0.56;
      const centerY = height * 0.54;
      for (const star of stars) {
        const previousX = centerX + star.x;
        const previousY = centerY + star.y;
        let respawned = false;
        if (advancing) {
          star.x *= 1 - star.speed;
          star.y *= 1 - star.speed;
          if (Math.hypot(star.x, star.y) < 12) { Object.assign(star, createStar(width, height, velocity)); respawned = true; }
        }
        const currentX = centerX + star.x;
        const currentY = centerY + star.y;
        // A respawned star has no trail: drawing from its old position would streak a line across the screen.
        if (!respawned) {
          context.beginPath();
          context.moveTo(advancing ? previousX : currentX + star.x * star.speed, advancing ? previousY : currentY + star.y * star.speed);
          context.lineTo(currentX, currentY);
          context.strokeStyle = `hsla(${star.hue}, 96%, 76%, ${star.alpha * 0.64})`;
          context.lineWidth = star.size * 0.82;
          context.stroke();
        }
        context.beginPath();
        context.arc(currentX, currentY, star.size, 0, Math.PI * 2);
        context.fillStyle = `hsla(${star.hue}, 96%, 79%, ${star.alpha})`;
        context.fill();
      }
    };
    const resize = () => {
      const bounds = canvas.getBoundingClientRect();
      const scale = Math.min(window.devicePixelRatio || 1, 2);
      // A scrollbar or layout shift changes the size by a few pixels. Reallocating the canvas clears it, so ignore tiny changes.
      if (Math.abs(bounds.width - width) < 2 && Math.abs(bounds.height - height) < 2 && width > 0) return;
      width = bounds.width;
      height = bounds.height;
      canvas.width = Math.floor(width * scale);
      canvas.height = Math.floor(height * scale);
      context.setTransform(scale, 0, 0, scale, 0, 0);
      // Keep the stars already in flight; only add or drop to match the new size.
      const target = count();
      if (stars.length > target) stars.length = target;
      while (stars.length < target) stars.push(createStar(width, height, velocity));
      // Repaint straight away so the cleared canvas is never visible between frames.
      advancing = false;
      paint();
    };
    const loop = () => {
      advancing = true;
      paint();
      if (!reduceMotion) animationFrame = requestAnimationFrame(loop);
    };
    const observer = new ResizeObserver(resize);
    observer.observe(canvas);
    resize();
    loop();
    return () => { observer.disconnect(); cancelAnimationFrame(animationFrame); };
  }, [density, velocity]);

  return <canvas ref={canvasRef} className={`inward-star-field ${className}`} aria-hidden="true" />;
}
