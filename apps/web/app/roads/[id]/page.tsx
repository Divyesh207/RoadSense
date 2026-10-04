"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AppShell } from "@/components/shell";
import { StatusBadge } from "@/components/status-badge";
import { api } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { hasPermission } from "@/lib/permissions";
import { SegmentFormModal } from "@/components/roads/segment-form-modal";
import { deductionBars, filterTimeline, healthClass, healthSeries } from "@/lib/intelligence";
import { DeteriorationEstimate, MapSegmentFeature, Road, RoadIntelligence, TimelineEvent } from "@/types/api";
import {
  ArrowLeft,
  History,
  Route,
  Activity,
  AlertTriangle,
  RotateCcw,
  CheckCircle2,
  TrendingDown,
  Layers,
  Plus,
  Sparkles,
} from "lucide-react";

const EVENT_TYPES: TimelineEvent["type"][] = [
  "INSPECTION",
  "DAMAGE",
  "DAMAGE_REVIEW",
  "HEALTH",
  "PRIORITY",
  "MAINTENANCE",
  "REPAIR_EVIDENCE",
  "VERIFICATION",
  "RECURRENCE",
];

const EVENT_COLOR: Record<string, string> = {
  INSPECTION: "bg-[#06B6D4]",
  DAMAGE: "bg-[#EF4444]",
  DAMAGE_REVIEW: "bg-[#F59E0B]",
  HEALTH: "bg-[#4CD7F6]",
  PRIORITY: "bg-[#3B82F6]",
  MAINTENANCE: "bg-[#ADC6FF]",
  REPAIR_EVIDENCE: "bg-[#10B981]",
  VERIFICATION: "bg-[#10B981]",
  RECURRENCE: "bg-[#EF4444]",
};

const LINE_COLORS = ["#06B6D4", "#4CD7F6", "#10B981", "#F59E0B", "#ADC6FF", "#3B82F6"];
const cardClass = "rounded-2xl border border-[#26344F] bg-[#111A2E] p-5 shadow-sm";

const eventLink = (e: TimelineEvent): string | null => {
  if (e.type === "INSPECTION") return `/inspections/${e.entity_id}`;
  if (["PRIORITY", "MAINTENANCE", "REPAIR_EVIDENCE", "VERIFICATION"].includes(e.type))
    return `/maintenance/${e.entity_id}`;
  if (e.type === "DAMAGE" && e.data.inspection_id) return `/inspections/${e.data.inspection_id}`;
  return null;
};

function EstimatePanel({
  segmentId,
  segmentNumber,
}: {
  segmentId: string;
  segmentNumber: number;
}) {
  const [est, setEst] = useState<DeteriorationEstimate | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.predictions
      .history(segmentId)
      .then((r) => setEst(r.data?.[0] ?? null))
      .catch(() => setEst(null));
  }, [segmentId]);

  const generate = async () => {
    setBusy(true);
    setError(null);
    try {
      setEst((await api.predictions.generate(segmentId, 90)).data ?? null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const f = est?.features || {};

  return (
    <div className="rounded-xl border border-[#26344F] bg-[#151B2A] p-4 text-xs">
      <div className="flex items-center justify-between">
        <span className="font-headline-sm text-xs font-bold text-[#F1F5F9]">
          Segment {segmentNumber}: deterioration estimate
        </span>
        <button
          onClick={generate}
          disabled={busy}
          className="h-8 px-3 rounded-lg bg-[#06B6D4] hover:bg-[#4CD7F6] text-[#003640] font-label-md text-xs font-bold transition-all disabled:opacity-50"
        >
          {busy ? "Calculating…" : "Recalculate (90 days)"}
        </button>
      </div>

      {error && <p className="text-[#EF4444] mt-2 font-body-sm">{error}</p>}

      {!est ? (
        <p className="text-[#94A3B8] mt-2">No estimate generated yet.</p>
      ) : est.status !== "GENERATED" ? (
        <p className="text-[#94A3B8] mt-2 font-body-sm">
          {est.status}: {f.reason ?? "insufficient inspection/health history"}.
        </p>
      ) : (
        <div className="mt-3 space-y-2 text-[#DCE2F6]">
          <p>
            Risk <b className="font-code-sm text-[#F59E0B]">{est.predicted_risk}</b> ({f.risk_band}) over{" "}
            {est.prediction_horizon_days} days ·{" "}
            {est.predicted_value != null
              ? `health ${est.predicted_value} by linear extrapolation of the observed trend (${f.health_trend_points_per_day}/day)`
              : "no future health value (no observed trend)"}
          </p>

          <div className="flex flex-wrap gap-1.5 pt-1">
            {Object.entries(f.contributions || {}).map(([k, v]) => (
              <span
                key={k}
                className="px-2 py-0.5 rounded-lg bg-[#19202E] border border-[#26344F] font-code-sm text-[10px] text-[#4CD7F6]"
              >
                {k.replace(/_/g, " ")}: {String(v)}
              </span>
            ))}
          </div>

          {Array.isArray(f.notes) &&
            f.notes.map((n: string, i: number) => (
              <p key={i} className="text-[10px] text-[#64748B]">
                {n}
              </p>
            ))}
          <p className="font-code-sm text-[10px] text-[#64748B] pt-1">
            {est.model_name} {est.model_version} · {est.estimation_method} · no confidence value (none is statistically
            justified) · training data: {f.ml_training_readiness?.segments_with_outcome_history ?? 0}/
            {f.ml_training_readiness?.required_segments ?? "—"} segments with outcome history (
            {f.ml_training_readiness?.status ?? "unknown"})
          </p>
        </div>
      )}
    </div>
  );
}

export default function RoadDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<RoadIntelligence | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [types, setTypes] = useState<Set<string>>(new Set());
  const [reloadTick, setReloadTick] = useState(0);

  // Segment administration (offered only to roles the API allows to create segments)
  const { user } = useAuth();
  const canAddSegment = hasPermission(user, "road_segments:create");
  const [showAddSegment, setShowAddSegment] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  // Per-segment damage counts come from the map layer (segments that have geometry).
  const [mapSegments, setMapSegments] = useState<MapSegmentFeature[]>([]);

  useEffect(() => {
    api.roads
      .getIntelligence(id)
      .then((r) => setData(r.data ?? null))
      .catch((e) => setError(e.message));
    api.map
      .segments()
      .then((r) => setMapSegments((r.data ?? []).filter((s) => s.road_id === id)))
      .catch(() => setMapSegments([]));
  }, [id, reloadTick]);

  const trend = useMemo(() => {
    if (!data) return { rows: [] as Record<string, any>[], keys: [] as string[] };
    const series: Record<string, ReturnType<typeof healthSeries>> = {
      Road: healthSeries(data.road_health_history),
    };
    for (const seg of data.segments) {
      const pts = healthSeries(data.segment_health_history[seg.id] || []);
      if (pts.length) series[`Segment ${seg.segment_number}`] = pts;
    }
    const byTime = new Map<string, Record<string, any>>();
    for (const [key, pts] of Object.entries(series)) {
      for (const p of pts) {
        const row = byTime.get(p.at) || { at: p.at, label: p.label };
        row[key] = p.score;
        byTime.set(p.at, row);
      }
    }
    const rows = Array.from(byTime.values()).sort((a, b) => a.at.localeCompare(b.at));
    return { rows, keys: Object.keys(series).filter((k) => series[k].length) };
  }, [data]);

  if (error) {
    return (
      <AppShell>
        <p className="text-sm text-[#EF4444]">{error}</p>
      </AppShell>
    );
  }

  if (!data) {
    return (
      <AppShell>
        <div className="flex items-center justify-center py-20 text-xs text-[#94A3B8]">
          Loading road intelligence…
        </div>
      </AppShell>
    );
  }

  const latestRoad = data.road_health_history[data.road_health_history.length - 1];
  const worstSegment = data.segments
    .map((s) => s.latest_health)
    .filter((h): h is NonNullable<typeof h> => !!h && typeof h.health_score === "number")
    .sort((a, b) => (a.health_score as number) - (b.health_score as number))[0];

  const contribution = deductionBars((worstSegment ?? latestRoad)?.score_deductions);
  const events = filterTimeline(data.timeline, types).slice().reverse();

  const toggle = (t: string) =>
    setTypes((prev) => {
      const next = new Set(prev);
      next.has(t) ? next.delete(t) : next.add(t);
      return next;
    });

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Back Link & Header */}
        <div>
          <Link
            href="/roads"
            className="inline-flex items-center gap-1.5 font-code-sm text-xs text-[#06B6D4] hover:underline mb-1"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Roads
          </Link>
          <h1 className="font-headline-sm text-2xl font-bold text-[#F1F5F9]">{data.road.name}</h1>
          <p className="font-code-sm text-xs text-[#94A3B8] mt-0.5">
            {data.road.road_code ?? "No code"} · {data.road.road_type ?? "type not set"} · traffic{" "}
            {data.road.traffic_volume_class
              ? `${data.road.traffic_volume_class}${
                  data.road.traffic_aadt != null ? ` (${data.road.traffic_aadt} veh/day)` : ""
                }${data.road.traffic_data_source ? `, source: ${data.road.traffic_data_source}` : ""}`
              : "unknown (no documented source)"}
          </p>
        </div>

        {/* 5-Column Bento Overview Strip */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <div className={cardClass}>
            <span className="font-label-sm text-[11px] text-[#94A3B8] uppercase tracking-wider">
              Current health
            </span>
            <div className={`font-code-lg text-2xl font-bold mt-2 ${latestRoad?.health_status ? healthClass(latestRoad.health_status) : "text-[#F1F5F9]"}`}>
              {latestRoad ? (latestRoad.health_score ?? "—") : "No data"}
            </div>
            {latestRoad?.health_status && (
              <span className={`font-code-sm text-[10px] mt-1 block ${healthClass(latestRoad.health_status)}`}>
                {latestRoad.health_status}
              </span>
            )}
          </div>

          <div className={cardClass}>
            <span className="font-label-sm text-[11px] text-[#EF4444] uppercase tracking-wider">
              Active Damage
            </span>
            <div className="font-code-lg text-2xl font-bold text-[#EF4444] mt-2">
              {data.summary.active_damages}
            </div>
          </div>

          <div className={cardClass}>
            <span className="font-label-sm text-[11px] text-[#F59E0B] uppercase tracking-wider">
              Awaiting Review
            </span>
            <div className="font-code-lg text-2xl font-bold text-[#F59E0B] mt-2">
              {data.summary.pending_review_damages}
            </div>
          </div>

          <div className={cardClass}>
            <span className="font-label-sm text-[11px] text-[#10B981] uppercase tracking-wider">
              Repaired
            </span>
            <div className="font-code-lg text-2xl font-bold text-[#10B981] mt-2">
              {data.summary.repaired_damages}
            </div>
          </div>

          <div className={cardClass}>
            <span className="font-label-sm text-[11px] text-[#3B82F6] uppercase tracking-wider">
              Active Recurrences
            </span>
            <div className="font-code-lg text-2xl font-bold text-[#ADC6FF] mt-2">
              {data.summary.active_recurrences}
            </div>
          </div>
        </div>

        {/* Road-level activity recorded so far */}
        <div className={`${cardClass} flex flex-wrap items-center gap-x-6 gap-y-2 text-xs`}>
          <span className="text-[#94A3B8]">
            Segments: <span className="font-code-sm text-[#F1F5F9]">{data.segments.length}</span>
          </span>
          <span className="text-[#94A3B8]">
            Inspections: <span className="font-code-sm text-[#F1F5F9]">{data.summary.inspections}</span>
          </span>
          <span className="text-[#94A3B8] flex flex-wrap items-center gap-1.5">
            Maintenance:
            {Object.keys(data.summary.maintenance_by_status).length === 0 ? (
              <span className="text-[#64748B]">no jobs</span>
            ) : (
              Object.entries(data.summary.maintenance_by_status).map(([status, count]) => (
                <StatusBadge key={status} status={status} label={`${status.replace(/_/g, " ")} ${count}`} size="sm" showDot={false} />
              ))
            )}
          </span>
        </div>

        {notice && (
          <p className="text-xs px-3 py-2 rounded-xl border border-[#10B981]/30 bg-[#10B981]/10 text-[#10B981]">{notice}</p>
        )}

        {/* Charts Grid */}
        <div className="grid lg:grid-cols-3 gap-4">
          <div className={`${cardClass} lg:col-span-2`}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-headline-sm text-sm font-semibold text-[#F1F5F9]">
                Health trend (snapshots)
              </h3>
              <span className="font-code-sm text-[10px] text-[#64748B]">rule-based score</span>
            </div>
            {trend.rows.length === 0 ? (
              <p className="text-xs text-[#94A3B8] py-16 text-center">
                No scored health snapshots for this road yet.
              </p>
            ) : (
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trend.rows}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#26344F" />
                    <XAxis dataKey="label" tick={{ fill: "#94A3B8", fontSize: 10 }} />
                    <YAxis domain={[0, 100]} tick={{ fill: "#94A3B8", fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{
                        background: "#17223A",
                        border: "1px solid #26344F",
                        borderRadius: "8px",
                        color: "#F1F5F9",
                        fontSize: "12px",
                      }}
                    />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    {trend.keys.map((k, i) => (
                      <Line
                        key={k}
                        type="stepAfter"
                        dataKey={k}
                        stroke={LINE_COLORS[i % LINE_COLORS.length]}
                        strokeWidth={2}
                        dot={{ r: 3, fill: LINE_COLORS[i % LINE_COLORS.length] }}
                        connectNulls
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          <div className={cardClass}>
            <h3 className="font-headline-sm text-sm font-semibold text-[#F1F5F9] mb-1">
              What lowers the score now
            </h3>
            <p className="font-body-sm text-[11px] text-[#94A3B8] mb-3">
              {worstSegment
                ? "Deductions in the latest snapshot of the lowest-scoring segment (the road score is the length-weighted average of its segments)"
                : "Deductions in the latest road snapshot"}
              {(worstSegment ?? latestRoad)?.traffic?.traffic_known
                ? ` · damage ×${(worstSegment ?? latestRoad)!.traffic!.traffic_multiplier} for traffic`
                : ""}
              .
            </p>
            {contribution.length === 0 ? (
              <p className="text-xs text-[#94A3B8] py-16 text-center">
                {latestRoad ? "No deductions: no active damage or recurrence." : "No snapshot yet."}
              </p>
            ) : (
              <div className="h-56">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={contribution} layout="vertical" margin={{ left: 20 }}>
                    <XAxis type="number" tick={{ fill: "#94A3B8", fontSize: 10 }} />
                    <YAxis
                      type="category"
                      dataKey="factor"
                      tick={{ fill: "#94A3B8", fontSize: 10 }}
                      width={80}
                    />
                    <Tooltip
                      contentStyle={{
                        background: "#17223A",
                        border: "1px solid #26344F",
                        borderRadius: "8px",
                        color: "#F1F5F9",
                        fontSize: "12px",
                      }}
                    />
                    <Bar dataKey="points" fill="#EF4444" radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </div>

        {/* Segments Table & Predictions */}
        <div className="space-y-4">
          <div className="bg-[#111A2E] border border-[#26344F] rounded-2xl overflow-hidden shadow-sm">
            <div className="p-4 border-b border-[#26344F] flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Layers className="h-4 w-4 text-[#06B6D4]" />
                <h3 className="font-headline-sm text-sm font-bold text-[#F1F5F9]">
                  Segments
                </h3>
                <span className="font-code-sm text-xs text-[#94A3B8]">
                  ({data.segments.length})
                </span>
              </div>
              {canAddSegment && (
                <button
                  onClick={() => setShowAddSegment(true)}
                  className="inline-flex items-center gap-1.5 h-9 px-3.5 rounded-xl bg-[#06B6D4] hover:bg-[#4CD7F6] text-[#003640] text-xs font-bold"
                >
                  <Plus className="h-3.5 w-3.5" /> Add Segment
                </button>
              )}
            </div>

            {data.segments.length === 0 ? (
              <p className="py-8 text-center text-xs text-[#94A3B8]">This road has no segments.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-[#0C1321] border-b border-[#26344F] text-[#94A3B8]">
                    <tr>
                      <th className="py-3 px-4 font-semibold">#</th>
                      <th className="py-3 px-4 font-semibold">Name</th>
                      <th className="py-3 px-4 font-semibold">Length</th>
                      <th className="py-3 px-4 font-semibold">Health</th>
                      <th className="py-3 px-4 font-semibold">Damage records</th>
                      <th className="py-3 px-4 font-semibold">Recurrences counted</th>
                      <th className="py-3 px-4 text-right font-semibold">Snapshot</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#26344F]/50 text-[#DCE2F6]">
                    {data.segments.map((s) => (
                      <tr key={s.id} className="hover:bg-[#17223A]/50 transition-colors">
                        <td className="py-3 px-4 font-bold text-white font-code-sm">
                          Seg #{s.segment_number}
                        </td>
                        <td className="py-3 px-4 text-[#F1F5F9]">{s.name ?? "—"}</td>
                        <td className="py-3 px-4 font-code-sm text-[#94A3B8]">
                          {s.length_meters != null ? `${s.length_meters} m` : "—"}
                        </td>
                        <td className="py-3 px-4">
                          {s.latest_health ? (
                            <StatusBadge
                              status={s.latest_health.health_status}
                              label={`${s.latest_health.health_score ?? "—"} (${s.latest_health.health_status})`}
                              size="sm"
                            />
                          ) : (
                            <span className="text-[#64748B]">No data</span>
                          )}
                        </td>
                        <td className="py-3 px-4 font-code-sm text-[#94A3B8]">
                          {(() => {
                            const m = mapSegments.find((x) => x.id === s.id);
                            return m ? `${m.damage_count}${m.critical_damage_count ? ` (${m.critical_damage_count} critical)` : ""}` : "—";
                          })()}
                        </td>
                        <td className="py-3 px-4 font-code-sm text-[#94A3B8]">
                          {s.latest_health?.recurrence_count ?? "—"}
                        </td>
                        <td className="py-3 px-4 font-code-sm text-right text-[#94A3B8]">
                          {s.latest_health ? new Date(s.latest_health.calculated_at).toLocaleString() : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* Deterioration estimates: every segment */}
          {data.segments.length > 0 && (
            <div className={cardClass}>
              <h3 className="font-headline-sm text-sm font-semibold text-[#F1F5F9] mb-1">
                Deterioration risk (rule-based estimate)
              </h3>
              <p className="text-[11px] text-[#94A3B8] mb-3">
                Hand-weighted rules over current damage, health and its observed trend, recurrence, previous repair
                verification, inspection age and documented traffic. Not a trained or validated model; not a guaranteed
                outcome.
              </p>
              <div className="grid md:grid-cols-2 gap-3">
                {data.segments.map((s) => (
                  <EstimatePanel key={s.id} segmentId={s.id} segmentNumber={s.segment_number} />
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Lifecycle Timeline */}
        <div className="bg-[#111A2E] border border-[#26344F] rounded-2xl p-5 shadow-sm space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
            <div className="flex items-center gap-2">
              <History className="h-4 w-4 text-[#06B6D4]" />
              <h3 className="font-headline-sm text-sm font-bold text-[#F1F5F9]">
                Historical timeline
              </h3>
              <span className="font-code-sm text-xs text-[#94A3B8]">({events.length})</span>
            </div>

            {/* Filter Chips */}
            <div className="flex flex-wrap gap-1.5">
              {EVENT_TYPES.map((t) => (
                <button
                  key={t}
                  onClick={() => toggle(t)}
                  className={`px-2.5 py-1 rounded-full font-code-sm text-[10px] font-semibold transition-all ${
                    types.has(t)
                      ? "bg-[#06B6D4] text-[#003640]"
                      : "bg-[#17223A] text-[#94A3B8] border border-[#26344F] hover:text-[#F1F5F9]"
                  }`}
                >
                  {t.replace(/_/g, " ")} ({data.timeline.filter((e) => e.type === t).length})
                </button>
              ))}
            </div>
          </div>

          {events.length === 0 ? (
            <p className="py-8 text-center text-xs text-[#94A3B8]">
              No recorded events for this road yet.
            </p>
          ) : (
            <div className="relative pl-6 border-l-2 border-[#26344F] space-y-3.5 my-2 max-h-[32rem] overflow-y-auto">
              {events.map((e, idx) => (
                <div key={idx} className="relative">
                  <div
                    className={`absolute -left-[31px] top-1.5 w-3.5 h-3.5 rounded-full border-2 border-[#111A2E] ${
                      EVENT_COLOR[e.type] || "bg-[#869397]"
                    }`}
                  />
                  <div className="bg-[#151B2A] border border-[#26344F] p-3 rounded-xl flex items-center justify-between">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-code-sm text-[11px] font-bold text-[#4CD7F6]">
                          {e.type.replace(/_/g, " ")}
                        </span>
                        <span className="font-code-sm text-[10px] text-[#64748B]">
                          {new Date(e.at).toLocaleString()}
                          {e.type === "PRIORITY" && e.data.mode ? ` · ${e.data.mode} ${e.data.priority_score ?? ""}` : ""}
                          {e.type === "RECURRENCE" && e.data.distance_meters != null
                            ? ` · ${e.data.distance_meters} m from repaired damage`
                            : ""}
                          {e.type === "VERIFICATION" && e.data.model ? ` · ${e.data.model}` : ""}
                        </span>
                      </div>
                      <p className="font-body-sm text-xs text-[#DCE2F6] mt-0.5">
                        {e.title}
                      </p>
                    </div>
                    {eventLink(e) && (
                      <Link
                        href={eventLink(e)!}
                        className="text-xs font-bold text-[#06B6D4] hover:underline shrink-0"
                      >
                        Open
                      </Link>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {showAddSegment && (
        <SegmentFormModal
          roads={[{ id: data.road.id, name: data.road.name, road_code: data.road.road_code ?? undefined } as Road]}
          presetRoadId={data.road.id}
          onClose={() => setShowAddSegment(false)}
          onCreated={(segment) => {
            setShowAddSegment(false);
            setNotice(`Segment ${segment.segment_number} added. It is now selectable in the field app for this road.`);
            setReloadTick((t) => t + 1);
          }}
        />
      )}
    </AppShell>
  );
}
