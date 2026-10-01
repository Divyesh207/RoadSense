"use client";

import React, { useEffect, useState } from "react";
import { AppShell } from "@/components/shell";
import { api } from "@/lib/api-client";
import { DamageRecord, DamageType } from "@/types/api";
import {
  AlertTriangle,
  CheckCircle,
  XCircle,
  Filter,
  ShieldAlert,
  Edit3,
  Calendar,
  Layers,
} from "lucide-react";

export default function DamagesPage() {
  const [damages, setDamages] = useState<DamageRecord[]>([]);
  const [types, setTypes] = useState<DamageType[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [severityFilter, setSeverityFilter] = useState<string>("");
  const [loading, setLoading] = useState(true);

  // Review modal state
  const [selectedDamage, setSelectedDamage] = useState<DamageRecord | null>(null);
  const [reviewDecision, setReviewDecision] = useState<"CONFIRMED" | "REJECTED">("CONFIRMED");
  const [reviewSeverity, setReviewSeverity] = useState<string>("HIGH");
  const [reviewNotes, setReviewNotes] = useState<string>("");
  const [submittingReview, setSubmittingReview] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [dmgRes, typeRes] = await Promise.all([
        api.damages.list({
          status: statusFilter || undefined,
          severity: severityFilter || undefined,
          page_size: 100,
        }),
        api.damages.types(),
      ]);

      if (dmgRes.data) setDamages(dmgRes.data);
      if (typeRes.data) setTypes(typeRes.data);
    } catch (err) {
      console.error("Failed to load damage intelligence data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [statusFilter, severityFilter]);

  const openReviewModal = (dmg: DamageRecord) => {
    setSelectedDamage(dmg);
    setReviewDecision("CONFIRMED");
    setReviewSeverity(dmg.severity);
    setReviewNotes("");
  };

  const handleReviewSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedDamage) return;
    setSubmittingReview(true);

    try {
      await api.damages.review(selectedDamage.id, {
        decision: reviewDecision,
        severity: reviewSeverity,
        notes: reviewNotes,
      });
      setSelectedDamage(null);
      await loadData();
    } catch (err: any) {
      alert(`Review submission error: ${err?.message || "Failed to submit review"}`);
    } finally {
      setSubmittingReview(false);
    }
  };

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white">Damage Intelligence & Review Queue</h1>
            <p className="text-xs text-slate-400 mt-1">
              Candidate AI detections, human validation workflow, and canonical damage records
            </p>
          </div>
        </div>

        {/* Filter bar */}
        <div className="flex flex-wrap items-center gap-4 bg-slate-900 p-3 rounded-lg border border-slate-800">
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400 font-medium">Status:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-slate-950 border border-slate-800 text-xs text-slate-200 rounded px-2.5 py-1.5 focus:outline-none focus:border-blue-500"
            >
              <option value="">All Statuses</option>
              <option value="PENDING_REVIEW">Pending Review</option>
              <option value="CONFIRMED">Confirmed</option>
              <option value="REJECTED">Rejected</option>
              <option value="REPAIRED">Repaired</option>
            </select>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400 font-medium">Severity:</span>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="bg-slate-950 border border-slate-800 text-xs text-slate-200 rounded px-2.5 py-1.5 focus:outline-none focus:border-blue-500"
            >
              <option value="">All Severities</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>
          </div>
        </div>

        {/* Damage Records Table */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/60 border-b border-slate-800 text-slate-400">
                <tr>
                  <th className="py-3 px-4 font-semibold">Damage Type</th>
                  <th className="py-3 px-4 font-semibold">Severity</th>
                  <th className="py-3 px-4 font-semibold">Status</th>
                  <th className="py-3 px-4 font-semibold">Road Location</th>
                  <th className="py-3 px-4 font-semibold">Source</th>
                  <th className="py-3 px-4 font-semibold">Confidence</th>
                  <th className="py-3 px-4 font-semibold">Area (m²)</th>
                  <th className="py-3 px-4 text-right font-semibold">Review Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {loading ? (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-slate-500">
                      Loading damage records...
                    </td>
                  </tr>
                ) : damages.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-slate-500">
                      No damage records found.
                    </td>
                  </tr>
                ) : (
                  damages.map((dmg) => (
                    <tr key={dmg.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="py-3 px-4 font-medium text-white flex items-center gap-2">
                        <AlertTriangle className="h-4 w-4 text-amber-400 shrink-0" />
                        <span>{dmg.damage_type_name || dmg.damage_type_code}</span>
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                            dmg.severity === "CRITICAL"
                              ? "bg-red-950 text-red-400 border border-red-800/60"
                              : dmg.severity === "HIGH"
                              ? "bg-orange-950 text-orange-400 border border-orange-800/60"
                              : dmg.severity === "MEDIUM"
                              ? "bg-amber-950 text-amber-400 border border-amber-800/60"
                              : "bg-emerald-950 text-emerald-400 border border-emerald-800/60"
                          }`}
                        >
                          {dmg.severity}
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                            dmg.status === "CONFIRMED"
                              ? "bg-emerald-950 text-emerald-400 border border-emerald-800/50"
                              : dmg.status === "PENDING_REVIEW"
                              ? "bg-purple-950 text-purple-400 border border-purple-800/50 animate-pulse"
                              : dmg.status === "REJECTED"
                              ? "bg-rose-950 text-rose-400 border border-rose-800/50"
                              : "bg-slate-800 text-slate-400"
                          }`}
                        >
                          {dmg.status}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-slate-300">
                        {dmg.road_name || "Unassigned Road"}
                      </td>
                      <td className="py-3 px-4 text-slate-400">{dmg.source_type}</td>
                      <td className="py-3 px-4 font-mono text-slate-300">
                        {dmg.confidence ? `${(dmg.confidence * 100).toFixed(1)}%` : "—"}
                      </td>
                      <td className="py-3 px-4 text-slate-400 font-mono">
                        {dmg.estimated_area_m2 ? `${dmg.estimated_area_m2.toFixed(2)} m²` : "—"}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={() => openReviewModal(dmg)}
                          className="px-2.5 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded text-[11px] font-medium transition-colors"
                        >
                          {dmg.status === "PENDING_REVIEW" ? "Review" : "Edit / Audit"}
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Human Review Modal */}
        {selectedDamage && (
          <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50">
            <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 space-y-5 shadow-2xl">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h3 className="text-base font-semibold text-white flex items-center gap-2">
                  <ShieldAlert className="h-5 w-5 text-blue-400" />
                  <span>Human Review: {selectedDamage.damage_type_name}</span>
                </h3>
                <button
                  onClick={() => setSelectedDamage(null)}
                  className="text-slate-400 hover:text-white text-xs"
                >
                  ✕
                </button>
              </div>

              <form onSubmit={handleReviewSubmit} className="space-y-4 text-xs">
                <div>
                  <label className="block text-slate-400 mb-1.5 font-medium">Review Decision</label>
                  <div className="grid grid-cols-2 gap-3">
                    <button
                      type="button"
                      onClick={() => setReviewDecision("CONFIRMED")}
                      className={`p-2.5 rounded-lg border text-center font-semibold transition-all ${
                        reviewDecision === "CONFIRMED"
                          ? "bg-emerald-950 border-emerald-500 text-emerald-400 shadow-md shadow-emerald-500/10"
                          : "bg-slate-950 border-slate-800 text-slate-400 hover:bg-slate-900"
                      }`}
                    >
                      ✓ Confirm Defect
                    </button>
                    <button
                      type="button"
                      onClick={() => setReviewDecision("REJECTED")}
                      className={`p-2.5 rounded-lg border text-center font-semibold transition-all ${
                        reviewDecision === "REJECTED"
                          ? "bg-rose-950 border-rose-500 text-rose-400 shadow-md shadow-rose-500/10"
                          : "bg-slate-950 border-slate-800 text-slate-400 hover:bg-slate-900"
                      }`}
                    >
                      ✕ Reject False Positive
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-slate-400 mb-1.5 font-medium">Adjust Severity Level</label>
                  <select
                    value={reviewSeverity}
                    onChange={(e) => setReviewSeverity(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2 text-white focus:outline-none focus:border-blue-500"
                  >
                    <option value="CRITICAL">CRITICAL — Immediate Safety Hazard</option>
                    <option value="HIGH">HIGH — Severe Pothole / Rapid Deterioration</option>
                    <option value="MEDIUM">MEDIUM — Moderate Surface Deformation</option>
                    <option value="LOW">LOW — Minor Surface Wear / Crack</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-400 mb-1.5 font-medium">Auditable Review Notes</label>
                  <textarea
                    rows={3}
                    value={reviewNotes}
                    onChange={(e) => setReviewNotes(e.target.value)}
                    placeholder="Provide justification for review decision or field verification notes..."
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white placeholder:text-slate-600 focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div className="flex justify-end gap-3 pt-3 border-t border-slate-800">
                  <button
                    type="button"
                    onClick={() => setSelectedDamage(null)}
                    className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg font-medium"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submittingReview}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-semibold shadow-md shadow-blue-500/20 disabled:opacity-50"
                  >
                    {submittingReview ? "Saving Review..." : "Commit Review"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
