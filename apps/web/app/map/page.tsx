"use client";

import React, { useCallback, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { AppShell } from "@/components/shell";
import { api } from "@/lib/api-client";
import { MapDamageFeature, MapSegmentFeature } from "@/types/api";
import { AlertTriangle, Layers, Map as MapIcon, MapPin, RefreshCw } from "lucide-react";

// Leaflet touches `window` at import time, so the map is client-only.
const SpatialMap = dynamic(() => import("@/components/map/spatial-map"), {
  ssr: false,
  loading: () => <MapPlaceholder message="Loading map..." />,
});

const SEVERITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW"] as const;
const STATUSES = ["DETECTED", "CONFIRMED", "MAINTENANCE_SCHEDULED", "REPAIRED", "REJECTED"] as const;
const DAMAGE_LIMIT = 1000;

const SEVERITY_DOT: Record<string, string> = {
  CRITICAL: "bg-red-500",
  HIGH: "bg-orange-500",
  MEDIUM: "bg-yellow-500",
  LOW: "bg-green-500",
};

const HEALTH_SWATCH: Record<string, string> = {
  GOOD: "bg-green-500",
  FAIR: "bg-yellow-500",
  POOR: "bg-orange-500",
  CRITICAL: "bg-red-500",
  INSUFFICIENT_DATA: "bg-slate-500",
};

function MapPlaceholder({ message }: { message: string }) {
  return (
    <div className="h-full w-full flex items-center justify-center rounded-xl bg-slate-900/60 border border-slate-800">
      <div className="flex flex-col items-center gap-3">
        <div className="h-7 w-7 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
        <p className="text-xs text-slate-400">{message}</p>
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

  const loadLayers = useCallback(async () => {
    setLoading(true);
    setError(null);
    const damageParams: Record<string, string> = { limit: String(DAMAGE_LIMIT) };
    if (severityFilter.length) damageParams.severity = severityFilter.join(",");
    if (statusFilter) damageParams.status = statusFilter;

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

  const isEmpty = !loading && !error && damages.length === 0 && segments.length === 0;
  const truncated = damages.length >= DAMAGE_LIMIT;

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-2">
              <MapIcon className="h-6 w-6 text-blue-400" />
              Spatial Map
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Damage records and road segment health from the GIS map API.
            </p>
          </div>
          <button
            onClick={loadLayers}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-xs font-medium text-slate-200 hover:bg-slate-800 disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-6">
          <aside className="space-y-5 rounded-xl border border-slate-800 bg-slate-900/50 p-4 h-fit">
            <section>
              <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2 flex items-center gap-1.5">
                <Layers className="h-3.5 w-3.5" /> Layers
              </h2>
              <label className="flex items-center gap-2 text-sm text-slate-200">
                <input type="checkbox" checked={showDamages} onChange={(e) => setShowDamages(e.target.checked)} />
                Damage records ({damages.length})
              </label>
              <label className="flex items-center gap-2 text-sm text-slate-200 mt-1">
                <input type="checkbox" checked={showSegments} onChange={(e) => setShowSegments(e.target.checked)} />
                Road segments ({segments.length})
              </label>
            </section>

            <section>
              <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Severity</h2>
              <div className="flex flex-wrap gap-1.5">
                {SEVERITIES.map((sev) => {
                  const active = severityFilter.includes(sev);
                  return (
                    <button
                      key={sev}
                      onClick={() => toggleSeverity(sev)}
                      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium ${
                        active ? "border-blue-500 bg-blue-500/15 text-blue-200" : "border-slate-700 text-slate-300 hover:bg-slate-800"
                      }`}
                    >
                      <span className={`h-2 w-2 rounded-full ${SEVERITY_DOT[sev]}`} />
                      {sev}
                    </button>
                  );
                })}
              </div>
              <p className="text-[11px] text-slate-500 mt-1.5">No selection shows all severities.</p>
            </section>

            <section>
              <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Status</h2>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="w-full rounded-lg border border-slate-700 bg-slate-950 px-2 py-1.5 text-sm text-slate-200"
              >
                <option value="">All statuses</option>
                {STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s.replace(/_/g, " ")}
                  </option>
                ))}
              </select>
            </section>

            <section>
              <h2 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">Segment health</h2>
              <ul className="space-y-1">
                {Object.entries(HEALTH_SWATCH).map(([status, cls]) => (
                  <li key={status} className="flex items-center gap-2 text-xs text-slate-300">
                    <span className={`h-1.5 w-5 rounded ${cls}`} />
                    {status.replace(/_/g, " ")}
                  </li>
                ))}
              </ul>
            </section>
          </aside>

          <div className="space-y-3">
            {error && (
              <div className="flex items-start gap-2 rounded-lg border border-red-900/60 bg-red-950/40 p-3 text-sm text-red-200">
                <AlertTriangle className="h-4 w-4 mt-0.5 shrink-0" />
                <div>
                  <p className="font-medium">Could not load map layers</p>
                  <p className="text-xs text-red-300/80">{error}</p>
                </div>
              </div>
            )}
            {truncated && (
              <p className="text-xs text-amber-300">
                Showing the {DAMAGE_LIMIT} most recent damage records; narrow the filters to see others.
              </p>
            )}
            <div className="relative h-[calc(100vh-14rem)] min-h-[420px]">
              {loading ? (
                <MapPlaceholder message="Loading spatial layers..." />
              ) : (
                <SpatialMap damages={damages} segments={segments} showDamages={showDamages} showSegments={showSegments} />
              )}
              {isEmpty && (
                <div className="pointer-events-none absolute inset-0 z-[500] flex items-center justify-center">
                  <div className="rounded-xl border border-slate-700 bg-slate-950/90 px-5 py-4 text-center">
                    <MapPin className="h-5 w-5 text-slate-400 mx-auto mb-2" />
                    <p className="text-sm font-medium text-slate-200">No mapped data yet</p>
                    <p className="text-xs text-slate-400 mt-1">
                      No damage records or road segments with geometry match the current filters.
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
