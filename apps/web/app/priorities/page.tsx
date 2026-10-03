"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/shell";
import { api } from "@/lib/api-client";
import { escalationClass, healthClass } from "@/lib/intelligence";
import { PriorityOverviewItem } from "@/types/api";
import { ListOrdered } from "lucide-react";

// Open maintenance jobs ranked by priority. Every score shows the components that make it
// up; nothing is ranked without its reasons.

const levelClass = (l: string) =>
  ({ CRITICAL: "bg-red-950 text-red-400", HIGH: "bg-orange-950 text-orange-400", MEDIUM: "bg-amber-950 text-amber-400" })[l] ||
  "bg-slate-800 text-slate-300";

export default function PrioritiesPage() {
  const [rows, setRows] = useState<PriorityOverviewItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [level, setLevel] = useState<string>("");

  useEffect(() => {
    api.analytics.getPriorities().then((r) => setRows(r.data ?? [])).catch((e) => setError(e.message));
  }, []);

  const shown = (rows || []).filter((r) => !level || r.priority_level === level);
  const counts = (rows || []).reduce<Record<string, number>>((a, r) => ({ ...a, [r.priority_level]: (a[r.priority_level] || 0) + 1 }), {});

  return (
    <AppShell>
      <div className="space-y-5">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2"><ListOrdered className="h-5 w-5" />Maintenance priorities</h1>
          <p className="text-xs text-slate-400 mt-1">
            Open jobs ranked by level, then score. Automatic scores add rule-based components (severity, repeat sightings,
            recurrence, prior repairs, road health, recurrence escalation, rule-based deterioration estimate); manual priorities
            are kept as set by a person.
          </p>
        </div>
        {error && <p className="text-sm text-red-400">{error}</p>}
        {rows && (
          <div className="flex flex-wrap gap-2 text-xs">
            {["", "CRITICAL", "HIGH", "MEDIUM", "LOW"].map((l) => (
              <button key={l || "all"} onClick={() => setLevel(l)}
                className={`px-2.5 py-1 rounded border ${level === l ? "border-blue-500 text-blue-300" : "border-slate-700 text-slate-400"}`}>
                {l || "All"} ({l ? counts[l] || 0 : rows.length})
              </button>
            ))}
          </div>
        )}
        {rows && shown.length === 0 && <p className="text-sm text-slate-500">No open maintenance jobs{level ? ` at ${level}` : ""}.</p>}
        <div className="space-y-3">
          {shown.map((r) => (
            <div key={r.job_id} className="rounded-xl border border-slate-800 bg-slate-900/60 p-4">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="text-slate-500 text-xs">#{r.rank}</span>
                  <span className={`px-2 py-0.5 rounded text-xs font-bold ${levelClass(r.priority_level)}`}>
                    {r.priority_level} {r.priority_score ?? ""}
                  </span>
                  <Link href={`/maintenance/${r.job_id}`} className="text-sm font-semibold text-white hover:text-blue-300">{r.title}</Link>
                </div>
                <span className="text-[11px] text-slate-400">
                  {r.status.replace(/_/g, " ")} · {r.mode ?? "manual (no breakdown)"} {r.version ? `· ${r.version}` : ""}
                </span>
              </div>
              <div className="grid md:grid-cols-4 gap-3 mt-3 text-xs">
                <div>
                  <p className="text-[10px] uppercase text-slate-500">Location</p>
                  <p className="text-slate-300">
                    {r.road_id ? <Link href={`/roads/${r.road_id}`} className="text-blue-400">{r.road_name}</Link> : "No road"}
                    {r.segment_number != null ? ` · seg ${r.segment_number}` : ""}
                  </p>
                  <p className="text-slate-500">{r.linked_damage_count} damage · max {r.max_severity ?? "—"}</p>
                </div>
                <div>
                  <p className="text-[10px] uppercase text-slate-500">Segment health</p>
                  <p className={healthClass(r.segment_health?.health_status)}>
                    {r.segment_health ? `${r.segment_health.health_score ?? "—"} (${r.segment_health.health_status})` : "No snapshot"}
                  </p>
                </div>
                <div>
                  <p className="text-[10px] uppercase text-slate-500">Recurrence</p>
                  <p className="text-slate-300">
                    {r.active_recurrences} active{" "}
                    {r.escalation_level && r.escalation_level !== "NONE" && (
                      <span className={`px-1.5 rounded ${escalationClass(r.escalation_level)}`}>{r.escalation_level}</span>
                    )}
                  </p>
                </div>
                <div>
                  <p className="text-[10px] uppercase text-slate-500">Deterioration estimate</p>
                  <p className="text-slate-300">
                    {r.deterioration_estimate?.predicted_risk != null
                      ? `risk ${r.deterioration_estimate.predicted_risk} (${r.deterioration_estimate.risk_band ?? "—"}) · ${r.deterioration_estimate.horizon_days} d`
                      : "Not generated"}
                  </p>
                  {r.deterioration_estimate && <p className="text-[10px] text-slate-500">rule-based, not a trained model</p>}
                </div>
              </div>
              {r.components ? (
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {Object.entries(r.components).map(([k, v]) => (
                    <span key={k} className={`px-2 py-0.5 rounded text-[11px] border ${v > 0 ? "border-blue-800 text-blue-300" : "border-slate-800 text-slate-500"}`}>
                      {k.replace(/_/g, " ")}: {v}
                    </span>
                  ))}
                </div>
              ) : (
                <p className="mt-3 text-[11px] text-slate-500">Priority was set manually or the job has no linked damage; no automatic breakdown exists.</p>
              )}
            </div>
          ))}
        </div>
      </div>
    </AppShell>
  );
}
