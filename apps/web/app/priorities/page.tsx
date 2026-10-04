"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/shell";
import { StatusBadge } from "@/components/status-badge";
import { EmptyState } from "@/components/empty-state";
import { api } from "@/lib/api-client";
import { escalationClass, healthClass } from "@/lib/intelligence";
import { PriorityOverviewItem } from "@/types/api";
import { ListOrdered, AlertTriangle, ArrowRight, Layers, MapPin, RefreshCw } from "lucide-react";

export default function PrioritiesPage() {
  const [rows, setRows] = useState<PriorityOverviewItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [level, setLevel] = useState<string>("");
  const [loading, setLoading] = useState(true);

  const loadData = () => {
    setLoading(true);
    api.analytics
      .getPriorities()
      .then((r) => setRows(r.data ?? []))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, []);

  const shown = (rows || []).filter((r) => !level || r.priority_level === level);
  const counts = (rows || []).reduce<Record<string, number>>(
    (a, r) => ({ ...a, [r.priority_level]: (a[r.priority_level] || 0) + 1 }),
    {}
  );

  return (
    <AppShell>
      <div className="space-y-5">
        {/* Section Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="font-code-sm text-[11px] text-ri-primary uppercase tracking-wider font-semibold">
                Rule-based priority scoring
              </span>
            </div>
            <h1 className="font-headline-sm text-2xl font-bold tracking-tight text-ri-text flex items-center gap-2.5">
              Maintenance priorities
            </h1>
            <p className="font-body-sm text-xs text-ri-muted mt-1">
              Open jobs ranked by level, then score. Automatic scores add rule-based components (severity, repeat sightings,
              recurrence, prior repairs, road health, recurrence escalation, rule-based deterioration estimate); manual
              priorities are kept as set by a person.
            </p>
          </div>
        </div>

        {error && (
          <div className="p-4 rounded-xl bg-ri-danger/15 border border-ri-danger/30 text-xs text-ri-danger-soft">
            {error}
          </div>
        )}

        {/* Filter Pills Bar (Matching Stitch Scrollable Horizon) */}
        {rows && (
          <div className="flex items-center justify-between gap-3 bg-ri-surface p-3 rounded-2xl border border-ri-line">
            <div className="flex items-center gap-2 overflow-x-auto pb-0.5">
              {["", "CRITICAL", "HIGH", "MEDIUM", "LOW"].map((l) => (
                <button
                  key={l || "all"}
                  onClick={() => setLevel(l)}
                  className={`px-3.5 py-1.5 rounded-full font-label-md text-xs whitespace-nowrap flex items-center gap-1.5 font-bold transition-all ${
                    level === l
                      ? "bg-ri-primary text-ri-on-primary shadow-sm shadow-ri-primary/20"
                      : "bg-ri-raised text-ri-muted hover:text-ri-text border border-ri-line"
                  }`}
                >
                  <span>{l || "All Priorities"}</span>
                  <span
                    className={`w-4 h-4 rounded-full font-code-sm text-[10px] flex items-center justify-center ${
                      level === l
                        ? "bg-ri-on-primary/30 text-ri-on-primary"
                        : "bg-ri-raised text-ri-muted"
                    }`}
                  >
                    {l ? counts[l] || 0 : rows.length}
                  </span>
                </button>
              ))}
            </div>

            <button
              onClick={loadData}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-ri-raised border border-ri-line text-xs text-ri-muted hover:text-ri-text"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin text-ri-primary" : ""}`} />
              <span>Refresh</span>
            </button>
          </div>
        )}

        {loading ? (
          <div className="h-64 flex items-center justify-center border border-ri-line rounded-2xl bg-ri-surface">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-ri-primary" />
          </div>
        ) : shown.length === 0 ? (
          <EmptyState
            icon={ListOrdered}
            title="No open maintenance jobs"
            description={`No open maintenance jobs${level ? ` at ${level}` : ""}.`}
          />
        ) : (
          <div className="space-y-3">
            {shown.map((r) => (
              <article
                key={r.job_id}
                className="rounded-2xl border border-ri-line bg-ri-surface p-4 hover:border-ri-primary/50 transition-colors"
              >
                {/* Desktop: identity | where and condition | status and risk. Stacks on smaller screens. */}
                <div className="grid gap-3 xl:grid-cols-[minmax(280px,1.15fr)_minmax(0,2.3fr)_minmax(260px,1fr)] xl:items-stretch">
                  {/* Rank, score, title */}
                  <div className="flex items-start gap-3 min-w-0">
                    <div className="shrink-0 w-[68px] rounded-xl bg-ri-input border border-ri-line py-2 text-center">
                      <p className="ri-label text-[9px]">Rank</p>
                      <p className="font-mono text-xl font-bold text-ri-primary-bright leading-6">#{r.rank}</p>
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-2">
                        <StatusBadge status={r.priority_level} size="sm" />
                        <span className="font-mono text-sm font-bold text-ri-text tabular-nums">
                          {r.priority_score ?? "—"}
                          <span className="text-ri-faint text-[10px] font-medium"> / 100</span>
                        </span>
                      </div>
                      <Link
                        href={`/maintenance/${r.job_id}`}
                        className="block mt-1.5 text-sm font-bold text-ri-text hover:text-ri-primary-bright transition-colors leading-snug"
                      >
                        {r.title}
                      </Link>
                      <p className="font-code-sm text-[10px] text-ri-faint mt-1">
                        {r.mode ?? "manual (no breakdown)"}
                        {r.version ? ` · ${r.version}` : ""}
                      </p>
                    </div>
                  </div>

                  {/* Location, segment health, recurrence */}
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                    <div className="bg-ri-input border border-ri-line/60 px-3 py-2.5 rounded-xl min-w-0">
                      <p className="ri-label text-[9.5px]">Location</p>
                      <p className="font-bold text-ri-text mt-1 break-words">
                        {r.road_id ? (
                          <Link href={`/roads/${r.road_id}`} className="text-ri-primary-bright hover:underline">
                            {r.road_name}
                          </Link>
                        ) : (
                          "No road"
                        )}
                        {r.segment_number != null ? ` · seg ${r.segment_number}` : ""}
                      </p>
                      <p className="font-code-sm text-ri-muted mt-0.5">
                        {r.linked_damage_count} damage · max {r.max_severity ?? "—"}
                      </p>
                    </div>
                    <div className="bg-ri-input border border-ri-line/60 px-3 py-2.5 rounded-xl min-w-0">
                      <p className="ri-label text-[9.5px]">Segment health</p>
                      <p className={`font-bold mt-1 ${healthClass(r.segment_health?.health_status)}`}>
                        {r.segment_health
                          ? `${r.segment_health.health_score ?? "—"} (${r.segment_health.health_status})`
                          : "No snapshot"}
                      </p>
                      <p className="font-code-sm text-[10px] text-ri-faint mt-0.5">rule-based score</p>
                    </div>
                    <div className="bg-ri-input border border-ri-line/60 px-3 py-2.5 rounded-xl min-w-0">
                      <p className="ri-label text-[9.5px]">Recurrence</p>
                      <p className="font-bold text-ri-text-soft mt-1">
                        {r.active_recurrences} active{" "}
                        {r.escalation_level && r.escalation_level !== "NONE" && (
                          <span className={`px-1.5 rounded ${escalationClass(r.escalation_level)}`}>{r.escalation_level}</span>
                        )}
                      </p>
                      <p className="font-code-sm text-[10px] text-ri-faint mt-0.5">at this job&apos;s damage</p>
                    </div>
                  </div>

                  {/* Job status and deterioration estimate */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-1 gap-3 text-xs">
                    <div className="flex items-center justify-between gap-2 bg-ri-input border border-ri-line/60 px-3 py-2 rounded-xl">
                      <p className="ri-label text-[9.5px]">Job status</p>
                      <StatusBadge status={r.status} label={r.status.replace(/_/g, " ")} size="sm" />
                    </div>
                    <div className="bg-ri-input border border-ri-line/60 px-3 py-2 rounded-xl min-w-0">
                      <p className="ri-label text-[9.5px]">Deterioration estimate</p>
                      <p className="font-bold text-ri-text-soft mt-0.5">
                        {r.deterioration_estimate?.predicted_risk != null
                          ? `risk ${r.deterioration_estimate.predicted_risk} (${r.deterioration_estimate.risk_band ?? "—"}) · ${r.deterioration_estimate.horizon_days} d`
                          : "Not generated"}
                      </p>
                      {r.deterioration_estimate && (
                        <p className="font-code-sm text-[10px] text-ri-faint">rule-based, not a trained model</p>
                      )}
                    </div>
                  </div>
                </div>

                {/* Scoring factors */}
                <div className="mt-3 pt-3 border-t border-ri-line/60">
                  {r.components ? (
                    <div className="grid grid-cols-2 sm:grid-cols-4 2xl:grid-cols-7 gap-2">
                      {Object.entries(r.components).map(([k, v]) => (
                        <div
                          key={k}
                          className={`flex items-baseline justify-between gap-2 px-2.5 py-1.5 rounded-lg border ${
                            v > 0 ? "border-ri-primary/35 bg-ri-primary/5" : "border-ri-line bg-ri-input"
                          }`}
                        >
                          <span className="font-code-sm text-[10px] text-ri-muted truncate">{k.replace(/_/g, " ")}</span>
                          <span className={`font-mono text-xs font-bold tabular-nums ${v > 0 ? "text-ri-primary-bright" : "text-ri-faint"}`}>
                            {v}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-[11px] text-ri-faint">
                      Priority was set manually or the job has no linked damage; no automatic breakdown exists.
                    </p>
                  )}
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
