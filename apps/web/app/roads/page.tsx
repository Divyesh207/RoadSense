"use client";

import Link from "next/link";
import React, { useEffect, useState } from "react";
import { AppShell } from "@/components/shell";
import { StatusBadge } from "@/components/status-badge";
import { EmptyState } from "@/components/empty-state";
import { api } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import { hasPermission } from "@/lib/permissions";
import { RoadFormModal } from "@/components/roads/road-form-modal";
import { SegmentFormModal } from "@/components/roads/segment-form-modal";
import { RecurrenceRecord, Road, RoadSegment, SegmentHistoricalTimelineResponse } from "@/types/api";
import {
  ChevronDown,
  GitBranch,
  Plus,
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
  MapPin,
  RefreshCw,
} from "lucide-react";

export default function RoadsPage() {
  const [activeTab, setActiveTab] = useState<"roads" | "recurrence">("roads");
  const [roads, setRoads] = useState<Road[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [reloadTick, setReloadTick] = useState(0);

  // Road / segment administration (offered only to roles the API allows to create them)
  const { user } = useAuth();
  const canAddRoad = hasPermission(user, "roads:create");
  const canAddSegment = hasPermission(user, "road_segments:create");
  const [showAddRoad, setShowAddRoad] = useState(false);
  const [addSegmentFor, setAddSegmentFor] = useState<string | null>(null); // "" = let the admin pick the road
  const [notice, setNotice] = useState<string | null>(null);

  // Road -> segments tree: segments are loaded when a road row is expanded.
  const [expanded, setExpanded] = useState<Record<string, RoadSegment[] | "loading" | "error">>({});

  const loadSegmentsFor = async (roadId: string) => {
    setExpanded((prev) => ({ ...prev, [roadId]: "loading" }));
    try {
      const res = await api.roads.getSegments(roadId);
      const list = [...(res.data ?? [])].sort((a, b) => a.segment_number - b.segment_number);
      setExpanded((prev) => ({ ...prev, [roadId]: list }));
    } catch {
      setExpanded((prev) => ({ ...prev, [roadId]: "error" }));
    }
  };

  const toggleRoad = (roadId: string) => {
    if (expanded[roadId] !== undefined) {
      setExpanded((prev) => {
        const next = { ...prev };
        delete next[roadId];
        return next;
      });
    } else {
      loadSegmentsFor(roadId);
    }
  };

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
      setLoading(true);
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
  }, [search, reloadTick]);

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

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="font-code-sm text-[11px] text-[#06B6D4] uppercase tracking-wider font-semibold">
                Road network
              </span>
            </div>
            <h1 className="font-headline-sm text-2xl font-bold tracking-tight text-[#F1F5F9]">
              Road Network & Recurrence Intelligence
            </h1>
            <p className="font-body-sm text-xs text-[#94A3B8] mt-1">
              Road inventory, recurrence review and segment lifecycle timelines.
            </p>
          </div>

          {/* Tab Selector */}
          <div className="flex bg-[#111A2E] border border-[#26344F] p-1 rounded-xl">
            <button
              onClick={() => setActiveTab("roads")}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
                activeTab === "roads"
                  ? "bg-[#06B6D4] text-[#003640] shadow-sm shadow-[#06B6D4]/20"
                  : "text-[#94A3B8] hover:text-[#F1F5F9]"
              }`}
            >
              <Route className="h-3.5 w-3.5" />
              Road Inventory
            </button>
            <button
              onClick={() => setActiveTab("recurrence")}
              className={`px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
                activeTab === "recurrence"
                  ? "bg-[#06B6D4] text-[#003640] shadow-sm shadow-[#06B6D4]/20"
                  : "text-[#94A3B8] hover:text-[#F1F5F9]"
              }`}
            >
              <RotateCcw className="h-3.5 w-3.5" />
              Recurrence Tracking
            </button>
          </div>
        </div>

        {(canAddRoad || canAddSegment) && activeTab === "roads" && (
          <div className="flex flex-wrap items-center gap-3">
            {canAddRoad && (
              <button
                onClick={() => setShowAddRoad(true)}
                className="inline-flex items-center gap-1.5 h-10 px-4 rounded-xl bg-[#06B6D4] hover:bg-[#4CD7F6] text-[#003640] text-xs font-bold"
              >
                <Plus className="h-4 w-4" /> Add Road
              </button>
            )}
            {canAddSegment && (
              <button
                onClick={() => setAddSegmentFor("")}
                disabled={roads.length === 0}
                className="inline-flex items-center gap-1.5 h-10 px-4 rounded-xl bg-[#17223A] border border-[#06B6D4]/40 text-[#4CD7F6] text-xs font-bold hover:bg-[#232A39] disabled:opacity-40"
              >
                <Plus className="h-4 w-4" /> Add Segment
              </button>
            )}
            <span className="text-[11px] text-[#64748B]">
              New roads and segments are available to field inspectors as soon as they are saved.
            </span>
          </div>
        )}

        {notice && (
          <p className="text-xs px-3 py-2 rounded-xl border border-[#10B981]/30 bg-[#10B981]/10 text-[#10B981]">{notice}</p>
        )}

        {activeTab === "roads" ? (
          <>
            {/* Filter & Search Bar */}
            <div className="flex items-center gap-4 bg-[#111A2E] p-3 rounded-2xl border border-[#26344F]">
              <div className="relative flex-1">
                <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-[#869397]" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search roads by name, road code, or district..."
                  className="w-full pl-10 pr-4 py-2 bg-[#151B2A] border border-[#26344F] rounded-xl font-body-sm text-xs text-[#F1F5F9] placeholder:text-[#64748B] focus:outline-none focus:border-[#06B6D4]"
                />
              </div>
            </div>

            {/* Roads Table */}
            <div className="bg-[#111A2E] border border-[#26344F] rounded-2xl overflow-hidden shadow-sm">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-[#0C1321] border-b border-[#26344F] text-[#94A3B8]">
                    <tr>
                      <th className="py-3 px-4 font-semibold">Road Name</th>
                      <th className="py-3 px-4 font-semibold">Road Code</th>
                      <th className="py-3 px-4 font-semibold">Classification</th>
                      <th className="py-3 px-4 font-semibold">Administrative Area</th>
                      <th className="py-3 px-4 font-semibold">Status</th>
                      <th className="py-3 px-4 text-right font-semibold">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#26344F]/50 text-[#DCE2F6]">
                    {loading ? (
                      <tr>
                        <td colSpan={6} className="py-12 text-center text-[#94A3B8]">
                          <div className="flex items-center justify-center gap-2">
                            <RefreshCw className="h-4 w-4 animate-spin text-[#06B6D4]" />
                            <span>Loading road network database...</span>
                          </div>
                        </td>
                      </tr>
                    ) : roads.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="py-12 text-center text-[#94A3B8]">
                          No roads found.
                        </td>
                      </tr>
                    ) : (
                      roads.map((road) => {
                        const segs = expanded[road.id];
                        return (
                        <React.Fragment key={road.id}>
                        <tr className="hover:bg-[#17223A]/50 transition-colors">
                          <td className="py-3 px-4 font-bold text-white">
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => toggleRoad(road.id)}
                                aria-label={segs !== undefined ? "Hide segments" : "Show segments"}
                                className="p-1 rounded-md text-[#94A3B8] hover:text-[#F1F5F9] hover:bg-[#232A39]"
                              >
                                {segs !== undefined ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                              </button>
                              <Route className="h-4 w-4 text-[#06B6D4] shrink-0" />
                              <Link href={`/roads/${road.id}`} className="hover:text-[#4CD7F6] transition-colors">
                                {road.name}
                              </Link>
                              <span className="font-code-sm text-[10px] font-normal text-[#94A3B8] px-1.5 py-0.5 rounded bg-[#17223A] border border-[#26344F]">
                                {road.segment_count ?? 0} {road.segment_count === 1 ? "segment" : "segments"}
                              </span>
                            </div>
                          </td>
                          <td className="py-3 px-4 font-code-sm text-[#94A3B8]">
                            {road.road_code || "—"}
                          </td>
                          <td className="py-3 px-4 text-[#ADC6FF]">{road.road_type || "—"}</td>
                          <td className="py-3 px-4 text-[#94A3B8]">
                            {road.administrative_area || "—"}
                          </td>
                          <td className="py-3 px-4">
                            <StatusBadge
                              status={road.is_active ? "Active" : "Inactive"}
                              variant={road.is_active ? "success" : "neutral"}
                              size="sm"
                            />
                          </td>
                          <td className="py-3 px-4 text-right">
                            <button
                              onClick={() => {
                                api.roads.getSegments(road.id).then((res) => {
                                  if (res.data && res.data.length > 0) {
                                    openTimeline(res.data[0].id);
                                  } else {
                                    alert("No registered segments found for this road yet.");
                                  }
                                });
                              }}
                              className="inline-flex items-center text-xs font-bold text-[#06B6D4] hover:text-[#4CD7F6]"
                            >
                              Timeline <ChevronRight className="h-3.5 w-3.5 ml-0.5" />
                            </button>
                          </td>
                        </tr>
                        {segs !== undefined && (
                          <tr className="bg-[#0C1321]/60">
                            <td colSpan={6} className="px-4 py-3">
                              <div className="ml-7 border-l-2 border-[#26344F] pl-4 space-y-1.5">
                                {segs === "loading" && <p className="text-xs text-[#94A3B8]">Loading segments...</p>}
                                {segs === "error" && <p className="text-xs text-[#F59E0B]">Could not load segments.</p>}
                                {Array.isArray(segs) && segs.length === 0 && (
                                  <p className="text-xs text-[#94A3B8]">This road has no segments yet.</p>
                                )}
                                {Array.isArray(segs) &&
                                  segs.map((s) => (
                                    <div key={s.id} className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
                                      <GitBranch className="h-3.5 w-3.5 text-[#64748B]" />
                                      <span className="font-code-sm font-semibold text-[#F1F5F9]">
                                        Segment {String(s.segment_number).padStart(2, "0")}
                                      </span>
                                      {s.name && <span className="text-[#DCE2F6]">{s.name}</span>}
                                      <span className="font-code-sm text-[#94A3B8]">
                                        {s.length_meters != null ? `${s.length_meters} m` : "length not set"}
                                      </span>
                                      <span className={`font-code-sm text-[10px] ${s.geometry ? "text-[#10B981]" : "text-[#F59E0B]"}`}>
                                        {s.geometry ? "mapped" : "no geometry"}
                                      </span>
                                      <button
                                        onClick={() => openTimeline(s.id)}
                                        className="text-[11px] font-semibold text-[#06B6D4] hover:underline"
                                      >
                                        Timeline
                                      </button>
                                    </div>
                                  ))}
                                {canAddSegment && (
                                  <button
                                    onClick={() => setAddSegmentFor(road.id)}
                                    className="inline-flex items-center gap-1 mt-1 text-[11px] font-bold text-[#4CD7F6] hover:underline"
                                  >
                                    <Plus className="h-3 w-3" /> Add segment to this road
                                  </button>
                                )}
                              </div>
                            </td>
                          </tr>
                        )}
                        </React.Fragment>
                        );
                      })
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </>
        ) : (
          /* Recurrence Tracking Tab */
          <div className="space-y-4">
            <div className="flex items-center gap-3 bg-[#111A2E] p-3 rounded-2xl border border-[#26344F]">
              <span className="font-label-sm text-xs text-[#94A3B8] font-medium">Status:</span>
              <select
                value={recurrenceStatusFilter}
                onChange={(e) => setRecurrenceStatusFilter(e.target.value)}
                className="bg-[#151B2A] border border-[#26344F] text-xs text-[#F1F5F9] rounded-xl px-3 py-1.5 focus:outline-none focus:border-[#06B6D4]"
              >
                <option value="">All Recurrence Statuses</option>
                <option value="POTENTIAL">Potential</option>
                <option value="CONFIRMED">Confirmed Recurrence</option>
                <option value="DISMISSED">Dismissed</option>
              </select>
            </div>

            {recurrenceLoading ? (
              <div className="p-12 text-center text-[#94A3B8] bg-[#111A2E] border border-[#26344F] rounded-2xl">
                Loading recurrence events...
              </div>
            ) : recurrences.length === 0 ? (
              <EmptyState
                icon={RotateCcw}
                title="No Recurrences Detected"
                description="No recurrence records match the selected status."
              />
            ) : (
              <div className="bg-[#111A2E] border border-[#26344F] rounded-2xl overflow-hidden shadow-sm">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-[#0C1321] border-b border-[#26344F] text-[#94A3B8]">
                      <tr>
                        <th className="py-3 px-4 font-semibold">Recurrence</th>
                        <th className="py-3 px-4 font-semibold">Status</th>
                        <th className="py-3 px-4 font-semibold">Historical Damage</th>
                        <th className="py-3 px-4 font-semibold">New Defect</th>
                        <th className="py-3 px-4 font-semibold">Spatial Proximity</th>
                        <th className="py-3 px-4 font-semibold">Time to Recurrence</th>
                        <th className="py-3 px-4 font-semibold">Recurrence Score</th>
                        <th className="py-3 px-4 text-right font-semibold">Action</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-[#26344F]/50 text-[#DCE2F6]">
                      {recurrences.map((rec) => (
                        <tr key={rec.id} className="hover:bg-[#17223A]/50 transition-colors">
                          <td className="py-3 px-4 align-top">
                            <span className="font-bold text-white block">{rec.segment_name || "Road Segment Defect"}</span>
                            <span className="font-code-sm text-[11px] text-[#06B6D4]">ID: {rec.id.slice(0, 8)}</span>
                            {rec.review_notes && (
                              <span className="block text-[11px] text-[#94A3B8] mt-1">
                                Reviewer note: &quot;{rec.review_notes}&quot;
                              </span>
                            )}
                          </td>
                          <td className="py-3 px-4 align-top">
                            <StatusBadge status={rec.status} variant={rec.status === "CONFIRMED" ? "error" : undefined} size="sm" />
                          </td>
                          <td className="py-3 px-4 align-top text-[#DCE2F6]">
                            {rec.historical_damage
                              ? `${rec.historical_damage.damage_type} (${rec.historical_damage.severity})`
                              : "—"}
                          </td>
                          <td className="py-3 px-4 align-top text-[#DCE2F6]">
                            {rec.new_damage ? `${rec.new_damage.damage_type} (${rec.new_damage.severity})` : "—"}
                          </td>
                          <td className="py-3 px-4 align-top font-code-sm text-[#94A3B8]">
                            {rec.spatial_distance_meters != null ? `${rec.spatial_distance_meters.toFixed(1)} m` : "—"}
                          </td>
                          <td className="py-3 px-4 align-top font-code-sm text-[#94A3B8]">
                            {rec.temporal_distance_days != null ? `${rec.temporal_distance_days} days after repair` : "—"}
                          </td>
                          <td className="py-3 px-4 align-top font-code-sm text-[#DCE2F6]">
                            {rec.recurrence_score != null ? (
                              <>
                                {Math.round(rec.recurrence_score * 100)}%
                                <span className="block text-[10px] text-[#64748B] font-sans">rule-based score, not a probability</span>
                              </>
                            ) : (
                              "—"
                            )}
                          </td>
                          <td className="py-3 px-4 align-top text-right space-x-2 whitespace-nowrap">
                            {rec.road_segment_id && (
                              <button
                                type="button"
                                onClick={() => openTimeline(rec.road_segment_id!)}
                                className="h-8 px-3 rounded-lg bg-[#17223A] border border-[#26344F] text-[#4CD7F6] font-label-md text-xs font-semibold hover:bg-[#232A39]"
                              >
                                View Segment Timeline
                              </button>
                            )}
                            {rec.status === "POTENTIAL" && (
                            <button
                              onClick={() => {
                                setReviewingRecurrence(rec);
                                setReviewStatus("CONFIRMED");
                                setReviewNotes("");
                              }}
                              className="h-8 px-3 rounded-lg bg-[#06B6D4] hover:bg-[#4CD7F6] text-[#003640] font-label-md text-xs font-bold transition-all active:scale-95"
                            >
                              Review Decision
                            </button>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        )}

        {showAddRoad && (
          <RoadFormModal
            onClose={() => setShowAddRoad(false)}
            onCreated={(road) => {
              setShowAddRoad(false);
              setNotice(`Road "${road.name}" created. Add its segments next.`);
              setReloadTick((t) => t + 1);
            }}
          />
        )}

        {addSegmentFor !== null && (
          <SegmentFormModal
            roads={roads}
            presetRoadId={addSegmentFor || undefined}
            onClose={() => setAddSegmentFor(null)}
            onCreated={(segment, roadId) => {
              setAddSegmentFor(null);
              const roadName = roads.find((r) => r.id === roadId)?.name ?? "the road";
              setNotice(`Segment ${segment.segment_number} added to ${roadName}.`);
              setReloadTick((t) => t + 1);
              loadSegmentsFor(roadId);
            }}
          />
        )}

        {/* Timeline Modal */}
        {timelineSegmentId && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
            <div className="bg-[#111A2E] border border-[#26344F] rounded-2xl max-w-2xl w-full p-6 space-y-4 shadow-2xl max-h-[85vh] flex flex-col">
              <div className="flex items-center justify-between border-b border-[#26344F] pb-3">
                <div className="flex items-center gap-2">
                  <History className="h-5 w-5 text-[#06B6D4]" />
                  <h3 className="font-headline-sm text-base font-bold text-[#F1F5F9]">
                    Historical Segment Lifecycle Audit
                  </h3>
                </div>
                <button
                  onClick={() => {
                    setTimelineSegmentId(null);
                    setTimelineData(null);
                  }}
                  className="text-[#94A3B8] hover:text-[#F1F5F9] text-sm p-1"
                >
                  ✕
                </button>
              </div>

              <div className="flex-1 overflow-y-auto space-y-3 pr-1">
                {timelineLoading ? (
                  <p className="py-12 text-center text-xs text-[#94A3B8]">
                    Reconstructing historical timeline...
                  </p>
                ) : !timelineData || timelineData.events.length === 0 ? (
                  <p className="py-12 text-center text-xs text-[#94A3B8]">
                    No historical events recorded for this segment yet.
                  </p>
                ) : (
                  <div className="relative pl-6 border-l-2 border-[#26344F] space-y-4 my-2">
                    {timelineData.events.map((evt, idx) => (
                      <div key={idx} className="relative">
                        <div
                          className={`absolute -left-[31px] top-1 w-3.5 h-3.5 rounded-full border-2 border-[#111A2E] ${
                            evt.event_type === "RECURRENCE_DETECTED"
                              ? "bg-[#EF4444]"
                              : evt.event_type === "REPAIR_VERIFIED"
                              ? "bg-[#10B981]"
                              : evt.event_type === "MAINTENANCE_COMPLETED"
                              ? "bg-[#3B82F6]"
                              : evt.event_type === "MAINTENANCE_CREATED"
                              ? "bg-[#F59E0B]"
                              : "bg-[#06B6D4]"
                          }`}
                        />
                        <div className="bg-[#151B2A] border border-[#26344F] p-3 rounded-xl">
                          <div className="flex items-center justify-between">
                            <span className="font-label-md text-xs font-bold text-[#F1F5F9]">
                              {evt.title}
                            </span>
                            <span className="font-code-sm text-[11px] text-[#94A3B8]">
                              {new Date(evt.timestamp).toLocaleString()}
                            </span>
                          </div>
                          {evt.description && <p className="text-xs text-[#94A3B8] mt-1">{evt.description}</p>}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Recurrence Review Modal */}
        {reviewingRecurrence && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
            <div className="bg-[#111A2E] border border-[#26344F] rounded-2xl max-w-md w-full p-6 space-y-4 shadow-2xl">
              <div className="flex items-center justify-between border-b border-[#26344F] pb-3">
                <div className="flex items-center gap-2">
                  <RotateCcw className="h-5 w-5 text-[#06B6D4]" />
                  <h3 className="font-headline-sm text-base font-bold text-[#F1F5F9]">
                    Review Recurrence Match
                  </h3>
                </div>
                <button
                  onClick={() => setReviewingRecurrence(null)}
                  className="text-[#94A3B8] hover:text-[#F1F5F9] text-sm p-1"
                >
                  ✕
                </button>
              </div>

              <form onSubmit={handleReviewSubmit} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="font-label-sm text-xs text-[#94A3B8] font-semibold">
                    Decision
                  </label>
                  <div className="grid grid-cols-2 gap-3">
                    <button
                      type="button"
                      onClick={() => setReviewStatus("CONFIRMED")}
                      className={`h-10 rounded-xl font-label-md text-xs font-bold border transition-all ${
                        reviewStatus === "CONFIRMED"
                          ? "bg-[#10B981] text-[#003824] border-[#10B981]"
                          : "bg-[#17223A] text-[#94A3B8] border-[#26344F]"
                      }`}
                    >
                      Confirm Recurrence (Pothole re-formed at same site)
                    </button>
                    <button
                      type="button"
                      onClick={() => setReviewStatus("DISMISSED")}
                      className={`h-10 rounded-xl font-label-md text-xs font-bold border transition-all ${
                        reviewStatus === "DISMISSED"
                          ? "bg-[#EF4444] text-white border-[#EF4444]"
                          : "bg-[#17223A] text-[#94A3B8] border-[#26344F]"
                      }`}
                    >
                      Dismiss (Unrelated nearby defect)
                    </button>
                  </div>
                </div>

                <div className="space-y-1.5">
                  <label className="font-label-sm text-xs text-[#94A3B8] font-semibold">
                    Audit Justification Notes
                  </label>
                  <textarea
                    rows={3}
                    value={reviewNotes}
                    onChange={(e) => setReviewNotes(e.target.value)}
                    placeholder="Document root cause or contractor rework instructions..."
                    className="w-full bg-[#151B2A] border border-[#26344F] rounded-xl p-3 text-xs text-[#F1F5F9] placeholder:text-[#64748B] focus:outline-none focus:border-[#06B6D4]"
                  />
                </div>

                <div className="flex items-center justify-end gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setReviewingRecurrence(null)}
                    className="h-10 px-4 rounded-xl bg-[#17223A] border border-[#26344F] text-xs font-semibold text-[#94A3B8]"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={submittingReview}
                    className="h-10 px-4 rounded-xl bg-[#06B6D4] hover:bg-[#4CD7F6] text-[#003640] text-xs font-bold transition-all disabled:opacity-50"
                  >
                    {submittingReview ? "Submitting..." : "Save Determination"}
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
