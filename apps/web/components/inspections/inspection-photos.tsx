"use client";

import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ImageOff, X } from "lucide-react";
import { api } from "@/lib/api-client";
import type { InspectionMedia } from "@/types/api";

const fileName = (m: InspectionMedia) => m.original_filename || m.storage_path.split("/").pop() || "photo";
const isPhoto = (m: InspectionMedia) => m.media_type === "IMAGE" && m.upload_status === "COMPLETED";

function Photo({ m, className }: { m: InspectionMedia; className: string }) {
  const [failed, setFailed] = useState(false);
  if (!m.download_url || failed) {
    return (
      <span className={`${className} flex items-center justify-center`}>
        <ImageOff className="h-4 w-4 text-ri-faint" aria-label="Photo unavailable" />
      </span>
    );
  }
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={m.download_url} alt={`Inspection photo ${fileName(m)}`} loading="lazy" onError={() => setFailed(true)} className={`${className} object-cover`} />
  );
}

/**
 * The stored photos of one inspection, as uploaded from the field. Each opens at full size.
 * `media` must have been loaded with view URLs (api.inspections.getMedia(id, { includeUrls: true })).
 */
export function InspectionPhotoGrid({ media }: { media: InspectionMedia[] }) {
  const photos = media.filter(isPhoto);
  const [open, setOpen] = useState<InspectionMedia | null>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(null);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  if (photos.length === 0) return null;
  return (
    <>
      <div className="grid grid-cols-2 gap-3 p-4 sm:grid-cols-3 lg:grid-cols-4">
        {photos.map((m) => (
          <button
            key={m.id}
            type="button"
            onClick={() => setOpen(m)}
            title="Open photo"
            className="group overflow-hidden rounded-lg border border-ri-line bg-ri-bg text-left transition-colors hover:border-ri-line-strong focus:outline-none focus-visible:ring-2 focus-visible:ring-ri-primary-bright"
          >
            <Photo m={m} className="aspect-video w-full" />
            <span className="block truncate px-2.5 py-1.5 font-code-sm text-[11px] text-ri-muted group-hover:text-ri-text">{fileName(m)}</span>
          </button>
        ))}
      </div>

      {open && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label={`Inspection photo ${fileName(open)}`}
          onClick={() => setOpen(null)}
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 p-4"
        >
          <button
            type="button"
            autoFocus
            onClick={() => setOpen(null)}
            aria-label="Close photo"
            className="absolute right-4 top-4 rounded-full border border-ri-line-strong bg-ri-surface p-2 text-ri-text hover:bg-ri-raised focus:outline-none focus-visible:ring-2 focus-visible:ring-ri-primary-bright"
          >
            <X className="h-4 w-4" />
          </button>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={open.download_url ?? ""}
            alt={`Inspection photo ${fileName(open)}`}
            onClick={(e) => e.stopPropagation()}
            className="max-h-full max-w-full rounded-lg object-contain"
          />
        </div>
      )}
    </>
  );
}

/**
 * Small previews of an inspection's photos for the inspections list. They are fetched only when
 * the row comes into view, and link to the inspection.
 */
export function InspectionThumbs({ inspectionId, max = 4 }: { inspectionId: string; max?: number }) {
  const host = useRef<HTMLAnchorElement>(null);
  const [photos, setPhotos] = useState<InspectionMedia[] | null>(null);

  useEffect(() => {
    const el = host.current;
    if (!el) return;
    let cancelled = false;
    const load = () =>
      api.inspections
        .getMedia(inspectionId, { includeUrls: true })
        .then((r) => !cancelled && setPhotos((r.data ?? []).filter(isPhoto)))
        .catch(() => !cancelled && setPhotos([]));
    if (typeof IntersectionObserver === "undefined") {
      load();
      return () => {
        cancelled = true;
      };
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          observer.disconnect();
          load();
        }
      },
      { rootMargin: "200px" }
    );
    observer.observe(el);
    return () => {
      cancelled = true;
      observer.disconnect();
    };
  }, [inspectionId]);

  if (photos && photos.length === 0) return null;
  const shown = photos?.slice(0, max) ?? [];
  const more = (photos?.length ?? 0) - shown.length;
  return (
    <Link ref={host} href={`/inspections/${inspectionId}`} aria-label="Open the inspection to see its photos" className="flex items-center gap-2">
      {photos === null ? (
        <span className="ri-skeleton h-14 w-[76px] rounded-lg" aria-hidden />
      ) : (
        shown.map((m) => <Photo key={m.id} m={m} className="h-14 w-[76px] rounded-lg border border-ri-line bg-ri-bg" />)
      )}
      {more > 0 && <span className="font-code-sm text-xs text-ri-muted">+{more}</span>}
    </Link>
  );
}
