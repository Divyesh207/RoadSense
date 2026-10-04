"use client";

import "leaflet/dist/leaflet.css";

import React, { useEffect, useMemo } from "react";
import L from "leaflet";
import { CircleMarker, GeoJSON, MapContainer, Popup, TileLayer, useMap } from "react-leaflet";
import type { Feature, FeatureCollection, Geometry } from "geojson";
import { Inspection, MapDamageFeature, MapSegmentFeature } from "@/types/api";
import { detectionMethodLabel, isHeuristic } from "@/lib/provenance";

export const INSPECTION_COLOR = "#38bdf8";

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
  /** Field inspections that have a recorded GPS position (capture points, not damage records). */
  inspections?: Inspection[];
  showInspections?: boolean;
}

function FitToData({
  damages,
  segments,
  inspections,
}: {
  damages: MapDamageFeature[];
  segments: MapSegmentFeature[];
  inspections: Inspection[];
}) {
  const map = useMap();

  useEffect(() => {
    const bounds = L.latLngBounds([]);
    damages.forEach((d) => bounds.extend([d.latitude, d.longitude]));
    inspections.forEach((i) => i.location && bounds.extend([i.location.latitude, i.location.longitude]));
    segments.forEach((s) => {
      const layer = L.geoJSON(s.geometry as Geometry);
      const b = layer.getBounds();
      if (b.isValid()) bounds.extend(b);
    });
    if (bounds.isValid()) {
      map.fitBounds(bounds, { padding: [32, 32], maxZoom: 16 });
    }
  }, [map, damages, segments, inspections]);

  return null;
}

// How the record was produced and what the score means, in the API's own terms.
function scoreText(d: MapDamageFeature): string | null {
  if (d.confidence === null || d.confidence === undefined) return null;
  const value = d.confidence.toFixed(2);
  if (isHeuristic(d.detection_method, d.score_type)) return `Heuristic score ${value} (rule-based, not a probability)`;
  if (d.score_type === "MODEL_CONFIDENCE") return `Model confidence ${value}`;
  return `Score ${value}`;
}

function reviewText(status: string): string {
  switch (status) {
    case "REJECTED":
      return "rejected by a reviewer";
    case "DETECTED":
    case "PENDING_REVIEW":
      return "awaiting human review";
    default:
      return "confirmed by a reviewer";
  }
}

function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <span style={{ color: "rgb(var(--ri-muted))" }}>{label}: </span>
      {children}
    </div>
  );
}

function formatScore(score?: number | null) {
  return score === null || score === undefined ? "n/a" : score.toFixed(1);
}

export default function SpatialMap({
  damages,
  segments,
  showDamages,
  showSegments,
  inspections = [],
  showInspections = false,
}: SpatialMapProps) {
  const locatedInspections = useMemo(() => inspections.filter((i) => i.location), [inspections]);

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
      <FitToData
        damages={showDamages ? damages : []}
        segments={showSegments ? segments : []}
        inspections={showInspections ? locatedInspections : []}
      />

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
              <div className="text-xs space-y-0.5" style={{ minWidth: 230 }}>
                <div className="font-semibold">Road damage: {d.damage_type}</div>
                <Row label="Severity">{d.severity} (rule-based assessment)</Row>
                <Row label="Status">{d.status.replace(/_/g, " ")}</Row>
                <Row label="Road">{d.road_name ?? "not assigned"}</Row>
                <Row label="Segment">
                  {d.segment_number !== null && d.segment_number !== undefined
                    ? `#${d.segment_number}${d.segment_name ? ` · ${d.segment_name}` : ""}`
                    : "not assigned"}
                </Row>
                <Row label="Latitude">{d.latitude.toFixed(6)}</Row>
                <Row label="Longitude">{d.longitude.toFixed(6)}</Row>
                <Row label="Detected">{d.detected_at ? new Date(d.detected_at).toLocaleString() : "not recorded"}</Row>
                <Row label="Detection method">
                  {isHeuristic(d.detection_method, d.score_type)
                    ? "Heuristic fallback (OpenCV rules, unverified, not a trained model)"
                    : detectionMethodLabel(d.detection_method)}
                </Row>
                {scoreText(d) && <div>{scoreText(d)}</div>}
                <Row label="Human review">{reviewText(d.status)}</Row>
                <Row label="Sightings">
                  {(d.observation_count ?? 1) > 1 ? `${d.observation_count} (GPS-grouped)` : "1"}
                </Row>
                <Row label="Recurrence">
                  {(d.active_recurrences ?? 0) > 0
                    ? `${d.active_recurrences} active${
                        d.escalation_level && d.escalation_level !== "NONE" ? ` · escalation ${d.escalation_level}` : ""
                      }`
                    : "none recorded"}
                </Row>
                <Row label="Maintenance">{d.maintenance_status ? d.maintenance_status.replace(/_/g, " ") : "no job"}</Row>
                <Row label="Segment health">
                  {d.segment_health_status ? `${d.segment_health_score ?? "—"} (${d.segment_health_status})` : "no snapshot"}
                </Row>
              </div>
            </Popup>
          </CircleMarker>
        ))}

      {showInspections &&
        locatedInspections.map((i) => (
          <CircleMarker
            key={`insp-${i.id}`}
            center={[i.location!.latitude, i.location!.longitude]}
            radius={5}
            pathOptions={{ color: INSPECTION_COLOR, fillColor: "#0f172a", fillOpacity: 0.9, weight: 2 }}
          >
            <Popup>
              <div className="text-xs space-y-0.5" style={{ minWidth: 220 }}>
                <div className="font-semibold">Field inspection #{i.id.slice(0, 8)}</div>
                <div style={{ color: "rgb(var(--ri-muted))" }}>Capture point of an inspection, not a damage record.</div>
                <Row label="Status">{i.status}</Row>
                <Row label="Source">{i.source}</Row>
                <Row label="Road">{i.road_name ?? "not assigned"}</Row>
                <Row label="Segment">
                  {i.segment_number !== null && i.segment_number !== undefined ? `#${i.segment_number}` : "not assigned"}
                </Row>
                <Row label="Latitude">{i.location!.latitude.toFixed(6)}</Row>
                <Row label="Longitude">{i.location!.longitude.toFixed(6)}</Row>
                {i.location!.accuracy_m !== undefined && i.location!.accuracy_m !== null && (
                  <Row label="Reported accuracy">±{i.location!.accuracy_m} m</Row>
                )}
                <Row label="Captured">{new Date(i.captured_at).toLocaleString()}</Row>
                <a href={`/inspections/${i.id}`}>Open inspection</a>
              </div>
            </Popup>
          </CircleMarker>
        ))}
    </MapContainer>
  );
}
