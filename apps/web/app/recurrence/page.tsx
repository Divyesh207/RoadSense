"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/shell";
import { api } from "@/lib/api-client";
import { escalationClass } from "@/lib/intelligence";
import { resultBadgeClass } from "@/lib/repair";
import { RecurrenceOverviewItem } from "@/types/api";
import { Repeat } from "lucide-react";

// Recurring damage: new confirmed damage at a previously repaired location (rule-based
// detection; escalation reasons are the rules that fired).

export default function RecurrencePage() {
  const [items, setItems] = useState<RecurrenceOverviewItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [escalatedOnly, setEscalatedOnly] = useState(false);

  useEffect(() => {
    api.analytics.getRecurrences().then((r) => setItems(r.data ?? [])).catch((e) => setError(e.message));
  }, []);

  const shown = (items || []).filter((r) => !escalatedOnly || (r.escalation_level && r.escalation_level !== "NONE"));
  const active = (items || []).filter((r) => r.status === "POTENTIAL" || r.status === "CONFIRMED");

  return (
    <AppShell>
      <div className="space-y-5">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2"><Repeat className="h-5 w-5" />Recurrence monitoring</h1>
          <p className="text-xs text-slate-400 mt-1">
            Confirmed damage of the same type found within the GPS grouping radius of damage that was repaired. Detected by
            fixed rules (distance, type, repair status, verification result, time since repair); not a prediction.
          </p>
        </div>
        {error && <p className="text-sm text-red-400">{error}</p>}
        {items && (
          <div className="flex items-center gap-4 text-xs text-slate-400">
            <span>{active.length} active · {items.length} total</span>
            <label className="flex items-center gap-1">
              <input type="checkbox" checked={escalatedOnly} onChange={(e) => setEscalatedOnly(e.target.checked)} /> escalated only
            </label>
          </div>
        )}
        {items && shown.length === 0 && <p className="text-sm text-slate-500">No recurrences recorded{escalatedOnly ? " with escalation" : ""}.</p>}
        {shown.length > 0 && (
          <div className="overflow-x-auto rounded-xl border border-slate-800">
            <table className="w-full text-xs">
              <thead className="bg-slate-900 text-slate-500 text-left">
                <tr>
                  <th className="p-2">Location</th><th>Type / severity</th><th>Recurrence #</th><th>Previous repair</th>
                  <th>Previous verification</th><th>Days since repair</th><th>Status</th><th>Escalation</th>
                </tr>
              </thead>
              <tbody>
                {shown.map((r) => (
                  <tr key={r.id} className="border-t border-slate-800 text-slate-300 align-top">
                    <td className="p-2">
                      {r.road_id ? <Link href={`/roads/${r.road_id}`} className="text-blue-400">{r.road_name}</Link> : "—"}
                      {r.segment_number != null && ` · seg ${r.segment_number}`}
                      <div className="text-[10px] text-slate-500">
                        {r.location ? `${r.location.latitude.toFixed(5)}, ${r.location.longitude.toFixed(5)}` : ""}
                        {r.distance_meters != null ? ` · ${r.distance_meters} m` : ""}
                      </div>
                    </td>
                    <td>{r.damage_type ?? "—"} · {r.new_severity ?? "—"}</td>
                    <td>{r.recurrence_number_at_location ?? "—"}</td>
                    <td>
                      {r.previous_repair_job_id ? (
                        <Link href={`/maintenance/${r.previous_repair_job_id}`} className="text-blue-400">{r.previous_repair_job_title ?? "job"}</Link>
                      ) : "repaired (no job recorded)"}
                    </td>
                    <td>
                      {r.previous_verification_result ? (
                        <span className={`px-1.5 rounded ${resultBadgeClass(r.previous_verification_result)}`}>
                          {r.previous_verification_result}
                        </span>
                      ) : "not verified"}
                      {r.previous_verification_source && r.previous_verification_source !== "NONE" && (
                        <span className="text-[10px] text-slate-500"> ({r.previous_verification_source.toLowerCase()})</span>
                      )}
                    </td>
                    <td>{r.days_since_repair ?? "—"}</td>
                    <td>{r.status}</td>
                    <td>
                      <span className={`px-1.5 rounded ${escalationClass(r.escalation_level)}`}>{r.escalation_level ?? "not evaluated"}</span>
                      {r.escalation_reasons.map((x) => (
                        <div key={x.code} className="text-[10px] text-slate-400 mt-0.5">{x.detail}</div>
                      ))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </AppShell>
  );
}
