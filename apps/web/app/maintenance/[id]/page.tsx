"use client";

import React, { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AppShell } from "@/components/shell";
import { StatusBadge } from "@/components/status-badge";
import { EmptyState } from "@/components/empty-state";
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
import {
  AlertTriangle,
  ArrowLeft,
  Camera,
  Cpu,
  History,
  MapPin,
  RefreshCw,
  ShieldCheck,
  Upload,
  User,
  Wrench,
  CheckCircle2,
  Clock,
  Layers,
  Sparkles,
} from "lucide-react";

const card = "rounded-2xl border border-[#26344F] bg-[#111A2E] p-5 shadow-sm";
const label = "font-label-sm text-[11px] uppercase tracking-wide text-[#94A3B8] font-semibold";

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
    <div className="rounded-xl border border-[#26344F] bg-[#151B2A] p-2.5 space-y-2">
      <div className="aspect-video bg-[#0C1321] rounded-lg flex items-center justify-center overflow-hidden border border-[#26344F]/50">
        {url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={url} alt={ev.evidence_type} className="object-contain w-full h-full" />
        ) : (
          <span className="font-code-sm text-[11px] text-[#869397]">
            {err ? `Preview unavailable: ${err}` : "Loading media…"}
          </span>
        )}
      </div>
      <div className="flex items-center justify-between text-[11px]">
        <span className="font-headline-sm font-semibold text-[#F1F5F9]">
          {ev.evidence_type.replace(/_/g, " ")}
        </span>
        <span className="font-code-sm text-[#869397]">{when(ev.created_at)}</span>
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
  const [images, setImages] = useState<{
    before_url: string | null;
    after_url: string | null;
    before_source: string | null;
  } | null>(null);
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
    api.repair
      .getVerificationImageUrls(jobId, automated.id)
      .then((r) => setImages(r.data ?? null))
      .catch(() => setImages(null));
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
    <div className="rounded-2xl border border-[#26344F] bg-[#151B2A] p-5 space-y-4">
      <div className="flex flex-wrap items-center gap-2 justify-between">
        <div className="flex items-center gap-2">
          <Cpu className="h-4 w-4 text-[#06B6D4]" />
          <span className="font-headline-sm text-sm font-bold text-white">
            Automated image analysis
          </span>
          <span className="font-code-sm text-[11px] text-[#869397]">{when(automated.created_at)}</span>
        </div>
        {isPending(automated) ? (
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-[#06B6D4]/15 border border-[#06B6D4]/30 text-[#4CD7F6] animate-pulse">
            {automated.verification_status}
          </span>
        ) : automated.verification_status === "FAILED" ? (
          <span className="px-2.5 py-1 rounded-full text-xs font-semibold bg-[#EF4444]/15 border border-[#EF4444]/30 text-[#EF4444]">
            FAILED
          </span>
        ) : (
          <StatusBadge
            status={automated.result ?? "UNKNOWN"}
            label={`Automated: ${automated.result ?? "no result"}`}
            size="sm"
          />
        )}
      </div>

      {automated.verification_status === "FAILED" && (
        <p className="font-body-sm text-xs text-[#FFB4AB]">
          {automated.error_code}: {automated.error_message}. No result was produced; re-run once the cause is fixed.
        </p>
      )}

      {/* Before / After Images */}
      <div className="grid grid-cols-2 gap-3">
        {(["before_url", "after_url"] as const).map((k) => (
          <div key={k}>
            <p className={label}>
              {k === "before_url"
                ? `Before (${
                    images?.before_source === "INSPECTION_MEDIA"
                      ? "original inspection photo"
                      : "before-repair evidence"
                  })`
                : "After Repair"}
            </p>
            <div className="mt-1 aspect-video rounded-xl bg-[#0C1321] overflow-hidden flex items-center justify-center border border-[#26344F]">
              {images?.[k] ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={images[k]!} alt={k} className="object-contain w-full h-full" />
              ) : (
                <span className="font-code-sm text-[11px] text-[#64748B]">No image</span>
              )}
            </div>
          </div>
        ))}
      </div>

      {automated.verification_status === "COMPLETED" && (
        <>
          <div className="text-xs text-[#DCE2F6] space-y-1 bg-[#111A2E] p-3 rounded-xl border border-[#26344F]">
            <p>
              <span className="text-[#94A3B8]">Reason:</span>{" "}
              <span className="font-code-sm font-semibold text-[#06B6D4]">{f.reason_code}</span>
            </p>
            {Array.isArray(f.reasons) &&
              f.reasons.map((r: string, i: number) => <p key={i} className="text-[#94A3B8]">{r}</p>)}
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
            <Metric k="Alignment" v={align.aligned ? "aligned" : `failed (${align.failure ?? "—"})`} />
            <Metric k="RANSAC Inliers" v={`${align.inliers ?? "—"} / ${align.good_matches ?? "—"}`} />
            <Metric k="Overlap" v={fmtNumber(align.overlap_fraction)} />
            <Metric k="Keypoints (B/A)" v={`${align.keypoints_before ?? "—"} / ${align.keypoints_after ?? "—"}`} />
            <Metric k="Region SSIM" v={fmtNumber(region.region_ssim)} />
            <Metric k="Surroundings SSIM" v={fmtNumber(region.background_ssim)} />
            <Metric k="Change contrast" v={fmtNumber(region.change_contrast)} />
            <Metric
              k="Edge Density B→A"
              v={`${fmtNumber(region.region_edge_density_before, 3)} → ${fmtNumber(
                region.region_edge_density_after,
                3
              )}`}
            />
            <Metric k="Detections before" v={String(f.before_detection_count ?? "—")} />
            <Metric k="Detections after" v={String(f.after_detection_count ?? "—")} />
            <Metric k="Residual in repaired area" v={String(f.residual_detection_count ?? "—")} />
            <Metric k="Model" v={`${automated.model_name ?? "—"} ${automated.model_version ?? ""}`} />
          </div>

          {Array.isArray(f.residual_detections) && f.residual_detections.length > 0 && (
            <div className="text-xs text-[#FFB4AB]">
              Residual damage:{" "}
              {f.residual_detections.map((d: any, i: number) => (
                <span key={i} className="mr-2">
                  {d.damage_type} ({fmtNumber(d.confidence)})
                </span>
              ))}
            </div>
          )}

          <p className="text-[11px] text-[#64748B]">
            Algorithm {automated.algorithm_version} · detector threshold {fmtNumber(f.model?.confidence_threshold, 3)}. The outcome
            follows fixed rules on these measurements; it is not a probability. A reviewer makes the final decision.
          </p>
        </>
      )}

      {/* Human Reviews History */}
      {reviews.length > 0 && (
        <div className="space-y-2">
          <p className={label}>Human review</p>
          {reviews.map((r) => (
            <div key={r.id} className="text-xs rounded-xl border border-[#26344F] p-3 bg-[#111A2E] space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-bold text-[#F1F5F9]">{r.review_decision}</span>
                <span className="font-code-sm text-[#869397]">
                  {when(r.verified_at)} · reviewer {r.verified_by_user_id?.slice(0, 8)}
                </span>
              </div>
              <p className="font-code-sm text-[#06B6D4]">
                Outcome: {r.previous_result} → <span className="font-bold text-white">{r.result}</span>
              </p>
              {r.reviewer_notes && <p className="text-[#94A3B8] text-xs">{r.reviewer_notes}</p>}
            </div>
          ))}
        </div>
      )}

      {/* Authority Review Input */}
      {canReview && automated.verification_status === "COMPLETED" && (
        <div className="space-y-3 border-t border-[#26344F] pt-4">
          <p className={label}>Reviewer decision</p>
          <div className="flex flex-wrap gap-2">
            {(["CONFIRMED", "REJECTED", "UNRESOLVED"] as const).map((d) => (
              <button
                key={d}
                onClick={() => setDecision(d)}
                className={`px-3 py-1.5 rounded-xl font-label-md text-xs font-bold border transition-all ${
                  decision === d
                    ? "border-[#06B6D4] bg-[#06B6D4] text-[#003640]"
                    : "border-[#26344F] bg-[#17223A] text-[#94A3B8] hover:text-white"
                }`}
              >
                {d === "CONFIRMED" ? "Confirm result" : d === "REJECTED" ? "Reject result" : "Mark unresolved"}
              </button>
            ))}
          </div>

          {decision === "REJECTED" && (
            <select
              value={finalResult}
              onChange={(e) => setFinalResult(e.target.value)}
              className="bg-[#111A2E] border border-[#26344F] rounded-xl px-3 py-2 text-xs text-[#F1F5F9] w-full"
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
            className="w-full bg-[#111A2E] border border-[#26344F] rounded-xl p-3 text-xs text-[#F1F5F9] placeholder:text-[#64748B] focus:outline-none focus:border-[#06B6D4]"
            rows={2}
          />

          {error && <p className="text-xs text-[#EF4444]">{error}</p>}

          <button
            onClick={submit}
            disabled={busy}
            className="h-10 px-4 rounded-xl bg-[#06B6D4] hover:bg-[#4CD7F6] text-[#003640] font-label-md text-xs font-bold transition-all disabled:opacity-50"
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
    <div className="rounded-xl border border-[#26344F] bg-[#111A2E] p-2.5">
      <p className={label}>{k}</p>
      <p className="text-[#F1F5F9] font-code-sm text-xs font-bold mt-0.5 break-all">{v}</p>
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
    api.maintenance
      .getAssignees()
      .then((r) => setAssignees(r.data ?? null))
      .catch(() => setAssignees(null));
  }, [load]);

  const pending = verifications.some(isPending);
  useEffect(() => {
    if (!pending) return;
    const t = setInterval(
      () => api.repair.listVerifications(id).then((r) => setVerifications(r.data ?? [])),
      3000
    );
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
    await act(
      () => api.repair.uploadEvidenceFile(id, file, uploadType, location),
      `${uploadType.replace("_", " ")} image uploaded.`
    );
    if (fileRef.current) fileRef.current.value = "";
    setUploading(false);
  };

  if (loading) {
    return (
      <AppShell>
        <div className="flex items-center justify-center py-20 text-xs text-[#94A3B8]">
          Loading maintenance job workspace...
        </div>
      </AppShell>
    );
  }

  if (error || !job) {
    return (
      <AppShell>
        <Link
          href="/maintenance"
          className="font-code-sm text-xs text-[#06B6D4] flex items-center gap-1 hover:underline"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Maintenance
        </Link>
        <p className="mt-4 text-xs text-[#EF4444]">{error || "Maintenance job not found."}</p>
      </AppShell>
    );
  }

  const analyses = automatedAnalyses(verifications);
  const others = verifications.filter(
    (v) =>
      v.verification_type === "HUMAN_SIGNOFF" ||
      v.verification_type === "AUTOMATED_EVIDENCE_CHECK"
  );
  const canVerify = job.status === "COMPLETED" || job.status === "VERIFICATION_PENDING";
  const comps = job.priority_factors?.components;

  return (
    <AppShell>
      <div className="space-y-6 max-w-6xl">
        {/* Back link & Header */}
        <div>
          <Link
            href="/maintenance"
            className="inline-flex items-center gap-1.5 font-code-sm text-xs text-[#06B6D4] hover:underline mb-1"
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Maintenance
          </Link>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h1 className="font-headline-sm text-2xl font-bold text-[#F1F5F9]">{job.title}</h1>
              <p className="font-code-sm text-xs text-[#94A3B8] mt-1">
                Job ID: {job.id} · Created {when(job.created_at)} · started {when(job.started_at)} · completed{" "}
                {when(job.completed_at)} · verified {when(job.verified_at)}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <StatusBadge status={job.status} />
              <StatusBadge
                status={job.priority_level}
                label={`Priority: ${job.priority_level}${job.priority_score != null ? ` · ${job.priority_score}` : ""}`}
              />
              <button
                onClick={load}
                className="p-2 rounded-xl bg-[#17223A] border border-[#26344F] text-[#94A3B8] hover:text-white"
              >
                <RefreshCw className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>

        {notice && (
          <div
            className={`p-3.5 rounded-xl border text-xs ${
              notice.startsWith("Error")
                ? "bg-[#EF4444]/15 border-[#EF4444]/30 text-[#FFB4AB]"
                : "bg-[#10B981]/15 border-[#10B981]/30 text-[#10B981]"
            }`}
          >
            {notice}
          </div>
        )}

        {/* Context Grid */}
        <div className="grid md:grid-cols-3 gap-4">
          <div className={card}>
            <p className={label}>Location</p>
            <p className="font-headline-sm text-sm font-bold text-white mt-1 flex items-center gap-1.5">
              <MapPin className="h-4 w-4 text-[#06B6D4]" />
              {ctx?.road?.name ?? "No road linked"}
            </p>
            <p className="font-code-sm text-xs text-[#ADC6FF] mt-1">
              {ctx?.segment
                ? `Segment #${ctx.segment.segment_number}${ctx.segment.name ? ` · ${ctx.segment.name}` : ""}`
                : "No segment"}
            </p>
            <p className="text-xs text-[#64748B] mt-1">Traffic class: {ctx?.road?.traffic_volume_class ?? "unknown"}</p>
          </div>

          <div className={card}>
            <p className={label}>Health context</p>
            {ctx?.segment_health || ctx?.road_health ? (
              <div className="mt-1 space-y-1">
                {ctx?.segment_health && (
                  <p className="font-headline-sm text-sm font-bold text-[#F1F5F9]">
                    Segment: {ctx.segment_health.health_score ?? "—"} ({ctx.segment_health.health_status})
                  </p>
                )}
                {ctx?.road_health && (
                  <p className="font-code-sm text-xs text-[#94A3B8]">
                    Road: {ctx.road_health.health_score ?? "—"} ({ctx.road_health.health_status})
                  </p>
                )}
                <p className="font-code-sm text-[11px] text-[#64748B]">
                  {ctx?.segment_health?.calculation_version ?? ctx?.road_health?.calculation_version} · rule-based score
                </p>
              </div>
            ) : (
              <p className="font-body-sm text-xs text-[#94A3B8] mt-1">No health snapshot yet.</p>
            )}
          </div>

          <div className={card}>
            <p className={label}>
              Priority breakdown {job.priority_factors?.mode ? `(${job.priority_factors.mode})` : ""}
            </p>
            {comps ? (
              <ul className="text-xs text-[#DCE2F6] mt-1 space-y-1">
                {Object.entries(comps).map(([k, v]) => (
                  <li key={k} className="flex justify-between font-code-sm">
                    <span className="text-[#94A3B8]">{k.replace(/_/g, " ")}:</span>
                    <span className="text-[#06B6D4] font-bold">{v}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-[#94A3B8] mt-1">Set manually or created without linked damage.</p>
            )}
          </div>
        </div>

        {/* Linked Damage Table */}
        <div className="bg-[#111A2E] border border-[#26344F] rounded-2xl overflow-hidden shadow-sm">
          <div className="p-4 border-b border-[#26344F] flex items-center justify-between">
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-4 w-4 text-[#F59E0B]" />
              <h3 className="font-headline-sm text-sm font-bold text-white">
                Linked damage
              </h3>
            </div>
          </div>
          {ctx && ctx.damages.length > 0 ? (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-[#0C1321] border-b border-[#26344F] text-[#94A3B8]">
                  <tr>
                    <th className="py-3 px-4">Type</th>
                    <th className="py-3 px-4">Severity</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4">Sightings</th>
                    <th className="py-3 px-4">Detected</th>
                    <th className="py-3 px-4">Inspection</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#26344F]/50 text-[#DCE2F6]">
                  {ctx.damages.map((d) => (
                    <tr key={d.id} className="hover:bg-[#17223A]/50">
                      <td className="py-3 px-4 font-bold text-white">{d.damage_type ?? "—"}</td>
                      <td className="py-3 px-4">
                        <StatusBadge status={d.severity} size="sm" />
                      </td>
                      <td className="py-3 px-4">
                        <StatusBadge status={d.status} size="sm" />
                      </td>
                      <td className="py-3 px-4 font-code-sm text-[#94A3B8]">{d.observation_count}</td>
                      <td className="py-3 px-4 font-code-sm text-[#94A3B8]">{when(d.detected_at)}</td>
                      <td className="py-3 px-4 font-code-sm">
                        {d.inspection_id ? (
                          <Link className="text-[#06B6D4] hover:underline" href={`/inspections/${d.inspection_id}`}>
                            {d.inspection_id.slice(0, 8)}
                          </Link>
                        ) : (
                          "—"
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="p-8 text-center text-xs text-[#94A3B8]">No damage linked to this job.</p>
          )}
        </div>

        {/* Assignment & State Controls */}
        <div className="grid md:grid-cols-2 gap-4">
          <div className={card}>
            <p className="font-headline-sm text-sm font-bold text-white mb-2 flex items-center gap-2">
              <User className="h-4 w-4 text-[#06B6D4]" /> Assignment
            </p>
            <p className="font-body-sm text-xs text-[#DCE2F6]">
              {ctx?.assigned_user
                ? `${ctx.assigned_user.full_name} (${ctx.assigned_user.email})`
                : "No user assigned"}
              {ctx?.assigned_organization ? ` · contractor ${ctx.assigned_organization.name}` : ""}
            </p>
            {!assignees && (
              <p className="text-[11px] text-[#64748B] mt-2">You do not have permission to assign this job.</p>
            )}
            {assignees && assignees.contractor_organizations.length === 0 && (
              <p className="text-[11px] text-[#64748B] mt-2">No contractor organizations are registered.</p>
            )}
            {assignees && (
              <div className="mt-3 flex gap-2">
                <select
                  value={assignee}
                  onChange={(e) => setAssignee(e.target.value)}
                  className="flex-1 bg-[#151B2A] border border-[#26344F] rounded-xl px-3 py-2 text-xs text-[#F1F5F9]"
                >
                  <option value="">Choose assignee…</option>
                  {assignees.users.map((u) => (
                    <option key={u.id} value={`user:${u.id}`}>
                      {u.full_name} · {u.role}
                    </option>
                  ))}
                  {assignees.contractor_organizations.map((o) => (
                    <option key={o.id} value={`org:${o.id}`}>
                      Contractor: {o.name}
                    </option>
                  ))}
                </select>
                <button
                  disabled={!assignee}
                  onClick={() => {
                    const [kind, aid] = assignee.split(":");
                    act(
                      () =>
                        api.maintenance.assign(
                          id,
                          kind === "user"
                            ? { assigned_to_user_id: aid }
                            : { assigned_to_organization_id: aid }
                        ),
                      "Assignment saved."
                    );
                  }}
                  className="px-4 py-2 rounded-xl bg-[#06B6D4] hover:bg-[#4CD7F6] text-[#003640] font-label-md text-xs font-bold disabled:opacity-40"
                >
                  Assign
                </button>
              </div>
            )}
          </div>

          <div className={card}>
            <p className="font-headline-sm text-sm font-bold text-white mb-2 flex items-center gap-2">
              <History className="h-4 w-4 text-[#06B6D4]" /> Status
            </p>
            {ctx && ctx.allowed_transitions.length > 0 ? (
              <div className="space-y-3">
                <input
                  value={transitionNotes}
                  onChange={(e) => setTransitionNotes(e.target.value)}
                  placeholder="Notes (optional)"
                  className="w-full bg-[#151B2A] border border-[#26344F] rounded-xl px-3 py-2 text-xs text-[#F1F5F9] focus:outline-none focus:border-[#06B6D4]"
                />
                <div className="flex flex-wrap gap-2">
                  {ctx.allowed_transitions.map((t) => (
                    <button
                      key={t}
                      onClick={() =>
                        act(
                          () =>
                            api.maintenance.transitionStatus(id, {
                              status: t,
                              notes: transitionNotes || undefined,
                            }),
                          `Moved to ${t}.`
                        )
                      }
                      className="px-3 py-1.5 rounded-xl border border-[#06B6D4]/30 bg-[#06B6D4]/15 hover:bg-[#06B6D4]/25 text-[#4CD7F6] font-label-md text-xs font-bold transition-all"
                    >
                      → {t.replace(/_/g, " ")}
                    </button>
                  ))}
                </div>
                <p className="text-[11px] text-[#64748B]">VERIFIED / REJECTED are set by repair verification review.</p>
              </div>
            ) : (
              <p className="font-code-sm text-xs text-[#64748B]">No further transitions from {job.status}.</p>
            )}
            <ul className="mt-3 space-y-1 max-h-40 overflow-y-auto text-[11px] text-[#94A3B8]">
              {history.map((h) => (
                <li key={h.id}>
                  <span className="font-code-sm">{when(h.changed_at)}</span> · {h.previous_status ?? "—"} →{" "}
                  <span className="text-[#F1F5F9]">{h.new_status}</span>
                  {h.reason ? ` · ${h.reason}` : ""}
                </li>
              ))}
            </ul>
          </div>
        </div>

        {/* Evidence Upload */}
        <div className={card}>
          <p className="font-headline-sm text-sm font-bold text-white mb-3 flex items-center gap-2">
            <Camera className="h-4 w-4 text-[#06B6D4]" /> Repair evidence
          </p>
          <div className="flex flex-wrap items-center gap-3 mb-4 bg-[#151B2A] p-3 rounded-xl border border-[#26344F]">
            <select
              value={uploadType}
              onChange={(e) => setUploadType(e.target.value as any)}
              className="bg-[#111A2E] border border-[#26344F] rounded-xl px-3 py-1.5 text-xs text-[#F1F5F9]"
            >
              <option value="BEFORE_REPAIR">Before repair</option>
              <option value="AFTER_REPAIR">After repair</option>
            </select>
            <input
              ref={fileRef}
              type="file"
              accept="image/jpeg,image/png,image/webp"
              className="text-xs text-[#94A3B8]"
            />
            <label className="text-xs text-[#94A3B8] flex items-center gap-1.5 cursor-pointer">
              <input
                type="checkbox"
                checked={attachGps}
                onChange={(e) => setAttachGps(e.target.checked)}
                className="rounded border-[#26344F]"
              />
              <span>attach my GPS position</span>
            </label>
            <button
              onClick={upload}
              disabled={uploading}
              className="px-4 py-2 rounded-xl bg-[#06B6D4] hover:bg-[#4CD7F6] text-[#003640] font-label-md text-xs font-bold flex items-center gap-1.5 ml-auto disabled:opacity-50"
            >
              <Upload className="h-3.5 w-3.5" />
              <span>{uploading ? "Uploading…" : "Upload"}</span>
            </button>
          </div>

          {evidence.length === 0 ? (
            <p className="text-xs text-[#94A3B8] py-8 text-center">
              No evidence uploaded yet. Without a before-repair image, the original inspection photo of the damage is used
              as the BEFORE image.
            </p>
          ) : (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {evidence.map((ev) => (
                <EvidenceThumb key={ev.id} jobId={id} ev={ev} />
              ))}
            </div>
          )}
        </div>

        {/* Repair Verification Section */}
        <div className={card}>
          <div className="flex items-center justify-between mb-3">
            <p className="font-headline-sm text-sm font-bold text-white flex items-center gap-2">
              <ShieldCheck className="h-4 w-4 text-[#10B981]" /> Repair verification
            </p>
            <button
              disabled={!canVerify || pending}
              onClick={() => act(() => api.repair.queueImageVerification(id), "Image verification queued.")}
              className="px-4 py-2 rounded-xl bg-[#06B6D4] hover:bg-[#4CD7F6] text-[#003640] font-label-md text-xs font-bold disabled:opacity-40 shadow-sm"
            >
              {pending ? "Analysis running…" : "Run image verification"}
            </button>
          </div>

          {!canVerify && (
            <p className="font-code-sm text-[11px] text-[#64748B] mb-2">
              Available once the job is COMPLETED or VERIFICATION PENDING.
            </p>
          )}
          <p className="text-[11px] text-[#64748B] mb-3">
            Compares the BEFORE and AFTER images with OpenCV (feature alignment, SSIM, difference and edge measures) and
            runs the deployed road-damage detector on both. Outcomes: SUCCESSFUL, SUBSTANDARD or UNRESOLVED (insufficient
            or ambiguous evidence). Not yet validated on real before/after repair photographs.
          </p>

          {analyses.length === 0 ? (
            <p className="text-xs text-[#94A3B8] py-8 text-center">
              No image analysis has been run for this job.
            </p>
          ) : (
            <div className="space-y-4">
              {analyses.map((a) => (
                <div key={a.id}>
                  <p className="text-[11px] text-[#94A3B8] mb-1.5 flex items-center gap-1.5">
                    Final outcome:
                    <StatusBadge
                      status={effectiveResult(verifications, a) ?? "PENDING"}
                      label={effectiveResult(verifications, a) ?? "pending"}
                      size="sm"
                    />
                  </p>
                  <AnalysisCard
                    jobId={id}
                    automated={a}
                    all={verifications}
                    canReview={canVerify}
                    onReviewed={load}
                  />
                </div>
              ))}
            </div>
          )}
          {others.length > 0 && (
            <div className="mt-4">
              <p className={label}>Earlier records</p>
              {others.map((v) => (
                <p key={v.id} className="text-[11px] text-[#94A3B8]">
                  {when(v.created_at)} ·{" "}
                  {v.verification_type === "HUMAN_SIGNOFF"
                    ? `Human sign-off: ${v.verification_status}`
                    : "Evidence presence/GPS check (no image analysis)"}
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
