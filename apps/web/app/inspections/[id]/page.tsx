"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AppShell } from "@/components/shell";
import { StatusBadge } from "@/components/status-badge";
import { EmptyState } from "@/components/empty-state";
import { api } from "@/lib/api-client";
import { InspectionPhotoGrid } from "@/components/inspections/inspection-photos";
import { detectionMethodLabel, isHeuristic, scoreLabel } from "@/lib/provenance";
import {
  AuditLogItem,
  DamageRecord,
  Inspection,
  InspectionDetection,
  InspectionMedia,
} from "@/types/api";
import {
  AlertTriangle,
  ArrowLeft,
  Calendar,
  ClipboardList,
  Cpu,
  FileImage,
  History,
  MapPin,
  RefreshCw,
  ShieldCheck,
  User,
  CheckCircle2,
  Clock,
  Sparkles,
  Bot,
  AlertCircle,
  Radio,
  Layers,
} from "lucide-react";

type Section<T> = { loading: boolean; data: T[]; error: string | null };
const emptySection = <T,>(): Section<T> => ({ loading: true, data: [], error: null });

const PROCESSING_STAGES = ["DRAFT", "UPLOADING", "SUBMITTED", "PROCESSING", "ANALYZED"] as const;

const formatDateTime = (value?: string | null) => (value ? new Date(value).toLocaleString() : "—");

const errorMessage = (err: unknown, fallback: string) => {
  const e = err as { status?: number; message?: string };
  if (e?.status === 403) return "You do not have permission to view this information.";
  return e?.message || fallback;
};

export default function InspectionDetailPage() {
  const params = useParams<{ id: string }>();
  const inspectionId = params?.id;

  const [inspection, setInspection] = useState<Inspection | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<{ message: string; notFound: boolean } | null>(null);

  const [media, setMedia] = useState<Section<InspectionMedia>>(emptySection);
  const [detections, setDetections] = useState<Section<InspectionDetection>>(emptySection);
  const [damages, setDamages] = useState<Section<DamageRecord>>(emptySection);
  const [audit, setAudit] = useState<Section<AuditLogItem>>(emptySection);

  // Promotion of AI detections to damage records (manual, per-detection action)
  const [promoted, setPromoted] = useState<Record<string, DamageRecord>>({});
  const [promoting, setPromoting] = useState<string | null>(null);
  const [promotionNotice, setPromotionNotice] = useState<{ ok: boolean; text: string } | null>(null);

  const load = useCallback(async () => {
    if (!inspectionId) return;
    setLoading(true);
    setError(null);
    setMedia(emptySection());
    setDetections(emptySection());
    setDamages(emptySection());
    setAudit(emptySection());

    try {
      const res = await api.inspections.get(inspectionId);
      setInspection(res.data ?? null);
    } catch (err) {
      const e = err as { status?: number; message?: string };
      const notFound = e?.status === 404 || e?.status === 403 || e?.status === 422;
      setError({
        message: notFound
          ? "This inspection does not exist or belongs to another organization."
          : e?.message || "Failed to load inspection.",
        notFound,
      });
      setInspection(null);
      setLoading(false);
      return;
    }
    setLoading(false);

    const [mediaRes, detRes, dmgRes, auditRes] = await Promise.allSettled([
      api.inspections.getMedia(inspectionId, { includeUrls: true }),
      api.inspections.getDetections(inspectionId),
      api.damages.list({ inspection_id: inspectionId, page_size: 100 }),
      api.auditLogs.list({ entity_id: inspectionId, page_size: 50 }),
    ]);

    setMedia(
      mediaRes.status === "fulfilled"
        ? { loading: false, data: mediaRes.value.data ?? [], error: null }
        : { loading: false, data: [], error: errorMessage(mediaRes.reason, "Failed to load media.") }
    );
    setDetections(
      detRes.status === "fulfilled"
        ? { loading: false, data: detRes.value.data ?? [], error: null }
        : { loading: false, data: [], error: errorMessage(detRes.reason, "Failed to load AI detections.") }
    );
    setDamages(
      dmgRes.status === "fulfilled"
        ? { loading: false, data: dmgRes.value.data ?? [], error: null }
        : { loading: false, data: [], error: errorMessage(dmgRes.reason, "Failed to load damage records.") }
    );
    setAudit(
      auditRes.status === "fulfilled"
        ? { loading: false, data: auditRes.value.data ?? [], error: null }
        : {
            loading: false,
            data: [],
            error:
              (auditRes.reason as { status?: number })?.status === 403
                ? "Audit history is available to administrators and road authority users."
                : errorMessage(auditRes.reason, "Failed to load audit history."),
          }
    );
  }, [inspectionId]);

  useEffect(() => {
    load();
  }, [load]);

  const refreshAfterPromotion = async () => {
    if (!inspectionId) return;
    const [inspRes, dmgRes] = await Promise.allSettled([
      api.inspections.get(inspectionId),
      api.damages.list({ inspection_id: inspectionId, page_size: 100 }),
    ]);
    if (inspRes.status === "fulfilled" && inspRes.value.data) setInspection(inspRes.value.data);
    setDamages(
      dmgRes.status === "fulfilled"
        ? { loading: false, data: dmgRes.value.data ?? [], error: null }
        : { loading: false, data: [], error: errorMessage(dmgRes.reason, "Failed to load damage records.") }
    );
  };

  const promoteDetection = async (d: InspectionDetection) => {
    if (
      isHeuristic(d.detection_method, d.score_type) &&
      !window.confirm(
        "This candidate was produced by the OpenCV heuristic fallback (rule-based, not the trained model) and is " +
          "unverified. Promote it to a damage record for human review anyway?"
      )
    ) {
      return;
    }
    setPromoting(d.id);
    setPromotionNotice(null);
    try {
      const rec = (await api.damages.promoteDetection(d.id)).data;
      if (!rec) throw new Error("The API returned no damage record.");
      setPromoted((prev) => ({ ...prev, [d.id]: rec }));
      const grouped = !!rec.source_detection_id && rec.source_detection_id !== d.id;
      setPromotionNotice({
        ok: true,
        text: grouped
          ? `Grouped into existing damage record ${rec.id.slice(0, 8)} (${rec.status}) as a repeat sighting of the same damage.`
          : `Damage record ${rec.id.slice(0, 8)} created with status ${rec.status}. Review it in Damage Intelligence.`,
      });
      await refreshAfterPromotion();
    } catch (err) {
      setPromotionNotice({ ok: false, text: `Promotion failed: ${errorMessage(err, "unknown error")}` });
    } finally {
      setPromoting(null);
    }
  };

  if (loading) {
    return (
      <AppShell>
        <div className="flex flex-col items-center justify-center py-24 text-xs text-ri-muted gap-3">
          <RefreshCw className="h-6 w-6 text-ri-primary animate-spin" />
          <span className="font-code-sm">Loading field inspection record...</span>
        </div>
      </AppShell>
    );
  }

  if (error || !inspection) {
    return (
      <AppShell>
        <div className="max-w-xl mx-auto mt-16 bg-ri-surface border border-ri-line rounded-xl p-8 text-center space-y-4">
          <AlertCircle className="h-10 w-10 mx-auto text-ri-warning" />
          <div>
            <h1 className="font-headline-sm text-base font-bold text-ri-text">
              {error?.notFound ? "Inspection Not Found" : "Unable to Load Inspection"}
            </h1>
            <p className="font-body-sm text-xs text-ri-muted mt-1">
              {error?.message || "Inspection not found."}
            </p>
          </div>
          <div className="flex items-center justify-center gap-3 pt-2">
            <Link
              href="/inspections"
              className="h-10 px-4 bg-ri-raised hover:bg-ri-raised border border-ri-line text-ri-text rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all"
            >
              <ArrowLeft className="h-3.5 w-3.5" /> Back to Inspections
            </Link>
            {!error?.notFound && (
              <button
                onClick={load}
                className="h-10 px-4 bg-ri-primary hover:bg-ri-primary-bright text-ri-on-primary rounded-xl text-xs font-bold transition-all"
              >
                Retry Request
              </button>
            )}
          </div>
        </div>
      </AppShell>
    );
  }

  const failed = inspection.status === "PROCESSING_FAILED";
  const stageIndex = PROCESSING_STAGES.indexOf(inspection.status as (typeof PROCESSING_STAGES)[number]);
  const progressPct = failed ? 100 : stageIndex < 0 ? 0 : Math.round((stageIndex / (PROCESSING_STAGES.length - 1)) * 100);

  // All detections of one inspection come from the detector(s) recorded on its processing runs.
  const methods = Array.from(new Set(detections.data.map((d) => d.detection_method ?? "UNKNOWN")));
  const heuristicOnly =
    detections.data.length > 0 && detections.data.every((d) => isHeuristic(d.detection_method, d.score_type));
  const scoreHeader = scoreLabel(
    heuristicOnly
      ? "HEURISTIC_SCORE"
      : detections.data.every((d) => d.score_type === "MODEL_CONFIDENCE") && detections.data.length > 0
      ? "MODEL_CONFIDENCE"
      : null
  );

  // Model name/version exactly as recorded on the detections by the backend.
  const models = Array.from(
    new Set(
      detections.data
        .filter((d) => d.model_name)
        .map((d) => `${d.model_name}${d.model_version ? ` · ${d.model_version}` : ""}`)
    )
  );

  const aiStatus = failed
    ? "Failed"
    : inspection.status === "PROCESSING"
    ? "Running"
    : inspection.status === "ANALYZED"
    ? "Completed"
    : inspection.status === "SUBMITTED"
    ? "Not started"
    : "Awaiting submission";

  const pendingReview = damages.data.filter((d) => d.status === "PENDING_REVIEW" || d.status === "DETECTED").length;
  const reviewStatus = damages.loading
    ? "…"
    : damages.error
    ? "Unavailable"
    : pendingReview > 0
    ? `Required (${pendingReview} pending)`
    : damages.data.length > 0
    ? "Reviewed"
    : detections.data.length > 0
    ? "Detections not yet promoted"
    : "Not required";

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Navigation & Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <Link
              href="/inspections"
              className="inline-flex items-center gap-1.5 font-code-sm text-xs text-ri-primary hover:underline mb-1"
            >
              <ArrowLeft className="h-3.5 w-3.5" /> Inspections
            </Link>
            <div className="flex items-center gap-3">
              <h1 className="font-headline-sm text-2xl font-bold tracking-tight text-ri-text">
                Inspection <span className="font-code-lg text-ri-primary">#{inspection.id.slice(0, 8)}</span>
              </h1>
              <StatusBadge status={inspection.status} variant={inspection.status === "COMPLETED" ? "success" : undefined} />
            </div>
            <p className="font-code-sm text-[11px] text-ri-faint mt-0.5">{inspection.id}</p>
          </div>
          <button
            onClick={load}
            className="self-start sm:self-auto inline-flex items-center gap-2 h-10 px-4 bg-ri-raised hover:bg-ri-raised border border-ri-line text-ri-text rounded-xl font-label-md text-xs font-semibold transition-all active:scale-95"
          >
            <RefreshCw className="h-3.5 w-3.5 text-ri-primary" /> Refresh
          </button>
        </div>

        {/* Stitch Header Card (Asset Record Summary) */}
        <div className="bg-ri-surface border border-ri-line rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <span className="font-label-sm text-[11px] text-ri-primary uppercase tracking-wider font-semibold">
                Road / Segment
              </span>
              <h2 className="font-headline-sm text-lg font-bold text-ri-text mt-0.5">
                {inspection.road_name || "Unassigned road"}
              </h2>
              {inspection.segment_number != null && (
                <p className="font-code-sm text-xs text-ri-info-soft mt-0.5">
                  Segment #{inspection.segment_number}
                </p>
              )}
            </div>
            <StatusBadge status={inspection.status} variant={inspection.status === "COMPLETED" ? "success" : undefined} />
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-3 border-t border-ri-line/60">
            <div className="bg-ri-input border border-ri-line/60 p-3 rounded-xl">
              <span className="font-label-sm text-[11px] text-ri-muted">Inspector</span>
              <p className="font-headline-sm text-xs font-semibold text-ri-text mt-1 truncate">
                {inspection.inspector_name || "Field Agent"}
              </p>
            </div>
            <div className="bg-ri-input border border-ri-line/60 p-3 rounded-xl">
              <span className="font-label-sm text-[11px] text-ri-muted">Captured</span>
              <p className="font-code-sm text-xs text-ri-text mt-1">
                {formatDateTime(inspection.captured_at)}
              </p>
            </div>
            <div className="bg-ri-input border border-ri-line/60 p-3 rounded-xl">
              <span className="font-label-sm text-[11px] text-ri-muted">Submitted</span>
              <p className="font-code-sm text-xs text-ri-text mt-1">
                {formatDateTime(inspection.submitted_at)}
              </p>
            </div>
            <div className="bg-ri-input border border-ri-line/60 p-3 rounded-xl">
              <span className="font-label-sm text-[11px] text-ri-muted">Source</span>
              <p className="font-code-sm text-xs text-ri-primary mt-1 truncate">
                {inspection.source || "—"}
              </p>
            </div>
          </div>
        </div>

        {/* Processing stages */}
        <div className="bg-ri-surface border border-ri-line rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex items-center justify-between">
            <span className="font-label-md text-xs font-semibold text-ri-text">
              Processing
            </span>
            <span className="font-code-sm text-xs text-ri-muted">
              {failed ? "Failed" : `Progress: ${progressPct}%`}
            </span>
          </div>

          <div className="grid grid-cols-5 gap-2 relative">
            <div className="absolute top-4 left-6 right-6 h-0.5 bg-ri-line z-0"></div>
            {PROCESSING_STAGES.map((s, idx) => {
              const isPast = idx <= stageIndex && !failed;
              const isCurrent = idx === stageIndex && !failed;
              const isFailedStage = failed && idx === stageIndex;

              return (
                <div key={s} className="flex flex-col items-center gap-1.5 z-10 text-center">
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center font-bold text-xs shadow-sm ${
                      isFailedStage
                        ? "bg-ri-danger text-white"
                        : isPast
                        ? "bg-ri-success text-ri-on-primary"
                        : isCurrent
                        ? "bg-ri-primary text-ri-on-primary animate-pulse"
                        : "bg-ri-raised text-ri-muted border border-ri-line-strong"
                    }`}
                  >
                    {isPast ? <CheckCircle2 className="h-4 w-4" /> : idx + 1}
                  </div>
                  <span
                    className={`font-label-sm text-[11px] font-semibold ${
                      isFailedStage
                        ? "text-ri-danger"
                        : isPast
                        ? "text-ri-success"
                        : isCurrent
                        ? "text-ri-primary-bright"
                        : "text-ri-muted"
                    }`}
                  >
                    {s}
                  </span>
                </div>
              );
            })}
          </div>

          {failed && (
            <div className="p-3 bg-ri-danger/15 border border-ri-danger/30 rounded-xl text-xs text-ri-danger-soft flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-ri-danger shrink-0" />
              <span>AI processing failed. Re-run processing from the inspections list.</span>
            </div>
          )}
        </div>

        {/* Location & AI Results */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* Location */}
          <div className="bg-ri-surface border border-ri-line rounded-xl p-5 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <MapPin className="h-4 w-4 text-ri-primary" />
                <h3 className="font-headline-sm text-sm font-semibold text-ri-text">Location (WGS84)</h3>
              </div>
              <StatusBadge
                status={inspection.location ? "GPS RECORDED" : "NO GPS LOCATION"}
                variant={inspection.location ? "success" : "neutral"}
                size="sm"
              />
            </div>

            <div className="grid grid-cols-2 gap-3 pt-1">
              <div className="bg-ri-input border border-ri-line/60 rounded-xl p-3">
                <span className="font-label-sm text-[11px] text-ri-muted">Latitude</span>
                <p className="font-code-md text-sm font-bold text-ri-text mt-0.5">
                  {inspection.location ? inspection.location.latitude.toFixed(6) : "—"}
                </p>
              </div>
              <div className="bg-ri-input border border-ri-line/60 rounded-xl p-3">
                <span className="font-label-sm text-[11px] text-ri-muted">Longitude</span>
                <p className="font-code-md text-sm font-bold text-ri-text mt-0.5">
                  {inspection.location ? inspection.location.longitude.toFixed(6) : "—"}
                </p>
              </div>
              <div className="col-span-2 bg-ri-input border border-ri-line/60 rounded-xl p-3">
                <span className="font-label-sm text-[11px] text-ri-muted">Reported GPS accuracy</span>
                <p className="font-code-md text-sm font-bold text-ri-primary mt-0.5">
                  {inspection.location?.accuracy_m != null ? `±${inspection.location.accuracy_m} m` : "—"}
                </p>
              </div>
            </div>
          </div>

          {/* AI results & review (values from the backend only) */}
          <div className="bg-ri-surface border border-ri-line rounded-xl p-5 shadow-sm space-y-3 flex flex-col justify-between">
            <div>
              <div className="flex items-center gap-2 mb-2">
                <Cpu className="h-4 w-4 text-ri-primary" />
                <h3 className="font-headline-sm text-sm font-semibold text-ri-text">AI Results</h3>
              </div>
              <p className="font-code-lg text-2xl font-bold text-ri-text">
                {detections.loading ? "…" : detections.error ? "—" : detections.data.length}
              </p>
              <p className="text-[11px] text-ri-muted">detections · AI status: {aiStatus}</p>
              {methods.length > 0 && (
                <p className={`text-[11px] mt-1 ${heuristicOnly ? "text-ri-warning" : "text-ri-muted"}`}>
                  Method: {methods.map(detectionMethodLabel).join(", ")}
                </p>
              )}
              {models.length > 0 && (
                <p className="font-code-sm text-[11px] text-ri-muted mt-1">Model: {models.join(", ")}</p>
              )}
              <p className="text-[11px] text-ri-faint mt-2 leading-relaxed">
                Detections are candidates until an authorized reviewer confirms them as damage records.
              </p>
            </div>

            <div className="pt-3 border-t border-ri-line/60">
              <div className="flex items-center gap-1.5 text-[11px] text-ri-muted">
                <ShieldCheck className="h-3.5 w-3.5 text-ri-primary" /> Human review
              </div>
              <p className={`text-sm font-semibold mt-1 ${pendingReview > 0 ? "text-ri-warning" : "text-ri-text"}`}>
                {reviewStatus}
              </p>
              <p className="text-[11px] text-ri-faint mt-0.5">
                {damages.data.length} damage records from this inspection
              </p>
            </div>
          </div>
        </div>

        {inspection.notes && (
          <div className="bg-ri-surface border border-ri-line rounded-xl p-5 shadow-sm">
            <h2 className="font-headline-sm text-sm font-semibold text-ri-text mb-1">Notes</h2>
            <p className="text-xs text-ri-muted whitespace-pre-wrap">{inspection.notes}</p>
          </div>
        )}

        {/* Promotion Notice */}
        {promotionNotice && (
          <div
            className={`p-4 rounded-xl border text-xs flex items-center gap-2 ${
              promotionNotice.ok
                ? "bg-ri-success/15 border-ri-success/30 text-ri-success"
                : "bg-ri-danger/15 border-ri-danger/30 text-ri-danger-soft"
            }`}
          >
            {promotionNotice.ok ? (
              <CheckCircle2 className="h-4 w-4 shrink-0" />
            ) : (
              <AlertCircle className="h-4 w-4 shrink-0" />
            )}
            <span>{promotionNotice.text}</span>
          </div>
        )}

        {/* AI detections */}
        <Panel
          title="AI Detections"
          icon={<Cpu className="h-4 w-4 text-ri-primary" />}
          section={detections}
          empty="No AI detections for this inspection yet."
        >
          {heuristicOnly && (
            <p className="px-4 py-2 text-[11px] text-ri-warning bg-ri-warning/10 border-b border-ri-line">
              These results were produced by the OpenCV heuristic fallback (rule-based, not a trained model), not by
              the trained detection model. Scores are rule-derived, not probabilities; treat these as unverified
              candidates.
            </p>
          )}
          <table className="w-full text-left text-xs">
            <thead className="bg-ri-bg border-b border-ri-line text-ri-muted">
              <tr>
                <th className="py-3 px-4 font-semibold">Damage Type</th>
                <th className="py-3 px-4 font-semibold">{scoreHeader}</th>
                <th className="py-3 px-4 font-semibold">Method</th>
                <th className="py-3 px-4 font-semibold">Severity</th>
                <th className="py-3 px-4 font-semibold">Bounding Box (normalized)</th>
                <th className="py-3 px-4 font-semibold">Location</th>
                <th className="py-3 px-4 text-right font-semibold">Damage record</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ri-line/50 text-ri-text-soft">
              {detections.data.map((d) => {
                const record = promoted[d.id] ?? damages.data.find((r) => r.source_detection_id === d.id);
                const heuristic = isHeuristic(d.detection_method, d.score_type);

                return (
                  <tr key={d.id} className="hover:bg-ri-raised/50 transition-colors">
                    <td className="py-3 px-4 font-bold text-white">{d.damage_type}</td>
                    <td className="py-3 px-4 font-code-sm">{(d.confidence * 100).toFixed(1)}%</td>
                    <td className={`py-3 px-4 text-[11px] ${heuristic ? "text-ri-warning" : "text-ri-muted"}`}>
                      {heuristic ? "Heuristic fallback (unverified)" : detectionMethodLabel(d.detection_method)}
                    </td>
                    <td className="py-3 px-4">
                      <StatusBadge status={d.severity} size="sm" />
                    </td>
                    <td className="py-3 px-4 font-code-sm text-ri-muted">
                      {[d.bbox.x_min, d.bbox.y_min, d.bbox.x_max, d.bbox.y_max].map((v) => v.toFixed(3)).join(", ")}
                    </td>
                    <td className="py-3 px-4 font-code-sm text-ri-muted">
                      {d.location ? `${d.location.latitude.toFixed(5)}, ${d.location.longitude.toFixed(5)}` : "—"}
                    </td>
                    <td className="py-3 px-4 text-right">
                      {record ? (
                        <Link
                          href="/damages"
                          className="inline-flex items-center gap-1.5 font-code-sm text-xs text-ri-primary hover:underline"
                        >
                          <StatusBadge status={record.status} size="sm" />
                          <span>{record.id.slice(0, 8)}</span>
                        </Link>
                      ) : (
                        <button
                          onClick={() => promoteDetection(d)}
                          disabled={promoting !== null}
                          title={heuristic ? "Heuristic fallback candidate (unverified)" : "Trained-model detection"}
                          className={`h-8 px-3 rounded-lg font-label-md text-xs font-bold transition-all active:scale-95 disabled:opacity-50 ${
                            heuristic
                              ? "bg-ri-warning/20 border border-ri-warning/40 text-ri-warning hover:bg-ri-warning/30"
                              : "bg-ri-primary hover:bg-ri-primary-bright text-ri-on-primary"
                          }`}
                        >
                          {promoting === d.id
                            ? "Promoting…"
                            : heuristic
                            ? "Promote (unverified heuristic)"
                            : "Promote to Damage Record"}
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Panel>

        {/* Damage records */}
        <Panel
          title="Damage Records"
          icon={<AlertTriangle className="h-4 w-4 text-ri-warning" />}
          section={damages}
          empty="No damage records have been created from this inspection."
        >
          <table className="w-full text-left text-xs">
            <thead className="bg-ri-bg border-b border-ri-line text-ri-muted">
              <tr>
                <th className="py-3 px-4 font-semibold">Type</th>
                <th className="py-3 px-4 font-semibold">Severity</th>
                <th className="py-3 px-4 font-semibold">Status</th>
                <th className="py-3 px-4 font-semibold">Source</th>
                <th className="py-3 px-4 font-semibold">Detected</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ri-line/50 text-ri-text-soft">
              {damages.data.map((d) => (
                <tr key={d.id} className="hover:bg-ri-raised/50 transition-colors">
                  <td className="py-3 px-4 font-bold text-white">
                    <Link href="/damages" className="hover:text-ri-primary">
                      {d.damage_type_name || d.damage_type_code}
                    </Link>
                  </td>
                  <td className="py-3 px-4">
                    <StatusBadge status={d.severity} size="sm" />
                  </td>
                  <td className="py-3 px-4">
                    <StatusBadge status={d.status} size="sm" />
                  </td>
                  <td className="py-3 px-4 font-code-sm text-ri-muted">{d.source_type}</td>
                  <td className="py-3 px-4 font-code-sm text-ri-muted">
                    {formatDateTime(d.detected_at || d.created_at)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>

        {/* Media */}
        <Panel
          title="Media"
          icon={<FileImage className="h-4 w-4 text-ri-success" />}
          section={media}
          empty="No media uploaded for this inspection."
        >
          <InspectionPhotoGrid media={media.data} />
          <table className="w-full text-left text-xs">
            <thead className="bg-ri-bg border-b border-ri-line text-ri-muted">
              <tr>
                <th className="py-3 px-4 font-semibold">File</th>
                <th className="py-3 px-4 font-semibold">Type</th>
                <th className="py-3 px-4 font-semibold">Size</th>
                <th className="py-3 px-4 font-semibold">Upload Status</th>
                <th className="py-3 px-4 font-semibold">Uploaded</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ri-line/50 text-ri-text-soft">
              {media.data.map((m) => (
                <tr key={m.id} className="hover:bg-ri-raised/50 transition-colors">
                  <td className="py-3 px-4 font-code-sm text-white">
                    {m.original_filename || m.storage_path.split("/").pop()}
                  </td>
                  <td className="py-3 px-4 text-ri-muted">
                    {m.media_type} · {m.mime_type}
                  </td>
                  <td className="py-3 px-4 font-code-sm text-ri-muted">
                    {m.file_size_bytes != null ? `${(m.file_size_bytes / 1024).toFixed(1)} KB` : "—"}
                  </td>
                  <td className="py-3 px-4">
                    <StatusBadge status={m.upload_status} variant={m.upload_status === "COMPLETED" ? "success" : undefined} size="sm" />
                  </td>
                  <td className="py-3 px-4 font-code-sm text-ri-muted">{formatDateTime(m.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>

        {/* Audit history */}
        <Panel
          title="Audit History"
          icon={<History className="h-4 w-4 text-ri-primary" />}
          section={audit}
          empty="No audit events recorded for this inspection."
        >
          <table className="w-full text-left text-xs">
            <thead className="bg-ri-bg border-b border-ri-line text-ri-muted">
              <tr>
                <th className="py-3 px-4 font-semibold">Time</th>
                <th className="py-3 px-4 font-semibold">Action</th>
                <th className="py-3 px-4 font-semibold">Entity</th>
                <th className="py-3 px-4 font-semibold">Actor</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-ri-line/50 text-ri-text-soft">
              {audit.data.map((a) => (
                <tr key={a.id} className="hover:bg-ri-raised/50 transition-colors">
                  <td className="py-3 px-4 font-code-sm text-ri-muted">{formatDateTime(a.created_at)}</td>
                  <td className="py-3 px-4 text-white">{a.action}</td>
                  <td className="py-3 px-4 text-ri-muted">{a.entity_type}</td>
                  <td className="py-3 px-4 font-code-sm text-ri-muted">
                    {a.actor_user_id ? a.actor_user_id.slice(0, 8) : "system"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      </div>
    </AppShell>
  );
}

function Panel<T>({
  title,
  icon,
  section,
  empty,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  section: Section<T>;
  empty: string;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-ri-surface border border-ri-line rounded-xl overflow-hidden shadow-sm">
      <div className="p-4 border-b border-ri-line flex items-center gap-2">
        {icon}
        <h2 className="font-headline-sm text-sm font-bold text-ri-text">{title}</h2>
        {!section.loading && !section.error && (
          <span className="font-code-sm text-xs text-ri-muted">({section.data.length})</span>
        )}
      </div>
      {section.loading ? (
        <p className="py-8 text-center text-xs text-ri-muted">Loading...</p>
      ) : section.error ? (
        <p className="py-8 px-4 text-center text-xs text-ri-warning">{section.error}</p>
      ) : section.data.length === 0 ? (
        <p className="py-8 text-center text-xs text-ri-muted">{empty}</p>
      ) : (
        <div className="overflow-x-auto">{children}</div>
      )}
    </div>
  );
}
