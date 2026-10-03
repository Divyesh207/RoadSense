"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { AppShell } from "@/components/shell";
import { api } from "@/lib/api-client";
import { HEALTH_ORDER, MAINTENANCE_ORDER, countEntries } from "@/lib/intelligence";
import { DamageTrendsData, DashboardSummaryData, RoadHealthAnalyticsData } from "@/types/api";
import { Activity, AlertTriangle, ArrowRight, CheckCircle2, Repeat, Route, ShieldAlert, Wrench } from "lucide-react";

// Road Intelligence overview. Every number comes from the API; when a source has no
// records the card/chart says so instead of showing a placeholder value.

const HEALTH_COLORS: Record<string, string> = {
  GOOD: "#34d399",
  FAIR: "#fbbf24",
  POOR: "#fb923c",
  CRITICAL: "#f87171",
  "INSUFFICIENT DATA": "#64748b",
};

function Kpi({ label, value, hint, href, icon: Icon }: { label: string; value: React.ReactNode; hint?: string; href?: string; icon: any }) {
  const body = (
    <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 h-full">
      <div className="flex items-center justify-between text-slate-400 mb-2">
        <span className="text-xs font-medium">{label}</span>
        <Icon className="h-4 w-4" />
      </div>
      <div className="text-2xl font-bold text-white">{value}</div>
      {hint && <p className="text-[11px] text-slate-500 mt-1">{hint}</p>}
    </div>
  );
  return href ? <Link href={href}>{body}</Link> : body;
}

function ChartCard({ title, empty, children }: { title: string; empty: string | null; children: React.ReactNode }) {
  return (
    <div className="p-5 rounded-xl bg-slate-900 border border-slate-800">
      <h3 className="text-sm font-semibold text-white mb-3">{title}</h3>
      {empty ? <p className="text-xs text-slate-500 py-10 text-center">{empty}</p> : <div className="h-56">{children}</div>}
    </div>
  );
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<DashboardSummaryData | null>(null);
  const [health, setHealth] = useState<RoadHealthAnalyticsData | null>(null);
  const [trends, setTrends] = useState<DamageTrendsData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.analytics.getDashboardSummary(), api.analytics.getRoadHealth(), api.analytics.getDamageTrends()])
      .then(([s, h, t]) => {
        setSummary(s.data ?? null);
        setHealth(h.data ?? null);
        setTrends(t.data ?? null);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const maint = countEntries(summary?.maintenance_by_status, MAINTENANCE_ORDER);
  const healthDist = countEntries(summary?.road_health_status_counts, HEALTH_ORDER);
  const severity = countEntries(trends?.by_severity, ["CRITICAL", "HIGH", "MEDIUM", "LOW"]);
  const results = countEntries(summary?.repair_verification_results, ["SUCCESSFUL", "SUBSTANDARD", "UNRESOLVED"]);

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white">Road Intelligence Overview</h1>
            <p className="text-xs text-slate-400 mt-1">Counts from inspections, damage records, health snapshots, maintenance and verification records.</p>
          </div>
          <Link href="/damages" className="inline-flex items-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-xs font-semibold text-white">
            Review damage queue <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        {loading && <p className="text-sm text-slate-400">Loading…</p>}
        {error && <p className="text-sm text-red-400">Could not load dashboard data: {error}</p>}

        {summary && (
          <>
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <Kpi label="Roads / segments" value={`${summary.total_roads} / ${summary.total_segments}`} icon={Route} href="/roads" />
              <Kpi
                label="Active damage"
                value={summary.open_damages}
                hint={`${summary.pending_review_damages ?? 0} AI candidate(s) awaiting review`}
                icon={AlertTriangle}
                href="/damages"
              />
              <Kpi label="Critical / high (active)" value={`${summary.critical_damages} / ${summary.high_severity_damages}`} icon={ShieldAlert} href="/damages" />
              <Kpi
                label="Average road health"
                value={summary.average_road_health != null ? summary.average_road_health.toFixed(1) : "No data"}
                hint={summary.roads_with_health ? `latest snapshot of ${summary.roads_with_health} road(s)` : "no health snapshot yet"}
                icon={Activity}
                href="/roads"
              />
              <Kpi
                label="Maintenance jobs"
                value={maint.reduce((a, b) => a + b.value, 0)}
                hint={`${summary.maintenance_open} open · ${summary.maintenance_in_progress} in progress`}
                icon={Wrench}
                href="/maintenance"
              />
              <Kpi label="Repairs pending verification" value={summary.verification_pending} icon={CheckCircle2} href="/repairs" />
              <Kpi label="Verified repairs" value={summary.verified_repairs} icon={CheckCircle2} href="/repairs" />
              <Kpi
                label="Active recurrences"
                value={summary.recurrence_count}
                hint={`${summary.escalated_recurrences ?? 0} escalated`}
                icon={Repeat}
                href="/recurrence"
              />
            </div>

            <div className="grid lg:grid-cols-2 gap-4">
              <ChartCard title="Maintenance jobs by status" empty={maint.length ? null : "No maintenance jobs yet."}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={maint}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 10 }} interval={0} angle={-20} height={50} textAnchor="end" />
                    <YAxis allowDecimals={false} tick={{ fill: "#94a3b8", fontSize: 11 }} />
                    <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155" }} />
                    <Bar dataKey="value" fill="#3b82f6" />
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>
              <ChartCard title="Road health (latest snapshot per road)" empty={healthDist.length ? null : "No road health snapshots yet."}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={healthDist}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} interval={0} />
                    <YAxis allowDecimals={false} tick={{ fill: "#94a3b8", fontSize: 11 }} />
                    <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155" }} />
                    <Bar dataKey="value">
                      {healthDist.map((d) => <Cell key={d.name} fill={HEALTH_COLORS[d.name] || "#64748b"} />)}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>
              <ChartCard title="Damage records by severity (all statuses)" empty={severity.length ? null : "No damage records yet."}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={severity}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} interval={0} />
                    <YAxis allowDecimals={false} tick={{ fill: "#94a3b8", fontSize: 11 }} />
                    <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155" }} />
                    <Bar dataKey="value" fill="#f59e0b" />
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>
              <ChartCard title="Repair verification outcomes (final per job)" empty={results.length ? null : "No repair has been verified yet."}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={results}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 11 }} interval={0} />
                    <YAxis allowDecimals={false} tick={{ fill: "#94a3b8", fontSize: 11 }} />
                    <Tooltip contentStyle={{ background: "#0f172a", border: "1px solid #334155" }} />
                    <Bar dataKey="value" fill="#10b981" />
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>
            </div>

            {health && health.critical_segments.length > 0 && (
              <div className="p-5 rounded-xl bg-slate-900 border border-red-900/50">
                <h3 className="text-sm font-semibold text-white mb-2">Segments in CRITICAL health</h3>
                <ul className="text-xs text-slate-300 space-y-1">
                  {health.critical_segments.map((c) => (
                    <li key={c.segment_id}>
                      <Link href={`/roads/${c.road_id}`} className="text-blue-400">{c.road_name}</Link> · segment {c.segment_number} · score{" "}
                      {c.current_health_score} · {c.open_damages_count} active damage
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {health && (health.segments_insufficient_data ?? 0) > 0 && (
              <p className="text-[11px] text-slate-500">
                {health.segments_insufficient_data} segment(s) have insufficient inspection data and are not scored.
              </p>
            )}
          </>
        )}
      </div>
    </AppShell>
  );
}
