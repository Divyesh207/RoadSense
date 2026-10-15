"use client";

import React, { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { Crosshair, GitBranch, Trash2, Undo2, X } from "lucide-react";
import { api } from "@/lib/api-client";
import { lineLengthMeters } from "@/lib/geo";
import { MapSegmentFeature, Road, RoadSegment, RoadSegmentCreatePayload } from "@/types/api";

// Leaflet touches `window` at import time, so the drawing map is client-only.
const GeometryDrawMap = dynamic(() => import("@/components/map/geometry-draw-map"), {
  ssr: false,
  loading: () => (
    <div className="h-full w-full flex items-center justify-center rounded-xl bg-ri-bg text-xs text-ri-muted">
      Loading map...
    </div>
  ),
});

const inputClass =
  "w-full h-10 bg-ri-input border border-ri-line rounded-xl px-3 text-xs text-ri-text placeholder:text-ri-faint focus:outline-none focus:border-ri-primary disabled:opacity-50";
const labelClass = "font-label-sm text-xs text-ri-muted font-semibold";

interface SegmentFormModalProps {
  /** Roads the administrator can choose from. */
  roads: Road[];
  /** Preselects and locks the road (used from the Road Detail page). */
  presetRoadId?: string;
  onClose: () => void;
  onCreated: (segment: RoadSegment, roadId: string) => void;
}

/**
 * Creates a road segment through POST /roads/{road_id}/segments. The line is drawn by clicking
 * on the map; nothing is generated. Length is measured from the drawn line and can be corrected.
 */
export function SegmentFormModal({ roads, presetRoadId, onClose, onCreated }: SegmentFormModalProps) {
  const [roadId, setRoadId] = useState(presetRoadId ?? "");
  const [existing, setExisting] = useState<RoadSegment[]>([]);
  const [context, setContext] = useState<MapSegmentFeature[]>([]);
  const [loadingRoad, setLoadingRoad] = useState(false);

  const [segmentNumber, setSegmentNumber] = useState("");
  const [name, setName] = useState("");
  const [startChainage, setStartChainage] = useState("");
  const [endChainage, setEndChainage] = useState("");
  const [lengthMeters, setLengthMeters] = useState("");
  const [lengthEdited, setLengthEdited] = useState(false);
  const [points, setPoints] = useState<number[][]>([]);

  const [gotoLat, setGotoLat] = useState("");
  const [gotoLon, setGotoLon] = useState("");
  const [focus, setFocus] = useState<[number, number] | null>(null);

  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Existing segments of the chosen road: for the next free number and as drawing context.
  useEffect(() => {
    if (!roadId) {
      setExisting([]);
      setContext([]);
      return;
    }
    let cancelled = false;
    setLoadingRoad(true);
    Promise.allSettled([api.roads.getSegments(roadId), api.map.segments()])
      .then(([segRes, mapRes]) => {
        if (cancelled) return;
        const segs = segRes.status === "fulfilled" ? segRes.value.data ?? [] : [];
        setExisting(segs);
        setContext(mapRes.status === "fulfilled" ? (mapRes.value.data ?? []).filter((s) => s.road_id === roadId) : []);
        const next = segs.reduce((max, s) => Math.max(max, s.segment_number), 0) + 1;
        setSegmentNumber(String(next));
      })
      .finally(() => !cancelled && setLoadingRoad(false));
    return () => {
      cancelled = true;
    };
  }, [roadId]);

  const drawnLength = useMemo(() => (points.length >= 2 ? lineLengthMeters(points) : null), [points]);

  // Keep the length field in step with the drawn line until the administrator types their own value.
  useEffect(() => {
    if (!lengthEdited) setLengthMeters(drawnLength != null ? drawnLength.toFixed(1) : "");
  }, [drawnLength, lengthEdited]);

  const usedNumbers = useMemo(() => new Set(existing.map((s) => s.segment_number)), [existing]);
  const road = roads.find((r) => r.id === roadId);

  const goTo = () => {
    const lat = Number(gotoLat);
    const lon = Number(gotoLon);
    if (!gotoLat || !gotoLon || Number.isNaN(lat) || Number.isNaN(lon) || Math.abs(lat) > 90 || Math.abs(lon) > 180) {
      return setError("Enter a valid latitude (-90 to 90) and longitude (-180 to 180) to move the map.");
    }
    setError(null);
    setFocus([lat, lon]);
  };

  const num = (value: string) => (value.trim() === "" ? undefined : Number(value));

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!roadId) return setError("Select the road this segment belongs to.");
    const n = Number(segmentNumber);
    if (!Number.isInteger(n) || n <= 0) return setError("Segment number must be a whole number greater than 0.");
    if (usedNumbers.has(n)) return setError(`Segment ${n} already exists on this road.`);
    const start = num(startChainage);
    const end = num(endChainage);
    const length = num(lengthMeters);
    if ([start, end, length].some((v) => v !== undefined && (Number.isNaN(v) || v < 0))) {
      return setError("Chainage and length must be numbers of 0 or more.");
    }
    if (start !== undefined && end !== undefined && end < start) {
      return setError("End chainage cannot be before start chainage.");
    }
    if (points.length === 1) return setError("A line needs at least two points. Add another point or clear the map.");

    const payload: RoadSegmentCreatePayload = { segment_number: n };
    if (name.trim()) payload.name = name.trim();
    if (start !== undefined) payload.start_chainage = start;
    if (end !== undefined) payload.end_chainage = end;
    if (length !== undefined) payload.length_meters = length;
    if (points.length >= 2) payload.geometry = { type: "LineString", coordinates: points };

    setSaving(true);
    try {
      const res = await api.roads.createSegment(roadId, payload);
      if (!res.data) throw new Error("The API returned no segment.");
      onCreated(res.data, roadId);
    } catch (err: any) {
      setError(err?.message || "The segment could not be created.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-[2000]">
      <div className="bg-ri-surface border border-ri-line rounded-xl max-w-5xl w-full p-6 space-y-4 shadow-2xl max-h-[94vh] overflow-y-auto">
        <div className="flex items-center justify-between border-b border-ri-line pb-3">
          <div className="flex items-center gap-2">
            <GitBranch className="h-5 w-5 text-ri-primary" />
            <h3 className="font-headline-sm text-base font-bold text-ri-text">Add Segment</h3>
          </div>
          <button onClick={onClose} aria-label="Close" className="text-ri-muted hover:text-ri-text p-1">
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={submit} className="grid lg:grid-cols-[320px_1fr] gap-5">
          {/* Metadata */}
          <div className="space-y-4">
            <div className="space-y-1.5">
              <label className={labelClass}>Road *</label>
              <select
                value={roadId}
                onChange={(e) => {
                  setRoadId(e.target.value);
                  setPoints([]);
                  setLengthEdited(false);
                }}
                disabled={!!presetRoadId}
                className={inputClass}
              >
                <option value="">Select a road...</option>
                {roads.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name}
                    {r.road_code ? ` (${r.road_code})` : ""}
                  </option>
                ))}
              </select>
              {roadId && (
                <p className="text-[11px] text-ri-faint">
                  {loadingRoad
                    ? "Loading existing segments..."
                    : existing.length === 0
                    ? "This road has no segments yet."
                    : `Existing segments: ${existing
                        .map((s) => `#${s.segment_number}`)
                        .sort()
                        .join(", ")}`}
                </p>
              )}
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className={labelClass}>Segment number *</label>
                <input
                  value={segmentNumber}
                  onChange={(e) => setSegmentNumber(e.target.value)}
                  inputMode="numeric"
                  disabled={!roadId}
                  className={inputClass}
                />
              </div>
              <div className="space-y-1.5">
                <label className={labelClass}>Length (m)</label>
                <input
                  value={lengthMeters}
                  onChange={(e) => {
                    setLengthMeters(e.target.value);
                    setLengthEdited(true);
                  }}
                  inputMode="decimal"
                  disabled={!roadId}
                  className={inputClass}
                />
              </div>
            </div>
            <p className="text-[11px] text-ri-faint -mt-2">
              {drawnLength != null
                ? `Drawn line measures ${drawnLength.toFixed(1)} m.${lengthEdited ? " The length above was typed by you." : ""}`
                : "Length fills in from the line you draw; you can also type it."}
            </p>

            <div className="space-y-1.5">
              <label className={labelClass}>Segment name</label>
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                maxLength={150}
                disabled={!roadId}
                placeholder="Optional"
                className={inputClass}
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <label className={labelClass}>Start chainage (km)</label>
                <input
                  value={startChainage}
                  onChange={(e) => setStartChainage(e.target.value)}
                  inputMode="decimal"
                  disabled={!roadId}
                  className={inputClass}
                />
              </div>
              <div className="space-y-1.5">
                <label className={labelClass}>End chainage (km)</label>
                <input
                  value={endChainage}
                  onChange={(e) => setEndChainage(e.target.value)}
                  inputMode="decimal"
                  disabled={!roadId}
                  className={inputClass}
                />
              </div>
            </div>

            {/* Preview of exactly what will be sent */}
            <div className="rounded-xl border border-ri-line bg-ri-input/60 p-3 text-[11px] space-y-1">
              <p className="font-semibold text-ri-text text-xs">Preview</p>
              <p className="text-ri-muted">
                Road: <span className="text-ri-text-soft">{road?.name ?? "not selected"}</span>
              </p>
              <p className="text-ri-muted">
                Segment: <span className="text-ri-text-soft">#{segmentNumber || "—"}</span>
                {name.trim() ? ` · ${name.trim()}` : ""}
              </p>
              <p className="text-ri-muted">
                Geometry:{" "}
                <span className={points.length >= 2 ? "text-ri-success" : "text-ri-warning"}>
                  {points.length >= 2 ? `line with ${points.length} points` : "none drawn"}
                </span>
              </p>
              {points.length >= 2 && (
                <p className="font-mono text-ri-muted">
                  {points[0][1].toFixed(6)}, {points[0][0].toFixed(6)} → {points[points.length - 1][1].toFixed(6)},{" "}
                  {points[points.length - 1][0].toFixed(6)}
                </p>
              )}
              {points.length < 2 && (
                <p className="text-ri-warning">
                  Without a line the segment is saved but will not appear on the Spatial Map and cannot be matched to GPS
                  positions.
                </p>
              )}
            </div>
          </div>

          {/* Geometry */}
          <div className="space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-xs text-ri-text-soft">
                <span className="font-semibold">Draw the segment:</span>{" "}
                <span className="text-ri-muted">click along the road from its start to its end.</span>
              </p>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setPoints((p) => p.slice(0, -1))}
                  disabled={points.length === 0}
                  className="inline-flex items-center gap-1 h-8 px-2.5 rounded-lg bg-ri-raised border border-ri-line text-[11px] text-ri-text-soft disabled:opacity-40"
                >
                  <Undo2 className="h-3 w-3" /> Undo
                </button>
                <button
                  type="button"
                  onClick={() => setPoints([])}
                  disabled={points.length === 0}
                  className="inline-flex items-center gap-1 h-8 px-2.5 rounded-lg bg-ri-raised border border-ri-line text-[11px] text-ri-text-soft disabled:opacity-40"
                >
                  <Trash2 className="h-3 w-3" /> Clear
                </button>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[11px] text-ri-muted">Move map to:</span>
              <input
                value={gotoLat}
                onChange={(e) => setGotoLat(e.target.value)}
                placeholder="Latitude"
                inputMode="decimal"
                className="h-8 w-28 bg-ri-input border border-ri-line rounded-lg px-2 text-[11px] font-mono text-ri-text placeholder:text-ri-faint focus:outline-none focus:border-ri-primary"
              />
              <input
                value={gotoLon}
                onChange={(e) => setGotoLon(e.target.value)}
                placeholder="Longitude"
                inputMode="decimal"
                className="h-8 w-28 bg-ri-input border border-ri-line rounded-lg px-2 text-[11px] font-mono text-ri-text placeholder:text-ri-faint focus:outline-none focus:border-ri-primary"
              />
              <button
                type="button"
                onClick={goTo}
                className="inline-flex items-center gap-1 h-8 px-2.5 rounded-lg bg-ri-raised border border-ri-line text-[11px] text-ri-primary-bright"
              >
                <Crosshair className="h-3 w-3" /> Go
              </button>
            </div>

            <div className="h-[420px] rounded-xl border border-ri-line overflow-hidden">
              <GeometryDrawMap points={points} onChange={setPoints} contextSegments={context} focus={focus} />
            </div>
            <p className="text-[11px] text-ri-faint">
              Grey dashed lines are this road&apos;s existing segments. Green is the start point, red the end. Coordinates are
              WGS 84 and are saved exactly as clicked.
            </p>
          </div>

          <div className="lg:col-span-2 space-y-3">
            {error && (
              <p className="text-xs px-3 py-2 rounded-xl border border-ri-danger/40 bg-ri-danger/10 text-ri-danger-soft">{error}</p>
            )}
            <div className="flex items-center justify-end gap-3">
              <button
                type="button"
                onClick={onClose}
                className="h-10 px-4 rounded-xl bg-ri-raised border border-ri-line text-xs font-semibold text-ri-muted hover:text-ri-text"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={saving || !roadId}
                className="h-10 px-5 rounded-xl bg-ri-primary hover:bg-ri-primary-bright text-ri-on-primary text-xs font-bold disabled:opacity-50"
              >
                {saving ? "Saving..." : "Save Segment"}
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
