"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/shell";
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
} from "lucide-react";

const STATUS_COLUMNS = [
  { id: "OPEN", label: "Open", color: "border-amber-500/30 bg-amber-500/10 text-amber-400" },
  { id: "ASSIGNED", label: "Assigned", color: "border-blue-500/30 bg-blue-500/10 text-blue-400" },
  { id: "IN_PROGRESS", label: "In Progress", color: "border-indigo-500/30 bg-indigo-500/10 text-indigo-400" },
  { id: "COMPLETED", label: "Completed", color: "border-teal-500/30 bg-teal-500/10 text-teal-400" },
  { id: "VERIFICATION_PENDING", label: "Verification Pending", color: "border-purple-500/30 bg-purple-500/10 text-purple-400" },
  { id: "VERIFIED", label: "Verified", color: "border-emerald-500/30 bg-emerald-500/10 text-emerald-400" },
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

  const getPriorityBadge = (lvl: string, score?: number) => {
    const colors: Record<string, string> = {
      CRITICAL: "bg-red-500/20 text-red-400 border-red-500/30",
      HIGH: "bg-orange-500/20 text-orange-400 border-orange-500/30",
      MEDIUM: "bg-amber-500/20 text-amber-400 border-amber-500/30",
      LOW: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
    };
    return (
      <span
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-semibold border ${
          colors[lvl] || colors.MEDIUM
        }`}
      >
        <span>{lvl}</span>
        {score !== undefined && score !== null && (
          <span className="text-[10px] opacity-75">({score.toFixed(0)})</span>
        )}
      </span>
    );
  };

  const getStatusBadge = (st: string) => {
    const col = STATUS_COLUMNS.find((c) => c.id === st);
    return (
      <span
        className={`inline-flex items-center px-2 py-0.5 rounded text-[11px] font-medium border ${
          col?.color || "border-slate-700 bg-slate-800 text-slate-400"
        }`}
      >
        {st.replace(/_/g, " ")}
      </span>
    );
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
            <h1 className="text-xl font-bold text-white tracking-tight flex items-center gap-2.5">
              <Wrench className="h-6 w-6 text-blue-500" />
              Maintenance Operations
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Operational maintenance workflow, contractor assignments, and repair tracking.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex rounded-lg bg-slate-900 border border-slate-800 p-0.5">
              <button
                onClick={() => setViewMode("kanban")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                  viewMode === "kanban"
                    ? "bg-blue-600 text-white shadow-sm"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <Kanban className="h-3.5 w-3.5" />
                Board
              </button>
              <button
                onClick={() => setViewMode("table")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors ${
                  viewMode === "table"
                    ? "bg-blue-600 text-white shadow-sm"
                    : "text-slate-400 hover:text-white"
                }`}
              >
                <List className="h-3.5 w-3.5" />
                Table
              </button>
            </div>

            <button
              onClick={() => setIsCreateOpen(true)}
              className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 text-white px-3.5 py-2 rounded-lg text-xs font-medium transition-colors shadow-sm shadow-blue-500/20"
            >
              <Plus className="h-4 w-4" />
              Create Job
            </button>
          </div>
        </div>

        {/* KPI Cards */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-3.5">
            <p className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Total Jobs</p>
            <p className="text-xl font-bold text-white mt-1">{counts.total}</p>
          </div>
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-3.5">
            <p className="text-[11px] font-medium text-amber-400 uppercase tracking-wider">Open / Assigned</p>
            <p className="text-xl font-bold text-white mt-1">{counts.open}</p>
          </div>
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-3.5">
            <p className="text-[11px] font-medium text-indigo-400 uppercase tracking-wider">In Progress</p>
            <p className="text-xl font-bold text-white mt-1">{counts.inProgress}</p>
          </div>
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-3.5">
            <p className="text-[11px] font-medium text-purple-400 uppercase tracking-wider">Awaiting QA</p>
            <p className="text-xl font-bold text-white mt-1">{counts.verification}</p>
          </div>
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-3.5">
            <p className="text-[11px] font-medium text-emerald-400 uppercase tracking-wider">Verified Repaired</p>
            <p className="text-xl font-bold text-white mt-1">{counts.verified}</p>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center gap-3 bg-slate-900/40 p-3 rounded-xl border border-slate-800/80">
          <div className="flex items-center gap-2 text-xs text-slate-400 mr-2">
            <Filter className="h-3.5 w-3.5" />
            <span>Filters:</span>
          </div>

          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 text-slate-200 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-blue-500"
          >
            <option value="">All Priorities</option>
            <option value="CRITICAL">Critical</option>
            <option value="HIGH">High</option>
            <option value="MEDIUM">Medium</option>
            <option value="LOW">Low</option>
          </select>

          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 text-slate-200 text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-blue-500"
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

          {(priorityFilter || statusFilter) && (
            <button
              onClick={() => {
                setPriorityFilter("");
                setStatusFilter("");
              }}
              className="text-xs text-blue-400 hover:text-blue-300 ml-auto"
            >
              Reset Filters
            </button>
          )}
        </div>

        {/* Content Body */}
        {loading ? (
          <div className="h-64 flex items-center justify-center border border-slate-800/60 rounded-xl bg-slate-900/20">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500" />
          </div>
        ) : viewMode === "kanban" ? (
          /* Kanban Board View */
          <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-3 min-h-[500px]">
            {STATUS_COLUMNS.map((col) => {
              const colJobs = jobs.filter((j) => j.status === col.id);
              return (
                <div
                  key={col.id}
                  className="bg-slate-900/40 border border-slate-800/80 rounded-xl p-3 flex flex-col min-h-[400px]"
                >
                  <div className="flex items-center justify-between pb-2.5 mb-2.5 border-b border-slate-800">
                    <span className="text-xs font-semibold text-white truncate">{col.label}</span>
                    <span className="text-[11px] px-1.5 py-0.5 rounded-full bg-slate-800 text-slate-400 font-medium">
                      {colJobs.length}
                    </span>
                  </div>

                  <div className="flex-1 space-y-2.5 overflow-y-auto">
                    {colJobs.length === 0 ? (
                      <p className="text-[11px] text-slate-500 text-center py-6">No jobs</p>
                    ) : (
                      colJobs.map((job) => (
                        <div
                          key={job.id}
                          onClick={() => openJobDetail(job)}
                          className="bg-slate-950/90 border border-slate-800 hover:border-blue-500/50 rounded-lg p-3 cursor-pointer transition-all hover:shadow-md hover:shadow-blue-500/5 space-y-2"
                        >
                          <div className="flex items-start justify-between gap-1.5">
                            <h4 className="text-xs font-medium text-white line-clamp-2 leading-snug">
                              {job.title}
                            </h4>
                          </div>

                          <div className="flex items-center justify-between gap-2 pt-1 border-t border-slate-900">
                            {getPriorityBadge(job.priority_level, job.priority_score)}
                            {job.damage_count !== undefined && job.damage_count > 0 && (
                              <span className="text-[10px] text-slate-400 flex items-center gap-1">
                                <AlertCircle className="h-3 w-3 text-amber-400" />
                                {job.damage_count} dmg
                              </span>
                            )}
                          </div>

                          {job.due_at && (
                            <p className="text-[10px] text-slate-400 flex items-center gap-1">
                              <Calendar className="h-3 w-3 text-slate-400" />
                              Due {new Date(job.due_at).toLocaleDateString()}
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
          <div className="border border-slate-800 rounded-xl overflow-hidden bg-slate-900/40">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/80 text-slate-400 border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4 font-medium">Job Title</th>
                  <th className="py-3 px-4 font-medium">Priority</th>
                  <th className="py-3 px-4 font-medium">Status</th>
                  <th className="py-3 px-4 font-medium">Linked Damages</th>
                  <th className="py-3 px-4 font-medium">Due Date</th>
                  <th className="py-3 px-4 font-medium">Created</th>
                  <th className="py-3 px-4 font-medium text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {jobs.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="text-center py-8 text-slate-500">
                      No maintenance jobs found matching the selected criteria.
                    </td>
                  </tr>
                ) : (
                  jobs.map((job) => (
                    <tr
                      key={job.id}
                      onClick={() => openJobDetail(job)}
                      className="hover:bg-slate-800/40 cursor-pointer transition-colors"
                    >
                      <td className="py-3 px-4 font-medium text-white max-w-xs truncate">
                        {job.title}
                      </td>
                      <td className="py-3 px-4">
                        {getPriorityBadge(job.priority_level, job.priority_score)}
                      </td>
                      <td className="py-3 px-4">{getStatusBadge(job.status)}</td>
                      <td className="py-3 px-4 text-slate-300">
                        {job.damage_count ? `${job.damage_count} damage(s)` : "None"}
                      </td>
                      <td className="py-3 px-4 text-slate-400">
                        {job.due_at ? new Date(job.due_at).toLocaleDateString() : "—"}
                      </td>
                      <td className="py-3 px-4 text-slate-400">
                        {new Date(job.created_at).toLocaleDateString()}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <span className="text-blue-400 hover:text-blue-300 inline-flex items-center gap-1 font-medium">
                          Details <ChevronRight className="h-3 w-3" />
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}

        {/* Create Job Modal */}
        {isCreateOpen && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 w-full max-w-md shadow-xl space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Plus className="h-4 w-4 text-blue-500" />
                  Create Maintenance Job
                </h3>
                <button
                  onClick={() => setIsCreateOpen(false)}
                  className="text-slate-400 hover:text-white"
                >
                  <XCircle className="h-4 w-4" />
                </button>
              </div>

              <form onSubmit={handleCreateSubmit} className="space-y-3.5">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Job Title *
                  </label>
                  <input
                    type="text"
                    required
                    value={createForm.title}
                    onChange={(e) => setCreateForm({ ...createForm, title: e.target.value })}
                    placeholder="e.g. Patch potholes on SH-42 KM 0-2"
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Description
                  </label>
                  <textarea
                    rows={3}
                    value={createForm.description}
                    onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
                    placeholder="Describe maintenance scope and specifications..."
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">
                      Priority Level
                    </label>
                    <select
                      value={createForm.priority}
                      onChange={(e) => setCreateForm({ ...createForm, priority: e.target.value })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
                    >
                      <option value="LOW">Low</option>
                      <option value="MEDIUM">Medium</option>
                      <option value="HIGH">High</option>
                      <option value="CRITICAL">Critical</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">
                      Due Date
                    </label>
                    <input
                      type="date"
                      value={createForm.due_at}
                      onChange={(e) => setCreateForm({ ...createForm, due_at: e.target.value })}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1">
                    Associated Road (Optional)
                  </label>
                  <select
                    value={createForm.road_id}
                    onChange={(e) => setCreateForm({ ...createForm, road_id: e.target.value })}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-blue-500"
                  >
                    <option value="">None / General Maintenance</option>
                    {roads.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.name} ({r.road_code || "No Code"})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="flex items-center justify-end gap-2 pt-3 border-t border-slate-800">
                  <button
                    type="button"
                    onClick={() => setIsCreateOpen(false)}
                    className="px-3 py-1.5 text-xs text-slate-400 hover:text-white"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={creating}
                    className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-xs font-medium transition-colors shadow-sm"
                  >
                    {creating ? "Creating..." : "Create Job"}
                  </button>
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Selected Job Detail Drawer */}
        {selectedJob && (
          <div className="fixed inset-0 z-50 flex items-center justify-end bg-slate-950/70 backdrop-blur-sm">
            <div className="w-full max-w-xl h-full bg-slate-900 border-l border-slate-800 flex flex-col p-6 overflow-y-auto space-y-6 shadow-2xl">
              {/* Header */}
              <div className="flex items-start justify-between border-b border-slate-800 pb-4">
                <div className="space-y-1">
                  <span className="text-[10px] text-slate-400 uppercase tracking-widest font-bold">
                    Job ID: {selectedJob.id.slice(0, 8)}...
                  </span>
                  <h2 className="text-base font-bold text-white">{selectedJob.title}</h2>
                  <div className="flex items-center gap-2 pt-1">
                    {getStatusBadge(selectedJob.status)}
                    {getPriorityBadge(selectedJob.priority_level, selectedJob.priority_score)}
                  </div>
                </div>
                <button
                  onClick={() => setSelectedJob(null)}
                  className="text-slate-400 hover:text-white p-1 rounded-md hover:bg-slate-800"
                >
                  <XCircle className="h-5 w-5" />
                </button>
              </div>

              {/* Description */}
              {selectedJob.description && (
                <div className="space-y-1">
                  <h4 className="text-xs font-semibold text-slate-300">Description</h4>
                  <p className="text-xs text-slate-400 leading-relaxed bg-slate-950/60 p-3 rounded-lg border border-slate-800/80">
                    {selectedJob.description}
                  </p>
                </div>
              )}

              {/* Status Action Controls */}
              <div className="space-y-2 bg-slate-950/80 p-4 rounded-xl border border-slate-800">
                <h4 className="text-xs font-semibold text-slate-200 flex items-center gap-2">
                  <ArrowRight className="h-3.5 w-3.5 text-blue-400" />
                  Available State Transitions
                </h4>
                <div className="flex flex-wrap gap-2 pt-1">
                  {(ALLOWED_TRANSITIONS[selectedJob.status] || []).length === 0 ? (
                    <p className="text-xs text-slate-500 italic">No further transitions allowed.</p>
                  ) : (
                    ALLOWED_TRANSITIONS[selectedJob.status].map((targetStatus) => (
                      <button
                        key={targetStatus}
                        onClick={() => {
                          setTransitionTarget(targetStatus);
                          setTransitionNotes("");
                        }}
                        className="bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 border border-blue-500/30 px-3 py-1.5 rounded-lg text-xs font-medium transition-colors"
                      >
                        Transition to {targetStatus.replace(/_/g, " ")}
                      </button>
                    ))
                  )}
                </div>
              </div>

              {/* Transition Notes Modal */}
              {transitionTarget && (
                <div className="p-4 bg-slate-950 border border-blue-500/30 rounded-xl space-y-3">
                  <h4 className="text-xs font-semibold text-white">
                    Transition to {transitionTarget.replace(/_/g, " ")}
                  </h4>
                  <textarea
                    rows={2}
                    value={transitionNotes}
                    onChange={(e) => setTransitionNotes(e.target.value)}
                    placeholder="Enter completion notes or transition justification..."
                    className="w-full bg-slate-900 border border-slate-800 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-blue-500"
                  />
                  <div className="flex items-center justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => setTransitionTarget(null)}
                      className="px-3 py-1 text-xs text-slate-400 hover:text-white"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      disabled={transitioning}
                      onClick={handleTransitionSubmit}
                      className="bg-blue-600 hover:bg-blue-500 text-white px-3.5 py-1.5 rounded-lg text-xs font-medium"
                    >
                      {transitioning ? "Updating..." : "Confirm Transition"}
                    </button>
                  </div>
                </div>
              )}

              {/* Linked Damages */}
              <div className="space-y-2">
                <h4 className="text-xs font-semibold text-slate-300 flex items-center justify-between">
                  <span>Linked Damage Records</span>
                  <span className="text-slate-500 font-normal">({jobDamages.length})</span>
                </h4>
                {jobDamages.length === 0 ? (
                  <p className="text-xs text-slate-500 italic bg-slate-950/40 p-3 rounded-lg border border-slate-800/60">
                    No individual damage records are linked to this maintenance work order.
                  </p>
                ) : (
                  <div className="space-y-2">
                    {jobDamages.map((dmg) => (
                      <div
                        key={dmg.damage_record_id}
                        className="bg-slate-950/80 border border-slate-800 p-3 rounded-lg flex items-center justify-between text-xs"
                      >
                        <div className="space-y-0.5">
                          <p className="font-medium text-white">
                            Damage #{dmg.damage_record_id.slice(0, 8)}
                          </p>
                          <p className="text-[11px] text-slate-400">
                            Role: {dmg.relationship_type}
                          </p>
                        </div>
                        {dmg.severity && getPriorityBadge(dmg.severity)}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Evidence upload, image verification and review live in the job workspace. */}
              <Link
                href={`/maintenance/${selectedJob.id}`}
                className="block bg-slate-950/60 p-4 rounded-xl border border-blue-800/50 hover:border-blue-500 text-xs text-blue-300"
              >
                Open job workspace: assignment, before/after evidence upload, automated image verification and review
                ({jobEvidence.length} evidence item(s), {jobVerifications.length} verification record(s)) →
              </Link>

              {/* Status History Timeline */}
              <div className="space-y-2">
                <h4 className="text-xs font-semibold text-slate-300">Audit Status History</h4>
                {jobHistory.length === 0 ? (
                  <p className="text-xs text-slate-500 italic">No history available.</p>
                ) : (
                  <div className="space-y-3 relative pl-4 border-l border-slate-800 ml-2">
                    {jobHistory.map((item) => (
                      <div key={item.id} className="relative space-y-1">
                        <div className="absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full bg-blue-500 border border-slate-900" />
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="font-semibold text-white">
                            {item.new_status.replace(/_/g, " ")}
                          </span>
                          <span className="text-slate-500">
                            {new Date(item.changed_at).toLocaleString()}
                          </span>
                        </div>
                        {item.reason && (
                          <p className="text-xs text-slate-400 bg-slate-950/60 p-2 rounded border border-slate-800/80">
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
      </div>
    </AppShell>
  );
}
