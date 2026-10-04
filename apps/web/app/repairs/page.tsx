"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/shell";
import { StatusBadge } from "@/components/status-badge";
import { EmptyState } from "@/components/empty-state";
import { api } from "@/lib/api-client";
import { resultBadgeClass } from "@/lib/repair";
import { ContractorHistoryItem, VerificationOverviewItem } from "@/types/api";
import { ShieldCheck, Users, RefreshCw, CheckCircle2 } from "lucide-react";

const when = (iso?: string | null) => (iso ? new Date(iso).toLocaleString() : "—");

export default function RepairsPage() {
  const [tab, setTab] = useState<"verifications" | "contractors">("verifications");
  const [verifications, setVerifications] = useState<VerificationOverviewItem[] | null>(null);
  const [contractors, setContractors] = useState<ContractorHistoryItem[] | null>(null);
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
      <div className="space-y-6 max-w-6xl">
        {/* Section Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="font-code-sm text-[11px] text-[#06B6D4] uppercase tracking-wider font-semibold">
                Repair verification & human review
              </span>
            </div>
            <h1 className="font-headline-sm text-2xl font-bold tracking-tight text-[#F1F5F9] flex items-center gap-2.5">
              Repairs & verification
            </h1>
            <p className="font-body-sm text-xs text-[#94A3B8] mt-1">
              Automated before/after image analyses (OpenCV alignment + trained detector) and the reviewer decisions on
              them. The automated pipeline has not yet been validated on real before/after repair photographs.
            </p>
          </div>

          {/* Tab Selector */}
          <div className="flex bg-[#111A2E] border border-[#26344F] p-1 rounded-xl">
            <button
              onClick={() => setTab("verifications")}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
                tab === "verifications"
                  ? "bg-[#06B6D4] text-[#003640] shadow-sm shadow-[#06B6D4]/20"
                  : "text-[#94A3B8] hover:text-[#F1F5F9]"
              }`}
            >
              <ShieldCheck className="h-3.5 w-3.5" />
              Verifications
            </button>
            <button
              onClick={() => setTab("contractors")}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
                tab === "contractors"
                  ? "bg-[#06B6D4] text-[#003640] shadow-sm shadow-[#06B6D4]/20"
                  : "text-[#94A3B8] hover:text-[#F1F5F9]"
              }`}
            >
              <Users className="h-3.5 w-3.5" />
              Contractor / assignee history
            </button>
          </div>
        </div>

        {error && (
          <div className="p-4 rounded-xl bg-[#EF4444]/15 border border-[#EF4444]/30 text-xs text-[#FFB4AB]">
            {error}
          </div>
        )}

        {loading ? (
          <div className="h-64 flex items-center justify-center border border-[#26344F] rounded-2xl bg-[#111A2E]">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#06B6D4]" />
          </div>
        ) : tab === "verifications" && verifications ? (
          verifications.length === 0 ? (
            <EmptyState
              icon={ShieldCheck}
              title="No repair verifications"
              description="No automated repair verification has been run yet."
            />
          ) : (
            <div className="bg-[#111A2E] border border-[#26344F] rounded-2xl overflow-hidden shadow-sm">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-[#0C1321] border-b border-[#26344F] text-[#94A3B8]">
                    <tr>
                      <th className="py-3 px-4 font-semibold">Job</th>
                      <th className="py-3 px-4 font-semibold">Automated</th>
                      <th className="py-3 px-4 font-semibold">Detections B/A/residual</th>
                      <th className="py-3 px-4 font-semibold">Model</th>
                      <th className="py-3 px-4 font-semibold">Analysed</th>
                      <th className="py-3 px-4 font-semibold">Reviewer</th>
                      <th className="py-3 px-4 text-right font-semibold">Final</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#26344F]/50 text-[#DCE2F6]">
                    {verifications.map((v) => (
                      <tr key={v.verification_id} className="hover:bg-[#17223A]/50 transition-colors">
                        <td className="py-3 px-4">
                          <Link
                            href={`/maintenance/${v.maintenance_job_id}`}
                            className="font-bold text-[#4CD7F6] hover:underline"
                          >
                            {v.job_title ?? v.maintenance_job_id.slice(0, 8)}
                          </Link>
                          <div className="font-code-sm text-[10px] text-[#869397] mt-0.5">
                            {v.job_status}
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          {v.automated_result ? (
                            <StatusBadge status={v.automated_result} size="sm" />
                          ) : (
                            <span className="font-code-sm text-[#94A3B8]">{v.status}</span>
                          )}
                          <div className="font-code-sm text-[10px] text-[#64748B] mt-0.5">
                            {v.reason_code}
                          </div>
                        </td>
                        <td className="py-3 px-4 font-code-sm text-[#DCE2F6]">
                          {v.before_detection_count ?? "—"} / {v.after_detection_count ?? "—"} /{" "}
                          <span className={v.residual_detection_count ? "text-[#EF4444]" : ""}>
                            {v.residual_detection_count ?? "—"}
                          </span>
                        </td>
                        <td className="py-3 px-4 font-code-sm text-[#94A3B8]">
                          {v.model_name ? `${v.model_name} ${v.model_version}` : "—"}
                          <div className="text-[10px] text-[#64748B]">{v.algorithm_version}</div>
                        </td>
                        <td className="py-3 px-4 font-code-sm text-[#94A3B8]">
                          {when(v.analysed_at)}
                        </td>
                        <td className="py-3 px-4 text-[#DCE2F6]">
                          {v.review_decision ?? "not reviewed"}
                          <div className="font-code-sm text-[10px] text-[#64748B]">
                            {when(v.reviewed_at)}
                          </div>
                        </td>
                        <td className="py-3 px-4 text-right">
                          {v.final_result ? (
                            <StatusBadge status={v.final_result} size="sm" />
                          ) : (
                            <span className="text-[#64748B] font-code-sm">—</span>
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
            <div className="grid md:grid-cols-2 gap-4">
              {contractors.map((c) => (
                <div
                  key={`${c.assignee_type}-${c.assignee_id}`}
                  className="rounded-2xl border border-[#26344F] bg-[#111A2E] p-5 shadow-sm space-y-4"
                >
                  <div className="flex items-center justify-between">
                    <p className="font-headline-sm text-sm font-bold text-white flex items-center gap-2">
                      <Users className="h-4 w-4 text-[#06B6D4]" />
                      {c.name ?? c.assignee_id.slice(0, 8)}
                    </p>
                    <span className="font-code-sm text-[10px] px-2 py-0.5 rounded-full bg-[#17223A] border border-[#26344F] text-[#94A3B8]">
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
                        className="rounded-xl border border-[#26344F] bg-[#151B2A] p-2.5"
                      >
                        <p className="font-label-sm text-[10px] uppercase text-[#94A3B8]">{k}</p>
                        <p
                          className="font-code-lg text-lg font-bold mt-1"
                          style={{ color: String(color) }}
                        >
                          {String(v)}
                        </p>
                      </div>
                    ))}
                  </div>

                  <p className="text-[11px] text-[#94A3B8] flex flex-wrap items-center gap-1.5">
                    Verification outcomes:
                    {Object.keys(c.verification_outcomes).length === 0
                      ? " none yet"
                      : Object.entries(c.verification_outcomes).map(([k, v]) => (
                          <StatusBadge key={k} status={k} label={`${k} ${v}`} size="sm" showDot={false} />
                        ))}
                  </p>

                  <ul className="text-[11px] text-[#94A3B8] space-y-0.5 max-h-32 overflow-y-auto">
                    {c.jobs.map((j) => (
                      <li key={j.id}>
                        <Link href={`/maintenance/${j.id}`} className="text-[#06B6D4] hover:underline">
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
    </AppShell>
  );
}
