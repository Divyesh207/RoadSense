"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/shell";
import { StatusBadge } from "@/components/status-badge";
import { EmptyState } from "@/components/empty-state";
import { api } from "@/lib/api-client";
import {
  MaintenanceJob,
  MaintenanceStatusHistory,
  MaintenanceDamageLink,
  RepairEvidence,
  RepairVerification,
  Road,
} from "@/types/api";
import {
  Wrench,
  CheckCircle,
  Clock,
  AlertCircle,
  Filter,
  Plus,
  ArrowRight,
  XCircle,
  ChevronRight,
  Kanban,
  List,
  Calendar,
  Layers,
  MapPin,
  TrendingUp,
  Check,
  RefreshCw,
} from "lucide-react";

const STATUS_COLUMNS = [
  { id: "OPEN", label: "Open", color: "border-[#F59E0B]/30 bg-[#F59E0B]/10 text-[#F59E0B]" },
  { id: "ASSIGNED", label: "Assigned", color: "border-[#3B82F6]/30 bg-[#3B82F6]/10 text-[#ADC6FF]" },
  { id: "IN_PROGRESS", label: "In Progress", color: "border-[#06B6D4]/30 bg-[#06B6D4]/10 text-[#4CD7F6]" },
  { id: "COMPLETED", label: "Completed", color: "border-[#10B981]/30 bg-[#10B981]/10 text-[#10B981]" },
  { id: "VERIFICATION_PENDING", label: "Verification Pending", color: "border-[#A78BFA]/30 bg-[#A78BFA]/10 text-[#A78BFA]" },
  { id: "VERIFIED", label: "Verified", color: "border-[#10B981]/40 bg-[#10B981]/20 text-[#10B981]" },
];

const ALLOWED_TRANSITIONS: Record<string, string[]> = {
  OPEN: ["ASSIGNED", "CANCELLED"],
  ASSIGNED: ["IN_PROGRESS", "OPEN", "CANCELLED"],
  IN_PROGRESS: ["COMPLETED", "CANCELLED"],
  COMPLETED: ["VERIFICATION_PENDING", "IN_PROGRESS"],
  VERIFICATION_PENDING: ["VERIFIED", "REJECTED"],
  REJECTED: ["IN_PROGRESS", "CANCELLED"],
  VERIFIED: [],
  CANCELLED: [],
};

export default function MaintenancePage() {
  const [jobs, setJobs] = useState<MaintenanceJob[]>([]);
  const [roads, setRoads] = useState<Road[]>([]);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<"kanban" | "table">("kanban");
  const [priorityFilter, setPriorityFilter] = useState<string>("");
  const [statusFilter, setStatusFilter] = useState<string>("");

  // Create Job Modal
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [createForm, setCreateForm] = useState({
    title: "",
    description: "",
    priority: "MEDIUM",
    road_id: "",
    due_at: "",
  });
  const [creating, setCreating] = useState(false);

  // Selected Job Details Drawer
  const [selectedJob, setSelectedJob] = useState<MaintenanceJob | null>(null);
  const [jobHistory, setJobHistory] = useState<MaintenanceStatusHistory[]>([]);
  const [jobDamages, setJobDamages] = useState<MaintenanceDamageLink[]>([]);
  const [jobEvidence, setJobEvidence] = useState<RepairEvidence[]>([]);
  const [jobVerifications, setJobVerifications] = useState<RepairVerification[]>([]);
  const [detailsLoading, setDetailsLoading] = useState(false);

  // Transition Status Modal
  const [transitionTarget, setTransitionTarget] = useState<string | null>(null);
  const [transitionNotes, setTransitionNotes] = useState("");
  const [transitioning, setTransitioning] = useState(false);

  const loadData = async () => {
    setLoading(true);
    try {
      const [jobsRes, roadsRes] = await Promise.all([
        api.maintenance.list({
          priority: priorityFilter || undefined,
          status: statusFilter || undefined,
          page_size: 100,
        }),
        api.roads.list({ page_size: 100 }),
      ]);
      if (jobsRes.data) setJobs(jobsRes.data);
      if (roadsRes.data) setRoads(roadsRes.data);
    } catch (err) {
      console.error("Failed to load maintenance data:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [priorityFilter, statusFilter]);

  const openJobDetail = async (job: MaintenanceJob) => {
    setSelectedJob(job);
    setDetailsLoading(true);
    try {
      const [histRes, dmgRes, evRes, verRes] = await Promise.all([
        api.maintenance.getHistory(job.id),
        api.maintenance.getDamages(job.id),
        api.repair.listEvidence(job.id),
        api.repair.listVerifications(job.id),
      ]);
      if (histRes.data) setJobHistory(histRes.data);
      if (dmgRes.data) setJobDamages(dmgRes.data);
      if (evRes.data) setJobEvidence(evRes.data);
      if (verRes.data) setJobVerifications(verRes.data);
    } catch (err) {
      console.error("Failed to load job details:", err);
    } finally {
      setDetailsLoading(false);
    }
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createForm.title.trim()) return;
    setCreating(true);
    try {
      await api.maintenance.create({
        title: createForm.title.trim(),
        description: createForm.description.trim() || undefined,
        priority: createForm.priority,
        road_id: createForm.road_id || undefined,
        due_at: createForm.due_at ? new Date(createForm.due_at).toISOString() : undefined,
      });
      setIsCreateOpen(false);
      setCreateForm({
        title: "",
        description: "",
        priority: "MEDIUM",
        road_id: "",
        due_at: "",
      });
      await loadData();
    } catch (err: any) {
      alert(`Failed to create maintenance job: ${err?.message || "Unknown error"}`);
    } finally {
      setCreating(false);
    }
  };

  const handleTransitionSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedJob || !transitionTarget) return;
    setTransitioning(true);
    try {
      const res = await api.maintenance.transitionStatus(selectedJob.id, {
        status: transitionTarget,
        notes: transitionNotes.trim() || undefined,
      });
      if (res.data) {
        setSelectedJob(res.data);
      }
      setTransitionTarget(null);
      setTransitionNotes("");
      await Promise.all([
        loadData(),
        api.maintenance.getHistory(selectedJob.id).then((r) => {
          if (r.data) setJobHistory(r.data);
        }),
      ]);
    } catch (err: any) {
      alert(`Status transition failed: ${err?.message || "Unknown error"}`);
    } finally {
      setTransitioning(false);
    }
  };

  // KPIs
  const counts = {
    total: jobs.length,
    open: jobs.filter((j) => j.status === "OPEN" || j.status === "ASSIGNED").length,
    inProgress: jobs.filter((j) => j.status === "IN_PROGRESS").length,
    verification: jobs.filter((j) => j.status === "VERIFICATION_PENDING").length,
    verified: jobs.filter((j) => j.status === "VERIFIED").length,
  };

  return (
    <AppShell>
      <div className="space-y-6 max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="font-code-sm text-[11px] text-[#06B6D4] uppercase tracking-wider font-semibold">
                Maintenance jobs
              </span>
            </div>
            <h1 className="font-headline-sm text-2xl font-bold tracking-tight text-[#F1F5F9] flex items-center gap-2.5">
              Maintenance Operations
            </h1>
            <p className="font-body-sm text-xs text-[#94A3B8] mt-1">
              Operational maintenance workflow, contractor assignments, and repair tracking.
            </p>
          </div>

          <div className="flex items-center gap-3">
            {/* View Mode Toggle */}
            <div className="flex rounded-xl bg-[#111A2E] border border-[#26344F] p-1">
              <button
                onClick={() => setViewMode("kanban")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  viewMode === "kanban"
                    ? "bg-[#06B6D4] text-[#003640] shadow-sm shadow-[#06B6D4]/20"
                    : "text-[#94A3B8] hover:text-[#F1F5F9]"
                }`}
              >
                <Kanban className="h-3.5 w-3.5" />
                Board
              </button>
              <button
                onClick={() => setViewMode("table")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  viewMode === "table"
                    ? "bg-[#06B6D4] text-[#003640] shadow-sm shadow-[#06B6D4]/20"
                    : "text-[#94A3B8] hover:text-[#F1F5F9]"
                }`}
              >
                <List className="h-3.5 w-3.5" />
                Table
              </button>
            </div>

            <button
              onClick={() => setIsCreateOpen(true)}
              className="flex items-center gap-2 bg-[#06B6D4] hover:bg-[#4CD7F6] text-[#003640] px-4 py-2 rounded-xl text-xs font-bold transition-all shadow-md shadow-[#06B6D4]/20 active:scale-95"
            >
              <Plus className="h-4 w-4" />
              <span>Create Job</span>
            </button>
          </div>
        </div>

        {/* 5-Column Bento KPI Strip */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <div className="bg-[#111A2E] border border-[#26344F] rounded-2xl p-4">
            <span className="font-label-sm text-[11px] text-[#94A3B8] uppercase tracking-wider">
              Total Jobs
            </span>
            <p className="font-code-lg text-2xl font-bold text-[#F1F5F9] mt-2">{counts.total}</p>
          </div>
          <div className="bg-[#111A2E] border border-[#26344F] rounded-2xl p-4">
            <span className="font-label-sm text-[11px] text-[#F59E0B] uppercase tracking-wider">
              Open / Assigned
            </span>
            <p className="font-code-lg text-2xl font-bold text-[#F59E0B] mt-2">{counts.open}</p>
          </div>
          <div className="bg-[#111A2E] border border-[#26344F] rounded-2xl p-4">
            <span className="font-label-sm text-[11px] text-[#06B6D4] uppercase tracking-wider">
              In Progress
            </span>
            <p className="font-code-lg text-2xl font-bold text-[#4CD7F6] mt-2">{counts.inProgress}</p>
          </div>
          <div className="bg-[#111A2E] border border-[#26344F] rounded-2xl p-4">
            <span className="font-label-sm text-[11px] text-[#ADC6FF] uppercase tracking-wider">
              Awaiting Verification
            </span>
            <p className="font-code-lg text-2xl font-bold text-[#ADC6FF] mt-2">{counts.verification}</p>
          </div>
          <div className="bg-[#111A2E] border border-[#26344F] rounded-2xl p-4">
            <span className="font-label-sm text-[11px] text-[#10B981] uppercase tracking-wider">
              Verified Repaired
            </span>
            <p className="font-code-lg text-2xl font-bold text-[#10B981] mt-2">{counts.verified}</p>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center justify-between gap-3 bg-[#111A2E] p-3 rounded-2xl border border-[#26344F]">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              <span className="font-label-sm text-xs text-[#94A3B8]">Priority:</span>
              <select
                value={priorityFilter}
                onChange={(e) => setPriorityFilter(e.target.value)}
                className="bg-[#151B2A] border border-[#26344F] text-[#F1F5F9] text-xs rounded-xl px-3 py-1.5 focus:outline-none focus:border-[#06B6D4]"
              >
                <option value="">All Priorities</option>
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <span className="font-label-sm text-xs text-[#94A3B8]">Status:</span>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-[#151B2A] border border-[#26344F] text-[#F1F5F9] text-xs rounded-xl px-3 py-1.5 focus:outline-none focus:border-[#06B6D4]"
              >
                <option value="">All Statuses</option>
                <option value="OPEN">Open</option>
                <option value="ASSIGNED">Assigned</option>
                <option value="IN_PROGRESS">In Progress</option>
                <option value="COMPLETED">Completed</option>
                <option value="VERIFICATION_PENDING">Verification Pending</option>
                <option value="VERIFIED">Verified</option>
                <option value="REJECTED">Rejected</option>
                <option value="CANCELLED">Cancelled</option>
              </select>
            </div>
          </div>

          <button
            onClick={() => {
              setPriorityFilter("");
              setStatusFilter("");
            }}
            disabled={!priorityFilter && !statusFilter}
            className="px-3 py-1.5 rounded-xl bg-[#17223A] border border-[#26344F] text-xs text-[#94A3B8] hover:text-[#F1F5F9] disabled:opacity-40 ml-auto"
          >
            Reset Filters
          </button>

          <button
            onClick={() => loadData()}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#17223A] border border-[#26344F] text-xs text-[#94A3B8] hover:text-[#F1F5F9] transition-colors"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin text-[#06B6D4]" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>

        {/* Content Body */}
        {loading ? (
          <div className="h-64 flex items-center justify-center border border-[#26344F] rounded-2xl bg-[#111A2E]">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#06B6D4]" />
          </div>
        ) : jobs.length === 0 ? (
          <EmptyState
            icon={Wrench}
            title="No jobs"
            description="No maintenance jobs match the current filters."
          />
        ) : viewMode === "kanban" ? (
          /* Kanban Board View */
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-3 min-h-[500px]">
            {STATUS_COLUMNS.map((col) => {
              const colJobs = jobs.filter((j) => j.status === col.id);
              return (
                <div
                  key={col.id}
                  className="bg-[#111A2E] border border-[#26344F] rounded-2xl p-3 flex flex-col min-h-[400px]"
                >
                  <div className="flex items-center justify-between pb-2 mb-2 border-b border-[#26344F]">
                    <span className="font-label-sm text-xs font-bold text-[#F1F5F9] truncate">
                      {col.label}
                    </span>
                    <span className="font-code-sm text-[10px] px-2 py-0.5 rounded-full bg-[#17223A] text-[#94A3B8] border border-[#26344F]">
                      {colJobs.length}
                    </span>
                  </div>

                  <div className="flex-1 space-y-2.5 overflow-y-auto">
                    {colJobs.length === 0 ? (
                      <p className="font-code-sm text-[11px] text-[#64748B] text-center py-8">
                        Empty
                      </p>
                    ) : (
                      colJobs.map((job) => (
                        <div
                          key={job.id}
                          onClick={() => openJobDetail(job)}
                          className="bg-[#151B2A] border border-[#26344F] hover:border-[#06B6D4]/50 rounded-xl p-3 cursor-pointer transition-all shadow-sm hover:shadow-md space-y-2"
                        >
                          <h4 className="font-headline-sm text-xs font-semibold text-[#F1F5F9] line-clamp-2 leading-snug">
                            {job.title}
                          </h4>

                          <div className="flex items-center justify-between gap-2 pt-1 border-t border-[#26344F]/60">
                            <StatusBadge status={job.priority_level} size="sm" />
                            {job.damage_count !== undefined && job.damage_count > 0 && (
                              <span className="font-code-sm text-[10px] text-[#94A3B8] flex items-center gap-1">
                                <AlertCircle className="h-3 w-3 text-[#F59E0B]" />
                                {job.damage_count} dmg
                              </span>
                            )}
                          </div>

                          {job.due_at && (
                            <p className="font-code-sm text-[10px] text-[#64748B]">
                              Due: {new Date(job.due_at).toLocaleDateString()}
                            </p>
                          )}
                        </div>
                      ))
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          /* Table View */
          <div className="bg-[#111A2E] border border-[#26344F] rounded-2xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-[#0C1321] border-b border-[#26344F] text-[#94A3B8]">
                  <tr>
                    <th className="py-3 px-4 font-semibold">Title</th>
                    <th className="py-3 px-4 font-semibold">Linked Road</th>
                    <th className="py-3 px-4 font-semibold">Priority</th>
                    <th className="py-3 px-4 font-semibold">Status</th>
                    <th className="py-3 px-4 font-semibold">Damages</th>
                    <th className="py-3 px-4 font-semibold">Due Date</th>
                    <th className="py-3 px-4 text-right font-semibold">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#26344F]/50 text-[#DCE2F6]">
                  {jobs.map((job) => (
                    <tr
                      key={job.id}
                      onClick={() => openJobDetail(job)}
                      className="hover:bg-[#17223A]/50 cursor-pointer transition-colors"
                    >
                      <td className="py-3 px-4 font-bold text-white">{job.title}</td>
                      <td className="py-3 px-4 text-[#DCE2F6]">
                        {job.road_id
                          ? roads.find((r) => r.id === job.road_id)?.name || "Linked Road"
                          : "Unassigned"}
                      </td>
                      <td className="py-3 px-4">
                        <StatusBadge status={job.priority_level} size="sm" />
                      </td>
                      <td className="py-3 px-4">
                        <StatusBadge status={job.status} size="sm" />
                      </td>
                      <td className="py-3 px-4 font-code-sm text-[#94A3B8]">
                        {job.damage_count || 0}
                      </td>
                      <td className="py-3 px-4 font-code-sm text-[#94A3B8]">
                        {job.due_at ? new Date(job.due_at).toLocaleDateString() : "—"}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            openJobDetail(job);
                          }}
                          className="h-8 px-3 rounded-lg bg-[#17223A] border border-[#26344F] text-[#4CD7F6] font-label-md text-xs font-semibold hover:bg-[#232A39]"
                        >
                          View Details
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Selected Job Drawer */}
        {selectedJob && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex justify-end z-50">
            <div className="bg-[#111A2E] border-l border-[#26344F] w-full max-w-xl h-full p-6 overflow-y-auto space-y-6 shadow-2xl">
              <div className="flex items-start justify-between border-b border-[#26344F] pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <StatusBadge status={selectedJob.status} />
                    <StatusBadge
                      status={selectedJob.priority_level}
                      label={`${selectedJob.priority_level}${
                        selectedJob.priority_score != null ? ` ${selectedJob.priority_score}` : ""
                      }`}
                      showDot={false}
                    />
                  </div>
                  <h3 className="font-headline-sm text-lg font-bold text-[#F1F5F9] mt-2">
                    {selectedJob.title}
                  </h3>
                  <p className="font-code-sm text-xs text-[#94A3B8] mt-0.5">
                    Job ID: {selectedJob.id}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedJob(null)}
                  className="text-[#94A3B8] hover:text-[#F1F5F9] p-1.5 rounded-lg hover:bg-[#17223A]"
                >
                  <XCircle className="h-6 w-6" />
                </button>
              </div>

              {selectedJob.description && (
                <div className="space-y-1.5">
                  <h4 className="font-label-md text-xs font-bold text-[#94A3B8]">Description</h4>
                  <p className="font-body-sm text-xs text-[#DCE2F6] leading-relaxed bg-[#151B2A] p-3 rounded-xl border border-[#26344F]">
                    {selectedJob.description}
                  </p>
                </div>
              )}

              {/* Status Action Controls */}
              <div className="space-y-3 bg-[#151B2A] p-4 rounded-xl border border-[#26344F]">
                <h4 className="font-label-md text-xs font-bold text-[#F1F5F9] flex items-center gap-2">
                  <ArrowRight className="h-4 w-4 text-[#06B6D4]" />
                  <span>Available State Transitions</span>
                </h4>
                <div className="flex flex-wrap gap-2 pt-1">
                  {(ALLOWED_TRANSITIONS[selectedJob.status] || []).length === 0 ? (
                    <p className="font-code-sm text-xs text-[#64748B]">No further transitions allowed.</p>
                  ) : (
                    ALLOWED_TRANSITIONS[selectedJob.status].map((targetStatus) => (
                      <button
                        key={targetStatus}
                        onClick={() => {
                          setTransitionTarget(targetStatus);
                          setTransitionNotes("");
                        }}
                        className="bg-[#06B6D4]/15 hover:bg-[#06B6D4]/25 text-[#4CD7F6] border border-[#06B6D4]/30 px-3 py-1.5 rounded-xl font-label-md text-xs font-bold transition-all"
                      >
                        Transition to {targetStatus.replace(/_/g, " ")}
                      </button>
                    ))
                  )}
                </div>
              </div>

              {/* Transition Form Modal */}
              {transitionTarget && (
                <div className="p-4 bg-[#151B2A] border border-[#06B6D4]/40 rounded-xl space-y-3">
                  <h4 className="font-headline-sm text-xs font-bold text-[#F1F5F9]">
                    Transition to {transitionTarget.replace(/_/g, " ")}
                  </h4>
                  <textarea
                    rows={2}
                    value={transitionNotes}
                    onChange={(e) => setTransitionNotes(e.target.value)}
                    placeholder="Enter completion notes or transition justification..."
                    className="w-full bg-[#111A2E] border border-[#26344F] rounded-xl p-3 text-xs text-[#F1F5F9] focus:outline-none focus:border-[#06B6D4]"
                  />
                  <div className="flex items-center justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => setTransitionTarget(null)}
                      className="px-3 py-1.5 text-xs text-[#94A3B8] hover:text-[#F1F5F9]"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      disabled={transitioning}
                      onClick={handleTransitionSubmit}
                      className="bg-[#06B6D4] hover:bg-[#4CD7F6] text-[#003640] px-4 py-1.5 rounded-xl font-label-md text-xs font-bold disabled:opacity-50"
                    >
                      {transitioning ? "Updating..." : "Confirm Transition"}
                    </button>
                  </div>
                </div>
              )}

              {/* Linked Damages */}
              <div className="space-y-2">
                <h4 className="font-label-md text-xs font-bold text-[#94A3B8] flex items-center justify-between">
                  <span>Linked Damage Records</span>
                  <span className="font-code-sm text-[#64748B] font-normal">({jobDamages.length})</span>
                </h4>
                {jobDamages.length === 0 ? (
                  <p className="text-xs text-[#64748B] bg-[#151B2A] p-3 rounded-xl border border-[#26344F]">
                    No individual damage records are linked to this maintenance work order.
                  </p>
                ) : (
                  <div className="space-y-2">
                    {jobDamages.map((dmg) => (
                      <div
                        key={dmg.damage_record_id}
                        className="bg-[#151B2A] border border-[#26344F] p-3 rounded-xl flex items-center justify-between text-xs"
                      >
                        <div className="space-y-0.5">
                          <p className="font-medium text-[#F1F5F9]">
                            Damage <span className="font-code-sm">#{dmg.damage_record_id.slice(0, 8)}</span>
                          </p>
                          <p className="text-[11px] text-[#94A3B8]">Role: {dmg.relationship_type}</p>
                        </div>
                        {dmg.severity && <StatusBadge status={dmg.severity} size="sm" showDot={false} />}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Evidence upload, image verification and review live in the job workspace. */}
              <Link
                href={`/maintenance/${selectedJob.id}`}
                className="block bg-[#151B2A] p-4 rounded-xl border border-[#06B6D4]/40 hover:border-[#06B6D4] text-xs text-[#4CD7F6] transition-all font-semibold"
              >
                Open job workspace: assignment, before/after evidence upload, automated image verification and review
                ({jobEvidence.length} evidence item(s), {jobVerifications.length} verification record(s)) →
              </Link>

              {/* Status History Timeline */}
              <div className="space-y-2">
                <h4 className="font-label-md text-xs font-bold text-[#94A3B8]">Audit Status History</h4>
                {jobHistory.length === 0 ? (
                  <p className="text-xs text-[#64748B]">No history available.</p>
                ) : (
                  <div className="space-y-3 relative pl-4 border-l border-[#26344F] ml-2">
                    {jobHistory.map((item) => (
                      <div key={item.id} className="relative space-y-1">
                        <div className="absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full bg-[#06B6D4] border border-[#111A2E]" />
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="font-semibold text-[#F1F5F9]">{item.new_status.replace(/_/g, " ")}</span>
                          <span className="font-code-sm text-[#64748B]">
                            {new Date(item.changed_at).toLocaleString()}
                          </span>
                        </div>
                        {item.reason && (
                          <p className="text-xs text-[#94A3B8] bg-[#151B2A] p-2 rounded-lg border border-[#26344F]">
                            {item.reason}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Create Job Modal */}
        {isCreateOpen && (
          <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4 z-50">
            <div className="bg-[#111A2E] border border-[#26344F] rounded-2xl max-w-lg w-full p-6 space-y-5 shadow-2xl">
              <div className="flex items-center justify-between border-b border-[#26344F] pb-3">
                <div className="flex items-center gap-2">
                  <Wrench className="h-5 w-5 text-[#06B6D4]" />
                  <h3 className="font-headline-sm text-base font-bold text-[#F1F5F9]">
                    Create Maintenance Job
                  </h3>
                </div>
                <button
                  onClick={() => setIsCreateOpen(false)}
                  className="text-[#94A3B8] hover:text-[#F1F5F9] text-sm p-1"
                >
                  ✕
                </button>
              </div>

              <form onSubmit={handleCreateSubmit} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="font-label-sm text-xs text-[#94A3B8] font-semibold">
                    Job Title *
                  </label>
                  <input
                    type="text"
                    required
                    value={createForm.title}
                    onChange={(e) => setCreateForm({ ...createForm, title: e.target.value })}
                    placeholder="e.g. Patch potholes on SH-42 KM 0-2"
                    className="w-full h-11 bg-[#151B2A] border border-[#26344F] rounded-xl px-3 text-xs text-[#F1F5F9] focus:outline-none focus:border-[#06B6D4]"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="font-label-sm text-xs text-[#94A3B8] font-semibold">
                    Associated Road (Optional)
                  </label>
                  <select
                    value={createForm.road_id}
                    onChange={(e) => setCreateForm({ ...createForm, road_id: e.target.value })}
                    className="w-full h-11 bg-[#151B2A] border border-[#26344F] rounded-xl px-3 text-xs text-[#F1F5F9] focus:outline-none focus:border-[#06B6D4]"
                  >
                    <option value="">None / General Maintenance</option>
                    {roads.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.name} ({r.road_code || "No code"})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="font-label-sm text-xs text-[#94A3B8] font-semibold">
                    Priority Level
                  </label>
                  <select
                    value={createForm.priority}
                    onChange={(e) => setCreateForm({ ...createForm, priority: e.target.value })}
                    className="w-full h-11 bg-[#151B2A] border border-[#26344F] rounded-xl px-3 text-xs text-[#F1F5F9] focus:outline-none focus:border-[#06B6D4]"
                  >
                    <option value="CRITICAL">Critical</option>
                    <option value="HIGH">High</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="LOW">Low</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="font-label-sm text-xs text-[#94A3B8] font-semibold">
                    Due Date
                  </label>
                  <input
                    type="date"
                    value={createForm.due_at}
                    onChange={(e) => setCreateForm({ ...createForm, due_at: e.target.value })}
                    className="w-full h-11 bg-[#151B2A] border border-[#26344F] rounded-xl px-3 text-xs text-[#F1F5F9] focus:outline-none focus:border-[#06B6D4]"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="font-label-sm text-xs text-[#94A3B8] font-semibold">
                    Description
                  </label>
                  <textarea
                    rows={3}
                    value={createForm.description}
                    onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
                    placeholder="Describe maintenance scope and specifications..."
                    className="w-full bg-[#151B2A] border border-[#26344F] rounded-xl p-3 text-xs text-[#F1F5F9] placeholder:text-[#64748B] focus:outline-none focus:border-[#06B6D4]"
                  />
                </div>

                <div className="flex items-center justify-end gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setIsCreateOpen(false)}
                    className="h-10 px-4 rounded-xl bg-[#17223A] border border-[#26344F] text-xs font-semibold text-[#94A3B8]"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={creating}
                    className="h-10 px-5 rounded-xl bg-[#06B6D4] hover:bg-[#4CD7F6] text-[#003640] text-xs font-bold transition-all shadow-md shadow-[#06B6D4]/20 disabled:opacity-50"
                  >
                    {creating ? "Creating..." : "Create Job"}
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
