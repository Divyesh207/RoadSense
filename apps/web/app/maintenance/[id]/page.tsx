"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AppShell } from "@/components/shell";
import { api } from "@/lib/api-client";
import {
  VERIFICATION_RESULTS,
  automatedAnalyses,
  effectiveResult,
  fmtNumber,
  imageFileError,
  isPending,
  resultBadgeClass,
  reviewInputError,
  reviewsOf,
} from "@/lib/repair";
import {
  MaintenanceAssignees,
  MaintenanceJob,
  MaintenanceJobContext,
  MaintenanceStatusHistory,
  RepairEvidence,
  RepairVerification,
} from "@/types/api";
import { AlertTriangle, ArrowLeft, Camera, Cpu, History, MapPin, RefreshCw, ShieldCheck, Upload, User } from "lucide-react";

// Maintenance job workspace: linked damage + context, assignment, state transitions,
// before/after evidence upload, automated image verification and human review.

const card = "rounded-xl border border-slate-800 bg-slate-900/60 p-5";
const label = "text-[11px] uppercase tracking-wide text-slate-500";

const statusClass = (s: string) =>
  ({
    OPEN: "bg-slate-800 text-slate-300",
    ASSIGNED: "bg-blue-950 text-blue-400",
    IN_PROGRESS: "bg-amber-950 text-amber-400",
    COMPLETED: "bg-cyan-950 text-cyan-400",
    VERIFICATION_PENDING: "bg-purple-950 text-purple-400",
    VERIFIED: "bg-emerald-950 text-emerald-400",
    REJECTED: "bg-red-950 text-red-400",
    CANCELLED: "bg-slate-800 text-slate-500",
  })[s] || "bg-slate-800 text-slate-400";

const when = (iso?: string | null) => (iso ? new Date(iso).toLocaleString() : "—");

function EvidenceThumb({ jobId, ev }: { jobId: string; ev: RepairEvidence }) {
  const [url, setUrl] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    api.repair
      .getEvidenceDownloadUrl(jobId, ev.id)
      .then((r) => setUrl(r.data?.download_url ?? null))
      .catch((e) => setErr(e.message));
  }, [jobId, ev.id]);
  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950 p-2">
      <div className="aspect-video bg-slate-900 rounded flex items-center justify-center overflow-hidden">
        {url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={url} alt={ev.evidence_type} className="object-contain w-full h-full" />
        ) : (
          <span className="text-[11px] text-slate-500">{err ? `Preview unavailable: ${err}` : "Loading…"}</span>
        )}
      </div>
      <div className="mt-2 flex items-center justify-between text-[11px]">
        <span className="font-semibold text-slate-300">{ev.evidence_type.replace(/_/g, " ")}</span>
        <span className="text-slate-500">{when(ev.created_at)}</span>
      </div>
    </div>
  );
}

function AnalysisCard({
  jobId,
  automated,
  all,
  canReview,
  onReviewed,
}: {
  jobId: string;
  automated: RepairVerification;
  all: RepairVerification[];
  canReview: boolean;
  onReviewed: () => void;
}) {
  const [images, setImages] = useState<{ before_url: string | null; after_url: string | null; before_source: string | null } | null>(null);
  const [decision, setDecision] = useState<"CONFIRMED" | "REJECTED" | "UNRESOLVED">("CONFIRMED");
  const [finalResult, setFinalResult] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const f = automated.findings || {};
  const m = automated.comparison_metrics || {};
  const region = m.region || {};
  const align = m.alignment || {};
  const reviews = reviewsOf(all, automated.id);

  useEffect(() => {
    api.repair.getVerificationImageUrls(jobId, automated.id).then((r) => setImages(r.data ?? null)).catch(() => setImages(null));
  }, [jobId, automated.id]);

  const submit = async () => {
    const problem = reviewInputError(decision, automated.result, finalResult, notes);
    if (problem) return setError(problem);
    setBusy(true);
    setError(null);
    try {
      await api.repair.reviewVerification(jobId, automated.id, {
        decision,
        final_result: decision === "REJECTED" ? finalResult : undefined,
        notes: notes || undefined,
      });
      setNotes("");
      onReviewed();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="rounded-lg border border-slate-800 bg-slate-950/60 p-4 space-y-4">
      <div className="flex flex-wrap items-center gap-2 justify-between">
        <div className="flex items-center gap-2">
          <Cpu className="h-4 w-4 text-blue-400" />
          <span className="text-sm font-semibold text-white">Automated image analysis</span>
          <span className="text-[11px] text-slate-500">{when(automated.created_at)}</span>
        </div>
        {isPending(automated) ? (
          <span className="px-2 py-0.5 rounded text-[11px] bg-blue-950 text-blue-400 animate-pulse">{automated.verification_status}</span>
        ) : automated.verification_status === "FAILED" ? (
          <span className="px-2 py-0.5 rounded text-[11px] bg-red-950 text-red-400">FAILED</span>
        ) : (
          <span className={`px-2 py-0.5 rounded text-[11px] font-bold ${resultBadgeClass(automated.result)}`}>
            Automated: {automated.result}
          </span>
        )}
      </div>

      {automated.verification_status === "FAILED" && (
        <p className="text-xs text-red-300">
          {automated.error_code}: {automated.error_message}. No result was produced; re-run once the cause is fixed.
        </p>
      )}

      <div className="grid grid-cols-2 gap-3">
        {(["before_url", "after_url"] as const).map((k) => (
          <div key={k}>
            <p className={label}>
              {k === "before_url"
                ? `Before (${images?.before_source === "INSPECTION_MEDIA" ? "original inspection photo" : "before-repair evidence"})`
                : "After repair"}
            </p>
            <div className="mt-1 aspect-video rounded bg-slate-900 overflow-hidden flex items-center justify-center">
              {images?.[k] ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={images[k]!} alt={k} className="object-contain w-full h-full" />
              ) : (
                <span className="text-[11px] text-slate-500">No image</span>
              )}
            </div>
          </div>
        ))}
      </div>

      {automated.verification_status === "COMPLETED" && (
        <>
          <div className="text-xs text-slate-300 space-y-1">
            <p>
              <span className="text-slate-500">Reason:</span> {f.reason_code}
            </p>
            {Array.isArray(f.reasons) && f.reasons.map((r: string, i: number) => <p key={i}>{r}</p>)}
          </div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
            <Metric k="Alignment" v={align.aligned ? "aligned" : `failed (${align.failure ?? "—"})`} />
            <Metric k="RANSAC inliers" v={`${align.inliers ?? "—"} / ${align.good_matches ?? "—"}`} />
            <Metric k="Overlap" v={fmtNumber(align.overlap_fraction)} />
            <Metric k="Keypoints (B/A)" v={`${align.keypoints_before ?? "—"} / ${align.keypoints_after ?? "—"}`} />
            <Metric k="Region SSIM" v={fmtNumber(region.region_ssim)} />
            <Metric k="Surroundings SSIM" v={fmtNumber(region.background_ssim)} />
            <Metric k="Change contrast" v={fmtNumber(region.change_contrast)} />
            <Metric k="Edge density B→A" v={`${fmtNumber(region.region_edge_density_before, 3)} → ${fmtNumber(region.region_edge_density_after, 3)}`} />
            <Metric k="Detections before" v={String(f.before_detection_count ?? "—")} />
            <Metric k="Detections after" v={String(f.after_detection_count ?? "—")} />
            <Metric k="Residual in repaired area" v={String(f.residual_detection_count ?? "—")} />
            <Metric k="Model" v={`${automated.model_name ?? "—"} ${automated.model_version ?? ""}`} />
          </div>
          {Array.isArray(f.residual_detections) && f.residual_detections.length > 0 && (
            <div className="text-xs text-red-300">
              Residual damage:{" "}
              {f.residual_detections.map((d: any, i: number) => (
                <span key={i} className="mr-2">
                  {d.damage_type} ({fmtNumber(d.confidence)})
                </span>
              ))}
            </div>
          )}
          <p className="text-[11px] text-slate-500">
            Algorithm {automated.algorithm_version} · detector threshold {fmtNumber(f.model?.confidence_threshold, 3)}. The outcome
            follows fixed rules on these measurements; it is not a probability. A reviewer makes the final decision.
          </p>
        </>
      )}

      {reviews.length > 0 && (
        <div className="space-y-2">
          <p className={label}>Human review</p>
          {reviews.map((r) => (
            <div key={r.id} className="text-xs rounded border border-slate-800 p-2">
              <span className="font-semibold text-slate-200">{r.review_decision}</span>: {r.previous_result} →{" "}
              <span className={`px-1.5 rounded ${resultBadgeClass(r.result)}`}>{r.result}</span>
              <span className="text-slate-500"> · {when(r.verified_at)} · reviewer {r.verified_by_user_id?.slice(0, 8)}</span>
              {r.reviewer_notes && <p className="mt-1 text-slate-400">{r.reviewer_notes}</p>}
            </div>
          ))}
        </div>
      )}

      {canReview && automated.verification_status === "COMPLETED" && (
        <div className="space-y-2 border-t border-slate-800 pt-3">
          <p className={label}>Reviewer decision</p>
          <div className="flex flex-wrap gap-2">
            {(["CONFIRMED", "REJECTED", "UNRESOLVED"] as const).map((d) => (
              <button
                key={d}
                onClick={() => setDecision(d)}
                className={`px-3 py-1 rounded text-xs border ${decision === d ? "border-blue-500 bg-blue-950 text-blue-300" : "border-slate-700 text-slate-400"}`}
              >
                {d === "CONFIRMED" ? "Confirm result" : d === "REJECTED" ? "Reject result" : "Mark unresolved"}
              </button>
            ))}
          </div>
          {decision === "REJECTED" && (
            <select
              value={finalResult}
              onChange={(e) => setFinalResult(e.target.value)}
              className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs"
            >
              <option value="">Correct outcome…</option>
              {VERIFICATION_RESULTS.filter((r) => r !== automated.result).map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          )}
          <textarea
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Reviewer notes"
            className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs h-16"
          />
          {error && <p className="text-xs text-red-400">{error}</p>}
          <button
            onClick={submit}
            disabled={busy}
            className="px-3 py-1.5 rounded bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold disabled:opacity-50"
          >
            {busy ? "Saving…" : "Submit review"}
          </button>
        </div>
      )}
    </div>
  );
}

function Metric({ k, v }: { k: string; v: string }) {
  return (
    <div className="rounded border border-slate-800 p-2">
      <p className={label}>{k}</p>
      <p className="text-slate-200 font-mono text-[12px] break-all">{v}</p>
    </div>
  );
}

export default function MaintenanceJobPage() {
  const { id } = useParams<{ id: string }>();
  const [job, setJob] = useState<MaintenanceJob | null>(null);
  const [ctx, setCtx] = useState<MaintenanceJobContext | null>(null);
  const [history, setHistory] = useState<MaintenanceStatusHistory[]>([]);
  const [evidence, setEvidence] = useState<RepairEvidence[]>([]);
  const [verifications, setVerifications] = useState<RepairVerification[]>([]);
  const [assignees, setAssignees] = useState<MaintenanceAssignees | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [transitionNotes, setTransitionNotes] = useState("");
  const [assignee, setAssignee] = useState("");
  const [uploadType, setUploadType] = useState<"BEFORE_REPAIR" | "AFTER_REPAIR">("AFTER_REPAIR");
  const [attachGps, setAttachGps] = useState(false);
  const [uploading, setUploading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    try {
      const [j, c, h, e, v] = await Promise.all([
        api.maintenance.get(id),
        api.maintenance.getContext(id),
        api.maintenance.getHistory(id),
        api.repair.listEvidence(id),
        api.repair.listVerifications(id),
      ]);
      setJob(j.data ?? null);
      setCtx(c.data ?? null);
      setHistory(h.data ?? []);
      setEvidence(e.data ?? []);
      setVerifications(v.data ?? []);
      setError(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    load();
    // Assignee list needs maintenance:assign; without it the section stays read-only.
    api.maintenance.getAssignees().then((r) => setAssignees(r.data ?? null)).catch(() => setAssignees(null));
  }, [load]);

  // Poll while an analysis is queued or running.
  const pending = verifications.some(isPending);
  useEffect(() => {
    if (!pending) return;
    const t = setInterval(() => api.repair.listVerifications(id).then((r) => setVerifications(r.data ?? [])), 3000);
    return () => clearInterval(t);
  }, [pending, id]);

  const act = async (fn: () => Promise<unknown>, ok: string) => {
    setNotice(null);
    try {
      await fn();
      setNotice(ok);
      await load();
    } catch (e: any) {
      setNotice(`Error: ${e.message}`);
    }
  };

  const upload = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file) return setNotice("Error: choose an image file first.");
    const problem = imageFileError(file);
    if (problem) return setNotice(`Error: ${problem}`);
    setUploading(true);
    let location: { latitude: number; longitude: number } | undefined;
    if (attachGps && typeof navigator !== "undefined" && navigator.geolocation) {
      location = await new Promise((resolve) =>
        navigator.geolocation.getCurrentPosition(
          (p) => resolve({ latitude: p.coords.latitude, longitude: p.coords.longitude }),
          () => resolve(undefined),
          { timeout: 8000 }
        )
      );
    }
    await act(() => api.repair.uploadEvidenceFile(id, file, uploadType, location), `${uploadType.replace("_", " ")} image uploaded.`);
    if (fileRef.current) fileRef.current.value = "";
    setUploading(false);
  };

  if (loading) return <AppShell><p className="text-sm text-slate-400">Loading maintenance job…</p></AppShell>;
  if (error || !job)
    return (
      <AppShell>
        <Link href="/maintenance" className="text-xs text-blue-400 flex items-center gap-1"><ArrowLeft className="h-3 w-3" />Maintenance</Link>
        <p className="mt-4 text-sm text-red-400">{error || "Maintenance job not found."}</p>
      </AppShell>
    );

  const analyses = automatedAnalyses(verifications);
  const others = verifications.filter((v) => v.verification_type === "HUMAN_SIGNOFF" || v.verification_type === "AUTOMATED_EVIDENCE_CHECK");
  const canVerify = job.status === "COMPLETED" || job.status === "VERIFICATION_PENDING";
  const comps = job.priority_factors?.components;

  return (
    <AppShell>
      <div className="space-y-5 max-w-6xl">
        <Link href="/maintenance" className="text-xs text-blue-400 flex items-center gap-1"><ArrowLeft className="h-3 w-3" />Maintenance</Link>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h1 className="text-xl font-bold text-white">{job.title}</h1>
            <p className="text-xs text-slate-500 mt-1">
              Created {when(job.created_at)} · started {when(job.started_at)} · completed {when(job.completed_at)} · verified {when(job.verified_at)}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <span className={`px-2 py-1 rounded text-xs font-bold ${statusClass(job.status)}`}>{job.status.replace(/_/g, " ")}</span>
            <span className="px-2 py-1 rounded text-xs bg-slate-800 text-slate-200">
              {job.priority_level} {job.priority_score != null ? `· ${job.priority_score}` : ""}
            </span>
            <button onClick={load} className="p-1.5 rounded border border-slate-700 text-slate-400"><RefreshCw className="h-3.5 w-3.5" /></button>
          </div>
        </div>
        {notice && <p className={`text-xs ${notice.startsWith("Error") ? "text-red-400" : "text-emerald-400"}`}>{notice}</p>}

        <div className="grid md:grid-cols-3 gap-4">
          <div className={card}>
            <p className={label}>Location</p>
            <p className="text-sm text-white mt-1 flex items-center gap-1"><MapPin className="h-3.5 w-3.5" />{ctx?.road?.name ?? "No road linked"}</p>
            <p className="text-xs text-slate-400">{ctx?.segment ? `Segment ${ctx.segment.segment_number}${ctx.segment.name ? ` · ${ctx.segment.name}` : ""}` : "No segment"}</p>
            <p className="text-xs text-slate-500 mt-1">Traffic class: {ctx?.road?.traffic_volume_class ?? "unknown"}</p>
          </div>
          <div className={card}>
            <p className={label}>Health context</p>
            {ctx?.segment_health || ctx?.road_health ? (
              <>
                {ctx?.segment_health && <p className="text-sm text-white mt-1">Segment: {ctx.segment_health.health_score ?? "—"} ({ctx.segment_health.health_status})</p>}
                {ctx?.road_health && <p className="text-sm text-white">Road: {ctx.road_health.health_score ?? "—"} ({ctx.road_health.health_status})</p>}
                <p className="text-[11px] text-slate-500">{ctx?.segment_health?.calculation_version ?? ctx?.road_health?.calculation_version}</p>
              </>
            ) : (
              <p className="text-xs text-slate-500 mt-1">No health snapshot yet.</p>
            )}
          </div>
          <div className={card}>
            <p className={label}>Priority breakdown {job.priority_factors?.mode ? `(${job.priority_factors.mode})` : ""}</p>
            {comps ? (
              <ul className="text-xs text-slate-300 mt-1 space-y-0.5">
                {Object.entries(comps).map(([k, v]) => (
                  <li key={k} className="flex justify-between"><span>{k.replace(/_/g, " ")}</span><span className="font-mono">{v}</span></li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-slate-500 mt-1">Set manually or created without linked damage.</p>
            )}
          </div>
        </div>

        <div className={card}>
          <p className="text-sm font-semibold text-white mb-2 flex items-center gap-2"><AlertTriangle className="h-4 w-4 text-amber-400" />Linked damage</p>
          {ctx && ctx.damages.length > 0 ? (
            <table className="w-full text-xs">
              <thead className="text-slate-500 text-left">
                <tr><th className="py-1">Type</th><th>Severity</th><th>Status</th><th>Sightings</th><th>Detected</th><th>Inspection</th></tr>
              </thead>
              <tbody>
                {ctx.damages.map((d) => (
                  <tr key={d.id} className="border-t border-slate-800 text-slate-300">
                    <td className="py-1.5">{d.damage_type ?? "—"}</td>
                    <td>{d.severity}</td>
                    <td>{d.status}</td>
                    <td>{d.observation_count}</td>
                    <td>{when(d.detected_at)}</td>
                    <td>{d.inspection_id ? <Link className="text-blue-400" href={`/inspections/${d.inspection_id}`}>{d.inspection_id.slice(0, 8)}</Link> : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <p className="text-xs text-slate-500">No damage linked to this job.</p>
          )}
        </div>

        <div className="grid md:grid-cols-2 gap-4">
          <div className={card}>
            <p className="text-sm font-semibold text-white mb-2 flex items-center gap-2"><User className="h-4 w-4" />Assignment</p>
            <p className="text-xs text-slate-300">
              {ctx?.assigned_user ? `${ctx.assigned_user.full_name} (${ctx.assigned_user.email})` : "No user assigned"}
              {ctx?.assigned_organization ? ` · contractor ${ctx.assigned_organization.name}` : ""}
            </p>
            {assignees ? (
              <div className="mt-2 flex gap-2">
                <select value={assignee} onChange={(e) => setAssignee(e.target.value)} className="flex-1 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs">
                  <option value="">Choose assignee…</option>
                  {assignees.users.map((u) => <option key={u.id} value={`user:${u.id}`}>{u.full_name} · {u.role}</option>)}
                  {assignees.contractor_organizations.map((o) => <option key={o.id} value={`org:${o.id}`}>Contractor: {o.name}</option>)}
                </select>
                <button
                  disabled={!assignee}
                  onClick={() => {
                    const [kind, aid] = assignee.split(":");
                    act(
                      () => api.maintenance.assign(id, kind === "user" ? { assigned_to_user_id: aid } : { assigned_to_organization_id: aid }),
                      "Assignment saved."
                    );
                  }}
                  className="px-3 py-1 rounded bg-slate-700 text-xs text-white disabled:opacity-40"
                >
                  Assign
                </button>
              </div>
            ) : (
              <p className="text-[11px] text-slate-500 mt-2">You do not have permission to assign this job.</p>
            )}
            {assignees && assignees.contractor_organizations.length === 0 && (
              <p className="text-[11px] text-slate-500 mt-1">No contractor organizations are registered.</p>
            )}
          </div>

          <div className={card}>
            <p className="text-sm font-semibold text-white mb-2 flex items-center gap-2"><History className="h-4 w-4" />Status</p>
            {ctx && ctx.allowed_transitions.length > 0 ? (
              <>
                <input
                  value={transitionNotes}
                  onChange={(e) => setTransitionNotes(e.target.value)}
                  placeholder="Notes (optional)"
                  className="w-full bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs mb-2"
                />
                <div className="flex flex-wrap gap-2">
                  {ctx.allowed_transitions.map((t) => (
                    <button
                      key={t}
                      onClick={() => act(() => api.maintenance.transitionStatus(id, { status: t, notes: transitionNotes || undefined }), `Moved to ${t}.`)}
                      className="px-2.5 py-1 rounded border border-slate-700 text-xs text-slate-200 hover:border-blue-500"
                    >
                      → {t.replace(/_/g, " ")}
                    </button>
                  ))}
                </div>
                <p className="text-[11px] text-slate-500 mt-2">VERIFIED / REJECTED are set by repair verification review.</p>
              </>
            ) : (
              <p className="text-xs text-slate-500">No further transitions from {job.status}.</p>
            )}
            <ul className="mt-3 space-y-1 max-h-40 overflow-y-auto text-[11px] text-slate-400">
              {history.map((h) => (
                <li key={h.id}>{when(h.changed_at)} · {h.previous_status ?? "—"} → <span className="text-slate-200">{h.new_status}</span>{h.reason ? ` · ${h.reason}` : ""}</li>
              ))}
            </ul>
          </div>
        </div>

        <div className={card}>
          <p className="text-sm font-semibold text-white mb-3 flex items-center gap-2"><Camera className="h-4 w-4" />Repair evidence</p>
          <div className="flex flex-wrap items-center gap-2 mb-3">
            <select value={uploadType} onChange={(e) => setUploadType(e.target.value as any)} className="bg-slate-900 border border-slate-700 rounded px-2 py-1 text-xs">
              <option value="BEFORE_REPAIR">Before repair</option>
              <option value="AFTER_REPAIR">After repair</option>
            </select>
            <input ref={fileRef} type="file" accept="image/jpeg,image/png,image/webp" className="text-xs text-slate-300" />
            <label className="text-xs text-slate-400 flex items-center gap-1">
              <input type="checkbox" checked={attachGps} onChange={(e) => setAttachGps(e.target.checked)} /> attach my GPS position
            </label>
            <button onClick={upload} disabled={uploading} className="px-3 py-1 rounded bg-slate-700 text-xs text-white flex items-center gap-1 disabled:opacity-50">
              <Upload className="h-3 w-3" />{uploading ? "Uploading…" : "Upload"}
            </button>
          </div>
          {evidence.length === 0 ? (
            <p className="text-xs text-slate-500">No evidence uploaded yet. Without a before-repair image, the original inspection photo of the damage is used as the BEFORE image.</p>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {evidence.map((ev) => <EvidenceThumb key={ev.id} jobId={id} ev={ev} />)}
            </div>
          )}
        </div>

        <div className={card}>
          <div className="flex items-center justify-between mb-3">
            <p className="text-sm font-semibold text-white flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-emerald-400" />Repair verification</p>
            <button
              disabled={!canVerify || pending}
              onClick={() => act(() => api.repair.queueImageVerification(id), "Image verification queued.")}
              className="px-3 py-1.5 rounded bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold disabled:opacity-40"
            >
              {pending ? "Analysis running…" : "Run image verification"}
            </button>
          </div>
          {!canVerify && <p className="text-[11px] text-slate-500 mb-2">Available once the job is COMPLETED or VERIFICATION PENDING.</p>}
          <p className="text-[11px] text-slate-500 mb-3">
            Compares the BEFORE and AFTER images with OpenCV (feature alignment, SSIM, difference and edge measures) and runs the
            deployed road-damage detector on both. Outcomes: SUCCESSFUL, SUBSTANDARD or UNRESOLVED (insufficient or ambiguous
            evidence). Not yet validated on real before/after repair photographs.
          </p>
          {analyses.length === 0 ? (
            <p className="text-xs text-slate-500">No image analysis has been run for this job.</p>
          ) : (
            <div className="space-y-4">
              {analyses.map((a) => (
                <div key={a.id}>
                  <p className="text-[11px] text-slate-500 mb-1">
                    Final outcome:{" "}
                    <span className={`px-1.5 rounded ${resultBadgeClass(effectiveResult(verifications, a))}`}>{effectiveResult(verifications, a) ?? "pending"}</span>
                  </p>
                  <AnalysisCard jobId={id} automated={a} all={verifications} canReview={canVerify} onReviewed={load} />
                </div>
              ))}
            </div>
          )}
          {others.length > 0 && (
            <div className="mt-4">
              <p className={label}>Earlier records</p>
              {others.map((v) => (
                <p key={v.id} className="text-[11px] text-slate-400">
                  {when(v.created_at)} · {v.verification_type === "HUMAN_SIGNOFF" ? `Human sign-off: ${v.verification_status}` : "Evidence presence/GPS check (no image analysis)"}
                  {v.reviewer_notes ? ` · ${v.reviewer_notes}` : ""}
                </p>
              ))}
            </div>
          )}
        </div>
      </div>
    </AppShell>
  );
}
