"use client";

import "leaflet/dist/leaflet.css";

import React, { useEffect } from "react";
import L from "leaflet";
import { CircleMarker, GeoJSON, MapContainer, Polyline, TileLayer, Tooltip, useMap, useMapEvents } from "react-leaflet";
import type { Geometry } from "geojson";
import { MapSegmentFeature } from "@/types/api";

// Used only until there is something to fit to (existing segments, drawn points or a typed position).
const INITIAL_CENTER: [number, number] = [20.5937, 78.9629];
const INITIAL_ZOOM = 5;

interface GeometryDrawMapProps {
  /** Points of the line being drawn, as [longitude, latitude] (GeoJSON order). */
  points: number[][];
  onChange: (points: number[][]) => void;
  /** Existing segments shown for orientation only. */
  contextSegments: MapSegmentFeature[];
  /** A position typed by the administrator to move the view to: [latitude, longitude]. */
  focus: [number, number] | null;
}

function ClickToAdd({ points, onChange }: { points: number[][]; onChange: (points: number[][]) => void }) {
  useMapEvents({
    click(e) {
      onChange([...points, [Number(e.latlng.lng.toFixed(7)), Number(e.latlng.lat.toFixed(7))]]);
    },
  });
  return null;
}

function ViewController({
  contextSegments,
  focus,
  hasPoints,
}: {
  contextSegments: MapSegmentFeature[];
  focus: [number, number] | null;
  hasPoints: boolean;
}) {
  const map = useMap();

  // Fit to the road's existing segments when they load, unless the administrator is already drawing.
  useEffect(() => {
    if (hasPoints) return;
    const bounds = L.latLngBounds([]);
    contextSegments.forEach((s) => {
      const b = L.geoJSON(s.geometry as Geometry).getBounds();
      if (b.isValid()) bounds.extend(b);
    });
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [40, 40], maxZoom: 17 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [map, contextSegments]);

  useEffect(() => {
    if (focus) map.setView(focus, 17);
  }, [map, focus]);

  return null;
}

/**
 * Map for drawing a road-segment line: each click adds a vertex. Nothing is generated or snapped;
 * the saved geometry is exactly the clicked points.
 */
export default function GeometryDrawMap({ points, onChange, contextSegments, focus }: GeometryDrawMapProps) {
  const latLngs = points.map((p) => [p[1], p[0]] as [number, number]);

  return (
    <MapContainer
      center={INITIAL_CENTER}
      zoom={INITIAL_ZOOM}
      scrollWheelZoom
      className="h-full w-full rounded-xl"
      style={{ background: "#0a0a0b", cursor: "crosshair" }}
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <ClickToAdd points={points} onChange={onChange} />
      <ViewController contextSegments={contextSegments} focus={focus} hasPoints={points.length > 0} />

      {contextSegments.map((s) => (
        <GeoJSON
          key={s.id}
          data={s.geometry as Geometry}
          style={{ color: "#71717a", weight: 4, opacity: 0.8, dashArray: "6 6" }}
        >
          <Tooltip sticky>
            Existing: {s.road_name ?? "Road"} · Segment {s.segment_number}
          </Tooltip>
        </GeoJSON>
      ))}

      {latLngs.length >= 2 && <Polyline positions={latLngs} pathOptions={{ color: "#06B6D4", weight: 5 }} />}
      {latLngs.map((pos, i) => (
        <CircleMarker
          key={`${pos[0]}-${pos[1]}-${i}`}
          center={pos}
          bubblingMouseEvents={false}
          radius={i === 0 || i === latLngs.length - 1 ? 7 : 5}
          pathOptions={{
            color: "#0A0A0B",
            weight: 2,
            fillColor: i === 0 ? "#10B981" : i === latLngs.length - 1 ? "#EF4444" : "#06B6D4",
            fillOpacity: 1,
          }}
        >
          <Tooltip>
            {i === 0 ? "Start" : i === latLngs.length - 1 ? "End" : `Point ${i + 1}`}: {pos[0].toFixed(6)}, {pos[1].toFixed(6)}
          </Tooltip>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
