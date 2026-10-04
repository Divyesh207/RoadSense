"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { Cpu, ScanSearch, UserCheck } from "lucide-react";
import { api } from "@/lib/api-client";
import { VerificationOverviewItem } from "@/types/api";
import { StatusBadge } from "@/components/status-badge";
import { GlassBadge, GlassModal, GlassSkeleton } from "@/components/ui/glass";
import { BeforeAfterViewer } from "@/components/repairs/before-after-viewer";

interface Images {
  before_url: string | null;
  before_source: string | null;
  after_url: string | null;
}

const when = (iso: string | null) => (iso ? new Date(iso).toLocaleString() : "—");

/**
 * Full-size before/after comparison for one verification. The automated analysis and the
 * human review are shown as two separate panels: the first is what the pipeline measured,
 * the second is what a person decided.
 */
export function VerificationCompareModal({ item, onClose }: { item: VerificationOverviewItem; onClose: () => void }) {
  const [images, setImages] = useState<Images | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api.repair
      .getVerificationImageUrls(item.maintenance_job_id, item.verification_id)
      .then((r) => !cancelled && setImages(r.data ?? null))
      .catch((e) => !cancelled && setError(e?.message || "The images could not be loaded."));
    return () => {
      cancelled = true;
    };
  }, [item.maintenance_job_id, item.verification_id]);

  return (
    <GlassModal open onClose={onClose} title={item.job_title ?? "Repair verification"} icon={ScanSearch} size="full">
      <div className="space-y-5">
        {error ? (
          <p role="alert" className="text-xs px-3 py-2 rounded-xl border border-ri-danger/40 bg-ri-danger/10 text-ri-danger-soft">
            {error}
          </p>
        ) : images ? (
          <BeforeAfterViewer
            large
            beforeUrl={images.before_url}
            afterUrl={images.after_url}
            beforeCaption={images.before_source === "INSPECTION_MEDIA" ? "original inspection photo" : "before-repair evidence"}
            afterCaption="after-repair evidence"
          />
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <GlassSkeleton className="h-[38vh]" />
            <GlassSkeleton className="h-[38vh]" />
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {/* What the pipeline measured */}
          <section className="rounded-xl border border-ri-primary/30 bg-ri-primary/5 p-4 space-y-3">
            <div className="flex items-center justify-between gap-2">
              <GlassBadge tone="primary" icon={Cpu}>
                AUTOMATED ANALYSIS
              </GlassBadge>
              {item.automated_result ? (
                <StatusBadge status={item.automated_result} size="sm" />
              ) : (
                <span className="font-code-sm text-ri-muted">{item.status}</span>
              )}
            </div>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
              <dt className="text-ri-muted">Reason</dt>
              <dd className="font-code-sm text-ri-text-soft">{item.reason_code ?? "—"}</dd>
              <dt className="text-ri-muted">Detections before / after / residual</dt>
              <dd className="font-code-sm text-ri-text-soft">
                {item.before_detection_count ?? "—"} / {item.after_detection_count ?? "—"} / {item.residual_detection_count ?? "—"}
              </dd>
              <dt className="text-ri-muted">Detector</dt>
              <dd className="font-code-sm text-ri-text-soft">
                {item.model_name ? `${item.model_name} ${item.model_version}` : "—"}
              </dd>
              <dt className="text-ri-muted">Comparison rules</dt>
              <dd className="font-code-sm text-ri-text-soft">{item.algorithm_version ?? "—"}</dd>
              <dt className="text-ri-muted">Analysed</dt>
              <dd className="font-code-sm text-ri-text-soft">{when(item.analysed_at)}</dd>
            </dl>
            <p className="text-[11px] text-ri-muted leading-relaxed">
              Image alignment, a trained detector and fixed comparison rules. It does not change the job; a person decides.
            </p>
          </section>

          {/* What a person decided */}
          <section className="rounded-xl border border-ri-review/30 bg-ri-review/5 p-4 space-y-3">
            <div className="flex items-center justify-between gap-2">
              <GlassBadge tone="review" icon={UserCheck}>
                HUMAN REVIEW
              </GlassBadge>
              {item.final_result ? (
                <StatusBadge status={item.final_result} size="sm" />
              ) : (
                <StatusBadge status="PENDING_REVIEW" label="PENDING REVIEW" size="sm" />
              )}
            </div>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
              <dt className="text-ri-muted">Decision on the automated result</dt>
              <dd className="font-code-sm text-ri-text-soft">{item.review_decision ?? "not reviewed yet"}</dd>
              <dt className="text-ri-muted">Final result</dt>
              <dd className="font-code-sm text-ri-text-soft">{item.final_result ?? "—"}</dd>
              <dt className="text-ri-muted">Reviewed</dt>
              <dd className="font-code-sm text-ri-text-soft">{when(item.reviewed_at)}</dd>
            </dl>
            {item.reviewer_notes && <p className="text-xs text-ri-text-soft leading-relaxed">“{item.reviewer_notes}”</p>}
            <p className="text-[11px] text-ri-muted leading-relaxed">
              The reviewer can confirm the automated result, reject it with their own outcome, or mark it unresolved.
            </p>
          </section>
        </div>

        <div className="flex items-center justify-between gap-3 text-xs">
          <span className="text-ri-muted">
            Maintenance job status: <span className="font-code-sm text-ri-text-soft">{item.job_status ?? "—"}</span>
          </span>
          <Link href={`/maintenance/${item.maintenance_job_id}`} className="font-semibold text-ri-primary-bright hover:underline">
            Open maintenance job
          </Link>
        </div>
      </div>
    </GlassModal>
  );
}
