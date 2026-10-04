"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { AppShell } from "@/components/shell";
import { BentoMetricTile } from "@/components/bento-metric-tile";
import { api } from "@/lib/api-client";
import { HEALTH_ORDER, MAINTENANCE_ORDER, countEntries } from "@/lib/intelligence";
import { DamageTrendsData, DashboardSummaryData, RoadHealthAnalyticsData } from "@/types/api";
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Repeat,
  Route,
  ShieldAlert,
  Wrench,
  Layers,
  AlertCircle,
} from "lucide-react";

const HEALTH_COLORS: Record<string, string> = {
  GOOD: "#10B981", // Stitch tertiary emerald
  FAIR: "#F59E0B", // Stitch amber
  POOR: "#FB923C",
  CRITICAL: "#EF4444", // Stitch red
  "INSUFFICIENT DATA": "#64748B",
};

function ChartCard({
  title,
  empty,
  children,
}: {
  title: string;
  empty: string | null;
  children: React.ReactNode;
}) {
  return (
    <div className="p-5 rounded-2xl bg-[#111A2E] border border-[#26344F] shadow-sm flex flex-col justify-between">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-headline-sm text-sm font-semibold text-[#F1F5F9]">{title}</h3>
      </div>
      {empty ? (
        <div className="h-56 flex flex-col items-center justify-center p-6 text-center">
          <p className="font-body-sm text-xs text-[#94A3B8]">{empty}</p>
        </div>
      ) : (
        <div className="h-56">{children}</div>
      )}
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
    Promise.all([
      api.analytics.getDashboardSummary(),
      api.analytics.getRoadHealth(),
      api.analytics.getDamageTrends(),
    ])
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
  const results = countEntries(summary?.repair_verification_results, [
    "SUCCESSFUL",
    "SUBSTANDARD",
    "UNRESOLVED",
  ]);

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Section Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="font-code-sm text-[11px] text-[#06B6D4] uppercase tracking-wider font-semibold">
                Operations overview
              </span>
            </div>
            <h1 className="font-headline-sm text-2xl font-bold tracking-tight text-[#F1F5F9]">
              Road Intelligence Overview
            </h1>
            <p className="font-body-sm text-xs text-[#94A3B8] mt-1">
              Counts from inspections, damage records, health snapshots, maintenance and verification records.
            </p>
          </div>
          <Link
            href="/damages"
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-[#06B6D4] hover:bg-[#4CD7F6] rounded-xl text-xs font-bold text-[#003640] shadow-sm shadow-[#06B6D4]/20 transition-all active:scale-95"
          >
            Review damage queue <ArrowRight className="h-3.5 w-3.5" />
          </Link>
        </div>

        {loading && (
          <div className="p-8 rounded-xl bg-[#111A2E] border border-[#26344F] flex items-center justify-center gap-3">
            <div className="h-5 w-5 border-2 border-[#06B6D4] border-t-transparent rounded-full animate-spin" />
            <span className="font-code-sm text-xs text-[#94A3B8]">
              Loading…
            </span>
          </div>
        )}

        {error && (
          <div className="p-4 rounded-xl bg-[#93000A]/20 border border-[#93000A]/50 flex items-center gap-3 text-[#FFB4AB]">
            <AlertCircle className="h-5 w-5 text-[#EF4444] shrink-0" />
            <p className="font-body-sm text-xs">Could not load dashboard data: {error}</p>
          </div>
        )}

        {summary && (
          <>
            {/* Primary Bento KPI Grid */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <BentoMetricTile
                label="Roads / Segments"
                value={`${summary.total_roads} / ${summary.total_segments}`}
                icon={Route}
                href="/roads"
                colorVariant="blue"
              />
              <BentoMetricTile
                label="Active Damage"
                value={summary.open_damages}
                hint={`${summary.pending_review_damages ?? 0} AI candidate(s) awaiting review`}
                icon={AlertTriangle}
                href="/damages"
                colorVariant="amber"
              />
              <BentoMetricTile
                label="Critical / High (Active)"
                value={`${summary.critical_damages} / ${summary.high_severity_damages}`}
                icon={ShieldAlert}
                href="/damages"
                colorVariant="red"
              />
              <BentoMetricTile
                label="Average Road Health"
                value={
                  summary.average_road_health != null
                    ? summary.average_road_health.toFixed(1)
                    : "No data"
                }
                hint={
                  summary.roads_with_health
                    ? `latest snapshot of ${summary.roads_with_health} road(s)`
                    : "no health snapshot yet"
                }
                icon={Activity}
                href="/roads"
                colorVariant="green"
              />
            </div>

            {/* Secondary Operational Status Tiles */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <BentoMetricTile
                label="Maintenance Jobs"
                value={maint.reduce((a, b) => a + b.value, 0)}
                hint={`${summary.maintenance_open} open · ${summary.maintenance_in_progress} in progress`}
                icon={Wrench}
                href="/maintenance"
                colorVariant="blue"
              />
              <BentoMetricTile
                label="Repairs Pending Verification"
                value={summary.verification_pending}
                icon={CheckCircle2}
                href="/repairs"
                colorVariant="cyan"
              />
              <BentoMetricTile
                label="Verified Repairs"
                value={summary.verified_repairs}
                icon={CheckCircle2}
                href="/repairs"
                colorVariant="green"
              />
              <BentoMetricTile
                label="Active Recurrences"
                value={summary.recurrence_count}
                hint={`${summary.escalated_recurrences ?? 0} escalated`}
                icon={Repeat}
                href="/recurrence"
                colorVariant="red"
              />
            </div>

            {/* Analytics Visualizations */}
            <div className="grid lg:grid-cols-2 gap-4">
              <ChartCard
                title="Maintenance Jobs by Status"
                empty={maint.length ? null : "No maintenance jobs yet."}
              >
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={maint}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#26344F" />
                    <XAxis
                      dataKey="name"
                      tick={{ fill: "#94A3B8", fontSize: 10 }}
                      interval={0}
                      angle={-20}
                      height={50}
                      textAnchor="end"
                    />
                    <YAxis allowDecimals={false} tick={{ fill: "#94A3B8", fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{
                        background: "#17223A",
                        border: "1px solid #26344F",
                        borderRadius: "8px",
                        color: "#F1F5F9",
                        fontSize: "12px",
                      }}
                    />
                    <Bar dataKey="value" fill="#06B6D4" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>

              <ChartCard
                title="Road Health (Latest Snapshot per Road)"
                empty={healthDist.length ? null : "No road health snapshots yet."}
              >
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={healthDist}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#26344F" />
                    <XAxis dataKey="name" tick={{ fill: "#94A3B8", fontSize: 11 }} interval={0} />
                    <YAxis allowDecimals={false} tick={{ fill: "#94A3B8", fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{
                        background: "#17223A",
                        border: "1px solid #26344F",
                        borderRadius: "8px",
                        color: "#F1F5F9",
                        fontSize: "12px",
                      }}
                    />
                    <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                      {healthDist.map((d) => (
                        <Cell key={d.name} fill={HEALTH_COLORS[d.name] || "#64748B"} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>

              <ChartCard
                title="Damage Records by Severity (All Statuses)"
                empty={severity.length ? null : "No damage records yet."}
              >
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={severity}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#26344F" />
                    <XAxis dataKey="name" tick={{ fill: "#94A3B8", fontSize: 11 }} interval={0} />
                    <YAxis allowDecimals={false} tick={{ fill: "#94A3B8", fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{
                        background: "#17223A",
                        border: "1px solid #26344F",
                        borderRadius: "8px",
                        color: "#F1F5F9",
                        fontSize: "12px",
                      }}
                    />
                    <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                      {severity.map((entry) => {
                        const colors: Record<string, string> = {
                          CRITICAL: "#EF4444",
                          HIGH: "#F59E0B",
                          MEDIUM: "#06B6D4",
                          LOW: "#10B981",
                        };
                        return <Cell key={entry.name} fill={colors[entry.name] || "#3B82F6"} />;
                      })}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>

              <ChartCard
                title="Repair Verification Outcomes (Final per Job)"
                empty={results.length ? null : "No repair has been verified yet."}
              >
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={results}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#26344F" />
                    <XAxis dataKey="name" tick={{ fill: "#94A3B8", fontSize: 11 }} interval={0} />
                    <YAxis allowDecimals={false} tick={{ fill: "#94A3B8", fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{
                        background: "#17223A",
                        border: "1px solid #26344F",
                        borderRadius: "8px",
                        color: "#F1F5F9",
                        fontSize: "12px",
                      }}
                    />
                    <Bar dataKey="value" fill="#10B981" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </ChartCard>
            </div>

            {/* Critical Segments Warning Alert */}
            {health && health.critical_segments.length > 0 && (
              <div className="p-5 rounded-2xl bg-[#EF4444]/10 border border-[#EF4444]/30">
                <div className="flex items-center gap-2 mb-2 text-[#EF4444]">
                  <ShieldAlert className="h-5 w-5" />
                  <h3 className="font-headline-sm text-sm font-semibold">
                    Segments in CRITICAL health
                  </h3>
                </div>
                <ul className="text-xs text-[#DCE2F6] space-y-1.5 divide-y divide-[#26344F]/40 pt-1">
                  {health.critical_segments.map((c) => (
                    <li key={c.segment_id} className="pt-1.5 flex items-center justify-between">
                      <div>
                        <Link
                          href={`/roads/${c.road_id}`}
                          className="text-[#4CD7F6] font-semibold hover:underline"
                        >
                          {c.road_name}
                        </Link>
                        <span className="text-[#94A3B8]"> · segment {c.segment_number}</span>
                      </div>
                      <div className="flex items-center gap-3 font-code-sm">
                        <span className="text-[#EF4444] font-bold">
                          Score: {c.current_health_score}
                        </span>
                        <span className="text-[#F59E0B]">
                          {c.open_damages_count} active damage(s)
                        </span>
                      </div>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {health && (health.segments_insufficient_data ?? 0) > 0 && (
              <p className="font-code-sm text-[11px] text-[#64748B]">
                {health.segments_insufficient_data} segment(s) have insufficient inspection data and are not scored.
              </p>
            )}
          </>
        )}
      </div>
    </AppShell>
  );
}
