"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/shell";
import { StatusBadge } from "@/components/status-badge";
import { EmptyState } from "@/components/empty-state";
import { api } from "@/lib/api-client";
import { resultBadgeClass } from "@/lib/repair";
import { ContractorHistoryItem, VerificationOverviewItem } from "@/types/api";
import { ShieldCheck, Users, RefreshCw, CheckCircle2, Columns2 } from "lucide-react";
import { VerificationCompareModal } from "@/components/repairs/verification-compare-modal";

const when = (iso?: string | null) => (iso ? new Date(iso).toLocaleString() : "—");

export default function RepairsPage() {
  const [tab, setTab] = useState<"verifications" | "contractors">("verifications");
  const [verifications, setVerifications] = useState<VerificationOverviewItem[] | null>(null);
  const [contractors, setContractors] = useState<ContractorHistoryItem[] | null>(null);
  const [comparing, setComparing] = useState<VerificationOverviewItem | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const loadData = () => {
    setLoading(true);
    Promise.all([api.analytics.getRepairVerifications(), api.analytics.getContractors()])
      .then(([v, c]) => {
        setVerifications(v.data ?? []);
        setContractors(c.data ?? []);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <AppShell>
      <div className="space-y-5">
        {/* Section Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="font-code-sm text-[11px] text-ri-primary uppercase tracking-wider font-semibold">
                Repair verification & human review
              </span>
            </div>
            <h1 className="font-headline-sm text-2xl font-bold tracking-tight text-ri-text flex items-center gap-2.5">
              Repairs & verification
            </h1>
            <p className="font-body-sm text-xs text-ri-muted mt-1">
              Automated before/after image analyses (OpenCV alignment + trained detector) and the reviewer decisions on
              them. The automated pipeline has not yet been validated on real before/after repair photographs.
            </p>
          </div>

          {/* Tab Selector */}
          <div className="flex bg-ri-surface border border-ri-line p-1 rounded-xl">
            <button
              onClick={() => setTab("verifications")}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
                tab === "verifications"
                  ? "bg-ri-primary text-ri-on-primary shadow-sm shadow-ri-primary/20"
                  : "text-ri-muted hover:text-ri-text"
              }`}
            >
              <ShieldCheck className="h-3.5 w-3.5" />
              Verifications
            </button>
            <button
              onClick={() => setTab("contractors")}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
                tab === "contractors"
                  ? "bg-ri-primary text-ri-on-primary shadow-sm shadow-ri-primary/20"
                  : "text-ri-muted hover:text-ri-text"
              }`}
            >
              <Users className="h-3.5 w-3.5" />
              Contractor / assignee history
            </button>
          </div>
        </div>

        {error && (
          <div className="p-4 rounded-xl bg-ri-danger/15 border border-ri-danger/30 text-xs text-ri-danger-soft">
            {error}
          </div>
        )}

        {loading ? (
          <div className="h-64 flex items-center justify-center border border-ri-line rounded-2xl bg-ri-surface">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-ri-primary" />
          </div>
        ) : tab === "verifications" && verifications ? (
          verifications.length === 0 ? (
            <EmptyState
              icon={ShieldCheck}
              title="No repair verifications"
              description="No automated repair verification has been run yet."
            />
          ) : (
            <div className="bg-ri-surface border border-ri-line rounded-2xl overflow-hidden shadow-sm">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs table-fixed min-w-[1040px]">
                  <colgroup>
                    <col className="w-[20%]" />
                    <col className="w-[9%]" />
                    <col className="w-[15%]" />
                    <col className="w-[8%]" />
                    <col className="w-[14%]" />
                    <col className="w-[10%]" />
                    <col className="w-[11%]" />
                    <col className="w-[13%]" />
                  </colgroup>
                  <thead className="bg-ri-bg border-b border-ri-line text-ri-muted">
                    <tr>
                      <th className="py-2.5 px-4 font-semibold">Job</th>
                      <th className="py-2.5 px-4 font-semibold">Before / after</th>
                      <th className="py-2.5 px-4 font-semibold">Automated analysis</th>
                      <th className="py-2.5 px-4 font-semibold" title="Detections in the BEFORE image / in the AFTER image / still overlapping the damage">Detections / residual</th>
                      <th className="py-2.5 px-4 font-semibold">Model</th>
                      <th className="py-2.5 px-4 font-semibold">Analysed</th>
                      <th className="py-2.5 px-4 font-semibold">Human review</th>
                      <th className="py-2.5 px-4 text-right font-semibold">Final result</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-ri-line/50 text-ri-text-soft">
                    {verifications.map((v) => (
                      <tr key={v.verification_id} className="hover:bg-ri-raised/50 transition-colors">
                        <td className="py-2.5 px-4 align-top">
                          <Link
                            href={`/maintenance/${v.maintenance_job_id}`}
                            className="font-bold text-ri-primary-bright hover:underline"
                          >
                            {v.job_title ?? v.maintenance_job_id.slice(0, 8)}
                          </Link>
                          <div className="font-code-sm text-[10px] text-ri-muted mt-0.5">
                            {v.job_status}
                          </div>
                        </td>
                        <td className="py-2.5 px-4 align-top">
                          <button
                            onClick={() => setComparing(v)}
                            className="inline-flex items-center gap-1.5 h-8 px-3 rounded-lg bg-ri-primary/15 border border-ri-primary/40 text-ri-primary-bright text-[11px] font-bold hover:bg-ri-primary/25 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ri-primary-bright"
                          >
                            <Columns2 className="h-3.5 w-3.5 text-ri-primary-bright" />
                            Compare
                          </button>
                        </td>
                        <td className="py-2.5 px-4 align-top">
                          {v.automated_result ? (
                            <StatusBadge status={v.automated_result} size="sm" />
                          ) : (
                            <span className="font-code-sm text-ri-muted">{v.status}</span>
                          )}
                          <div className="font-code-sm text-[10px] text-ri-faint mt-0.5 break-words" title={v.reason_code ?? undefined}>
                            {v.reason_code}
                          </div>
                        </td>
                        <td className="py-2.5 px-4 align-top font-code-sm text-ri-text-soft">
                          {v.before_detection_count ?? "—"} / {v.after_detection_count ?? "—"} /{" "}
                          <span className={v.residual_detection_count ? "text-ri-danger" : ""}>
                            {v.residual_detection_count ?? "—"}
                          </span>
                        </td>
                        <td
                          className="py-2.5 px-4 align-top font-code-sm text-ri-muted break-words"
                          title={v.model_name ? `Detector ${v.model_name} ${v.model_version}; comparison rules ${v.algorithm_version ?? "unknown"}` : undefined}
                        >
                          {v.model_name ? `${v.model_name} ${v.model_version}` : "—"}
                          <div className="text-[10px] text-ri-faint">{v.algorithm_version}</div>
                        </td>
                        <td className="py-2.5 px-4 align-top font-code-sm text-ri-muted">
                          {when(v.analysed_at)}
                        </td>
                        <td className="py-2.5 px-4 align-top text-ri-text-soft">
                          {v.review_decision ?? "not reviewed"}
                          <div className="font-code-sm text-[10px] text-ri-faint">
                            {when(v.reviewed_at)}
                          </div>
                        </td>
                        <td className="py-2.5 px-4 align-top text-right">
                          {v.final_result ? (
                            <StatusBadge status={v.final_result} size="sm" />
                          ) : (
                            <span className="text-ri-faint font-code-sm">—</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )
        ) : tab === "contractors" && contractors ? (
          contractors.length === 0 ? (
            <EmptyState
              icon={Users}
              title="No assignee history"
              description="No maintenance job has been assigned yet, so there is no assignee history."
            />
          ) : (
            <div className="grid md:grid-cols-2 2xl:grid-cols-3 gap-4">
              {contractors.map((c) => (
                <div
                  key={`${c.assignee_type}-${c.assignee_id}`}
                  className="rounded-2xl border border-ri-line bg-ri-surface p-5 shadow-sm space-y-4"
                >
                  <div className="flex items-center justify-between">
                    <p className="font-headline-sm text-sm font-bold text-white flex items-center gap-2">
                      <Users className="h-4 w-4 text-ri-primary" />
                      {c.name ?? c.assignee_id.slice(0, 8)}
                    </p>
                    <span className="font-code-sm text-[10px] px-2 py-0.5 rounded-full bg-ri-raised border border-ri-line text-ri-muted">
                      {c.assignee_type === "CONTRACTOR" ? "contractor organization" : "user"}
                    </span>
                  </div>

                  <div className="grid grid-cols-3 gap-2 text-center text-xs">
                    {[
                      ["Assigned", c.assigned_jobs, "#06B6D4"],
                      ["Completed", c.completed_jobs, "#10B981"],
                      ["Open", c.open_jobs, "#F59E0B"],
                      ["Verified", c.verified_jobs, "#10B981"],
                      ["Rejected", c.rejected_jobs, "#EF4444"],
                      ["Recurrence after repair", c.recurrences_after_repair, "#EF4444"],
                    ].map(([k, v, color]) => (
                      <div
                        key={String(k)}
                        className="rounded-xl border border-ri-line bg-ri-input p-2.5"
                      >
                        <p className="font-label-sm text-[10px] uppercase text-ri-muted">{k}</p>
                        <p
                          className="font-code-lg text-lg font-bold mt-1"
                          style={{ color: String(color) }}
                        >
                          {String(v)}
                        </p>
                      </div>
                    ))}
                  </div>

                  <p className="text-[11px] text-ri-muted flex flex-wrap items-center gap-1.5">
                    Verification outcomes:
                    {Object.keys(c.verification_outcomes).length === 0
                      ? " none yet"
                      : Object.entries(c.verification_outcomes).map(([k, v]) => (
                          <StatusBadge key={k} status={k} label={`${k} ${v}`} size="sm" showDot={false} />
                        ))}
                  </p>

                  <ul className="text-[11px] text-ri-muted space-y-0.5 max-h-32 overflow-y-auto">
                    {c.jobs.map((j) => (
                      <li key={j.id}>
                        <Link href={`/maintenance/${j.id}`} className="text-ri-primary hover:underline">
                          {j.title}
                        </Link>{" "}
                        · {j.status}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          )
        ) : null}
      </div>

      {comparing && <VerificationCompareModal item={comparing} onClose={() => setComparing(null)} />}
    </AppShell>
  );
}
