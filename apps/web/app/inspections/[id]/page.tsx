"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { AppShell } from "@/components/shell";
import { api } from "@/lib/api-client";
import { detectionMethodLabel, isHeuristic, scoreLabel } from "@/lib/provenance";
import { AuditLogItem, DamageRecord, Inspection, InspectionDetection, InspectionMedia } from "@/types/api";
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
} from "lucide-react";

// Inspection Detail Page (docs/10_UI_UX_SPECIFICATION.md section 20)

type Section<T> = { loading: boolean; data: T[]; error: string | null };

const emptySection = <T,>(): Section<T> => ({ loading: true, data: [], error: null });

// Lifecycle order used for the processing progress bar.
const PROCESSING_STAGES = ["DRAFT", "UPLOADING", "SUBMITTED", "PROCESSING", "ANALYZED"] as const;

const statusBadgeClass = (status: string) => {
  switch (status) {
    case "ANALYZED":
    case "COMPLETED":
    case "CONFIRMED":
      return "bg-emerald-950 text-emerald-400 border border-emerald-800/50";
    case "PROCESSING":
      return "bg-blue-950 text-blue-400 border border-blue-800/50 animate-pulse";
    case "SUBMITTED":
    case "PENDING_REVIEW":
      return "bg-purple-950 text-purple-400 border border-purple-800/50";
    case "PROCESSING_FAILED":
    case "REJECTED":
      return "bg-red-950 text-red-400 border border-red-800/50";
    default:
      return "bg-slate-800 text-slate-400";
  }
};

const severityClass = (severity: string) => {
  switch (severity) {
    case "CRITICAL":
      return "text-red-400";
    case "HIGH":
      return "text-orange-400";
    case "MEDIUM":
      return "text-amber-400";
    default:
      return "text-emerald-400";
  }
};

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

  // Promotion of AI detections to damage records (always a manual, per-detection action).
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
      // The API answers 404 for unknown IDs and 403 for another organization's inspection.
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
      api.inspections.getMedia(inspectionId),
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

  // Refresh inspection status and its damage records without resetting the page.
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
        <div className="flex items-center justify-center py-24 text-xs text-slate-500">
          <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
          Loading inspection...
        </div>
      </AppShell>
    );
  }

  if (error || !inspection) {
    return (
      <AppShell>
        <div className="max-w-xl mx-auto mt-16 bg-slate-900 border border-slate-800 rounded-xl p-6 text-center space-y-4">
          <AlertTriangle className="h-8 w-8 mx-auto text-amber-400" />
          <div>
            <h1 className="text-sm font-semibold text-white">
              {error?.notFound ? "Inspection not found" : "Unable to load inspection"}
            </h1>
            <p className="text-xs text-slate-400 mt-1">{error?.message || "Inspection not found."}</p>
          </div>
          <div className="flex items-center justify-center gap-2">
            <Link
              href="/inspections"
              className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs font-medium"
            >
              Back to inspections
            </Link>
            {!error?.notFound && (
              <button
                onClick={load}
                className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded text-xs font-medium"
              >
                Retry
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

  const aiStatus = failed
    ? "Failed"
    : inspection.status === "PROCESSING"
    ? "Running"
    : inspection.status === "ANALYZED"
    ? "Completed"
    : inspection.status === "SUBMITTED"
    ? "Not started"
    : "Awaiting submission";

  // All detections of one inspection come from the detector(s) recorded on its processing runs.
  const methods = Array.from(new Set(detections.data.map((d) => d.detection_method ?? "UNKNOWN")));
  const heuristicOnly = detections.data.length > 0 && detections.data.every((d) => isHeuristic(d.detection_method, d.score_type));
  const scoreHeader = scoreLabel(heuristicOnly ? "HEURISTIC_SCORE" : detections.data.every((d) => d.score_type === "MODEL_CONFIDENCE") && detections.data.length > 0 ? "MODEL_CONFIDENCE" : null);

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
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <Link href="/inspections" className="inline-flex items-center gap-1 text-[11px] text-slate-400 hover:text-blue-400">
              <ArrowLeft className="h-3 w-3" /> Inspections
            </Link>
            <div className="flex items-center gap-3 mt-1">
              <h1 className="text-xl font-bold tracking-tight text-white">
                Inspection <span className="font-mono text-blue-400">#{inspection.id.slice(0, 8)}</span>
              </h1>
              <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${statusBadgeClass(inspection.status)}`}>
                {inspection.status}
              </span>
            </div>
            <p className="text-[11px] text-slate-500 mt-1 font-mono">{inspection.id}</p>
          </div>
          <button
            onClick={load}
            className="self-start sm:self-auto inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded text-xs font-medium"
          >
            <RefreshCw className="h-3.5 w-3.5" /> Refresh
          </button>
        </div>

        {/* Summary */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <InfoCard icon={<User className="h-4 w-4 text-blue-400" />} label="Inspector" value={inspection.inspector_name || "Field Agent"} />
          <InfoCard
            icon={<ClipboardList className="h-4 w-4 text-blue-400" />}
            label="Road / Segment"
            value={inspection.road_name || "Unassigned road"}
            sub={inspection.segment_number != null ? `Segment ${inspection.segment_number}` : "No segment"}
          />
          <InfoCard
            icon={<Calendar className="h-4 w-4 text-blue-400" />}
            label="Captured"
            value={formatDateTime(inspection.captured_at)}
            sub={`Submitted: ${formatDateTime(inspection.submitted_at)}`}
          />
          <InfoCard
            icon={<MapPin className="h-4 w-4 text-blue-400" />}
            label="Location"
            value={
              inspection.location
                ? `${inspection.location.latitude.toFixed(5)}, ${inspection.location.longitude.toFixed(5)}`
                : "No GPS location"
            }
            sub={inspection.location?.accuracy_m != null ? `±${inspection.location.accuracy_m} m` : `Source: ${inspection.source}`}
          />
        </div>

        {/* Processing / AI / Review */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <h2 className="text-xs font-semibold text-slate-300 mb-3">Processing</h2>
            <div className="h-2 w-full bg-slate-800 rounded-full overflow-hidden">
              <div
                className={`h-full ${failed ? "bg-red-500" : "bg-blue-500"} transition-all`}
                style={{ width: `${progressPct}%` }}
              />
            </div>
            <div className="flex flex-wrap justify-between gap-x-2 gap-y-1 mt-2 text-[9px] tracking-tight text-slate-500">
              {PROCESSING_STAGES.map((s, i) => (
                <span key={s} className={i <= stageIndex && !failed ? "text-blue-400" : undefined}>
                  {s}
                </span>
              ))}
            </div>
            {failed && <p className="text-[11px] text-red-400 mt-2">AI processing failed. Re-run processing from the inspections list.</p>}
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <h2 className="text-xs font-semibold text-slate-300 mb-3 flex items-center gap-1.5">
              <Cpu className="h-3.5 w-3.5 text-blue-400" /> AI Results
            </h2>
            <p className="text-2xl font-bold text-white">{detections.loading ? "…" : detections.error ? "—" : detections.data.length}</p>
            <p className="text-[11px] text-slate-500">detections · AI status: {aiStatus}</p>
            {methods.length > 0 && (
              <p className={`text-[11px] mt-1 ${heuristicOnly ? "text-amber-400" : "text-slate-400"}`}>
                Method: {methods.map(detectionMethodLabel).join(", ")}
              </p>
            )}
          </div>
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <h2 className="text-xs font-semibold text-slate-300 mb-3 flex items-center gap-1.5">
              <ShieldCheck className="h-3.5 w-3.5 text-blue-400" /> Review
            </h2>
            <p className={`text-sm font-semibold ${pendingReview > 0 ? "text-purple-400" : "text-slate-200"}`}>{reviewStatus}</p>
            <p className="text-[11px] text-slate-500 mt-1">{damages.data.length} damage records from this inspection</p>
          </div>
        </div>

        {inspection.notes && (
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
            <h2 className="text-xs font-semibold text-slate-300 mb-1">Notes</h2>
            <p className="text-xs text-slate-400 whitespace-pre-wrap">{inspection.notes}</p>
          </div>
        )}

        {/* AI detections */}
        {promotionNotice && (
          <p
            className={`text-xs px-3 py-2 rounded border ${
              promotionNotice.ok
                ? "text-emerald-300 border-emerald-800/50 bg-emerald-950/30"
                : "text-red-300 border-red-800/50 bg-red-950/30"
            }`}
          >
            {promotionNotice.text}
          </p>
        )}
        <Panel title="AI Detections" icon={<Cpu className="h-3.5 w-3.5 text-blue-400" />} section={detections} empty="No AI detections for this inspection yet.">
          {heuristicOnly && (
            <p className="px-4 py-2 text-[11px] text-amber-400 bg-amber-950/30 border-b border-slate-800">
              These results were produced by the OpenCV heuristic fallback (rule-based, not a trained model), not by
              the trained detection model. Scores are rule-derived, not probabilities; treat these as unverified
              candidates.
            </p>
          )}
          <table className="w-full text-left text-xs">
            <thead className="text-slate-500 border-b border-slate-800">
              <tr>
                <th className="py-2 px-4 font-medium">Damage Type</th>
                <th className="py-2 px-4 font-medium">{scoreHeader}</th>
                <th className="py-2 px-4 font-medium">Severity</th>
                <th className="py-2 px-4 font-medium">Bounding Box (normalized)</th>
                <th className="py-2 px-4 font-medium">Location</th>
                <th className="py-2 px-4 font-medium">Damage record</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {detections.data.map((d) => {
                const record = promoted[d.id] ?? damages.data.find((r) => r.source_detection_id === d.id);
                const heuristic = isHeuristic(d.detection_method, d.score_type);
                return (
                <tr key={d.id}>
                  <td className="py-2 px-4 text-white">{d.damage_type}</td>
                  <td className="py-2 px-4">{(d.confidence * 100).toFixed(1)}%</td>
                  <td className={`py-2 px-4 font-semibold ${severityClass(d.severity)}`}>{d.severity}</td>
                  <td className="py-2 px-4 font-mono text-[11px] text-slate-400">
                    {[d.bbox.x_min, d.bbox.y_min, d.bbox.x_max, d.bbox.y_max].map((v) => v.toFixed(3)).join(", ")}
                  </td>
                  <td className="py-2 px-4 text-slate-400">
                    {d.location ? `${d.location.latitude.toFixed(5)}, ${d.location.longitude.toFixed(5)}` : "—"}
                  </td>
                  <td className="py-2 px-4">
                    {record ? (
                      <Link href="/damages" className="inline-flex items-center gap-1.5 hover:text-blue-400">
                        <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${statusBadgeClass(record.status)}`}>
                          {record.status}
                        </span>
                        <span className="font-mono text-[10px] text-slate-500">{record.id.slice(0, 8)}</span>
                      </Link>
                    ) : (
                      <button
                        onClick={() => promoteDetection(d)}
                        disabled={promoting !== null}
                        title={heuristic ? "Heuristic fallback candidate (unverified)" : "Trained-model detection"}
                        className={`px-2 py-1 rounded text-[11px] font-medium disabled:opacity-50 ${
                          heuristic
                            ? "border border-amber-700/60 text-amber-300 hover:bg-amber-950/40"
                            : "bg-blue-600 hover:bg-blue-500 text-white"
                        }`}
                      >
                        {promoting === d.id ? "Promoting…" : heuristic ? "Promote (unverified heuristic)" : "Promote to Damage Record"}
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
          icon={<AlertTriangle className="h-3.5 w-3.5 text-blue-400" />}
          section={damages}
          empty="No damage records have been created from this inspection."
        >
          <table className="w-full text-left text-xs">
            <thead className="text-slate-500 border-b border-slate-800">
              <tr>
                <th className="py-2 px-4 font-medium">Type</th>
                <th className="py-2 px-4 font-medium">Severity</th>
                <th className="py-2 px-4 font-medium">Status</th>
                <th className="py-2 px-4 font-medium">Source</th>
                <th className="py-2 px-4 font-medium">Detected</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {damages.data.map((d) => (
                <tr key={d.id}>
                  <td className="py-2 px-4 text-white">
                    <Link href="/damages" className="hover:text-blue-400">
                      {d.damage_type_name || d.damage_type_code}
                    </Link>
                  </td>
                  <td className={`py-2 px-4 font-semibold ${severityClass(d.severity)}`}>{d.severity}</td>
                  <td className="py-2 px-4">
                    <span className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${statusBadgeClass(d.status)}`}>{d.status}</span>
                  </td>
                  <td className="py-2 px-4 text-slate-400">{d.source_type}</td>
                  <td className="py-2 px-4 text-slate-500">{formatDateTime(d.detected_at || d.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>

        {/* Media */}
        <Panel title="Media" icon={<FileImage className="h-3.5 w-3.5 text-blue-400" />} section={media} empty="No media uploaded for this inspection.">
          <table className="w-full text-left text-xs">
            <thead className="text-slate-500 border-b border-slate-800">
              <tr>
                <th className="py-2 px-4 font-medium">File</th>
                <th className="py-2 px-4 font-medium">Type</th>
                <th className="py-2 px-4 font-medium">Size</th>
                <th className="py-2 px-4 font-medium">Upload Status</th>
                <th className="py-2 px-4 font-medium">Uploaded</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {media.data.map((m) => (
                <tr key={m.id}>
                  <td className="py-2 px-4 text-white">{m.original_filename || m.storage_path.split("/").pop()}</td>
                  <td className="py-2 px-4 text-slate-400">
                    {m.media_type} · {m.mime_type}
                  </td>
                  <td className="py-2 px-4 text-slate-400">
                    {m.file_size_bytes != null ? `${(m.file_size_bytes / 1024).toFixed(1)} KB` : "—"}
                  </td>
                  <td className="py-2 px-4">{m.upload_status}</td>
                  <td className="py-2 px-4 text-slate-500">{formatDateTime(m.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>

        {/* Audit history */}
        <Panel title="Audit History" icon={<History className="h-3.5 w-3.5 text-blue-400" />} section={audit} empty="No audit events recorded for this inspection.">
          <table className="w-full text-left text-xs">
            <thead className="text-slate-500 border-b border-slate-800">
              <tr>
                <th className="py-2 px-4 font-medium">Time</th>
                <th className="py-2 px-4 font-medium">Action</th>
                <th className="py-2 px-4 font-medium">Entity</th>
                <th className="py-2 px-4 font-medium">Actor</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              {audit.data.map((a) => (
                <tr key={a.id}>
                  <td className="py-2 px-4 text-slate-500">{formatDateTime(a.created_at)}</td>
                  <td className="py-2 px-4 text-white">{a.action}</td>
                  <td className="py-2 px-4 text-slate-400">{a.entity_type}</td>
                  <td className="py-2 px-4 font-mono text-[11px] text-slate-400">{a.actor_user_id ? a.actor_user_id.slice(0, 8) : "system"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Panel>
      </div>
    </AppShell>
  );
}

function InfoCard({ icon, label, value, sub }: { icon: React.ReactNode; label: string; value: string; sub?: string }) {
  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
      <div className="flex items-center gap-2 text-[11px] text-slate-400 font-medium">
        {icon}
        {label}
      </div>
      <p className="text-sm font-semibold text-white mt-2 break-words">{value}</p>
      {sub && <p className="text-[11px] text-slate-500 mt-0.5">{sub}</p>}
    </div>
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
    <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-800 flex items-center gap-1.5">
        {icon}
        <h2 className="text-xs font-semibold text-slate-300">{title}</h2>
        {!section.loading && !section.error && <span className="text-[10px] text-slate-500 ml-1">({section.data.length})</span>}
      </div>
      {section.loading ? (
        <p className="py-6 text-center text-xs text-slate-500">Loading...</p>
      ) : section.error ? (
        <p className="py-6 px-4 text-center text-xs text-amber-400">{section.error}</p>
      ) : section.data.length === 0 ? (
        <p className="py-6 text-center text-xs text-slate-500">{empty}</p>
      ) : (
        <div className="overflow-x-auto">{children}</div>
      )}
    </div>
  );
}
