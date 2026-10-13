import React from "react";

export type StatusVariant =
  | "success"
  | "warning"
  | "orange"
  | "error"
  | "info"
  | "review"
  | "neutral"
  | "primary";

interface StatusBadgeProps {
  status: string;
  variant?: StatusVariant;
  label?: string;
  size?: "sm" | "md";
  showDot?: boolean;
  className?: string;
}

// Explicit colours for the status values the API actually returns. A value that is not
// listed falls back to neutral; pass `variant` where one word means different things
// (e.g. a CONFIRMED recurrence is bad, a CONFIRMED damage record is not).
const STATUS_VARIANTS: Record<string, StatusVariant> = {
  // Severity and priority levels
  CRITICAL: "error",
  HIGH: "orange",
  MEDIUM: "warning",
  LOW: "success",
  // Road / segment health
  GOOD: "success",
  FAIR: "warning",
  POOR: "orange",
  INSUFFICIENT_DATA: "neutral",
  // Deterioration risk bands
  SEVERE: "error",
  MODERATE: "warning",
  // Inspection lifecycle
  DRAFT: "neutral",
  UPLOADING: "primary",
  SUBMITTED: "review",
  PROCESSING: "primary",
  PROCESSED: "success",
  ANALYZED: "success",
  PROCESSING_FAILED: "error",
  FAILED: "error",
  // Media upload
  PENDING: "neutral",
  UPLOADED: "success",
  // Damage records
  DETECTED: "info",
  PENDING_REVIEW: "review",
  CONFIRMED: "success",
  REJECTED: "error",
  MAINTENANCE_SCHEDULED: "info",
  REPAIRED: "success",
  // Maintenance jobs
  OPEN: "neutral",
  ASSIGNED: "info",
  IN_PROGRESS: "warning",
  COMPLETED: "primary",
  VERIFICATION_PENDING: "review",
  VERIFIED: "success",
  CANCELLED: "neutral",
  // Repair verification
  SUCCESSFUL: "success",
  SUBSTANDARD: "error",
  UNRESOLVED: "warning",
  QUEUED: "info",
  // Recurrence
  POTENTIAL: "warning",
  DISMISSED: "neutral",
  FALSE_POSITIVE: "neutral",
  // Recurrence escalation
  NONE: "neutral",
  ELEVATED: "warning",
};

const VARIANT_STYLES: Record<StatusVariant, { bg: string; border: string; text: string; dot: string }> = {
  error: { bg: "bg-ri-danger/15", border: "border-ri-danger/35", text: "text-ri-danger", dot: "bg-ri-danger" },
  orange: { bg: "bg-ri-orange/15", border: "border-ri-orange/35", text: "text-ri-orange", dot: "bg-ri-orange" },
  warning: { bg: "bg-ri-warning/15", border: "border-ri-warning/35", text: "text-ri-warning", dot: "bg-ri-warning" },
  success: { bg: "bg-ri-success/15", border: "border-ri-success/35", text: "text-ri-success", dot: "bg-ri-success" },
  primary: { bg: "bg-ri-primary/15", border: "border-ri-primary/35", text: "text-ri-primary-bright", dot: "bg-ri-primary" },
  info: { bg: "bg-ri-info/15", border: "border-ri-info/35", text: "text-ri-info-soft", dot: "bg-ri-info" },
  review: { bg: "bg-ri-review/15", border: "border-ri-review/35", text: "text-ri-review-soft", dot: "bg-ri-review" },
  neutral: { bg: "bg-ri-raised", border: "border-ri-line-strong", text: "text-ri-text-soft", dot: "bg-ri-muted" },
};

export function statusVariant(status?: string | null): StatusVariant {
  const norm = (status || "").toUpperCase().replace(/[\s-]/g, "_");
  return STATUS_VARIANTS[norm] ?? "neutral";
}

export function StatusBadge({
  status,
  variant,
  label,
  size = "md",
  showDot = true,
  className = "",
}: StatusBadgeProps) {
  const computedVariant: StatusVariant = variant || statusVariant(status);
  const current = VARIANT_STYLES[computedVariant];
  const sizeClasses = size === "sm" ? "px-2 py-0.5 text-[10px]" : "px-2.5 py-1 text-xs";
  const isRunning = (status || "").toUpperCase() === "PROCESSING" || (status || "").toUpperCase() === "UPLOADING";

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-md font-code-sm font-semibold tracking-wide border ${current.bg} ${current.border} ${current.text} ${sizeClasses} ${className}`}
    >
      {showDot && (
        <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${current.dot} ${isRunning ? "animate-pulse" : ""}`} />
      )}
      <span className="truncate">{label || status}</span>
    </span>
  );
}
