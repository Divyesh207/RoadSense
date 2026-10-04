"use client";

import React, { useCallback, useRef, useState } from "react";
import { Maximize2, ZoomIn, ZoomOut } from "lucide-react";

interface BeforeAfterViewerProps {
  beforeUrl: string | null;
  afterUrl: string | null;
  /** Shown under the BEFORE heading, e.g. "original inspection photo". */
  beforeCaption?: string;
  afterCaption?: string;
  /** Taller panes, for the full-screen comparison. */
  large?: boolean;
}

const MIN_ZOOM = 1;
const MAX_ZOOM = 6;

/**
 * BEFORE (left) and AFTER (right) with one shared zoom and pan, so the same spot of both
 * images stays side by side. Zoom with the buttons, the mouse wheel or + / -; drag or use
 * the arrow keys to pan; 0 resets.
 */
export function BeforeAfterViewer({ beforeUrl, afterUrl, beforeCaption, afterCaption, large }: BeforeAfterViewerProps) {
  const [zoom, setZoom] = useState(1);
  const [offset, setOffset] = useState({ x: 0, y: 0 }); // in % of the pane, at the current zoom
  const drag = useRef<{ x: number; y: number; ox: number; oy: number; w: number; h: number } | null>(null);

  const clamp = useCallback((o: { x: number; y: number }, z: number) => {
    const limit = ((z - 1) / 2) * 100; // how far the image can move before an edge shows
    return { x: Math.max(-limit, Math.min(limit, o.x)), y: Math.max(-limit, Math.min(limit, o.y)) };
  }, []);

  const applyZoom = useCallback(
    (next: number) => {
      const z = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, Math.round(next * 100) / 100));
      setZoom(z);
      setOffset((o) => clamp(o, z));
    },
    [clamp]
  );

  const reset = () => {
    setZoom(1);
    setOffset({ x: 0, y: 0 });
  };

  const onPointerDown = (e: React.PointerEvent<HTMLDivElement>) => {
    if (zoom === 1) return;
    const rect = e.currentTarget.getBoundingClientRect();
    drag.current = { x: e.clientX, y: e.clientY, ox: offset.x, oy: offset.y, w: rect.width, h: rect.height };
    e.currentTarget.setPointerCapture(e.pointerId);
  };
  const onPointerMove = (e: React.PointerEvent<HTMLDivElement>) => {
    const d = drag.current;
    if (!d) return;
    setOffset(clamp({ x: d.ox + ((e.clientX - d.x) / d.w) * 100, y: d.oy + ((e.clientY - d.y) / d.h) * 100 }, zoom));
  };
  const onPointerUp = () => {
    drag.current = null;
  };
  const onWheel = (e: React.WheelEvent<HTMLDivElement>) => {
    if (!e.ctrlKey && zoom === 1 && e.deltaY > 0) return; // let the page scroll when not zoomed
    applyZoom(zoom * (e.deltaY < 0 ? 1.15 : 1 / 1.15));
  };
  const onKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    const step = 8;
    const moves: Record<string, [number, number]> = {
      ArrowLeft: [step, 0],
      ArrowRight: [-step, 0],
      ArrowUp: [0, step],
      ArrowDown: [0, -step],
    };
    if (e.key === "+" || e.key === "=") applyZoom(zoom * 1.25);
    else if (e.key === "-") applyZoom(zoom / 1.25);
    else if (e.key === "0") reset();
    else if (moves[e.key]) setOffset((o) => clamp({ x: o.x + moves[e.key][0], y: o.y + moves[e.key][1] }, zoom));
    else return;
    e.preventDefault();
  };

  const transform = { transform: `translate(${offset.x}%, ${offset.y}%) scale(${zoom})` };
  const paneHeight = large ? "h-[38vh] lg:h-[62vh]" : "aspect-video";
  const controlClass =
    "h-8 w-8 inline-flex items-center justify-center rounded-lg border border-ri-line bg-ri-input text-ri-text-soft hover:border-ri-primary/50 hover:text-ri-text transition-colors disabled:opacity-40 focus:outline-none focus-visible:ring-2 focus-visible:ring-ri-primary-bright";

  const pane = (side: "BEFORE" | "AFTER", url: string | null, caption: string | undefined, tone: string) => (
    <figure className="min-w-0">
      <figcaption className="flex items-baseline justify-between gap-2 mb-1.5">
        <span className={`ri-label ${tone}`}>{side}</span>
        {caption && <span className="text-[11px] text-ri-muted truncate">{caption}</span>}
      </figcaption>
      <div
        className={`${paneHeight} rounded-xl bg-ri-bg border border-ri-line overflow-hidden flex items-center justify-center select-none ${
          zoom > 1 ? "cursor-grab active:cursor-grabbing" : ""
        }`}
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerCancel={onPointerUp}
        onWheel={onWheel}
      >
        {url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={url}
            alt={`${side === "BEFORE" ? "Before" : "After"} repair image`}
            draggable={false}
            className="w-full h-full object-contain will-change-transform"
            style={transform}
          />
        ) : (
          <span className="font-code-sm text-[11px] text-ri-faint">No image</span>
        )}
      </div>
    </figure>
  );

  return (
    <div
      role="group"
      aria-label="Before and after comparison. Use plus and minus to zoom, arrow keys to pan, zero to reset."
      tabIndex={0}
      onKeyDown={onKeyDown}
      className="space-y-3 rounded-xl focus:outline-none focus-visible:ring-2 focus-visible:ring-ri-primary-bright/60"
    >
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {pane("BEFORE", beforeUrl, beforeCaption, "text-ri-warning")}
        {pane("AFTER", afterUrl, afterCaption, "text-ri-success")}
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <p className="text-[11px] text-ri-faint">Both images move together. Drag to pan when zoomed.</p>
        <div className="flex items-center gap-1.5">
          <button type="button" onClick={() => applyZoom(zoom / 1.25)} disabled={zoom <= MIN_ZOOM} aria-label="Zoom out" className={controlClass}>
            <ZoomOut className="h-4 w-4" />
          </button>
          <span className="font-mono text-[11px] text-ri-text-soft w-12 text-center tabular-nums">{Math.round(zoom * 100)}%</span>
          <button type="button" onClick={() => applyZoom(zoom * 1.25)} disabled={zoom >= MAX_ZOOM} aria-label="Zoom in" className={controlClass}>
            <ZoomIn className="h-4 w-4" />
          </button>
          <button type="button" onClick={reset} disabled={zoom === 1} aria-label="Reset zoom" className={controlClass}>
            <Maximize2 className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
