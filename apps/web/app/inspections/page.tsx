"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/shell";
import { StatusBadge } from "@/components/status-badge";
import { EmptyState } from "@/components/empty-state";
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
  MapPin,
  Camera,
  AlertCircle,
  PlusCircle,
  RefreshCw,
  SlidersHorizontal,
} from "lucide-react";

export default function InspectionsPage() {
  const [inspections, setInspections] = useState<Inspection[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [processingId, setProcessingId] = useState<string | null>(null);
  // Per-status totals for the whole organization (API meta.total_count), independent of the active filter.
  const [counts, setCounts] = useState<Record<string, number | null>>({});

  const loadCounts = async () => {
    const statuses = ["", "DRAFT", "SUBMITTED", "PROCESSING", "COMPLETED"];
    const results = await Promise.allSettled(
      statuses.map((s) => api.inspections.list({ status: s || undefined, page_size: 1 }))
    );
    const next: Record<string, number | null> = {};
    results.forEach((r, i) => {
      next[statuses[i]] = r.status === "fulfilled" ? r.value.meta?.total_count ?? null : null;
    });
    setCounts(next);
  };

  const loadInspections = async () => {
    setLoading(true);
    loadCounts();
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

  const countLabel = (status: string) => counts[status] ?? "—";
  const draftCount = countLabel("DRAFT");
  const submittedCount = countLabel("SUBMITTED");
  const processingCount = countLabel("PROCESSING");
  const completedCount = countLabel("COMPLETED");

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Section Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="font-code-sm text-[11px] text-[#06B6D4] uppercase tracking-wider font-semibold">
                Field Operations & Evidence
              </span>
            </div>
            <h1 className="font-headline-sm text-2xl font-bold tracking-tight text-[#F1F5F9]">
              Field Inspections & Evidence
            </h1>
            <p className="font-body-sm text-xs text-[#94A3B8] mt-1">
              Field evidence captures, media uploads, and AI damage processing lifecycle
            </p>
          </div>
        </div>

        {/* Operational Metric Tiles (4-Column Bento matching Stitch Screen) */}
        <section aria-label="Inspection Metrics" className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <div className="flex flex-col items-center justify-center p-3 rounded-2xl bg-[#111A2E] border border-[#26344F] text-center shadow-sm">
            <div className="w-8 h-8 rounded-xl bg-[#232A39] flex items-center justify-center text-[#BCC9CD] mb-1.5 border border-[#3D494C]">
              <Clock className="h-4 w-4" />
            </div>
            <span className="font-code-lg text-2xl font-bold text-[#F1F5F9] leading-none mb-1">
              {draftCount}
            </span>
            <span className="font-label-sm text-[11px] text-[#94A3B8] uppercase tracking-wider font-semibold">
              Drafts
            </span>
          </div>

          <div className="flex flex-col items-center justify-center p-3 rounded-2xl bg-[#111A2E] border border-[#26344F] text-center shadow-sm">
            <div className="w-8 h-8 rounded-xl bg-[#3B82F6]/15 flex items-center justify-center text-[#ADC6FF] mb-1.5 border border-[#3B82F6]/30">
              <Layers className="h-4 w-4" />
            </div>
            <span className="font-code-lg text-2xl font-bold text-[#ADC6FF] leading-none mb-1">
              {submittedCount}
            </span>
            <span className="font-label-sm text-[11px] text-[#94A3B8] uppercase tracking-wider font-semibold">
              Submitted
            </span>
          </div>

          <div className="flex flex-col items-center justify-center p-3 rounded-2xl bg-[#111A2E] border border-[#26344F] text-center shadow-sm">
            <div className="w-8 h-8 rounded-xl bg-[#06B6D4]/15 flex items-center justify-center text-[#4CD7F6] mb-1.5 border border-[#06B6D4]/30">
              <Cpu className="h-4 w-4" />
            </div>
            <span className="font-code-lg text-2xl font-bold text-[#4CD7F6] leading-none mb-1">
              {processingCount}
            </span>
            <span className="font-label-sm text-[11px] text-[#06B6D4] uppercase tracking-wider font-semibold">
              AI Processing
            </span>
          </div>

          <div className="flex flex-col items-center justify-center p-3 rounded-2xl bg-[#111A2E] border border-[#26344F] text-center shadow-sm">
            <div className="w-8 h-8 rounded-xl bg-[#10B981]/15 flex items-center justify-center text-[#10B981] mb-1.5 border border-[#10B981]/30">
              <CheckCircle2 className="h-4 w-4" />
            </div>
            <span className="font-code-lg text-2xl font-bold text-[#10B981] leading-none mb-1">
              {completedCount}
            </span>
            <span className="font-label-sm text-[11px] text-[#94A3B8] uppercase tracking-wider font-semibold">
              Completed
            </span>
          </div>
        </section>

        {/* Filter Pills Bar (Matching Stitch Scrollable Horizon) */}
        <div className="flex items-center justify-between gap-3 bg-[#111A2E] p-3 rounded-2xl border border-[#26344F]">
          <div className="flex items-center gap-2 overflow-x-auto pb-0.5">
            {[
              { label: "All", value: "", count: countLabel("") },
              { label: "Draft", value: "DRAFT", count: draftCount },
              { label: "Submitted", value: "SUBMITTED", count: submittedCount },
              { label: "Processing", value: "PROCESSING", count: processingCount },
              { label: "Completed", value: "COMPLETED", count: completedCount },
            ].map((tab) => (
              <button
                key={tab.label}
                onClick={() => setStatusFilter(tab.value)}
                className={`px-3.5 py-1.5 rounded-full font-label-md text-xs whitespace-nowrap flex items-center gap-1.5 font-bold transition-all ${
                  statusFilter === tab.value
                    ? "bg-[#06B6D4] text-[#003640] shadow-sm shadow-[#06B6D4]/20"
                    : "bg-[#17223A] text-[#94A3B8] hover:text-[#F1F5F9] border border-[#26344F]"
                }`}
              >
                <span>{tab.label}</span>
                <span
                  className={`min-w-4 h-4 px-1 rounded-full font-code-sm text-[10px] flex items-center justify-center ${
                    statusFilter === tab.value
                      ? "bg-[#003640]/30 text-[#003640]"
                      : "bg-[#232A39] text-[#94A3B8]"
                  }`}
                >
                  {tab.count}
                </span>
              </button>
            ))}
          </div>

          <button
            onClick={() => loadInspections()}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#17223A] border border-[#26344F] text-xs text-[#94A3B8] hover:text-[#F1F5F9] transition-colors shrink-0"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin text-[#06B6D4]" : ""}`} />
            <span className="hidden sm:inline">Refresh</span>
          </button>
        </div>

        {/* Inspections Cards Feed (Matching Stitch Field UI) */}
        {loading ? (
          <div className="flex flex-col gap-3">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="w-full bg-[#111A2E] border border-[#26344F] rounded-2xl p-5 animate-pulse flex flex-col gap-3"
              >
                <div className="flex justify-between items-center">
                  <div className="h-4 bg-[#232A39] rounded w-1/4"></div>
                  <div className="h-6 bg-[#232A39] rounded-full w-24"></div>
                </div>
                <div className="h-5 bg-[#232A39] rounded w-1/2"></div>
                <div className="h-4 bg-[#232A39] rounded w-3/4"></div>
              </div>
            ))}
          </div>
        ) : inspections.length === 0 ? (
          <EmptyState
            icon={ClipboardList}
            title="No Field Inspections Recorded"
            description="Field survey sessions and geotagged captures recorded from mobile survey devices will appear here."
          />
        ) : (
          <div className="flex flex-col gap-3.5">
            {inspections.map((insp) => (
              <article
                key={insp.id}
                className="flex flex-col p-5 rounded-2xl bg-[#111A2E] border border-[#26344F] hover:border-[#06B6D4]/50 transition-all shadow-sm group"
              >
                {/* Header row */}
                <div className="flex items-start justify-between gap-3 mb-2.5">
                  <div className="flex items-center gap-2 flex-wrap min-w-0">
                    <span className="px-2.5 py-0.5 rounded-lg bg-[#17223A] border border-[#26344F] text-[#4CD7F6] font-code-sm text-[11px] uppercase font-semibold">
                      {insp.segment_number ? `Seg #${insp.segment_number}` : `ID: ${insp.id.slice(0, 8)}`}
                    </span>
                    <span className="font-code-sm text-xs text-[#94A3B8]">
                      {new Date(insp.captured_at).toLocaleString()}
                    </span>
                  </div>
                  <StatusBadge status={insp.status} variant={insp.status === "COMPLETED" ? "success" : undefined} />
                </div>

                {/* Road Title */}
                <h3 className="font-headline-sm text-base text-[#F1F5F9] font-bold leading-snug mb-3">
                  <Link
                    href={`/inspections/${insp.id}`}
                    className="hover:text-[#4CD7F6] transition-colors"
                  >
                    {insp.road_name ? insp.road_name : "Unassigned road"}
                  </Link>
                </h3>

                {/* Telemetry and Media row */}
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pt-2 border-t border-[#26344F]/60">
                  <div className="flex flex-wrap items-center gap-4 text-xs text-[#94A3B8]">
                    <div className="flex items-center gap-1.5 font-code-sm">
                      <MapPin className="h-3.5 w-3.5 text-[#06B6D4]" />
                      <span>Inspector: {insp.inspector_name || "Field Agent"}</span>
                    </div>
                    <div className="flex items-center gap-1.5 font-code-sm">
                      <Camera className="h-3.5 w-3.5 text-[#10B981]" />
                      <span>
                        {insp.media_summary?.media_count || 0} Media Units (
                        {insp.media_summary?.image_count || 0} img,{" "}
                        {insp.media_summary?.video_count || 0} vid)
                      </span>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 self-end sm:self-auto">
                    {insp.status === "DRAFT" && (
                      <button
                        onClick={() => handleSubmitDraft(insp.id)}
                        className="h-9 px-3.5 rounded-xl bg-[#232A39] hover:bg-[#2E3544] text-[#F1F5F9] font-label-md text-xs font-semibold flex items-center gap-1.5 border border-[#3D494C] transition-all active:scale-95"
                      >
                        <Send className="h-3.5 w-3.5 text-[#06B6D4]" />
                        <span>Submit Inspection</span>
                      </button>
                    )}

                    {insp.status === "SUBMITTED" && (
                      <button
                        disabled={processingId === insp.id}
                        onClick={() => handleTriggerAI(insp.id)}
                        className="h-9 px-3.5 rounded-xl bg-[#06B6D4] hover:bg-[#4CD7F6] text-[#003640] font-label-md text-xs font-bold flex items-center gap-1.5 shadow-sm shadow-[#06B6D4]/20 transition-all active:scale-95 disabled:opacity-50"
                      >
                        <Cpu className="h-3.5 w-3.5" />
                        <span>{processingId === insp.id ? "Queuing..." : "Process AI"}</span>
                      </button>
                    )}

                    <Link
                      href={`/inspections/${insp.id}`}
                      className="h-9 px-3.5 rounded-xl bg-[#17223A] hover:bg-[#232A39] text-[#4CD7F6] font-label-md text-xs font-semibold flex items-center gap-1.5 border border-[#26344F] transition-all"
                    >
                      <Eye className="h-3.5 w-3.5" />
                      <span>Details</span>
                    </Link>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </AppShell>
  );
}
