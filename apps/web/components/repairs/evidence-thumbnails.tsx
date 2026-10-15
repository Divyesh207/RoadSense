"use client";

import React, { useEffect, useState } from "react";
import { ImageOff } from "lucide-react";
import { api } from "@/lib/api-client";

interface Images {
  before_url: string | null;
  after_url: string | null;
}

function Thumb({ side, url, loading }: { side: "BEFORE" | "AFTER"; url: string | null; loading: boolean }) {
  const [failed, setFailed] = useState(false);
  useEffect(() => setFailed(false), [url]);
  const unavailable = !loading && (!url || failed);
  return (
    <span className="flex flex-col items-center gap-1 min-w-0">
      <span
        className={`relative h-14 w-[76px] rounded-lg overflow-hidden border bg-ri-bg flex items-center justify-center ${
          side === "BEFORE" ? "border-ri-warning/40" : "border-ri-success/40"
        }`}
      >
        {loading ? (
          <span className="ri-skeleton h-full w-full rounded-none" aria-hidden />
        ) : unavailable ? (
          <ImageOff className="h-4 w-4 text-ri-faint" aria-label="Evidence image unavailable" />
        ) : (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={url!}
            alt={`${side === "BEFORE" ? "Before" : "After"} repair evidence`}
            loading="lazy"
            onError={() => setFailed(true)}
            className="h-full w-full object-cover"
          />
        )}
      </span>
      <span className={`font-code-sm text-[9px] tracking-wider ${side === "BEFORE" ? "text-ri-warning" : "text-ri-success"}`}>
        {unavailable ? "UNAVAILABLE" : side}
      </span>
    </span>
  );
}

/**
 * The stored BEFORE and AFTER evidence of one verification, as two small previews. They are
 * the real images behind the automated analysis, fetched through the existing signed-URL
 * endpoint. Clicking opens the full comparison.
 */
export function EvidenceThumbnails({
  jobId,
  verificationId,
  onOpen,
}: {
  jobId: string;
  verificationId: string;
  onOpen: () => void;
}) {
  const [images, setImages] = useState<Images | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api.repair
      .getVerificationImageUrls(jobId, verificationId)
      .then((r) => !cancelled && setImages(r.data ?? null))
      .catch(() => !cancelled && setImages(null))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [jobId, verificationId]);

  return (
    <button
      type="button"
      onClick={onOpen}
      aria-label="Open the before and after comparison"
      title="Open the before / after comparison"
      className="group inline-flex items-start gap-2 p-1.5 rounded-xl border border-transparent hover:border-ri-primary/40 hover:bg-ri-raised transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ri-primary-bright"
    >
      <Thumb side="BEFORE" url={images?.before_url ?? null} loading={loading} />
      <Thumb side="AFTER" url={images?.after_url ?? null} loading={loading} />
    </button>
  );
}
