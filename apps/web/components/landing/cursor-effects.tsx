"use client";

/**
 * Cursor-driven effects for the landing page. Everything is written straight to element
 * styles inside one requestAnimationFrame loop: no React state changes while the mouse moves,
 * and the loop stops as soon as the motion has settled. Nothing here runs on touch devices or
 * when the visitor asks for reduced motion, and no element intercepts pointer events.
 */

import React, { useEffect, useRef } from "react";

function cursorEffectsAllowed(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia("(hover: hover) and (pointer: fine)").matches &&
    !window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

/**
 * Mounted once. Draws a soft glow that follows the cursor and moves every element marked
 * `data-parallax="<px>"` by up to that many pixels (a negative value moves against the cursor).
 * An element marked `data-tilt="<deg>"` also leans by up to that many degrees.
 */
export function CursorAmbient() {
  const glow = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!cursorEffectsAllowed()) return;
    const glowEl = glow.current;
    const layers = Array.from(document.querySelectorAll<HTMLElement>("[data-parallax], [data-tilt]")).map((el) => ({
      el,
      depth: Number(el.dataset.parallax ?? 0),
      tilt: Number(el.dataset.tilt ?? 0),
    }));

    // Target (where the cursor is) and current (eased) positions; nx / ny are -1..1 from the centre.
    const target = { x: window.innerWidth / 2, y: window.innerHeight / 3, nx: 0, ny: 0 };
    const current = { ...target };
    let frame = 0;
    let visible = false;

    const tick = () => {
      const ease = 0.12;
      current.x += (target.x - current.x) * ease;
      current.y += (target.y - current.y) * ease;
      current.nx += (target.nx - current.nx) * ease;
      current.ny += (target.ny - current.ny) * ease;

      if (glowEl) glowEl.style.transform = `translate3d(${current.x}px, ${current.y}px, 0) translate(-50%, -50%)`;
      for (const { el, depth, tilt } of layers) {
        const move = `translate3d(${(current.nx * depth).toFixed(2)}px, ${(current.ny * depth).toFixed(2)}px, 0)`;
        el.style.transform = tilt
          ? `perspective(1200px) ${move} rotateX(${(-current.ny * tilt).toFixed(2)}deg) rotateY(${(current.nx * tilt).toFixed(2)}deg)`
          : move;
      }

      const settled =
        Math.abs(target.x - current.x) < 0.3 && Math.abs(target.y - current.y) < 0.3 && Math.abs(target.nx - current.nx) < 0.002;
      frame = settled ? 0 : requestAnimationFrame(tick);
    };

    const onMove = (e: PointerEvent) => {
      if (e.pointerType !== "mouse") return;
      target.x = e.clientX;
      target.y = e.clientY;
      target.nx = (e.clientX / window.innerWidth) * 2 - 1;
      target.ny = (e.clientY / window.innerHeight) * 2 - 1;
      if (!visible && glowEl) {
        visible = true;
        glowEl.style.opacity = "1";
      }
      if (!frame) frame = requestAnimationFrame(tick);
    };
    const onLeave = () => {
      target.nx = 0;
      target.ny = 0;
      visible = false;
      if (glowEl) glowEl.style.opacity = "0";
      if (!frame) frame = requestAnimationFrame(tick);
    };

    window.addEventListener("pointermove", onMove, { passive: true });
    document.documentElement.addEventListener("pointerleave", onLeave);
    return () => {
      window.removeEventListener("pointermove", onMove);
      document.documentElement.removeEventListener("pointerleave", onLeave);
      if (frame) cancelAnimationFrame(frame);
      for (const { el } of layers) el.style.transform = "";
    };
  }, []);

  return (
    <div
      ref={glow}
      aria-hidden
      className="fixed left-0 top-0 z-[-1] h-[560px] w-[560px] rounded-full pointer-events-none opacity-0 transition-opacity duration-500 will-change-transform bg-[radial-gradient(closest-side,rgb(var(--ri-primary)/0.13),rgb(var(--ri-info)/0.05)_55%,transparent)]"
    />
  );
}

/**
 * Lets its child drift a few pixels toward the cursor while hovered (a "magnetic" control).
 * It only moves a wrapper; the child keeps its own hover, focus and click behaviour.
 */
export function Magnetic({ children, strength = 6, className = "" }: { children: React.ReactNode; strength?: number; className?: string }) {
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el || !cursorEffectsAllowed()) return;
    let frame = 0;
    let tx = 0;
    let ty = 0;

    const apply = () => {
      frame = 0;
      el.style.transform = `translate3d(${tx.toFixed(2)}px, ${ty.toFixed(2)}px, 0)`;
    };
    const onMove = (e: PointerEvent) => {
      const r = el.getBoundingClientRect();
      tx = ((e.clientX - (r.left + r.width / 2)) / (r.width / 2)) * strength;
      ty = ((e.clientY - (r.top + r.height / 2)) / (r.height / 2)) * strength;
      if (!frame) frame = requestAnimationFrame(apply);
    };
    const onLeave = () => {
      tx = 0;
      ty = 0;
      if (!frame) frame = requestAnimationFrame(apply);
    };
    el.addEventListener("pointermove", onMove, { passive: true });
    el.addEventListener("pointerleave", onLeave);
    return () => {
      el.removeEventListener("pointermove", onMove);
      el.removeEventListener("pointerleave", onLeave);
      if (frame) cancelAnimationFrame(frame);
    };
  }, [strength]);

  return (
    <span ref={ref} className={`inline-flex transition-transform duration-200 ease-out will-change-transform ${className}`}>
      {children}
    </span>
  );
}
