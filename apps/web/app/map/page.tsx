"use client";

import React, { useCallback, useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { AppShell } from "@/components/shell";
import { SegmentFormModal } from "@/components/roads/segment-form-modal";
import { api } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { hasPermission } from "@/lib/permissions";
import { Inspection, MapDamageFeature, MapSegmentFeature, Road } from "@/types/api";
import {
  Plus,
  AlertTriangle,
  Layers,
  Map as MapIcon,
  MapPin,
  RefreshCw,
  SlidersHorizontal,
  Compass,
} from "lucide-react";

// Leaflet touches `window` at import time, so the map is client-only.
const SpatialMap = dynamic(() => import("@/components/map/spatial-map"), {
  ssr: false,
  loading: () => <MapPlaceholder message="Loading map..." />,
});

const SEVERITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW"] as const;
const STATUSES = ["DETECTED", "CONFIRMED", "MAINTENANCE_SCHEDULED", "REPAIRED", "REJECTED"] as const;
const DAMAGE_LIMIT = 1000;
const INSPECTION_LIMIT = 100;
const NO_JOB = "__NO_JOB__";

const SEVERITY_DOT: Record<string, string> = {
  CRITICAL: "bg-ri-danger",
  HIGH: "bg-ri-orange",
  MEDIUM: "bg-ri-warning",
  LOW: "bg-ri-success",
};

const HEALTH_SWATCH: Record<string, string> = {
  GOOD: "bg-ri-success",
  FAIR: "bg-ri-warning",
  POOR: "bg-ri-orange",
  CRITICAL: "bg-ri-danger",
  INSUFFICIENT_DATA: "bg-ri-faint",
};

function MapPlaceholder({ message }: { message: string }) {
  return (
    <div className="h-full w-full flex items-center justify-center rounded-xl bg-ri-bg border border-ri-line">
      <div className="flex flex-col items-center gap-3">
        <div className="h-8 w-8 border-2 border-ri-primary border-t-transparent rounded-full animate-spin" />
        <p className="text-xs font-mono text-ri-muted">{message}</p>
      </div>
    </div>
  );
}

export default function SpatialMapPage() {
  const [damages, setDamages] = useState<MapDamageFeature[]>([]);
  const [segments, setSegments] = useState<MapSegmentFeature[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [severityFilter, setSeverityFilter] = useState<string[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [showDamages, setShowDamages] = useState(true);
  const [showSegments, setShowSegments] = useState(true);

  // Field inspection capture points (GPS recorded by the field app), shown as their own layer.
  const [inspections, setInspections] = useState<Inspection[]>([]);
  const [showInspections, setShowInspections] = useState(true);

  // Filters applied in the browser to the loaded records; their options come from the data itself.
  const [typeFilter, setTypeFilter] = useState("");
  const [roadFilter, setRoadFilter] = useState("");
  const [segmentFilter, setSegmentFilter] = useState("");
  const [maintenanceFilter, setMaintenanceFilter] = useState("");
  const [healthFilter, setHealthFilter] = useState("");
  const [recurrenceOnly, setRecurrenceOnly] = useState(false);

  // Segment administration from the map (offered only to roles the API allows to create segments)
  const { user } = useAuth();
  const canAddSegment = hasPermission(user, "road_segments:create");
  const [roads, setRoads] = useState<Road[] | null>(null);
  const [showAddSegment, setShowAddSegment] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const openAddSegment = async () => {
    setShowAddSegment(true);
    if (roads === null) {
      try {
        setRoads((await api.roads.list({ page_size: 100 })).data ?? []);
      } catch {
        setRoads([]);
      }
    }
  };

  const loadLayers = useCallback(async () => {
    setLoading(true);
    setError(null);
    const damageParams: Record<string, string> = { limit: String(DAMAGE_LIMIT) };
    if (severityFilter.length) damageParams.severity = severityFilter.join(",");
    if (statusFilter) damageParams.status = statusFilter;

    // Inspection capture points are optional context; a failure here must not hide the damage map.
    api.inspections
      .list({ page_size: INSPECTION_LIMIT })
      .then((res) => setInspections((res.data ?? []).filter((i) => i.location)))
      .catch(() => setInspections([]));

    try {
      const [damageRes, segmentRes] = await Promise.all([api.map.damages(damageParams), api.map.segments()]);
      setDamages(damageRes.data ?? []);
      setSegments(segmentRes.data ?? []);
    } catch (err: any) {
      setError(err?.message || "Failed to load map data.");
      setDamages([]);
      setSegments([]);
    } finally {
      setLoading(false);
    }
  }, [severityFilter, statusFilter]);

  useEffect(() => {
    loadLayers();
  }, [loadLayers]);

  const toggleSeverity = (sev: string) =>
    setSeverityFilter((prev) => (prev.includes(sev) ? prev.filter((s) => s !== sev) : [...prev, sev]));

  // Filter options: only values present in the loaded records.
  const typeOptions = useMemo(() => Array.from(new Set(damages.map((d) => d.damage_type))).sort(), [damages]);
  const roadOptions = useMemo(() => {
    const m = new Map<string, string>();
    segments.forEach((s) => m.set(s.road_id, s.road_name ?? "Unnamed road"));
    damages.forEach((d) => d.road_id && m.set(d.road_id, d.road_name ?? "Unnamed road"));
    inspections.forEach((i) => i.road_id && m.set(i.road_id, i.road_name ?? "Unnamed road"));
    return Array.from(m.entries()).sort((a, b) => a[1].localeCompare(b[1]));
  }, [segments, damages, inspections]);
  const segmentOptions = useMemo(() => {
    const m = new Map<string, number>();
    segments.filter((s) => !roadFilter || s.road_id === roadFilter).forEach((s) => m.set(s.id, s.segment_number));
    damages
      .filter((d) => d.road_segment_id && d.segment_number != null && (!roadFilter || d.road_id === roadFilter))
      .forEach((d) => m.set(d.road_segment_id!, d.segment_number!));
    return Array.from(m.entries()).sort((a, b) => a[1] - b[1]);
  }, [segments, damages, roadFilter]);
  const maintenanceOptions = useMemo(
    () => Array.from(new Set(damages.map((d) => d.maintenance_status).filter((v): v is string => !!v))).sort(),
    [damages]
  );
  const healthOptions = useMemo(
    () =>
      Array.from(
        new Set([
          ...segments.map((s) => s.health_status ?? "INSUFFICIENT_DATA"),
          ...damages.map((d) => d.segment_health_status).filter((v): v is string => !!v),
        ])
      ).sort(),
    [segments, damages]
  );

  const shownDamages = useMemo(
    () =>
      damages.filter(
        (d) =>
          (!typeFilter || d.damage_type === typeFilter) &&
          (!roadFilter || d.road_id === roadFilter) &&
          (!segmentFilter || d.road_segment_id === segmentFilter) &&
          (!maintenanceFilter ||
            (maintenanceFilter === NO_JOB ? !d.maintenance_status : d.maintenance_status === maintenanceFilter)) &&
          (!healthFilter || d.segment_health_status === healthFilter) &&
          (!recurrenceOnly || (d.active_recurrences ?? 0) > 0)
      ),
    [damages, typeFilter, roadFilter, segmentFilter, maintenanceFilter, healthFilter, recurrenceOnly]
  );
  const shownSegments = useMemo(
    () =>
      segments.filter(
        (s) =>
          (!roadFilter || s.road_id === roadFilter) &&
          (!segmentFilter || s.id === segmentFilter) &&
          (!healthFilter || (s.health_status ?? "INSUFFICIENT_DATA") === healthFilter)
      ),
    [segments, roadFilter, segmentFilter, healthFilter]
  );
  const shownInspections = useMemo(
    () =>
      inspections.filter(
        (i) => (!roadFilter || i.road_id === roadFilter) && (!segmentFilter || i.road_segment_id === segmentFilter)
      ),
    [inspections, roadFilter, segmentFilter]
  );

  const clientFiltersActive =
    !!(typeFilter || roadFilter || segmentFilter || maintenanceFilter || healthFilter) || recurrenceOnly;
  const resetFilters = () => {
    setSeverityFilter([]);
    setStatusFilter("");
    setTypeFilter("");
    setRoadFilter("");
    setSegmentFilter("");
    setMaintenanceFilter("");
    setHealthFilter("");
    setRecurrenceOnly(false);
  };

  const isEmpty =
    !loading &&
    !error &&
    shownDamages.length === 0 &&
    shownSegments.length === 0 &&
    (!showInspections || shownInspections.length === 0);
  const truncated = damages.length >= DAMAGE_LIMIT;

  return (
    <AppShell>
      <div className="space-y-6 animate-in fade-in duration-300">
        {/* Page Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-2 rounded-lg bg-ri-primary/10 border border-ri-primary/30 text-ri-primary">
                <MapIcon className="h-5 w-5" />
              </span>
              <h1 className="text-xl md:text-2xl font-bold tracking-tight text-white">
                Spatial Map — Locate Road Damage
              </h1>
            </div>
            <p className="text-xs text-ri-muted mt-1 max-w-3xl leading-relaxed">
              Damage records at their recorded GPS positions, road segments coloured by their latest rule-based health
              status, and the capture points of field inspections. Every position comes from the stored record; nothing
              is placed by default.
            </p>
          </div>
          <div className="flex items-center gap-2">
          {canAddSegment && (
            <button
              onClick={openAddSegment}
              className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-ri-primary hover:bg-ri-primary-bright text-ri-on-primary text-xs font-bold"
            >
              <Plus className="h-3.5 w-3.5" />
              Add Segment
            </button>
          )}
          <button
            onClick={loadLayers}
            disabled={loading}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-ri-surface border border-ri-line text-ri-text-soft text-xs font-semibold hover:border-ri-primary/40 hover:text-white transition-all disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin text-ri-primary" : ""}`} />
            Refresh
          </button>
          </div>
        </div>

        {notice && (
          <p className="text-xs px-3 py-2 rounded-xl border border-ri-success/30 bg-ri-success/10 text-ri-success">{notice}</p>
        )}

        {/* Main Grid: Sidebar Controls & Spatial Viewport */}
        <div className="grid grid-cols-1 lg:grid-cols-[280px_1fr] gap-6">
          {/* Controls Sidebar */}
          <aside className="space-y-5 rounded-xl border border-ri-line bg-ri-surface p-5 h-fit shadow-xl">
            {/* Layer Visibility */}
            <section className="space-y-2.5">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-ri-muted font-mono flex items-center gap-1.5 pb-2 border-b border-ri-line">
                <Layers className="h-3.5 w-3.5 text-ri-primary" />
                Layers
              </h2>
              <label className="flex items-center justify-between p-2 rounded-lg bg-ri-bg border border-ri-line cursor-pointer hover:border-ri-line-strong transition">
                <span className="text-xs text-ri-text-soft font-medium">Damage Points</span>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-ri-raised text-ri-primary">
                    {shownDamages.length}
                  </span>
                  <input
                    type="checkbox"
                    checked={showDamages}
                    onChange={(e) => setShowDamages(e.target.checked)}
                    className="rounded border-ri-line bg-ri-bg text-ri-primary focus:ring-0 focus:ring-offset-0 h-4 w-4"
                  />
                </div>
              </label>

              <label className="flex items-center justify-between p-2 rounded-lg bg-ri-bg border border-ri-line cursor-pointer hover:border-ri-line-strong transition">
                <span className="text-xs text-ri-text-soft font-medium">Road Segments</span>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-ri-raised text-ri-success">
                    {shownSegments.length}
                  </span>
                  <input
                    type="checkbox"
                    checked={showSegments}
                    onChange={(e) => setShowSegments(e.target.checked)}
                    className="rounded border-ri-line bg-ri-bg text-ri-primary focus:ring-0 focus:ring-offset-0 h-4 w-4"
                  />
                </div>
              </label>

              <label className="flex items-center justify-between p-2 rounded-lg bg-ri-bg border border-ri-line cursor-pointer hover:border-ri-line-strong transition-colors">
                <span className="text-xs text-ri-text-soft font-medium flex items-center gap-2">
                  <span className="h-2.5 w-2.5 rounded-full border-2 border-ri-info" />
                  Field Inspections
                </span>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-ri-raised text-ri-info">
                    {shownInspections.length}
                  </span>
                  <input
                    type="checkbox"
                    checked={showInspections}
                    onChange={(e) => setShowInspections(e.target.checked)}
                    className="rounded border-ri-line bg-ri-bg text-ri-primary focus:ring-0 focus:ring-offset-0 h-4 w-4"
                  />
                </div>
              </label>
              <p className="text-[10px] text-ri-faint leading-relaxed">
                A field inspection appears as a damage point only after a detection from it is promoted to a damage
                record. Until then it is shown as an inspection capture point (blue ring).
              </p>
            </section>

            {/* Severity Filter */}
            <section className="space-y-2">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-ri-muted font-mono flex items-center gap-1.5 pb-2 border-b border-ri-line">
                <SlidersHorizontal className="h-3.5 w-3.5 text-ri-primary" />
                Severity
              </h2>
              <div className="flex flex-wrap gap-1.5">
                {SEVERITIES.map((sev) => {
                  const active = severityFilter.includes(sev);
                  return (
                    <button
                      key={sev}
                      onClick={() => toggleSeverity(sev)}
                      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-mono font-medium transition-all ${
                        active
                          ? "border-ri-primary bg-ri-primary/15 text-ri-primary-bright"
                          : "border-ri-line bg-ri-bg text-ri-text-soft hover:bg-ri-raised"
                      }`}
                    >
                      <span className={`h-2 w-2 rounded-full ${SEVERITY_DOT[sev]}`} />
                      {sev}
                    </button>
                  );
                })}
              </div>
              <p className="text-[10px] text-ri-faint font-mono">
                {severityFilter.length === 0 ? "No selection shows all severities." : `${severityFilter.length} selected`}
              </p>
            </section>

            {/* Status Filter */}
            <section className="space-y-2">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-ri-muted font-mono pb-2 border-b border-ri-line">
                Status
              </h2>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="w-full rounded-xl border border-ri-line bg-ri-bg px-3 py-2 text-xs text-ri-text-soft font-mono focus:border-ri-primary focus:outline-none"
              >
                <option value="">All Statuses</option>
                {STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s.replace(/_/g, " ")}
                  </option>
                ))}
              </select>
            </section>

            {/* Filters on the loaded records */}
            <section className="space-y-2">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-ri-muted font-mono pb-2 border-b border-ri-line">
                Damage type
              </h2>
              <select value={typeFilter} onChange={(e) => setTypeFilter(e.target.value)} className="w-full rounded-xl border border-ri-line bg-ri-bg px-3 py-2 text-xs text-ri-text-soft font-mono focus:border-ri-primary focus:outline-none">
                <option value="">All types</option>
                {typeOptions.map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </section>

            <section className="space-y-2">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-ri-muted font-mono pb-2 border-b border-ri-line">
                Road / segment
              </h2>
              <select
                value={roadFilter}
                onChange={(e) => {
                  setRoadFilter(e.target.value);
                  setSegmentFilter("");
                }}
                className="w-full rounded-xl border border-ri-line bg-ri-bg px-3 py-2 text-xs text-ri-text-soft font-mono focus:border-ri-primary focus:outline-none"
              >
                <option value="">All roads</option>
                {roadOptions.map(([id, name]) => (
                  <option key={id} value={id}>
                    {name}
                  </option>
                ))}
              </select>
              <select value={segmentFilter} onChange={(e) => setSegmentFilter(e.target.value)} className="w-full rounded-xl border border-ri-line bg-ri-bg px-3 py-2 text-xs text-ri-text-soft font-mono focus:border-ri-primary focus:outline-none">
                <option value="">All segments</option>
                {segmentOptions.map(([id, number]) => (
                  <option key={id} value={id}>
                    Segment #{number}
                  </option>
                ))}
              </select>
            </section>

            <section className="space-y-2">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-ri-muted font-mono pb-2 border-b border-ri-line">
                Maintenance / recurrence
              </h2>
              <select value={maintenanceFilter} onChange={(e) => setMaintenanceFilter(e.target.value)} className="w-full rounded-xl border border-ri-line bg-ri-bg px-3 py-2 text-xs text-ri-text-soft font-mono focus:border-ri-primary focus:outline-none">
                <option value="">Any maintenance state</option>
                <option value={NO_JOB}>No maintenance job</option>
                {maintenanceOptions.map((m) => (
                  <option key={m} value={m}>
                    {m.replace(/_/g, " ")}
                  </option>
                ))}
              </select>
              <label className="flex items-center gap-2 text-xs text-ri-text-soft cursor-pointer">
                <input
                  type="checkbox"
                  checked={recurrenceOnly}
                  onChange={(e) => setRecurrenceOnly(e.target.checked)}
                  className="rounded border-ri-line bg-ri-bg text-ri-primary focus:ring-0 focus:ring-offset-0 h-4 w-4"
                />
                Only damage with an active recurrence
              </label>
            </section>

            <section className="space-y-2">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-ri-muted font-mono pb-2 border-b border-ri-line">
                Road health
              </h2>
              <select value={healthFilter} onChange={(e) => setHealthFilter(e.target.value)} className="w-full rounded-xl border border-ri-line bg-ri-bg px-3 py-2 text-xs text-ri-text-soft font-mono focus:border-ri-primary focus:outline-none">
                <option value="">Any segment health</option>
                {healthOptions.map((h) => (
                  <option key={h} value={h}>
                    {h.replace(/_/g, " ")}
                  </option>
                ))}
              </select>
            </section>

            <button
              onClick={resetFilters}
              disabled={!clientFiltersActive && severityFilter.length === 0 && !statusFilter}
              className="w-full h-9 rounded-xl bg-ri-raised border border-ri-line text-xs text-ri-text-soft hover:text-white disabled:opacity-40"
            >
              Reset filters
            </button>

            {/* Segment Health Legend */}
            <section className="space-y-2">
              <h2 className="text-xs font-semibold uppercase tracking-wider text-ri-muted font-mono pb-2 border-b border-ri-line">
                Segment health
              </h2>
              <ul className="space-y-1.5">
                {Object.entries(HEALTH_SWATCH).map(([status, cls]) => (
                  <li key={status} className="flex items-center justify-between text-xs text-ri-text-soft font-mono">
                    <span className="flex items-center gap-2">
                      <span className={`h-2 w-4 rounded-full ${cls}`} />
                      <span>{status.replace(/_/g, " ")}</span>
                    </span>
                  </li>
                ))}
              </ul>
            </section>

            <div className="pt-2 border-t border-ri-line text-[10px] text-ri-faint font-mono">
              Coordinates: WGS 84 (EPSG:4326)
            </div>
          </aside>

          {/* Spatial Map Viewport */}
          <div className="space-y-3">
            {error && (
              <div className="flex items-start gap-2 rounded-xl border border-ri-danger/60 bg-ri-danger/40 p-3 text-xs text-ri-danger-soft">
                <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0 text-ri-danger" />
                <div>
                  <p className="font-semibold">Could not load map layers</p>
                  <p className="text-[11px] text-ri-danger-soft/80">{error}</p>
                </div>
              </div>
            )}

            {truncated && (
              <div className="p-2.5 rounded-xl bg-ri-warning/10 border border-ri-warning/30 text-ri-warning text-xs font-mono flex items-center gap-2">
                <AlertTriangle className="h-3.5 w-3.5 shrink-0" />
                <span>Showing the {DAMAGE_LIMIT} most recent damage records. Narrow the severity or status filters to see the rest.</span>
              </div>
            )}

            <div className="relative h-[calc(100vh-15rem)] min-h-[460px] rounded-xl border border-ri-line overflow-hidden shadow-2xl bg-ri-bg">
              {/* Layer counts */}
              <div className="absolute top-3 left-3 z-[400] pointer-events-none">
                <div className="px-3 py-1.5 rounded-xl bg-ri-bg/90 border border-ri-line backdrop-blur-md shadow-lg flex items-center gap-3 text-xs font-mono">
                  <span className="text-ri-text-soft">
                    <span className="text-ri-primary font-semibold">{shownDamages.length}</span> damage points
                  </span>
                  <span className="text-ri-faint">|</span>
                  <span className="text-ri-text-soft">
                    <span className="text-ri-success font-semibold">{shownSegments.length}</span> segments
                  </span>
                  <span className="text-ri-faint">|</span>
                  <span className="text-ri-text-soft">
                    <span className="text-ri-info font-semibold">{showInspections ? shownInspections.length : 0}</span> inspections
                  </span>
                </div>
              </div>

              {loading ? (
                <MapPlaceholder message="Loading spatial layers..." />
              ) : (
                <SpatialMap
                  damages={shownDamages}
                  segments={shownSegments}
                  showDamages={showDamages}
                  showSegments={showSegments}
                  inspections={shownInspections}
                  showInspections={showInspections}
                />
              )}

              {isEmpty && (
                <div className="pointer-events-none absolute inset-0 z-[500] flex items-center justify-center p-4">
                  <div className="rounded-xl border border-ri-line bg-ri-bg/95 px-6 py-5 text-center shadow-2xl max-w-sm">
                    <MapPin className="h-6 w-6 text-ri-primary mx-auto mb-2" />
                    <p className="text-sm font-semibold text-white">No mapped data yet</p>
                    <p className="text-xs text-ri-muted mt-1">
                      No damage records, inspections or road segments with geometry match the current filters.
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {showAddSegment && roads !== null && (
        <SegmentFormModal
          roads={roads}
          onClose={() => setShowAddSegment(false)}
          onCreated={(segment, roadId) => {
            setShowAddSegment(false);
            const roadName = roads.find((r) => r.id === roadId)?.name ?? "the road";
            setNotice(`Segment ${segment.segment_number} added to ${roadName}.`);
            loadLayers();
          }}
        />
      )}
    </AppShell>
  );
}
