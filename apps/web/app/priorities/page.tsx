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
      <div className="space-y-6 max-w-6xl">
        {/* Section Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="font-code-sm text-[11px] text-[#06B6D4] uppercase tracking-wider font-semibold">
                Rule-based priority scoring
              </span>
            </div>
            <h1 className="font-headline-sm text-2xl font-bold tracking-tight text-[#F1F5F9] flex items-center gap-2.5">
              Maintenance priorities
            </h1>
            <p className="font-body-sm text-xs text-[#94A3B8] mt-1">
              Open jobs ranked by level, then score. Automatic scores add rule-based components (severity, repeat sightings,
              recurrence, prior repairs, road health, recurrence escalation, rule-based deterioration estimate); manual
              priorities are kept as set by a person.
            </p>
          </div>
        </div>

        {error && (
          <div className="p-4 rounded-xl bg-[#EF4444]/15 border border-[#EF4444]/30 text-xs text-[#FFB4AB]">
            {error}
          </div>
        )}

        {/* Filter Pills Bar (Matching Stitch Scrollable Horizon) */}
        {rows && (
          <div className="flex items-center justify-between gap-3 bg-[#111A2E] p-3 rounded-2xl border border-[#26344F]">
            <div className="flex items-center gap-2 overflow-x-auto pb-0.5">
              {["", "CRITICAL", "HIGH", "MEDIUM", "LOW"].map((l) => (
                <button
                  key={l || "all"}
                  onClick={() => setLevel(l)}
                  className={`px-3.5 py-1.5 rounded-full font-label-md text-xs whitespace-nowrap flex items-center gap-1.5 font-bold transition-all ${
                    level === l
                      ? "bg-[#06B6D4] text-[#003640] shadow-sm shadow-[#06B6D4]/20"
                      : "bg-[#17223A] text-[#94A3B8] hover:text-[#F1F5F9] border border-[#26344F]"
                  }`}
                >
                  <span>{l || "All Priorities"}</span>
                  <span
                    className={`w-4 h-4 rounded-full font-code-sm text-[10px] flex items-center justify-center ${
                      level === l
                        ? "bg-[#003640]/30 text-[#003640]"
                        : "bg-[#232A39] text-[#94A3B8]"
                    }`}
                  >
                    {l ? counts[l] || 0 : rows.length}
                  </span>
                </button>
              ))}
            </div>

            <button
              onClick={loadData}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#17223A] border border-[#26344F] text-xs text-[#94A3B8] hover:text-[#F1F5F9]"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin text-[#06B6D4]" : ""}`} />
              <span>Refresh</span>
            </button>
          </div>
        )}

        {loading ? (
          <div className="h-64 flex items-center justify-center border border-[#26344F] rounded-2xl bg-[#111A2E]">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#06B6D4]" />
          </div>
        ) : shown.length === 0 ? (
          <EmptyState
            icon={ListOrdered}
            title="No open maintenance jobs"
            description={`No open maintenance jobs${level ? ` at ${level}` : ""}.`}
          />
        ) : (
          <div className="space-y-3.5">
            {shown.map((r) => (
              <div
                key={r.job_id}
                className="rounded-2xl border border-[#26344F] bg-[#111A2E] p-5 shadow-sm hover:border-[#06B6D4]/50 transition-all space-y-3"
              >
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="flex items-center gap-2.5">
                    <span className="font-code-sm text-xs font-bold text-[#06B6D4] px-2 py-0.5 rounded bg-[#17223A] border border-[#26344F]">
                      Rank #{r.rank}
                    </span>
                    <StatusBadge
                      status={r.priority_level}
                      label={`${r.priority_level} ${r.priority_score ?? ""}`}
                    />
                    <Link
                      href={`/maintenance/${r.job_id}`}
                      className="font-headline-sm text-base font-bold text-[#F1F5F9] hover:text-[#4CD7F6] transition-colors"
                    >
                      {r.title}
                    </Link>
                  </div>
                  <span className="font-code-sm text-xs text-[#94A3B8]">
                    {r.status.replace(/_/g, " ")} · {r.mode ?? "manual (no breakdown)"} {r.version ? `· ${r.version}` : ""}
                  </span>
                </div>

                <div className="grid md:grid-cols-4 gap-3 pt-3 border-t border-[#26344F]/60 text-xs">
                  <div className="bg-[#151B2A] border border-[#26344F]/50 p-3 rounded-xl">
                    <p className="font-label-sm text-[10px] uppercase text-[#94A3B8] font-semibold">
                      Location
                    </p>
                    <p className="font-bold text-[#F1F5F9] mt-1">
                      {r.road_id ? (
                        <Link href={`/roads/${r.road_id}`} className="text-[#06B6D4] hover:underline">
                          {r.road_name}
                        </Link>
                      ) : (
                        "No road"
                      )}
                      {r.segment_number != null ? ` · seg ${r.segment_number}` : ""}
                    </p>
                    <p className="font-code-sm text-[#94A3B8] mt-0.5">
                      {r.linked_damage_count} damage · max {r.max_severity ?? "—"}
                    </p>
                  </div>

                  <div className="bg-[#151B2A] border border-[#26344F]/50 p-3 rounded-xl">
                    <p className="font-label-sm text-[10px] uppercase text-[#94A3B8] font-semibold">
                      Segment health
                    </p>
                    <p className={`font-bold mt-1 ${healthClass(r.segment_health?.health_status)}`}>
                      {r.segment_health
                        ? `${r.segment_health.health_score ?? "—"} (${r.segment_health.health_status})`
                        : "No snapshot"}
                    </p>
                  </div>

                  <div className="bg-[#151B2A] border border-[#26344F]/50 p-3 rounded-xl">
                    <p className="font-label-sm text-[10px] uppercase text-[#94A3B8] font-semibold">
                      Recurrence
                    </p>
                    <p className="font-bold text-[#DCE2F6] mt-1">
                      {r.active_recurrences} active{" "}
                      {r.escalation_level && r.escalation_level !== "NONE" && (
                        <span className={`px-1.5 rounded ${escalationClass(r.escalation_level)}`}>{r.escalation_level}</span>
                      )}
                    </p>
                  </div>

                  <div className="bg-[#151B2A] border border-[#26344F]/50 p-3 rounded-xl">
                    <p className="font-label-sm text-[10px] uppercase text-[#94A3B8] font-semibold">
                      Deterioration estimate
                    </p>
                    <p className="font-bold text-[#DCE2F6] mt-1">
                      {r.deterioration_estimate?.predicted_risk != null
                        ? `risk ${r.deterioration_estimate.predicted_risk} (${r.deterioration_estimate.risk_band ?? "—"}) · ${r.deterioration_estimate.horizon_days} d`
                        : "Not generated"}
                    </p>
                    {r.deterioration_estimate && (
                      <p className="font-code-sm text-[10px] text-[#64748B]">rule-based, not a trained model</p>
                    )}
                  </div>
                </div>

                {r.components ? (
                  <div className="flex flex-wrap gap-1.5">
                    {Object.entries(r.components).map(([k, v]) => (
                      <span
                        key={k}
                        className={`px-2 py-0.5 rounded-lg font-code-sm text-[11px] border ${
                          v > 0 ? "border-[#06B6D4]/40 text-[#4CD7F6]" : "border-[#26344F] text-[#64748B]"
                        }`}
                      >
                        {k.replace(/_/g, " ")}: {v}
                      </span>
                    ))}
                  </div>
                ) : (
                  <p className="text-[11px] text-[#64748B]">
                    Priority was set manually or the job has no linked damage; no automatic breakdown exists.
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
