"use client";

import "leaflet/dist/leaflet.css";

import React, { useEffect, useMemo } from "react";
import L from "leaflet";
import { CircleMarker, GeoJSON, MapContainer, Popup, TileLayer, useMap } from "react-leaflet";
import type { Feature, FeatureCollection, Geometry } from "geojson";
import { MapDamageFeature, MapSegmentFeature } from "@/types/api";
import { isHeuristic, scoreLabel } from "@/lib/provenance";

export const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: "#ef4444",
  HIGH: "#f97316",
  MEDIUM: "#eab308",
  LOW: "#22c55e",
};

export const HEALTH_COLORS: Record<string, string> = {
  GOOD: "#22c55e",
  FAIR: "#eab308",
  POOR: "#f97316",
  CRITICAL: "#ef4444",
  INSUFFICIENT_DATA: "#64748b",
};

// Used only until data arrives; the view is then fitted to the returned features.
const INITIAL_CENTER: [number, number] = [20.5937, 78.9629];
const INITIAL_ZOOM = 5;

interface SpatialMapProps {
  damages: MapDamageFeature[];
  segments: MapSegmentFeature[];
  showDamages: boolean;
  showSegments: boolean;
}

function FitToData({ damages, segments }: { damages: MapDamageFeature[]; segments: MapSegmentFeature[] }) {
  const map = useMap();

  useEffect(() => {
    const bounds = L.latLngBounds([]);
    damages.forEach((d) => bounds.extend([d.latitude, d.longitude]));
    segments.forEach((s) => {
      const layer = L.geoJSON(s.geometry as Geometry);
      const b = layer.getBounds();
      if (b.isValid()) bounds.extend(b);
    });
    if (bounds.isValid()) {
      map.fitBounds(bounds, { padding: [32, 32], maxZoom: 16 });
    }
  }, [map, damages, segments]);

  return null;
}

function formatScore(score?: number | null) {
  return score === null || score === undefined ? "n/a" : score.toFixed(1);
}

export default function SpatialMap({ damages, segments, showDamages, showSegments }: SpatialMapProps) {
  const segmentCollection = useMemo<FeatureCollection>(
    () => ({
      type: "FeatureCollection",
      features: segments.map(
        (s): Feature => ({
          type: "Feature",
          geometry: s.geometry as Geometry,
          properties: s as unknown as Record<string, unknown>,
        })
      ),
    }),
    [segments]
  );

  // GeoJSON layers do not re-render on data change; key forces a remount.
  const segmentKey = useMemo(() => segments.map((s) => `${s.id}:${s.health_status}`).join("|"), [segments]);

  return (
    <MapContainer
      center={INITIAL_CENTER}
      zoom={INITIAL_ZOOM}
      scrollWheelZoom
      className="h-full w-full rounded-xl"
      style={{ background: "#0f172a" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <FitToData damages={showDamages ? damages : []} segments={showSegments ? segments : []} />

      {showSegments && segments.length > 0 && (
        <GeoJSON
          key={segmentKey}
          data={segmentCollection}
          style={(feature) => {
            const props = feature?.properties as MapSegmentFeature | undefined;
            return {
              color: HEALTH_COLORS[props?.health_status ?? "INSUFFICIENT_DATA"] ?? HEALTH_COLORS.INSUFFICIENT_DATA,
              weight: 5,
              opacity: 0.85,
            };
          }}
          onEachFeature={(feature, layer) => {
            const s = feature.properties as MapSegmentFeature;
            const container = document.createElement("div");
            const title = document.createElement("strong");
            title.textContent = `${s.road_name ?? "Road"} - Segment ${s.segment_number}`;
            container.appendChild(title);
            [
              `Health: ${s.health_status ?? "n/a"} (${formatScore(s.health_score)})`,
              `Damages: ${s.damage_count} (${s.critical_damage_count} critical)`,
              s.length_meters ? `Length: ${Math.round(s.length_meters)} m` : null,
            ]
              .filter(Boolean)
              .forEach((line) => {
                const row = document.createElement("div");
                row.textContent = line as string;
                container.appendChild(row);
              });
            layer.bindPopup(container);
          }}
        />
      )}

      {showDamages &&
        damages.map((d) => (
          <CircleMarker
            key={d.id}
            center={[d.latitude, d.longitude]}
            radius={d.severity === "CRITICAL" ? 9 : d.severity === "HIGH" ? 8 : 6}
            pathOptions={{
              color: SEVERITY_COLORS[d.severity] ?? "#94a3b8",
              fillColor: SEVERITY_COLORS[d.severity] ?? "#94a3b8",
              fillOpacity: 0.75,
              weight: 2,
            }}
          >
            <Popup>
              <div className="text-xs space-y-0.5">
                <div className="font-semibold">{d.damage_type}</div>
                <div>
                  Severity: {d.severity} &middot; Status: {d.status}
                </div>
                {d.confidence !== null && d.confidence !== undefined && (
                  <div>
                    {scoreLabel(d.score_type)}: {(d.confidence * 100).toFixed(0)}%
                    {isHeuristic(d.detection_method, d.score_type) ? " (OpenCV rules, not a trained model)" : ""}
                  </div>
                )}
                {d.road_name && (
                  <div>
                    {d.road_name}
                    {d.segment_number !== null && d.segment_number !== undefined ? ` - Segment ${d.segment_number}` : ""}
                  </div>
                )}
                {d.detected_at && <div>Detected: {new Date(d.detected_at).toLocaleString()}</div>}
                <div>
                  {d.latitude.toFixed(5)}, {d.longitude.toFixed(5)}
                </div>
              </div>
            </Popup>
          </CircleMarker>
        ))}
    </MapContainer>
  );
}
