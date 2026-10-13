"use client";

import React, { useEffect, useRef, useState } from "react";
import { Moon, Sun } from "lucide-react";
import type { RoadScene as Scene } from "@/components/landing/road-scene/scene";

const ASSETS = "/road-scene/";

/**
 * Hero background: an interactive 3D road scene with traffic and potholes (three.js, loaded in
 * the browser only and in its own chunk).
 *
 * - Pointing at a pothole eases the scene to a stop, outlines the pothole and opens a panel
 *   beside it; moving away closes the panel and traffic resumes from where it stopped. A click
 *   or a tap keeps the panel open until it is closed, and Escape closes it.
 * - A rendered still is shown first; it stays when WebGL is unavailable or the scene cannot start.
 * - While the page scrolls, the scene moves a little slower than the content and fades into the
 *   page background, so the next section rises out of it.
 *
 * The scene is a demonstration: its potholes are samples, not inspection records, and the panel
 * says so.
 */
export function RoadScene() {
  const host = useRef<HTMLDivElement>(null);
  const layer = useRef<HTMLDivElement>(null);
  const fade = useRef<HTMLDivElement>(null);
  const scene = useRef<Scene>();
  const [state, setState] = useState<"loading" | "ready" | "failed">("loading");
  const [readout, setReadout] = useState<string | null>(null);
  const [night, setNight] = useState(false);
  const choose = (on: boolean) => {
    setNight(on);
    scene.current?.setNight(on);
  };

  useEffect(() => {
    const el = host.current;
    if (!el) return;
    let cancelled = false;
    let timer = 0;

    import("@/components/landing/road-scene/scene")
      .then(({ createRoadScene }) => {
        if (cancelled) return;
        const created = createRoadScene(el, ASSETS);
        scene.current = created;
        setState("ready");
        // Add ?scene-debug to the address to see the frame rate and to let a test reach the scene.
        if (window.location.search.includes("scene-debug")) {
          (window as unknown as { __roadScene?: Scene }).__roadScene = created;
          timer = window.setInterval(() => {
            const s = created.stats();
            setReadout(`${s.fps} fps · ${s.calls} draw calls · ${Math.round(s.triangles / 1000)}k triangles · quality ${s.quality} · flow ${s.flow} · ${s.width}×${s.height} @${s.pixelRatio}x`);
          }, 1000);
        }
      })
      .catch((error) => {
        console.warn("Road scene unavailable, showing the still image instead:", error);
        if (!cancelled) setState("failed");
      });

    return () => {
      cancelled = true;
      window.clearInterval(timer);
      scene.current?.dispose();
      scene.current = undefined;
    };
  }, []);

  // Scroll blending: the scene lags behind the content and darkens into the page background.
  useEffect(() => {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    let frame = 0;
    const apply = () => {
      frame = 0;
      const h = window.innerHeight || 1;
      const p = Math.min(1, Math.max(0, window.scrollY / h));
      if (layer.current) layer.current.style.transform = `translate3d(0, ${(p * h * 0.22).toFixed(1)}px, 0)`;
      if (fade.current) fade.current.style.opacity = (p * p * 0.7).toFixed(3);
    };
    const onScroll = () => {
      if (!frame) frame = requestAnimationFrame(apply);
    };
    apply();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      window.removeEventListener("scroll", onScroll);
      if (frame) cancelAnimationFrame(frame);
    };
  }, []);

  return (
    <>
      <div ref={layer} className="absolute inset-0 will-change-transform">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={`${ASSETS}poster.jpg`}
          alt=""
          aria-hidden
          className={`absolute inset-0 h-full w-full object-cover transition-opacity duration-700 ${state === "ready" ? "opacity-0" : "opacity-100"}`}
        />
        <div
          ref={host}
          aria-hidden
          className={`absolute inset-0 transition-opacity duration-700 [&>canvas]:block [&>canvas]:h-full [&>canvas]:w-full ${state === "ready" ? "opacity-100" : "opacity-0"}`}
        />
      </div>

      {/* The foot of the hero settles into the page background, which the next section shares. */}
      <div aria-hidden className="pointer-events-none absolute inset-x-0 bottom-0 z-[1] h-[32%] bg-[linear-gradient(to_bottom,transparent,rgb(var(--ri-solid)/0.45)_55%,rgb(var(--ri-solid))_100%)]" />
      {/* Deepens while the page scrolls away from the hero. */}
      <div ref={fade} aria-hidden className="pointer-events-none absolute inset-0 z-[1] bg-ri-solid opacity-0" />

      {state === "ready" && (
        <>
          <p className="pointer-events-none absolute left-1/2 top-[92px] z-10 hidden -translate-x-1/2 whitespace-nowrap rounded-md border border-white/20 bg-black/50 px-2.5 py-1 text-[11px] uppercase tracking-[0.08em] text-zinc-200 sm:block">
            Demonstration scene · point at or tap a pothole
          </p>
          {/* Day / night: relights the same scene (sun, sky, street lights, vehicle lamps, pothole highlights). */}
          <div role="group" aria-label="Scene lighting" style={{ position: "absolute" }} className="liquid-glass right-6 top-[88px] z-10 flex rounded-lg p-1 text-white md:right-12 lg:right-16">
            {([[false, "Day", Sun], [true, "Night", Moon]] as const).map(([on, label, Icon]) => (
              <button
                key={label}
                type="button"
                aria-pressed={night === on}
                onClick={() => choose(on)}
                className={`inline-flex h-9 items-center gap-1.5 rounded-md px-3 text-xs font-medium transition-colors duration-200 focus:outline-none focus-visible:ring-2 focus-visible:ring-white ${night === on ? "bg-white text-black" : "text-zinc-200 hover:bg-white/10"}`}
              >
                <Icon className="h-3.5 w-3.5" />
                {label}
              </button>
            ))}
          </div>
          {/* Keyboard route to the same panel; visible only when focused. */}
          <button
            type="button"
            onClick={() => {
              if (scene.current?.selectNearest()) document.getElementById("roadSceneCard")?.focus();
            }}
            className="sr-only focus:not-sr-only focus:absolute focus:left-6 focus:top-[92px] focus:z-30 focus:rounded-lg focus:bg-white focus:px-3 focus:py-2 focus:text-sm focus:font-medium focus:text-black"
          >
            Inspect a sample pothole
          </button>
        </>
      )}

      {readout && (
        <p className="pointer-events-none absolute bottom-2 left-1/2 z-10 -translate-x-1/2 whitespace-nowrap rounded-md bg-black/70 px-2.5 py-1 font-mono text-[11px] text-white">
          {readout}
        </p>
      )}

      {/* Filled in, positioned and opened by the scene when a pothole is pointed at or selected. */}
      <div
        id="roadSceneCard"
        role="dialog"
        tabIndex={-1}
        aria-label="Pothole details (demonstration)"
        className="liquid-glass pointer-events-none absolute left-0 top-0 z-20 w-[min(260px,calc(100vw-20px))] translate-y-1.5 rounded-xl p-4 text-[13px] leading-snug text-white opacity-0 outline-none transition-[opacity,transform] duration-200 ease-out data-[open=true]:pointer-events-auto data-[open=true]:translate-y-0 data-[open=true]:opacity-100"
        style={{ background: "rgba(0, 0, 0, 0.7)", position: "absolute" }}
      >
        <button id="roadSceneCardClose" type="button" aria-label="Close" className="absolute right-1.5 top-1 h-8 w-8 rounded-md text-lg text-zinc-400 hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-white">
          ×
        </button>
        <h2 id="roadSceneCardTitle" className="pr-8 text-[15px] font-semibold" />
        <p className="mb-2.5 text-[10.5px] uppercase tracking-[0.08em] text-amber-400">Demonstration, not an inspection record</p>
        <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
          <dt className="text-zinc-400">Severity</dt>
          <dd>
            <span id="roadSceneCardSev" className="inline-block rounded px-1.5 text-[11px] font-semibold text-black" />
          </dd>
          <dt className="text-zinc-400">Depth</dt>
          <dd id="roadSceneCardDepth" />
          <dt className="text-zinc-400">Size</dt>
          <dd id="roadSceneCardSize" />
          <dt className="text-zinc-400">Condition</dt>
          <dd id="roadSceneCardCond" />
          <dt className="text-zinc-400">Inspection</dt>
          <dd>None (sample)</dd>
        </dl>
        <p className="mt-2.5 text-[11.5px] text-zinc-400">
          Traffic is paused while this is open. In the console, a damage record shows its real severity, segment, review status and photos.
        </p>
      </div>
    </>
  );
}
