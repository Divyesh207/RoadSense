"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/shell";
import { api } from "@/lib/api-client";
import { escalationClass } from "@/lib/intelligence";
import { resultBadgeClass } from "@/lib/repair";
import { RecurrenceOverviewItem } from "@/types/api";
import { BentoMetricTile } from "@/components/bento-metric-tile";
import { StatusBadge } from "@/components/status-badge";
import { EmptyState } from "@/components/empty-state";
import {
  Repeat,
  AlertTriangle,
  ShieldAlert,
  MapPin,
  Clock,
  Wrench,
  CheckCircle2,
  RefreshCw,
  Info,
} from "lucide-react";

export default function RecurrencePage() {
  const [items, setItems] = useState<RecurrenceOverviewItem[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [escalatedOnly, setEscalatedOnly] = useState(false);

  const loadData = () => {
    setLoading(true);
    setError(null);
    api.analytics
      .getRecurrences()
      .then((r) => setItems(r.data ?? []))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, []);

  const totalItems = items ?? [];
  const shown = totalItems.filter((r) => !escalatedOnly || (r.escalation_level && r.escalation_level !== "NONE"));
  const active = totalItems.filter((r) => r.status === "POTENTIAL" || r.status === "CONFIRMED");
  const escalated = totalItems.filter((r) => r.escalation_level && r.escalation_level !== "NONE");

  return (
    <AppShell>
      <div className="space-y-6 animate-in fade-in duration-300">
        {/* Page Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-2 rounded-lg bg-[#06B6D4]/10 border border-[#06B6D4]/30 text-[#06B6D4]">
                <Repeat className="h-5 w-5" />
              </span>
              <h1 className="text-xl md:text-2xl font-bold tracking-tight text-white">
                Recurrence monitoring
              </h1>
            </div>
            <p className="text-xs text-slate-400 mt-1 max-w-3xl leading-relaxed">
              Confirmed damage of the same type found within the GPS grouping radius of damage that was repaired. Detected by
              fixed rules (distance, type, repair status, verification result, time since repair); not a prediction.
            </p>
          </div>
          <button
            onClick={loadData}
            disabled={loading}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-[#111A2E] border border-[#26344F] text-slate-200 text-xs font-semibold hover:border-[#06B6D4]/40 hover:text-white transition-all disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin text-[#06B6D4]" : ""}`} />
            Refresh
          </button>
        </div>

        {/* Technical Provenance Note */}
        <div className="p-3.5 rounded-xl bg-[#111A2E]/80 border border-[#26344F] flex items-start gap-3">
          <Info className="h-4 w-4 text-[#06B6D4] mt-0.5 shrink-0" />
          <div className="text-xs space-y-1">
            <span className="font-semibold text-slate-200">Rule-based detection:</span>
            <span className="text-slate-400 block">
              A recurrence is recorded when newly confirmed damage lies within the grouping radius of earlier damage of the
              same type that was repaired. Escalation reasons listed per row are the rules that fired.
            </span>
          </div>
        </div>

        {/* KPI Bento Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <BentoMetricTile
            label="Active"
            value={loading ? "..." : active.length}
            subtext="Status POTENTIAL or CONFIRMED"
            icon={Repeat}
          />
          <BentoMetricTile
            label="Escalated"
            value={loading ? "..." : escalated.length}
            subtext="Escalation level ELEVATED or CRITICAL"
            icon={ShieldAlert}
            status={escalated.length > 0 ? "warning" : "nominal"}
          />
          <BentoMetricTile
            label="Total"
            value={loading ? "..." : totalItems.length}
            subtext="All recurrence records"
            icon={MapPin}
          />
        </div>

        {/* Filter & Controls Toolbar */}
        <div className="p-4 rounded-xl bg-[#111A2E] border border-[#26344F] flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-slate-300 select-none">
              <input
                type="checkbox"
                checked={escalatedOnly}
                onChange={(e) => setEscalatedOnly(e.target.checked)}
                className="rounded border-[#26344F] bg-[#0C1321] text-[#06B6D4] focus:ring-0 focus:ring-offset-0 h-4 w-4"
              />
              Escalated only
            </label>
            {escalatedOnly && (
              <span className="px-2 py-0.5 rounded-full text-[10px] font-mono bg-amber-500/10 border border-amber-500/30 text-amber-300">
                Filter: Escalation Level != NONE
              </span>
            )}
          </div>
          <div className="text-xs text-slate-400 font-mono">
            Displaying <span className="text-white font-semibold">{shown.length}</span> of {totalItems.length} recurrence records
          </div>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="p-4 rounded-xl bg-red-950/40 border border-red-800 text-red-200 text-xs flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 shrink-0 text-red-400" />
            <span>{error}</span>
          </div>
        )}

        {/* Table / Empty State */}
        {loading ? (
          <div className="py-20 text-center rounded-2xl bg-[#111A2E] border border-[#26344F]">
            <RefreshCw className="h-6 w-6 animate-spin mx-auto text-[#06B6D4] mb-3" />
            <p className="text-xs font-mono text-slate-400">Loading recurrences...</p>
          </div>
        ) : shown.length === 0 ? (
          <EmptyState
            title={`No recurrences recorded${escalatedOnly ? " with escalation" : ""}`}
            description={
              escalatedOnly
                ? "No recurrence record has an escalation level other than NONE."
                : "Recurrences appear here when confirmed damage is found at a previously repaired location."
            }
            icon={Repeat}
          />
        ) : (
          <div className="rounded-2xl border border-[#26344F] bg-[#111A2E] overflow-hidden shadow-xl">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-[#26344F] bg-[#0C1321]/60 text-[11px] font-semibold text-slate-400 uppercase tracking-wider font-mono">
                    <th className="px-4 py-3.5">Location</th>
                    <th className="px-4 py-3.5">Type / severity</th>
                    <th className="px-4 py-3.5">Recurrence #</th>
                    <th className="px-4 py-3.5">Previous repair</th>
                    <th className="px-4 py-3.5">Previous verification</th>
                    <th className="px-4 py-3.5">Days since repair</th>
                    <th className="px-4 py-3.5">Status</th>
                    <th className="px-4 py-3.5">Escalation</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#26344F]/60">
                  {shown.map((r) => (
                    <tr key={r.id} className="hover:bg-[#17223A]/50 transition-colors">
                      <td className="px-4 py-3.5 align-top">
                        {r.road_id ? (
                          <Link
                            href={`/roads/${r.road_id}`}
                            className="font-medium text-[#4CD7F6] hover:underline flex items-center gap-1"
                          >
                            <span>{r.road_name || "Unknown Road"}</span>
                          </Link>
                        ) : (
                          <span className="text-slate-400 font-mono">Unassigned</span>
                        )}
                        {r.segment_number != null && (
                          <span className="text-slate-400 text-[11px] font-mono block">
                            Segment #{r.segment_number}
                          </span>
                        )}
                        <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                          {r.location ? `${r.location.latitude.toFixed(5)}, ${r.location.longitude.toFixed(5)}` : "—"}
                          {r.distance_meters != null ? ` · Δ ${r.distance_meters}m` : ""}
                        </div>
                      </td>

                      <td className="px-4 py-3.5 align-top whitespace-nowrap">
                        <span className="font-semibold text-white">{r.damage_type ?? "—"}</span>
                        <span className="block text-[11px] font-mono text-slate-400">
                          Severity: {r.new_severity ?? "—"}
                        </span>
                      </td>

                      <td className="px-4 py-3.5 align-top whitespace-nowrap font-mono">
                        <span className="inline-flex items-center px-2 py-0.5 rounded bg-[#0C1321] border border-[#26344F] font-bold text-[#06B6D4]">
                          {r.recurrence_number_at_location != null ? `#${r.recurrence_number_at_location}` : "—"}
                        </span>
                      </td>

                      <td className="px-4 py-3.5 align-top">
                        {r.previous_repair_job_id ? (
                          <Link
                            href={`/maintenance/${r.previous_repair_job_id}`}
                            className="text-[#4CD7F6] hover:underline flex items-center gap-1 font-mono text-[11px]"
                          >
                            <Wrench className="h-3 w-3 text-slate-400" />
                            <span>{r.previous_repair_job_title ?? "job"}</span>
                          </Link>
                        ) : (
                          <span className="text-slate-500">—</span>
                        )}
                      </td>

                      <td className="px-4 py-3.5 align-top whitespace-nowrap">
                        {r.previous_verification_result ? (
                          <span className={`inline-flex px-2 py-0.5 rounded text-[11px] font-mono ${resultBadgeClass(r.previous_verification_result)}`}>
                            {r.previous_verification_result}
                          </span>
                        ) : (
                          <span className="text-slate-500 text-[11px] font-mono">none</span>
                        )}
                        {r.previous_verification_source && r.previous_verification_source !== "NONE" && (
                          <span className="text-[10px] text-slate-500 font-mono block mt-0.5">
                            source: {r.previous_verification_source.toLowerCase()}
                          </span>
                        )}
                      </td>

                      <td className="px-4 py-3.5 align-top whitespace-nowrap font-mono text-slate-300">
                        {r.days_since_repair != null ? (
                          <span>{r.days_since_repair} days</span>
                        ) : (
                          <span className="text-slate-500">—</span>
                        )}
                      </td>

                      <td className="px-4 py-3.5 align-top whitespace-nowrap">
                        <StatusBadge status={r.status} variant={r.status === "CONFIRMED" ? "error" : undefined} />
                      </td>

                      <td className="px-4 py-3.5 align-top">
                        <span className={`inline-flex px-2 py-0.5 rounded text-[11px] font-mono font-semibold ${escalationClass(r.escalation_level)}`}>
                          {r.escalation_level ?? "not evaluated"}
                        </span>
                        {r.escalation_reasons && r.escalation_reasons.length > 0 && (
                          <div className="mt-1 space-y-0.5">
                            {r.escalation_reasons.map((x) => (
                              <div key={x.code} className="text-[10px] text-slate-400 font-mono bg-[#0C1321] px-1.5 py-0.5 rounded border border-[#26344F]/50">
                                {x.detail}
                              </div>
                            ))}
                          </div>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
