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
  { id: "OPEN", label: "Open", color: "border-ri-warning/30 bg-ri-warning/10 text-ri-warning" },
  { id: "ASSIGNED", label: "Assigned", color: "border-ri-info/30 bg-ri-info/10 text-ri-info-soft" },
  { id: "IN_PROGRESS", label: "In Progress", color: "border-ri-primary/30 bg-ri-primary/10 text-ri-primary-bright" },
  { id: "COMPLETED", label: "Completed", color: "border-ri-success/30 bg-ri-success/10 text-ri-success" },
  { id: "VERIFICATION_PENDING", label: "Verification Pending", color: "border-ri-review/30 bg-ri-review/10 text-ri-review" },
  { id: "VERIFIED", label: "Verified", color: "border-ri-success/40 bg-ri-success/20 text-ri-success" },
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
      <div className="space-y-5">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="font-code-sm text-[11px] text-ri-primary uppercase tracking-wider font-semibold">
                Maintenance jobs
              </span>
            </div>
            <h1 className="font-headline-sm text-2xl font-bold tracking-tight text-ri-text flex items-center gap-2.5">
              Maintenance Operations
            </h1>
            <p className="font-body-sm text-xs text-ri-muted mt-1">
              Operational maintenance workflow, contractor assignments, and repair tracking.
            </p>
          </div>

          <div className="flex items-center gap-3">
            {/* View Mode Toggle */}
            <div className="flex rounded-xl bg-ri-surface border border-ri-line p-1">
              <button
                onClick={() => setViewMode("kanban")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  viewMode === "kanban"
                    ? "bg-ri-primary text-ri-on-primary shadow-sm shadow-ri-primary/20"
                    : "text-ri-muted hover:text-ri-text"
                }`}
              >
                <Kanban className="h-3.5 w-3.5" />
                Board
              </button>
              <button
                onClick={() => setViewMode("table")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all ${
                  viewMode === "table"
                    ? "bg-ri-primary text-ri-on-primary shadow-sm shadow-ri-primary/20"
                    : "text-ri-muted hover:text-ri-text"
                }`}
              >
                <List className="h-3.5 w-3.5" />
                Table
              </button>
            </div>

            <button
              onClick={() => setIsCreateOpen(true)}
              className="flex items-center gap-2 bg-ri-primary hover:bg-ri-primary-bright text-ri-on-primary px-4 py-2 rounded-xl text-xs font-bold transition-all shadow-md shadow-ri-primary/20 active:scale-95"
            >
              <Plus className="h-4 w-4" />
              <span>Create Job</span>
            </button>
          </div>
        </div>

        {/* 5-Column Bento KPI Strip */}
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          <div className="bg-ri-surface border border-ri-line rounded-2xl p-4">
            <span className="font-label-sm text-[11px] text-ri-muted uppercase tracking-wider">
              Total Jobs
            </span>
            <p className="font-code-lg text-2xl font-bold text-ri-text mt-2">{counts.total}</p>
          </div>
          <div className="bg-ri-surface border border-ri-line rounded-2xl p-4">
            <span className="font-label-sm text-[11px] text-ri-warning uppercase tracking-wider">
              Open / Assigned
            </span>
            <p className="font-code-lg text-2xl font-bold text-ri-warning mt-2">{counts.open}</p>
          </div>
          <div className="bg-ri-surface border border-ri-line rounded-2xl p-4">
            <span className="font-label-sm text-[11px] text-ri-primary uppercase tracking-wider">
              In Progress
            </span>
            <p className="font-code-lg text-2xl font-bold text-ri-primary-bright mt-2">{counts.inProgress}</p>
          </div>
          <div className="bg-ri-surface border border-ri-line rounded-2xl p-4">
            <span className="font-label-sm text-[11px] text-ri-info-soft uppercase tracking-wider">
              Awaiting Verification
            </span>
            <p className="font-code-lg text-2xl font-bold text-ri-info-soft mt-2">{counts.verification}</p>
          </div>
          <div className="bg-ri-surface border border-ri-line rounded-2xl p-4">
            <span className="font-label-sm text-[11px] text-ri-success uppercase tracking-wider">
              Verified Repaired
            </span>
            <p className="font-code-lg text-2xl font-bold text-ri-success mt-2">{counts.verified}</p>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-wrap items-center justify-between gap-3 bg-ri-surface p-3 rounded-2xl border border-ri-line">
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              <span className="font-label-sm text-xs text-ri-muted">Priority:</span>
              <select
                value={priorityFilter}
                onChange={(e) => setPriorityFilter(e.target.value)}
                className="bg-ri-input border border-ri-line text-ri-text text-xs rounded-xl px-3 py-1.5 focus:outline-none focus:border-ri-primary"
              >
                <option value="">All Priorities</option>
                <option value="CRITICAL">Critical</option>
                <option value="HIGH">High</option>
                <option value="MEDIUM">Medium</option>
                <option value="LOW">Low</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <span className="font-label-sm text-xs text-ri-muted">Status:</span>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-ri-input border border-ri-line text-ri-text text-xs rounded-xl px-3 py-1.5 focus:outline-none focus:border-ri-primary"
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
            className="px-3 py-1.5 rounded-xl bg-ri-raised border border-ri-line text-xs text-ri-muted hover:text-ri-text disabled:opacity-40 ml-auto"
          >
            Reset Filters
          </button>

          <button
            onClick={() => loadData()}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-ri-raised border border-ri-line text-xs text-ri-muted hover:text-ri-text transition-colors"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin text-ri-primary" : ""}`} />
            <span>Refresh</span>
          </button>
        </div>

        {/* Content Body */}
        {loading ? (
          <div className="h-64 flex items-center justify-center border border-ri-line rounded-2xl bg-ri-surface">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-ri-primary" />
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
                  className="bg-ri-surface border border-ri-line rounded-2xl p-3 flex flex-col min-h-[400px]"
                >
                  <div className="flex items-center justify-between pb-2 mb-2 border-b border-ri-line">
                    <span className="font-label-sm text-xs font-bold text-ri-text truncate">
                      {col.label}
                    </span>
                    <span className="font-code-sm text-[10px] px-2 py-0.5 rounded-full bg-ri-raised text-ri-muted border border-ri-line">
                      {colJobs.length}
                    </span>
                  </div>

                  <div className="flex-1 space-y-2.5 overflow-y-auto">
                    {colJobs.length === 0 ? (
                      <p className="font-code-sm text-[11px] text-ri-faint text-center py-8">
                        Empty
                      </p>
                    ) : (
                      colJobs.map((job) => (
                        <div
                          key={job.id}
                          onClick={() => openJobDetail(job)}
                          className="bg-ri-input border border-ri-line hover:border-ri-primary/50 rounded-xl p-3 cursor-pointer transition-all shadow-sm hover:shadow-md space-y-2"
                        >
                          <h4 className="font-headline-sm text-xs font-semibold text-ri-text line-clamp-2 leading-snug">
                            {job.title}
                          </h4>

                          <div className="flex items-center justify-between gap-2 pt-1 border-t border-ri-line/60">
                            <StatusBadge status={job.priority_level} size="sm" />
                            {job.damage_count !== undefined && job.damage_count > 0 && (
                              <span className="font-code-sm text-[10px] text-ri-muted flex items-center gap-1">
                                <AlertCircle className="h-3 w-3 text-ri-warning" />
                                {job.damage_count} dmg
                              </span>
                            )}
                          </div>

                          {job.due_at && (
                            <p className="font-code-sm text-[10px] text-ri-faint">
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
          <div className="bg-ri-surface border border-ri-line rounded-2xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-ri-bg border-b border-ri-line text-ri-muted">
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
                <tbody className="divide-y divide-ri-line/50 text-ri-text-soft">
                  {jobs.map((job) => (
                    <tr
                      key={job.id}
                      onClick={() => openJobDetail(job)}
                      className="hover:bg-ri-raised/50 cursor-pointer transition-colors"
                    >
                      <td className="py-3 px-4 font-bold text-white">{job.title}</td>
                      <td className="py-3 px-4 text-ri-text-soft">
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
                      <td className="py-3 px-4 font-code-sm text-ri-muted">
                        {job.damage_count || 0}
                      </td>
                      <td className="py-3 px-4 font-code-sm text-ri-muted">
                        {job.due_at ? new Date(job.due_at).toLocaleDateString() : "—"}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            openJobDetail(job);
                          }}
                          className="h-8 px-3 rounded-lg bg-ri-raised border border-ri-line text-ri-primary-bright font-label-md text-xs font-semibold hover:bg-ri-raised"
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
            <div className="bg-ri-surface border-l border-ri-line w-full max-w-xl h-full p-6 overflow-y-auto space-y-6 shadow-2xl">
              <div className="flex items-start justify-between border-b border-ri-line pb-4">
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
                  <h3 className="font-headline-sm text-lg font-bold text-ri-text mt-2">
                    {selectedJob.title}
                  </h3>
                  <p className="font-code-sm text-xs text-ri-muted mt-0.5">
                    Job ID: {selectedJob.id}
                  </p>
                </div>
                <button
                  onClick={() => setSelectedJob(null)}
                  className="text-ri-muted hover:text-ri-text p-1.5 rounded-lg hover:bg-ri-raised"
                >
                  <XCircle className="h-6 w-6" />
                </button>
              </div>

              {selectedJob.description && (
                <div className="space-y-1.5">
                  <h4 className="font-label-md text-xs font-bold text-ri-muted">Description</h4>
                  <p className="font-body-sm text-xs text-ri-text-soft leading-relaxed bg-ri-input p-3 rounded-xl border border-ri-line">
                    {selectedJob.description}
                  </p>
                </div>
              )}

              {/* Status Action Controls */}
              <div className="space-y-3 bg-ri-input p-4 rounded-xl border border-ri-line">
                <h4 className="font-label-md text-xs font-bold text-ri-text flex items-center gap-2">
                  <ArrowRight className="h-4 w-4 text-ri-primary" />
                  <span>Available State Transitions</span>
                </h4>
                <div className="flex flex-wrap gap-2 pt-1">
                  {(ALLOWED_TRANSITIONS[selectedJob.status] || []).length === 0 ? (
                    <p className="font-code-sm text-xs text-ri-faint">No further transitions allowed.</p>
                  ) : (
                    ALLOWED_TRANSITIONS[selectedJob.status].map((targetStatus) => (
                      <button
                        key={targetStatus}
                        onClick={() => {
                          setTransitionTarget(targetStatus);
                          setTransitionNotes("");
                        }}
                        className="bg-ri-primary/15 hover:bg-ri-primary/25 text-ri-primary-bright border border-ri-primary/30 px-3 py-1.5 rounded-xl font-label-md text-xs font-bold transition-all"
                      >
                        Transition to {targetStatus.replace(/_/g, " ")}
                      </button>
                    ))
                  )}
                </div>
              </div>

              {/* Transition Form Modal */}
              {transitionTarget && (
                <div className="p-4 bg-ri-input border border-ri-primary/40 rounded-xl space-y-3">
                  <h4 className="font-headline-sm text-xs font-bold text-ri-text">
                    Transition to {transitionTarget.replace(/_/g, " ")}
                  </h4>
                  <textarea
                    rows={2}
                    value={transitionNotes}
                    onChange={(e) => setTransitionNotes(e.target.value)}
                    placeholder="Enter completion notes or transition justification..."
                    className="w-full bg-ri-surface border border-ri-line rounded-xl p-3 text-xs text-ri-text focus:outline-none focus:border-ri-primary"
                  />
                  <div className="flex items-center justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => setTransitionTarget(null)}
                      className="px-3 py-1.5 text-xs text-ri-muted hover:text-ri-text"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      disabled={transitioning}
                      onClick={handleTransitionSubmit}
                      className="bg-ri-primary hover:bg-ri-primary-bright text-ri-on-primary px-4 py-1.5 rounded-xl font-label-md text-xs font-bold disabled:opacity-50"
                    >
                      {transitioning ? "Updating..." : "Confirm Transition"}
                    </button>
                  </div>
                </div>
              )}

              {/* Linked Damages */}
              <div className="space-y-2">
                <h4 className="font-label-md text-xs font-bold text-ri-muted flex items-center justify-between">
                  <span>Linked Damage Records</span>
                  <span className="font-code-sm text-ri-faint font-normal">({jobDamages.length})</span>
                </h4>
                {jobDamages.length === 0 ? (
                  <p className="text-xs text-ri-faint bg-ri-input p-3 rounded-xl border border-ri-line">
                    No individual damage records are linked to this maintenance work order.
                  </p>
                ) : (
                  <div className="space-y-2">
                    {jobDamages.map((dmg) => (
                      <div
                        key={dmg.damage_record_id}
                        className="bg-ri-input border border-ri-line p-3 rounded-xl flex items-center justify-between text-xs"
                      >
                        <div className="space-y-0.5">
                          <p className="font-medium text-ri-text">
                            Damage <span className="font-code-sm">#{dmg.damage_record_id.slice(0, 8)}</span>
                          </p>
                          <p className="text-[11px] text-ri-muted">Role: {dmg.relationship_type}</p>
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
                className="block bg-ri-input p-4 rounded-xl border border-ri-primary/40 hover:border-ri-primary text-xs text-ri-primary-bright transition-all font-semibold"
              >
                Open job workspace: assignment, before/after evidence upload, automated image verification and review
                ({jobEvidence.length} evidence item(s), {jobVerifications.length} verification record(s)) →
              </Link>

              {/* Status History Timeline */}
              <div className="space-y-2">
                <h4 className="font-label-md text-xs font-bold text-ri-muted">Audit Status History</h4>
                {jobHistory.length === 0 ? (
                  <p className="text-xs text-ri-faint">No history available.</p>
                ) : (
                  <div className="space-y-3 relative pl-4 border-l border-ri-line ml-2">
                    {jobHistory.map((item) => (
                      <div key={item.id} className="relative space-y-1">
                        <div className="absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full bg-ri-primary border border-ri-surface" />
                        <div className="flex items-center justify-between text-[11px]">
                          <span className="font-semibold text-ri-text">{item.new_status.replace(/_/g, " ")}</span>
                          <span className="font-code-sm text-ri-faint">
                            {new Date(item.changed_at).toLocaleString()}
                          </span>
                        </div>
                        {item.reason && (
                          <p className="text-xs text-ri-muted bg-ri-input p-2 rounded-lg border border-ri-line">
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
            <div className="bg-ri-surface border border-ri-line rounded-2xl max-w-lg w-full p-6 space-y-5 shadow-2xl">
              <div className="flex items-center justify-between border-b border-ri-line pb-3">
                <div className="flex items-center gap-2">
                  <Wrench className="h-5 w-5 text-ri-primary" />
                  <h3 className="font-headline-sm text-base font-bold text-ri-text">
                    Create Maintenance Job
                  </h3>
                </div>
                <button
                  onClick={() => setIsCreateOpen(false)}
                  className="text-ri-muted hover:text-ri-text text-sm p-1"
                >
                  ✕
                </button>
              </div>

              <form onSubmit={handleCreateSubmit} className="space-y-4">
                <div className="space-y-1.5">
                  <label className="font-label-sm text-xs text-ri-muted font-semibold">
                    Job Title *
                  </label>
                  <input
                    type="text"
                    required
                    value={createForm.title}
                    onChange={(e) => setCreateForm({ ...createForm, title: e.target.value })}
                    placeholder="e.g. Patch potholes on SH-42 KM 0-2"
                    className="w-full h-11 bg-ri-input border border-ri-line rounded-xl px-3 text-xs text-ri-text focus:outline-none focus:border-ri-primary"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="font-label-sm text-xs text-ri-muted font-semibold">
                    Associated Road (Optional)
                  </label>
                  <select
                    value={createForm.road_id}
                    onChange={(e) => setCreateForm({ ...createForm, road_id: e.target.value })}
                    className="w-full h-11 bg-ri-input border border-ri-line rounded-xl px-3 text-xs text-ri-text focus:outline-none focus:border-ri-primary"
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
                  <label className="font-label-sm text-xs text-ri-muted font-semibold">
                    Priority Level
                  </label>
                  <select
                    value={createForm.priority}
                    onChange={(e) => setCreateForm({ ...createForm, priority: e.target.value })}
                    className="w-full h-11 bg-ri-input border border-ri-line rounded-xl px-3 text-xs text-ri-text focus:outline-none focus:border-ri-primary"
                  >
                    <option value="CRITICAL">Critical</option>
                    <option value="HIGH">High</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="LOW">Low</option>
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="font-label-sm text-xs text-ri-muted font-semibold">
                    Due Date
                  </label>
                  <input
                    type="date"
                    value={createForm.due_at}
                    onChange={(e) => setCreateForm({ ...createForm, due_at: e.target.value })}
                    className="w-full h-11 bg-ri-input border border-ri-line rounded-xl px-3 text-xs text-ri-text focus:outline-none focus:border-ri-primary"
                  />
                </div>

                <div className="space-y-1.5">
                  <label className="font-label-sm text-xs text-ri-muted font-semibold">
                    Description
                  </label>
                  <textarea
                    rows={3}
                    value={createForm.description}
                    onChange={(e) => setCreateForm({ ...createForm, description: e.target.value })}
                    placeholder="Describe maintenance scope and specifications..."
                    className="w-full bg-ri-input border border-ri-line rounded-xl p-3 text-xs text-ri-text placeholder:text-ri-faint focus:outline-none focus:border-ri-primary"
                  />
                </div>

                <div className="flex items-center justify-end gap-3 pt-2">
                  <button
                    type="button"
                    onClick={() => setIsCreateOpen(false)}
                    className="h-10 px-4 rounded-xl bg-ri-raised border border-ri-line text-xs font-semibold text-ri-muted"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={creating}
                    className="h-10 px-5 rounded-xl bg-ri-primary hover:bg-ri-primary-bright text-ri-on-primary text-xs font-bold transition-all shadow-md shadow-ri-primary/20 disabled:opacity-50"
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
