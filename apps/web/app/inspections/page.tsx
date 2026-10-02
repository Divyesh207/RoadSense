"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/shell";
import { api } from "@/lib/api-client";
import { Inspection } from "@/types/api";
import {
  ClipboardList,
  Search,
  Cpu,
  Send,
  Eye,
  CheckCircle2,
  Clock,
  Layers,
} from "lucide-react";

export default function InspectionsPage() {
  const [inspections, setInspections] = useState<Inspection[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [processingId, setProcessingId] = useState<string | null>(null);

  const loadInspections = async () => {
    setLoading(true);
    try {
      const res = await api.inspections.list({
        status: statusFilter || undefined,
        page_size: 50,
      });
      if (res.data) {
        setInspections(res.data);
      }
    } catch (err) {
      console.error("Failed to load inspections:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInspections();
  }, [statusFilter]);

  const handleTriggerAI = async (id: string) => {
    setProcessingId(id);
    try {
      await api.inspections.process(id);
      await loadInspections();
    } catch (err: any) {
      alert(`AI trigger error: ${err?.message || "Failed to start AI processing"}`);
    } finally {
      setProcessingId(null);
    }
  };

  const handleSubmitDraft = async (id: string) => {
    try {
      await api.inspections.submit(id);
      await loadInspections();
    } catch (err: any) {
      alert(`Submit error: ${err?.message || "Failed to submit inspection"}`);
    }
  };

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white">Field Inspections & Evidence</h1>
            <p className="text-xs text-slate-400 mt-1">
              Field evidence captures, media uploads, and AI damage processing lifecycle
            </p>
          </div>
        </div>

        {/* Filter bar */}
        <div className="flex items-center gap-4 bg-slate-900 p-3 rounded-lg border border-slate-800">
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400 font-medium">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-slate-950 border border-slate-800 text-xs text-slate-200 rounded px-2.5 py-1.5 focus:outline-none focus:border-blue-500"
            >
              <option value="">All Statuses</option>
              <option value="DRAFT">Draft</option>
              <option value="SUBMITTED">Submitted</option>
              <option value="PROCESSING">Processing</option>
              <option value="COMPLETED">Completed</option>
            </select>
          </div>
        </div>

        {/* Inspections Table */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/60 border-b border-slate-800 text-slate-400">
                <tr>
                  <th className="py-3 px-4 font-semibold">Inspection ID</th>
                  <th className="py-3 px-4 font-semibold">Road Association</th>
                  <th className="py-3 px-4 font-semibold">Inspector</th>
                  <th className="py-3 px-4 font-semibold">Status</th>
                  <th className="py-3 px-4 font-semibold">Media Evidence</th>
                  <th className="py-3 px-4 font-semibold">Captured At</th>
                  <th className="py-3 px-4 text-right font-semibold">Workflow Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-slate-500">
                      Loading inspections...
                    </td>
                  </tr>
                ) : inspections.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-8 text-center text-slate-500">
                      No inspections found.
                    </td>
                  </tr>
                ) : (
                  inspections.map((insp) => (
                    <tr key={insp.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="py-3 px-4 font-mono text-[11px] text-blue-400 font-medium">
                        <Link href={`/inspections/${insp.id}`} className="hover:text-blue-300 hover:underline">
                          {insp.id.slice(0, 8)}...
                        </Link>
                      </td>
                      <td className="py-3 px-4 text-white">
                        {insp.road_name ? (
                          <span>{insp.road_name} {insp.segment_number ? `(Seg ${insp.segment_number})` : ""}</span>
                        ) : (
                          <span className="text-slate-500 italic">Unassigned road</span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-slate-400">{insp.inspector_name || "Field Agent"}</td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                            insp.status === "COMPLETED"
                              ? "bg-emerald-950 text-emerald-400 border border-emerald-800/50"
                              : insp.status === "PROCESSING"
                              ? "bg-blue-950 text-blue-400 border border-blue-800/50 animate-pulse"
                              : insp.status === "SUBMITTED"
                              ? "bg-purple-950 text-purple-400 border border-purple-800/50"
                              : "bg-slate-800 text-slate-400"
                          }`}
                        >
                          {insp.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-400">
                        {insp.media_summary?.media_count || 0} items ({insp.media_summary?.image_count || 0} img, {insp.media_summary?.video_count || 0} vid)
                      </td>
                      <td className="py-3 px-4 text-slate-500">
                        {new Date(insp.captured_at).toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          {insp.status === "DRAFT" && (
                            <button
                              onClick={() => handleSubmitDraft(insp.id)}
                              className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-[11px] font-medium transition-colors"
                            >
                              Submit
                            </button>
                          )}

                          {insp.status === "SUBMITTED" && (
                            <button
                              disabled={processingId === insp.id}
                              onClick={() => handleTriggerAI(insp.id)}
                              className="px-2.5 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded text-[11px] font-medium flex items-center gap-1.5 shadow-sm shadow-blue-500/20 disabled:opacity-50 transition-all"
                            >
                              <Cpu className="h-3 w-3" />
                              <span>{processingId === insp.id ? "Queuing..." : "Process AI"}</span>
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
