"use client";

import React, { useEffect, useState } from "react";
import { AppShell } from "@/components/shell";
import { api } from "@/lib/api-client";
import { RecurrenceRecord, Road, SegmentHistoricalTimelineResponse } from "@/types/api";
import {
  Route,
  Search,
  ChevronRight,
  History,
  RotateCcw,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Layers,
  Sparkles,
  Calendar,
  Clock,
} from "lucide-react";

export default function RoadsPage() {
  const [activeTab, setActiveTab] = useState<"roads" | "recurrence">("roads");
  const [roads, setRoads] = useState<Road[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  // Recurrence State
  const [recurrences, setRecurrences] = useState<RecurrenceRecord[]>([]);
  const [recurrenceStatusFilter, setRecurrenceStatusFilter] = useState<string>("");
  const [recurrenceLoading, setRecurrenceLoading] = useState(false);

  // Timeline Modal State
  const [timelineSegmentId, setTimelineSegmentId] = useState<string | null>(null);
  const [timelineData, setTimelineData] = useState<SegmentHistoricalTimelineResponse | null>(null);
  const [timelineLoading, setTimelineLoading] = useState(false);

  // Recurrence Review Modal State
  const [reviewingRecurrence, setReviewingRecurrence] = useState<RecurrenceRecord | null>(null);
  const [reviewStatus, setReviewStatus] = useState<"CONFIRMED" | "DISMISSED">("CONFIRMED");
  const [reviewNotes, setReviewNotes] = useState("");
  const [submittingReview, setSubmittingReview] = useState(false);

  useEffect(() => {
    async function loadRoads() {
      try {
        const res = await api.roads.list({ search: search || undefined });
        if (res.data) {
          setRoads(res.data);
        }
      } catch (err) {
        console.error("Failed to load roads:", err);
      } finally {
        setLoading(false);
      }
    }

    loadRoads();
  }, [search]);

  useEffect(() => {
    if (activeTab === "recurrence") {
      loadRecurrences();
    }
  }, [activeTab, recurrenceStatusFilter]);

  const loadRecurrences = async () => {
    setRecurrenceLoading(true);
    try {
      const res = await api.recurrence.list({
        status: recurrenceStatusFilter || undefined,
        page_size: 50,
      });
      if (res.data) {
        setRecurrences(res.data);
      }
    } catch (err) {
      console.error("Failed to load recurrence records:", err);
    } finally {
      setRecurrenceLoading(false);
    }
  };

  const openTimeline = async (segmentId: string) => {
    setTimelineSegmentId(segmentId);
    setTimelineLoading(true);
    try {
      const res = await api.recurrence.getSegmentTimeline(segmentId);
      if (res.data) {
        setTimelineData(res.data);
      }
    } catch (err) {
      console.error("Failed to load segment timeline:", err);
    } finally {
      setTimelineLoading(false);
    }
  };

  const handleReviewSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reviewingRecurrence) return;
    setSubmittingReview(true);
    try {
      await api.recurrence.review(reviewingRecurrence.id, {
        status: reviewStatus,
        notes: reviewNotes.trim() || undefined,
      });
      setReviewingRecurrence(null);
      setReviewNotes("");
      await loadRecurrences();
    } catch (err: any) {
      alert(`Review submission failed: ${err?.message || "Unknown error"}`);
    } finally {
      setSubmittingReview(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "CONFIRMED":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-500/10 text-rose-400 border border-rose-500/30">
            CONFIRMED RECURRENCE
          </span>
        );
      case "DISMISSED":
      case "FALSE_POSITIVE":
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-500/10 text-slate-400 border border-slate-500/30">
            DISMISSED
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/30">
            POTENTIAL
          </span>
        );
    }
  };

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white">Road Network & Recurrence Intelligence</h1>
            <p className="text-xs text-slate-400 mt-1">
              Authoritative road inventory, spatial recurrence tracking, and complete lifecycle audit timelines
            </p>
          </div>

          {/* Tab Selector */}
          <div className="flex bg-slate-900 border border-slate-800 p-1 rounded-lg">
            <button
              onClick={() => setActiveTab("roads")}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors flex items-center gap-1.5 ${
                activeTab === "roads"
                  ? "bg-blue-600 text-white"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <Route className="h-3.5 w-3.5" />
              Road Inventory
            </button>
            <button
              onClick={() => setActiveTab("recurrence")}
              className={`px-3 py-1.5 rounded-md text-xs font-medium transition-colors flex items-center gap-1.5 ${
                activeTab === "recurrence"
                  ? "bg-purple-600 text-white"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Recurrence Tracking (Phase 13)
            </button>
          </div>
        </div>

        {activeTab === "roads" ? (
          <>
            {/* Filter bar */}
            <div className="flex items-center gap-4 bg-slate-900 p-3 rounded-lg border border-slate-800">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search roads by name, road code, or district..."
                  className="w-full pl-9 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-md text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-blue-500"
                />
              </div>
            </div>

            {/* Roads Table */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-950/60 border-b border-slate-800 text-slate-400">
                    <tr>
                      <th className="py-3 px-4 font-semibold">Road Name</th>
                      <th className="py-3 px-4 font-semibold">Road Code</th>
                      <th className="py-3 px-4 font-semibold">Classification</th>
                      <th className="py-3 px-4 font-semibold">Administrative Area</th>
                      <th className="py-3 px-4 font-semibold">Status</th>
                      <th className="py-3 px-4 text-right font-semibold">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-slate-300">
                    {loading ? (
                      <tr>
                        <td colSpan={6} className="py-8 text-center text-slate-500">
                          Loading road inventory...
                        </td>
                      </tr>
                    ) : roads.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="py-8 text-center text-slate-500">
                          No roads found matching criteria.
                        </td>
                      </tr>
                    ) : (
                      roads.map((road) => (
                        <tr key={road.id} className="hover:bg-slate-800/40 transition-colors">
                          <td className="py-3 px-4 font-medium text-white flex items-center gap-2">
                            <Route className="h-4 w-4 text-blue-400 shrink-0" />
                            <span>{road.name}</span>
                          </td>
                          <td className="py-3 px-4 font-mono text-[11px] text-slate-400">
                            {road.road_code || "—"}
                          </td>
                          <td className="py-3 px-4 text-slate-400">{road.road_type || "URBAN"}</td>
                          <td className="py-3 px-4 text-slate-400">{road.administrative_area || "—"}</td>
                          <td className="py-3 px-4">
                            <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-950 text-emerald-400 border border-emerald-800/50">
                              Active
                            </span>
                          </td>
                          <td className="py-3 px-4 text-right">
                            <button
                              onClick={() => {
                                // Default preview timeline if segment exists
                                api.roads.getSegments(road.id).then((res) => {
                                  if (res.data && res.data.length > 0) {
                                    openTimeline(res.data[0].id);
                                  } else {
                                    alert("No registered segments found for this road yet.");
                                  }
                                });
                              }}
                              className="inline-flex items-center text-xs font-semibold text-blue-400 hover:text-blue-300"
                            >
                              Timeline <ChevronRight className="h-3.5 w-3.5 ml-1" />
                            </button>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        ) : (
          /* Recurrence Tracking Tab (Phase 13) */
          <div className="space-y-4">
            {/* Filter controls */}
            <div className="flex items-center justify-between bg-slate-900 p-3 rounded-lg border border-slate-800 text-xs">
              <div className="flex items-center gap-2">
                <span className="text-slate-400 font-medium">Filter Status:</span>
                <select
                  value={recurrenceStatusFilter}
                  onChange={(e) => setRecurrenceStatusFilter(e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded px-2.5 py-1 text-white focus:outline-none focus:border-purple-500"
                >
                  <option value="">All Statuses</option>
                  <option value="POTENTIAL">Potential</option>
                  <option value="CONFIRMED">Confirmed</option>
                  <option value="DISMISSED">Dismissed</option>
                </select>
              </div>

              <div className="text-slate-400">
                Found <span className="text-white font-bold">{recurrences.length}</span> recorded recurrence pairs
              </div>
            </div>

            {/* Recurrence Cards */}
            <div className="space-y-3">
              {recurrenceLoading ? (
                <div className="py-12 text-center text-slate-500 text-xs">Loading recurrence intelligence...</div>
              ) : recurrences.length === 0 ? (
                <div className="py-12 text-center bg-slate-900 border border-slate-800 rounded-xl p-6 text-slate-400 text-xs">
                  <RotateCcw className="h-8 w-8 text-slate-600 mx-auto mb-2" />
                  <p className="font-semibold text-white">No Recurrences Detected</p>
                  <p className="text-slate-500 mt-1 max-w-sm mx-auto">
                    Repairs in this road network are holding without recurring damage at the same coordinates.
                  </p>
                </div>
              ) : (
                recurrences.map((rec) => (
                  <div
                    key={rec.id}
                    className="bg-slate-900/90 border border-slate-800 hover:border-slate-700 rounded-xl p-4 space-y-3 transition-colors text-xs"
                  >
                    <div className="flex items-start justify-between">
                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          {getStatusBadge(rec.status)}
                          <span className="text-[11px] text-slate-400 font-mono">
                            ID: {rec.id.slice(0, 8)}...
                          </span>
                        </div>
                        <h4 className="text-sm font-bold text-white pt-1">
                          {rec.segment_name || "Road Segment Defect"}
                        </h4>
                      </div>

                      {/* Recurrence Confidence Badge */}
                      {rec.recurrence_score !== undefined && rec.recurrence_score !== null && (
                        <div className="text-right">
                          <span className="text-[10px] text-slate-400 uppercase tracking-wider block">Recurrence Score</span>
                          <span className="text-sm font-bold text-purple-400">
                            {Math.round(rec.recurrence_score * 100)}%
                          </span>
                        </div>
                      )}
                    </div>

                    {/* Proximity Details */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 bg-slate-950/60 p-3 rounded-lg border border-slate-800/80 text-[11px]">
                      <div>
                        <span className="text-slate-500 block">Spatial Proximity</span>
                        <span className="font-semibold text-white">
                          ~{rec.spatial_distance_meters?.toFixed(1) || "0.0"} meters
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500 block">Time to Recurrence</span>
                        <span className="font-semibold text-amber-300">
                          {rec.temporal_distance_days} days after repair
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500 block">Historical Damage</span>
                        <span className="font-semibold text-slate-300">
                          {rec.historical_damage?.damage_type || "POTHOLE"} ({rec.historical_damage?.severity || "HIGH"})
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500 block">New Defect</span>
                        <span className="font-semibold text-slate-300">
                          {rec.new_damage?.damage_type || "POTHOLE"} ({rec.new_damage?.severity || "MEDIUM"})
                        </span>
                      </div>
                    </div>

                    {/* Review notes if present */}
                    {rec.review_notes && (
                      <p className="text-[11px] text-slate-400 italic bg-slate-950/40 p-2.5 rounded border border-slate-800">
                        Reviewer Note: &quot;{rec.review_notes}&quot;
                      </p>
                    )}

                    {/* Actions */}
                    <div className="flex items-center justify-end gap-2 pt-1 border-t border-slate-800">
                      {rec.road_segment_id && (
                        <button
                          type="button"
                          onClick={() => openTimeline(rec.road_segment_id!)}
                          className="text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 px-3 py-1.5 rounded-lg flex items-center gap-1.5 transition-colors"
                        >
                          <History className="h-3 w-3 text-blue-400" />
                          View Segment Timeline
                        </button>
                      )}
                      {rec.status === "POTENTIAL" && (
                        <button
                          type="button"
                          onClick={() => {
                            setReviewingRecurrence(rec);
                            setReviewStatus("CONFIRMED");
                            setReviewNotes("");
                          }}
                          className="text-xs bg-purple-600 hover:bg-purple-500 text-white px-3 py-1.5 rounded-lg font-medium transition-colors"
                        >
                          Review Decision
                        </button>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* Segment Lifecycle Timeline Modal (Phase 13 Core Requirement) */}
        {timelineSegmentId && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 w-full max-w-2xl max-h-[85vh] flex flex-col shadow-2xl space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="space-y-0.5">
                  <h3 className="text-sm font-bold text-white flex items-center gap-2">
                    <History className="h-4 w-4 text-purple-400" />
                    Historical Segment Lifecycle Audit
                  </h3>
                  <p className="text-[11px] text-slate-400">
                    Chronological lifecycle timeline: Damage → Maintenance → Repair → Verification → Recurrence
                  </p>
                </div>
                <button
                  onClick={() => {
                    setTimelineSegmentId(null);
                    setTimelineData(null);
                  }}
                  className="text-slate-400 hover:text-white"
                >
                  <XCircle className="h-5 w-5" />
                </button>
              </div>

              <div className="flex-1 overflow-y-auto pr-1">
                {timelineLoading ? (
                  <div className="py-12 text-center text-slate-500 text-xs">Reconstructing historical timeline...</div>
                ) : !timelineData || timelineData.events.length === 0 ? (
                  <p className="py-8 text-center text-slate-500 text-xs italic">
                    No historical events recorded for this segment yet.
                  </p>
                ) : (
                  <div className="relative pl-6 border-l-2 border-slate-800 ml-3 space-y-4">
                    {timelineData.events.map((evt, idx) => (
                      <div key={idx} className="relative space-y-1 text-xs">
                        {/* Event Dot */}
                        <div
                          className={`absolute -left-[31px] top-1 h-3.5 w-3.5 rounded-full border-2 border-slate-900 ${
                            evt.event_type === "RECURRENCE_DETECTED"
                              ? "bg-rose-500"
                              : evt.event_type === "REPAIR_VERIFIED"
                              ? "bg-emerald-500"
                              : evt.event_type === "MAINTENANCE_COMPLETED"
                              ? "bg-blue-500"
                              : evt.event_type === "MAINTENANCE_CREATED"
                              ? "bg-amber-500"
                              : "bg-indigo-500"
                          }`}
                        />

                        <div className="flex items-center justify-between text-[11px]">
                          <span className="font-bold text-white">{evt.title}</span>
                          <span className="text-slate-500 font-mono">
                            {new Date(evt.timestamp).toLocaleString()}
                          </span>
                        </div>

                        {evt.description && (
                          <p className="text-slate-400 bg-slate-950/70 p-2.5 rounded-lg border border-slate-800/80">
                            {evt.description}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div className="flex justify-end pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => {
                    setTimelineSegmentId(null);
                    setTimelineData(null);
                  }}
                  className="px-4 py-1.5 text-xs text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg"
                >
                  Close
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Recurrence Review Modal */}
        {reviewingRecurrence && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 w-full max-w-md shadow-xl space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h4 className="text-sm font-bold text-white flex items-center gap-2">
                  <RotateCcw className="h-4 w-4 text-purple-400" />
                  Review Recurrence Detection
                </h4>
                <button
                  onClick={() => setReviewingRecurrence(null)}
                  className="text-slate-400 hover:text-white"
                >
                  <XCircle className="h-4 w-4" />
                </button>
              </div>

              <form onSubmit={handleReviewSubmit} className="space-y-3.5 text-xs">
                <div>
                  <label className="block text-slate-300 font-medium mb-1">Decision</label>
                  <select
                    value={reviewStatus}
                    onChange={(e) => setReviewStatus(e.target.value as any)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-white focus:outline-none focus:border-purple-500"
                  >
                    <option value="CONFIRMED">Confirm Recurrence (Pothole re-formed at same site)</option>
                    <option value="DISMISSED">Dismiss (Unrelated nearby defect)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-300 font-medium mb-1">Audit Justification Notes</label>
                  <textarea
                    rows={3}
                    value={reviewNotes}
                    onChange={(e) => setReviewNotes(e.target.value)}
                    placeholder="Document root cause or contractor rework instructions..."
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg p-2.5 text-white focus:outline-none focus:border-purple-500"
                  />
                </div>

                <div className="flex items-center justify-end gap-2 pt-2 border-t border-slate-800">
                  <button
                    type="button"
                    onClick={() => setReviewingRecurrence(null)}
                    className="px-3 py-1.5 text-slate-400 hover:text-white"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submittingReview}
                    className="bg-purple-600 hover:bg-purple-500 text-white px-4 py-2 rounded-lg font-semibold transition-colors"
                  >
                    {submittingReview ? "Submitting..." : "Save Review Decision"}
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
