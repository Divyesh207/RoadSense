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
  error: { bg: "bg-[#EF4444]/15", border: "border-[#EF4444]/35", text: "text-[#EF4444]", dot: "bg-[#EF4444]" },
  orange: { bg: "bg-[#FB923C]/15", border: "border-[#FB923C]/35", text: "text-[#FB923C]", dot: "bg-[#FB923C]" },
  warning: { bg: "bg-[#F59E0B]/15", border: "border-[#F59E0B]/35", text: "text-[#F59E0B]", dot: "bg-[#F59E0B]" },
  success: { bg: "bg-[#10B981]/15", border: "border-[#10B981]/35", text: "text-[#10B981]", dot: "bg-[#10B981]" },
  primary: { bg: "bg-[#06B6D4]/15", border: "border-[#06B6D4]/35", text: "text-[#4CD7F6]", dot: "bg-[#06B6D4]" },
  info: { bg: "bg-[#3B82F6]/15", border: "border-[#3B82F6]/35", text: "text-[#ADC6FF]", dot: "bg-[#3B82F6]" },
  review: { bg: "bg-[#A78BFA]/15", border: "border-[#A78BFA]/35", text: "text-[#C4B5FD]", dot: "bg-[#A78BFA]" },
  neutral: { bg: "bg-[#232A39]", border: "border-[#3D494C]", text: "text-[#BCC9CD]", dot: "bg-[#869397]" },
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
      className={`inline-flex items-center gap-1.5 rounded-full font-code-sm font-semibold tracking-wide border ${current.bg} ${current.border} ${current.text} ${sizeClasses} ${className}`}
    >
      {showDot && (
        <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${current.dot} ${isRunning ? "animate-pulse" : ""}`} />
      )}
      <span className="truncate">{label || status}</span>
    </span>
  );
}
