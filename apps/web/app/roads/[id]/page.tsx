"use client";

import React, { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { AppShell } from "@/components/shell";
import { api } from "@/lib/api-client";
import { deductionBars, filterTimeline, healthClass, healthSeries } from "@/lib/intelligence";
import { RoadIntelligence, TimelineEvent } from "@/types/api";
import { ArrowLeft, History } from "lucide-react";

// Historical Road Intelligence: Inspection -> Damage -> Health -> Priority -> Maintenance ->
// Repair Evidence -> Verification -> Recurrence, all from stored records.

const EVENT_TYPES: TimelineEvent["type"][] = [
  "INSPECTION", "DAMAGE", "DAMAGE_REVIEW", "HEALTH", "PRIORITY", "MAINTENANCE", "REPAIR_EVIDENCE", "VERIFICATION", "RECURRENCE",
];
const EVENT_COLOR: Record<string, string> = {
  INSPECTION: "bg-slate-500", DAMAGE: "bg-orange-500", DAMAGE_REVIEW: "bg-amber-500", HEALTH: "bg-cyan-500",
  PRIORITY: "bg-purple-500", MAINTENANCE: "bg-blue-500", REPAIR_EVIDENCE: "bg-indigo-500", VERIFICATION: "bg-emerald-500",
  RECURRENCE: "bg-red-500",
};
const LINE_COLORS = ["#22d3ee", "#a78bfa", "#f472b6", "#facc15", "#4ade80", "#fb923c"];
const card = "rounded-xl border border-slate-800 bg-slate-900/60 p-5";

const eventLink = (e: TimelineEvent): string | null => {
  if (e.type === "INSPECTION") return `/inspections/${e.entity_id}`;
  if (["PRIORITY", "MAINTENANCE", "REPAIR_EVIDENCE", "VERIFICATION"].includes(e.type)) return `/maintenance/${e.entity_id}`;
  if (e.type === "DAMAGE" && e.data.inspection_id) return `/inspections/${e.data.inspection_id}`;
  return null;
};

export default function RoadDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<RoadIntelligence | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [types, setTypes] = useState<Set<string>>(new Set());

  useEffect(() => {
    api.roads.getIntelligence(id).then((r) => setData(r.data ?? null)).catch((e) => setError(e.message));
  }, [id]);

  // One chart row per snapshot time, one line per road / segment.
  const trend = useMemo(() => {
    if (!data) return { rows: [] as Record<string, any>[], keys: [] as string[] };
    const series: Record<string, ReturnType<typeof healthSeries>> = { Road: healthSeries(data.road_health_history) };
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

  if (error) return <AppShell><p className="text-sm text-red-400">{error}</p></AppShell>;
  if (!data) return <AppShell><p className="text-sm text-slate-400">Loading road intelligence…</p></AppShell>;

  const latestRoad = data.road_health_history[data.road_health_history.length - 1];
  // A road with segments is the length-weighted average of its segments, so factor
  // deductions live on the segment snapshots; show the lowest-scoring segment's breakdown.
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
      <div className="space-y-5 max-w-6xl">
        <Link href="/roads" className="text-xs text-blue-400 flex items-center gap-1"><ArrowLeft className="h-3 w-3" />Roads</Link>
        <div>
          <h1 className="text-xl font-bold text-white">{data.road.name}</h1>
          <p className="text-xs text-slate-400">
            {data.road.road_code ?? "No code"} · {data.road.road_type ?? "type not set"} · traffic{" "}
            {data.road.traffic_volume_class
              ? `${data.road.traffic_volume_class}${data.road.traffic_aadt != null ? ` (${data.road.traffic_aadt} veh/day)` : ""}${data.road.traffic_data_source ? `, source: ${data.road.traffic_data_source}` : ""}`
              : "unknown (no documented source)"}
          </p>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-center">
          {[
            ["Current health", latestRoad ? (latestRoad.health_score ?? "—") : "No data", latestRoad?.health_status],
            ["Active damage", data.summary.active_damages, null],
            ["Awaiting review", data.summary.pending_review_damages, null],
            ["Repaired", data.summary.repaired_damages, null],
            ["Active recurrences", data.summary.active_recurrences, null],
          ].map(([k, v, st]) => (
            <div key={String(k)} className={card}>
              <p className="text-[11px] text-slate-500">{k}</p>
              <p className={`text-xl font-bold ${st ? healthClass(String(st)) : "text-white"}`}>{v as React.ReactNode}</p>
              {st && <p className={`text-[11px] ${healthClass(String(st))}`}>{String(st)}</p>}
            </div>
          ))}
        </div>

        <div className="grid lg:grid-cols-3 gap-4">
          <div className={`${card} lg:col-span-2`}>
            <h3 className="text-sm font-semibold text-white mb-3">Health trend (snapshots)</h3>
            {trend.rows.length === 0 ? (
              <p className="text-xs text-slate-500 py-10 text-center">No scored health snapshots for this road yet.</p>
            ) : (
              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trend.rows}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="label" tick={{ fill: "#94a3b8", fontSize: 10 }} />
                    <YAxis domain={[0, 100]} tick={{ fill: "#94a3b8", fontSize: 11 }} />
                    <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155" }} />
                    <Legend wrapperStyle={{ fontSize: 11 }} />
                    {trend.keys.map((k, i) => (
                      <Line key={k} type="stepAfter" dataKey={k} stroke={LINE_COLORS[i % LINE_COLORS.length]} dot connectNulls />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
          <div className={card}>
            <h3 className="text-sm font-semibold text-white mb-1">What lowers the score now</h3>
            <p className="text-[11px] text-slate-500 mb-2">
              {worstSegment
                ? `Deductions in the latest snapshot of the lowest-scoring segment (the road score is the length-weighted average of its segments)`
                : "Deductions in the latest road snapshot"}
              {(worstSegment ?? latestRoad)?.traffic?.traffic_known
                ? ` · damage ×${(worstSegment ?? latestRoad)!.traffic!.traffic_multiplier} for traffic`
                : ""}
              .
            </p>
            {contribution.length === 0 ? (
              <p className="text-xs text-slate-500 py-8 text-center">{latestRoad ? "No deductions: no active damage or recurrence." : "No snapshot yet."}</p>
            ) : (
              <div className="h-52">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={contribution} layout="vertical" margin={{ left: 30 }}>
                    <XAxis type="number" tick={{ fill: "#94a3b8", fontSize: 10 }} />
                    <YAxis type="category" dataKey="factor" tick={{ fill: "#94a3b8", fontSize: 10 }} width={90} />
                    <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155" }} />
                    <Bar dataKey="points" fill="#f87171" />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </div>

        <div className={card}>
          <h3 className="text-sm font-semibold text-white mb-2">Segments</h3>
          {data.segments.length === 0 ? (
            <p className="text-xs text-slate-500">This road has no segments.</p>
          ) : (
            <table className="w-full text-xs">
              <thead className="text-slate-500 text-left"><tr><th className="py-1">#</th><th>Name</th><th>Length</th><th>Health</th><th>Recurrences counted</th><th>Snapshot</th></tr></thead>
              <tbody>
                {data.segments.map((s) => (
                  <tr key={s.id} className="border-t border-slate-800 text-slate-300">
                    <td className="py-1.5">{s.segment_number}</td>
                    <td>{s.name ?? "—"}</td>
                    <td>{s.length_meters != null ? `${s.length_meters} m` : "—"}</td>
                    <td className={healthClass(s.latest_health?.health_status)}>
                      {s.latest_health ? `${s.latest_health.health_score ?? "—"} (${s.latest_health.health_status})` : "No data"}
                    </td>
                    <td>{s.latest_health?.recurrence_count ?? "—"}</td>
                    <td>{s.latest_health ? new Date(s.latest_health.calculated_at).toLocaleString() : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        <div className={card}>
          <h3 className="text-sm font-semibold text-white mb-2 flex items-center gap-2"><History className="h-4 w-4" />Historical timeline</h3>
          <div className="flex flex-wrap gap-1.5 mb-3">
            {EVENT_TYPES.map((t) => (
              <button
                key={t}
                onClick={() => toggle(t)}
                className={`px-2 py-0.5 rounded text-[10px] border ${types.has(t) ? "border-blue-500 text-blue-300" : "border-slate-700 text-slate-400"}`}
              >
                {t.replace(/_/g, " ")} ({data.timeline.filter((e) => e.type === t).length})
              </button>
            ))}
          </div>
          {events.length === 0 ? (
            <p className="text-xs text-slate-500">No recorded events for this road yet.</p>
          ) : (
            <ol className="space-y-2 max-h-[32rem] overflow-y-auto">
              {events.map((e, i) => {
                const href = eventLink(e);
                return (
                  <li key={`${e.type}-${e.entity_id}-${i}`} className="flex gap-3 text-xs">
                    <span className={`mt-1 h-2 w-2 rounded-full shrink-0 ${EVENT_COLOR[e.type]}`} />
                    <div>
                      <p className="text-slate-200">
                        {href ? <Link href={href} className="hover:text-blue-300">{e.title}</Link> : e.title}
                      </p>
                      <p className="text-[11px] text-slate-500">
                        {new Date(e.at).toLocaleString()} · {e.type.replace(/_/g, " ")}
                        {e.type === "PRIORITY" && e.data.mode ? ` · ${e.data.mode} ${e.data.priority_score ?? ""}` : ""}
                        {e.type === "RECURRENCE" && e.data.distance_meters != null ? ` · ${e.data.distance_meters} m from repaired damage` : ""}
                        {e.type === "VERIFICATION" && e.data.model ? ` · ${e.data.model}` : ""}
                      </p>
                    </div>
                  </li>
                );
              })}
            </ol>
          )}
        </div>
      </div>
    </AppShell>
  );
}
