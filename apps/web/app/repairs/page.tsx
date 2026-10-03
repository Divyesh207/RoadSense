"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/shell";
import { api } from "@/lib/api-client";
import { resultBadgeClass } from "@/lib/repair";
import { ContractorHistoryItem, VerificationOverviewItem } from "@/types/api";
import { ShieldCheck, Users } from "lucide-react";

// Repair verification outcomes and assignee (contractor) history, from stored records.

const when = (iso?: string | null) => (iso ? new Date(iso).toLocaleString() : "—");

export default function RepairsPage() {
  const [tab, setTab] = useState<"verifications" | "contractors">("verifications");
  const [verifications, setVerifications] = useState<VerificationOverviewItem[] | null>(null);
  const [contractors, setContractors] = useState<ContractorHistoryItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api.analytics.getRepairVerifications(), api.analytics.getContractors()])
      .then(([v, c]) => {
        setVerifications(v.data ?? []);
        setContractors(c.data ?? []);
      })
      .catch((e) => setError(e.message));
  }, []);

  return (
    <AppShell>
      <div className="space-y-5">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2"><ShieldCheck className="h-5 w-5" />Repairs & verification</h1>
          <p className="text-xs text-slate-400 mt-1">
            Automated before/after image analyses (OpenCV alignment + trained detector) and the reviewer decisions on them.
            The automated pipeline has not yet been validated on real before/after repair photographs.
          </p>
        </div>
        <div className="flex gap-2">
          {(["verifications", "contractors"] as const).map((t) => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-3 py-1 rounded text-xs border ${tab === t ? "border-blue-500 text-blue-300" : "border-slate-700 text-slate-400"}`}>
              {t === "verifications" ? "Verifications" : "Contractor / assignee history"}
            </button>
          ))}
        </div>
        {error && <p className="text-sm text-red-400">{error}</p>}

        {tab === "verifications" && verifications && (
          verifications.length === 0 ? (
            <p className="text-sm text-slate-500">No automated repair verification has been run yet.</p>
          ) : (
            <div className="overflow-x-auto rounded-xl border border-slate-800">
              <table className="w-full text-xs">
                <thead className="bg-slate-900 text-slate-500 text-left">
                  <tr><th className="p-2">Job</th><th>Automated</th><th>Detections B/A/residual</th><th>Model</th><th>Analysed</th><th>Reviewer</th><th>Final</th></tr>
                </thead>
                <tbody>
                  {verifications.map((v) => (
                    <tr key={v.verification_id} className="border-t border-slate-800 text-slate-300 align-top">
                      <td className="p-2">
                        <Link href={`/maintenance/${v.maintenance_job_id}`} className="text-blue-400">{v.job_title ?? v.maintenance_job_id.slice(0, 8)}</Link>
                        <div className="text-[10px] text-slate-500">{v.job_status}</div>
                      </td>
                      <td>
                        {v.automated_result ? <span className={`px-1.5 rounded ${resultBadgeClass(v.automated_result)}`}>{v.automated_result}</span> : v.status}
                        <div className="text-[10px] text-slate-500">{v.reason_code}</div>
                      </td>
                      <td>{v.before_detection_count ?? "—"} / {v.after_detection_count ?? "—"} / {v.residual_detection_count ?? "—"}</td>
                      <td className="text-[11px]">{v.model_name ? `${v.model_name} ${v.model_version}` : "—"}<div className="text-[10px] text-slate-500">{v.algorithm_version}</div></td>
                      <td>{when(v.analysed_at)}</td>
                      <td>{v.review_decision ?? "not reviewed"}<div className="text-[10px] text-slate-500">{when(v.reviewed_at)}</div></td>
                      <td>{v.final_result ? <span className={`px-1.5 rounded ${resultBadgeClass(v.final_result)}`}>{v.final_result}</span> : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        )}

        {tab === "contractors" && contractors && (
          contractors.length === 0 ? (
            <p className="text-sm text-slate-500">No maintenance job has been assigned yet, so there is no assignee history.</p>
          ) : (
            <div className="grid md:grid-cols-2 gap-4">
              {contractors.map((c) => (
                <div key={`${c.assignee_type}-${c.assignee_id}`} className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
                  <p className="text-sm font-semibold text-white flex items-center gap-2">
                    <Users className="h-4 w-4" />{c.name ?? c.assignee_id.slice(0, 8)}
                    <span className="text-[10px] text-slate-500">{c.assignee_type === "CONTRACTOR" ? "contractor organization" : "user"}</span>
                  </p>
                  <div className="grid grid-cols-3 gap-2 text-center text-xs mt-3">
                    {[
                      ["Assigned", c.assigned_jobs], ["Completed", c.completed_jobs], ["Open", c.open_jobs],
                      ["Verified", c.verified_jobs], ["Rejected", c.rejected_jobs], ["Recurrence after repair", c.recurrences_after_repair],
                    ].map(([k, v]) => (
                      <div key={String(k)} className="rounded border border-slate-800 p-2">
                        <p className="text-[10px] text-slate-500">{k}</p>
                        <p className="text-white font-bold">{v}</p>
                      </div>
                    ))}
                  </div>
                  <p className="text-[11px] text-slate-400 mt-2">
                    Verification outcomes:{" "}
                    {Object.keys(c.verification_outcomes).length === 0
                      ? "none yet"
                      : Object.entries(c.verification_outcomes).map(([k, v]) => (
                          <span key={k} className={`mr-1 px-1.5 rounded ${resultBadgeClass(k)}`}>{k} {v}</span>
                        ))}
                  </p>
                  <ul className="mt-2 text-[11px] text-slate-400 space-y-0.5 max-h-32 overflow-y-auto">
                    {c.jobs.map((j) => (
                      <li key={j.id}><Link href={`/maintenance/${j.id}`} className="text-blue-400">{j.title}</Link> · {j.status}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          )
        )}
      </div>
    </AppShell>
  );
}
