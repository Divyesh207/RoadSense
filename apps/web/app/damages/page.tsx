"use client";

import React, { useEffect, useState } from "react";
import { AppShell } from "@/components/shell";
import { StatusBadge } from "@/components/status-badge";
import { EmptyState } from "@/components/empty-state";
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
  Cpu,
  Sparkles,
  Bot,
  MapPin,
  Clock,
  ShieldCheck,
  RefreshCw,
} from "lucide-react";
import { detectionMethodLabel, isHeuristic } from "@/lib/provenance";

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

  const pendingCount = damages.filter((d) => d.status === "PENDING_REVIEW").length;
  const confirmedCount = damages.filter((d) => d.status === "CONFIRMED").length;
  const criticalCount = damages.filter((d) => d.severity === "CRITICAL").length;

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Section Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="font-code-sm text-[11px] text-[#06B6D4] uppercase tracking-wider font-semibold">
                AI Detection & Human Review
              </span>
            </div>
            <h1 className="font-headline-sm text-2xl font-bold tracking-tight text-[#F1F5F9]">
              Damage Intelligence & Review Queue
            </h1>
            <p className="font-body-sm text-xs text-[#94A3B8] mt-1">
              Candidate AI detections, human validation workflow, and canonical damage records
            </p>
          </div>
        </div>

        {/* Operational Overview Bento Strip */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="p-4 rounded-2xl bg-[#111A2E] border border-[#26344F] flex flex-col justify-between">
            <span className="font-label-sm text-[11px] text-[#94A3B8] uppercase tracking-wider">
              Total Records
            </span>
            <div className="font-code-lg text-2xl font-bold text-[#F1F5F9] mt-2">
              {damages.length}
            </div>
          </div>
          <div className="p-4 rounded-2xl bg-[#111A2E] border border-[#26344F] flex flex-col justify-between">
            <span className="font-label-sm text-[11px] text-[#F59E0B] uppercase tracking-wider">
              Pending Human Review
            </span>
            <div className="font-code-lg text-2xl font-bold text-[#F59E0B] mt-2">
              {pendingCount}
            </div>
          </div>
          <div className="p-4 rounded-2xl bg-[#111A2E] border border-[#26344F] flex flex-col justify-between">
            <span className="font-label-sm text-[11px] text-[#10B981] uppercase tracking-wider">
              Confirmed
            </span>
            <div className="font-code-lg text-2xl font-bold text-[#10B981] mt-2">
              {confirmedCount}
            </div>
          </div>
          <div className="p-4 rounded-2xl bg-[#111A2E] border border-[#26344F] flex flex-col justify-between">
            <span className="font-label-sm text-[11px] text-[#EF4444] uppercase tracking-wider">
              Critical Severity
            </span>
            <div className="font-code-lg text-2xl font-bold text-[#EF4444] mt-2">
              {criticalCount}
            </div>
          </div>
        </div>

        {/* AI & Human Review Provenance Callout */}
        <div className="bg-[#111A2E] border border-[#26344F] rounded-2xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <div className="w-9 h-9 rounded-xl bg-[#06B6D4]/15 border border-[#06B6D4]/30 flex items-center justify-center text-[#4CD7F6] shrink-0 mt-0.5">
              <Cpu className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-label-md text-xs font-bold text-[#F1F5F9]">
                  Detection provenance
                </span>
              </div>
              <p className="text-xs text-[#94A3B8] mt-0.5 leading-relaxed">
                Each record shows how it was produced: trained model, heuristic fallback (OpenCV rules, not a trained
                model) or manual entry. Trained-model classes:{" "}
                <span className="text-[#4CD7F6]">D40 → POTHOLE</span>,{" "}
                <span className="text-[#ADC6FF]">D00/D10/D20 → CRACK</span>. Heuristic scores are not probabilities.
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 font-code-sm text-[11px] text-[#94A3B8] shrink-0 bg-[#151B2A] border border-[#26344F] px-3 py-1.5 rounded-xl">
            <ShieldCheck className="h-4 w-4 text-[#10B981]" />
            <span>Human review decides every record</span>
          </div>
        </div>

        {/* Filter bar */}
        <div className="flex flex-wrap items-center justify-between gap-3 bg-[#111A2E] p-3 rounded-2xl border border-[#26344F]">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              <span className="font-label-sm text-xs text-[#94A3B8] font-medium">Status:</span>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-[#151B2A] border border-[#26344F] text-xs text-[#F1F5F9] rounded-xl px-3 py-1.5 focus:outline-none focus:border-[#06B6D4]"
              >
                <option value="">All Statuses</option>
                <option value="PENDING_REVIEW">Pending Review</option>
                <option value="CONFIRMED">Confirmed</option>
                <option value="REJECTED">Rejected</option>
                <option value="REPAIRED">Repaired</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <span className="font-label-sm text-xs text-[#94A3B8] font-medium">Severity:</span>
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                className="bg-[#151B2A] border border-[#26344F] text-xs text-[#F1F5F9] rounded-xl px-3 py-1.5 focus:outline-none focus:border-[#06B6D4]"
              >
                <option value="">All Severities</option>
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>
            </div>
          </div>

          <button
            onClick={() => loadData()}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#17223A] border border-[#26344F] text-xs text-[#94A3B8] hover:text-[#F1F5F9] transition-colors"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin text-[#06B6D4]" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>

        {/* Damage Records Table */}
        <div className="bg-[#111A2E] border border-[#26344F] rounded-2xl overflow-hidden shadow-sm">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-[#0C1321] border-b border-[#26344F] text-[#94A3B8]">
                <tr>
                  <th className="py-3 px-4 font-semibold">Damage Type</th>
                  <th className="py-3 px-4 font-semibold">Severity</th>
                  <th className="py-3 px-4 font-semibold">Status</th>
                  <th className="py-3 px-4 font-semibold">Road Location</th>
                  <th className="py-3 px-4 font-semibold">Source / Method</th>
                  <th className="py-3 px-4 font-semibold">Score</th>
                  <th className="py-3 px-4 font-semibold">Area (m²)</th>
                  <th className="py-3 px-4 text-right font-semibold">Review Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#26344F]/50 text-[#DCE2F6]">
                {loading ? (
                  <tr>
                    <td colSpan={8} className="py-12 text-center text-[#94A3B8]">
                      <div className="flex items-center justify-center gap-2">
                        <RefreshCw className="h-4 w-4 animate-spin text-[#06B6D4]" />
                        <span>Loading road damage intelligence records...</span>
                      </div>
                    </td>
                  </tr>
                ) : damages.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-12 text-center text-[#94A3B8]">
                      No active damage records matching criteria.
                    </td>
                  </tr>
                ) : (
                  damages.map((dmg) => {
                    const heuristic = isHeuristic(dmg.detection_method, dmg.score_type);
                    return (
                      <tr key={dmg.id} className="hover:bg-[#17223A]/50 transition-colors">
                        <td className="py-3 px-4 font-bold text-white">
                          <div className="flex items-center gap-2">
                            <span>{dmg.damage_type_name || dmg.damage_type_code}</span>
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <StatusBadge status={dmg.severity} size="sm" />
                        </td>
                        <td className="py-3 px-4">
                          <StatusBadge status={dmg.status} size="sm" />
                        </td>
                        <td className="py-3 px-4 text-[#DCE2F6]">
                          {dmg.road_name || "Unassigned Road"}
                        </td>
                        <td className="py-3 px-4 font-code-sm" title={detectionMethodLabel(dmg.detection_method)}>
                          <span className="text-[#94A3B8] mr-1.5">{dmg.source_type}</span>
                          {heuristic ? (
                            <span className="px-2 py-0.5 rounded bg-[#F59E0B]/15 border border-[#F59E0B]/30 text-[#F59E0B] text-[10px]">
                              Heuristic fallback
                            </span>
                          ) : dmg.detection_method === "TRAINED_MODEL" ? (
                            <span className="px-2 py-0.5 rounded bg-[#06B6D4]/15 border border-[#06B6D4]/30 text-[#4CD7F6] text-[10px]">
                              Trained model
                            </span>
                          ) : dmg.detection_method === "MANUAL" ? (
                            <span className="px-2 py-0.5 rounded bg-[#232A39] border border-[#3D494C] text-[#BCC9CD] text-[10px]">
                              Manual entry
                            </span>
                          ) : null}
                        </td>
                        <td className="py-3 px-4 font-code-sm text-[#F1F5F9]">
                          {dmg.confidence ? `${(dmg.confidence * 100).toFixed(1)}%` : "—"}
                          {dmg.confidence && heuristic ? (
                            <span className="block text-[10px] text-[#F59E0B] font-sans">heuristic, not a probability</span>
                          ) : null}
                        </td>
                        <td className="py-3 px-4 font-code-sm text-[#94A3B8]">
                          {dmg.estimated_area_m2 ? `${dmg.estimated_area_m2.toFixed(2)} m²` : "—"}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <button
                            onClick={() => openReviewModal(dmg)}
                            className="h-8 px-3 rounded-lg bg-[#06B6D4] hover:bg-[#4CD7F6] text-[#003640] font-label-md text-xs font-bold transition-all active:scale-95"
                          >
                            {dmg.status === "PENDING_REVIEW" ? "Review" : "Edit / Audit"}
                          </button>
                        </td>
                      </tr>
                    );
                  })
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Human Review Modal (Matching Stitch tactile dialog) */}
        {selectedDamage && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
            <div className="bg-[#111A2E] border border-[#26344F] rounded-2xl max-w-lg w-full p-6 space-y-5 shadow-2xl">
              <div className="flex items-center justify-between border-b border-[#26344F] pb-3">
                <div className="flex items-center gap-2">
                  <ShieldAlert className="h-5 w-5 text-[#06B6D4]" />
                  <h3 className="font-headline-sm text-base font-bold text-[#F1F5F9]">
                    Human Review: {selectedDamage.damage_type_name}
                  </h3>
                </div>
                <button
                  onClick={() => setSelectedDamage(null)}
                  className="text-[#94A3B8] hover:text-[#F1F5F9] text-sm p-1"
                >
                  ✕
                </button>
              </div>

              <form onSubmit={handleReviewSubmit} className="space-y-4">
                <div className="bg-[#151B2A] border border-[#26344F] p-3 rounded-xl space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-[#94A3B8]">Damage ID:</span>
                    <span className="font-code-sm text-[#F1F5F9]">{selectedDamage.id}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-[#94A3B8]">Road:</span>
                    <span className="text-[#F1F5F9] font-medium">{selectedDamage.road_name || "Unassigned"}</span>
                  </div>
                  <div className="flex justify-between text-xs">
                    <span className="text-[#94A3B8]">Detection method:</span>
                    <span className="font-code-sm text-[#06B6D4]">
                      {detectionMethodLabel(selectedDamage.detection_method)}
                    </span>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="font-label-sm text-xs text-[#94A3B8] font-semibold">
                    Review Decision
                  </label>
                  <div className="grid grid-cols-2 gap-3">
                    <button
                      type="button"
                      onClick={() => setReviewDecision("CONFIRMED")}
                      className={`h-11 rounded-xl font-label-md text-xs font-bold flex items-center justify-center gap-2 border transition-all ${
                        reviewDecision === "CONFIRMED"
                          ? "bg-[#10B981] text-[#003824] border-[#10B981]"
                          : "bg-[#17223A] text-[#94A3B8] border-[#26344F]"
                      }`}
                    >
                      <CheckCircle className="h-4 w-4" />
                      <span>Confirm Defect</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setReviewDecision("REJECTED")}
                      className={`h-11 rounded-xl font-label-md text-xs font-bold flex items-center justify-center gap-2 border transition-all ${
                        reviewDecision === "REJECTED"
                          ? "bg-[#EF4444] text-white border-[#EF4444]"
                          : "bg-[#17223A] text-[#94A3B8] border-[#26344F]"
                      }`}
                    >
                      <XCircle className="h-4 w-4" />
                      <span>Reject False Positive</span>
                    </button>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="font-label-sm text-xs text-[#94A3B8] font-semibold">
                    Adjust Severity Level
                  </label>
                  <select
                    value={reviewSeverity}
                    onChange={(e) => setReviewSeverity(e.target.value)}
                    className="w-full h-11 bg-[#151B2A] border border-[#26344F] rounded-xl px-3 text-xs text-[#F1F5F9] focus:outline-none focus:border-[#06B6D4]"
                  >
                    <option value="CRITICAL">CRITICAL — Immediate Safety Hazard</option>
                    <option value="HIGH">HIGH — Severe Pothole / Rapid Deterioration</option>
                    <option value="MEDIUM">MEDIUM — Moderate Surface Deformation</option>
                    <option value="LOW">LOW — Minor Surface Wear / Crack</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="font-label-sm text-xs text-[#94A3B8] font-semibold">
                    Auditable Review Notes
                  </label>
                  <textarea
                    rows={3}
                    value={reviewNotes}
                    onChange={(e) => setReviewNotes(e.target.value)}
                    placeholder="Provide justification for review decision or field verification notes..."
                    className="w-full bg-[#151B2A] border border-[#26344F] rounded-xl p-3 text-xs text-[#F1F5F9] placeholder:text-[#64748B] focus:outline-none focus:border-[#06B6D4]"
                  />
                </div>

                <div className="flex items-center justify-end gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setSelectedDamage(null)}
                    className="h-10 px-4 rounded-xl bg-[#17223A] border border-[#26344F] text-xs font-semibold text-[#94A3B8] hover:text-[#F1F5F9]"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submittingReview}
                    className="h-10 px-5 rounded-xl bg-[#06B6D4] hover:bg-[#4CD7F6] text-[#003640] text-xs font-bold shadow-md shadow-[#06B6D4]/20 transition-all active:scale-95 disabled:opacity-50"
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
