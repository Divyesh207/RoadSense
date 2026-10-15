"use client";

import React, { useEffect, useRef, useState } from "react";
import { MapPinned } from "lucide-react";
import "maplibre-gl/dist/maplibre-gl.css";

/**
 * Landing-page map preview: a real, interactive, tilted WebGL map (MapLibre GL with
 * OpenStreetMap vector tiles served by OpenFreeMap, 3D buildings extruded from the tile data).
 *
 * The base map is real geography. The coloured segments and points drawn on top are an
 * ILLUSTRATION of how the console presents data. They are fixed sample shapes defined in this
 * file: they are not read from any organization's database and do not describe the condition
 * of the real roads underneath. The frame says so.
 */

// Base map. With no configuration it is OpenFreeMap's colourful "Liberty" street map (OpenStreetMap data, no key).
// Satellite imagery needs a provider account, so it is opt-in: set NEXT_PUBLIC_SATELLITE_TILE_URL to the provider's
// raster tile URL template ({z}/{x}/{y}, including its public browser key) and NEXT_PUBLIC_SATELLITE_ATTRIBUTION to
// the attribution text that provider requires. Road names and 3D buildings are then drawn over the imagery.
const SATELLITE_URL = process.env.NEXT_PUBLIC_SATELLITE_TILE_URL || "";
const SATELLITE_ATTRIBUTION = process.env.NEXT_PUBLIC_SATELLITE_ATTRIBUTION || "";
const SATELLITE = Boolean(SATELLITE_URL && SATELLITE_ATTRIBUTION);
const STREET_STYLE = "https://tiles.openfreemap.org/styles/liberty";
function mapStyle(): string | import("maplibre-gl").StyleSpecification {
  if (!SATELLITE) return STREET_STYLE;
  return {
    version: 8,
    glyphs: "https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf",
    sources: {
      satellite: { type: "raster", tiles: [SATELLITE_URL], tileSize: 256, maxzoom: 19, attribution: SATELLITE_ATTRIBUTION },
      openmaptiles: { type: "vector", url: "https://tiles.openfreemap.org/planet" },
    },
    layers: [
      { id: "satellite", type: "raster", source: "satellite" },
      {
        id: "road-names", type: "symbol", source: "openmaptiles", "source-layer": "transportation_name", minzoom: 13,
        layout: { "symbol-placement": "line", "text-field": ["coalesce", ["get", "name:en"], ["get", "name"]], "text-font": ["Noto Sans Regular"], "text-size": 11 },
        paint: { "text-color": "#ffffff", "text-halo-color": "rgba(0,0,0,0.75)", "text-halo-width": 1.4 },
      },
    ],
  };
}
const CENTER: [number, number] = [73.8553, 18.5196]; // central Pune, for map context only

// Illustrative overlay (sample shapes only).
const SEGMENTS = [
  { status: "GOOD", coords: [[73.8496, 18.5212], [73.8528, 18.5207], [73.8556, 18.5203]] },
  { status: "FAIR", coords: [[73.8556, 18.5203], [73.8584, 18.5197], [73.8611, 18.5188]] },
  { status: "POOR", coords: [[73.8549, 18.5166], [73.8553, 18.5184], [73.8556, 18.5203]] },
  { status: "GOOD", coords: [[73.8556, 18.5203], [73.8561, 18.5221], [73.8569, 18.5238]] },
];
const DAMAGE = [
  { severity: "CRITICAL", at: [73.8552, 18.5179] },
  { severity: "HIGH", at: [73.8590, 18.5195] },
  { severity: "MEDIUM", at: [73.8571, 18.5200] },
  { severity: "LOW", at: [73.8519, 18.5208] },
];
const INSPECTIONS = [[73.8507, 18.5210], [73.8563, 18.5228], [73.8603, 18.5191], [73.8550, 18.5171]];

// Status colours of the design tokens (MapLibre paint properties cannot read CSS variables).
const HEALTH_COLOR = ["match", ["get", "status"], "GOOD", "#10B981", "FAIR", "#F59E0B", "POOR", "#FB923C", "#EF4444"];
const SEVERITY_COLOR = ["match", ["get", "severity"], "CRITICAL", "#EF4444", "HIGH", "#FB923C", "MEDIUM", "#F59E0B", "#10B981"];

const LEGEND = [
  { color: "bg-ri-danger", label: "Damage point (severity colour)" },
  { color: "border-2 border-ri-info-soft", label: "Inspection point" },
  { color: "bg-ri-success", label: "Road segment (health colour)", line: true },
];

type State = "idle" | "loading" | "ready" | "failed";

export function DemoMap({ className = "" }: { className?: string }) {
  const holder = useRef<HTMLDivElement>(null);
  const [state, setState] = useState<State>("idle");

  useEffect(() => {
    const el = holder.current;
    if (!el) return;
    let map: import("maplibre-gl").Map | undefined;
    let cancelled = false;
    const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const start = async () => {
      setState("loading");
      try {
        const maplibre = (await import("maplibre-gl")).default;
        if (cancelled) return;
        map = new maplibre.Map({
          container: el,
          style: mapStyle(),
          center: CENTER,
          zoom: 15.4,
          pitch: reduceMotion ? 58 : 38,
          bearing: reduceMotion ? -22 : -6,
          maxPitch: 70,
          attributionControl: { compact: true },
          // The page must keep scrolling normally: no wheel zoom, and on touch screens the map
          // only pans with two fingers.
          scrollZoom: false,
          cooperativeGestures: true,
        });
        map.addControl(new maplibre.NavigationControl({ visualizePitch: true }), "top-right");
        map.on("error", (e) => {
          // A failed style or tile source: say so instead of showing an empty frame.
          if (!map?.isStyleLoaded() && String(e?.error?.message ?? "").length > 0) setState((s) => (s === "ready" ? s : "failed"));
        });
        map.on("load", () => {
          if (!map || cancelled) return;
          // 3D buildings from the same vector tiles.
          if (SATELLITE && map.getSource("openmaptiles") && !map.getLayer("ri-buildings-3d")) {
            map.addLayer({
              id: "ri-buildings-3d",
              type: "fill-extrusion",
              source: "openmaptiles",
              "source-layer": "building",
              minzoom: 13,
              paint: {
                "fill-extrusion-color": "#e9e3d8",
                "fill-extrusion-height": ["coalesce", ["get", "render_height"], 6],
                "fill-extrusion-base": ["coalesce", ["get", "render_min_height"], 0],
                "fill-extrusion-opacity": 0.45,
              },
            });
          }
          const feature = (geometry: GeoJSON.Geometry, properties: Record<string, string>) =>
            ({ type: "Feature", geometry, properties }) as GeoJSON.Feature;
          map.addSource("ri-segments", {
            type: "geojson",
            data: { type: "FeatureCollection", features: SEGMENTS.map((s) => feature({ type: "LineString", coordinates: s.coords }, { status: s.status })) },
          });
          map.addSource("ri-damage", {
            type: "geojson",
            data: { type: "FeatureCollection", features: DAMAGE.map((d) => feature({ type: "Point", coordinates: d.at }, { severity: d.severity })) },
          });
          map.addSource("ri-inspections", {
            type: "geojson",
            data: { type: "FeatureCollection", features: INSPECTIONS.map((p) => feature({ type: "Point", coordinates: p }, {})) },
          });
          map.addLayer({
            id: "ri-segments-glow", type: "line", source: "ri-segments",
            layout: { "line-cap": "round", "line-join": "round" },
            paint: { "line-color": "#ffffff", "line-width": 9.5, "line-opacity": 0.95 }, // white casing keeps the segments readable on any base map
          });
          map.addLayer({
            id: "ri-segments", type: "line", source: "ri-segments",
            layout: { "line-cap": "round", "line-join": "round" },
            paint: { "line-color": HEALTH_COLOR as never, "line-width": 5 },
          });
          map.addLayer({
            id: "ri-inspections", type: "circle", source: "ri-inspections",
            paint: { "circle-radius": 6, "circle-color": "#ffffff", "circle-stroke-color": "#111827", "circle-stroke-width": 2.5 },
          });
          map.addLayer({
            id: "ri-damage-halo", type: "circle", source: "ri-damage",
            paint: { "circle-radius": 16, "circle-color": SEVERITY_COLOR as never, "circle-opacity": 0.3, "circle-blur": 0.5 },
          });
          map.addLayer({
            id: "ri-damage", type: "circle", source: "ri-damage",
            paint: { "circle-radius": 7, "circle-color": SEVERITY_COLOR as never, "circle-stroke-color": "#ffffff", "circle-stroke-width": 2.2 },
          });
          setState("ready");
          // One short camera move into the tilted view; nothing keeps animating afterwards.
          if (!reduceMotion) map.easeTo({ pitch: 58, bearing: -22, duration: 2200 });
        });
      } catch {
        if (!cancelled) setState("failed");
      }
    };

    // Start only when the frame is about to be seen, so the map library never delays the page.
    const observer =
      typeof IntersectionObserver === "undefined"
        ? null
        : new IntersectionObserver(
            ([entry]) => {
              if (entry.isIntersecting) {
                observer?.disconnect();
                start();
              }
            },
            { rootMargin: "200px" }
          );
    if (observer) observer.observe(el);
    else start();

    return () => {
      cancelled = true;
      observer?.disconnect();
      map?.remove();
    };
  }, []);

  return (
    <figure
      className={`rounded-xl border border-ri-line bg-ri-surface overflow-hidden shadow-2xl shadow-black/40 transition-[box-shadow,border-color] duration-300 hover:border-ri-primary/40 ${className}`}
    >
      <div className="flex items-center justify-between gap-3 px-4 py-2.5 border-b border-ri-line bg-ri-bg">
        <span className="font-code-sm text-ri-muted uppercase tracking-wider">Spatial Map · 3D preview</span>
        <span className="font-code-sm text-[10px] text-ri-warning border border-ri-warning/30 bg-ri-warning/10 rounded-full px-2 py-0.5">
          Demo overlay, not live data
        </span>
      </div>

      <div className="relative h-[340px] sm:h-[440px] lg:h-[520px] bg-[#dfe6e2]">
        <div ref={holder} className="h-full w-full" aria-label="Interactive 3D map preview with illustrative road segments, damage points and inspection points" role="application" />
        {state !== "ready" && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-2 text-center px-6 pointer-events-none">
            <MapPinned className="h-6 w-6 text-ri-faint" />
            <p className="font-code-sm text-[11px] text-ri-muted">
              {state === "failed" ? "Map preview unavailable (the map tiles could not be loaded)." : "Loading map..."}
            </p>
          </div>
        )}
      </div>

      <figcaption className="px-4 py-3 border-t border-ri-line space-y-2">
        <div className="flex flex-wrap gap-x-5 gap-y-2 text-xs text-ri-muted">
          {LEGEND.map((l) => (
            <span key={l.label} className="inline-flex items-center gap-2">
              <span className={l.line ? `h-1 w-5 rounded-full ${l.color}` : `h-3 w-3 rounded-full ${l.color}`} aria-hidden />
              {l.label}
            </span>
          ))}
        </div>
        <p className="text-[11px] text-ri-faint leading-relaxed">
          {SATELLITE ? "Satellite imagery with road names from OpenStreetMap data." : "Real base map (OpenStreetMap data)."} The coloured segments and points are sample shapes for illustration; they are
          not survey results for these streets. Drag to rotate; use two fingers on touch screens.
        </p>
      </figcaption>
    </figure>
  );
}
