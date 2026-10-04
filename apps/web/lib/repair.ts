import { RepairVerification } from "@/types/api";

// Presentation helpers for repair verification. They only format values the API
// returned; no scores are derived here.

export const VERIFICATION_RESULTS = ["SUCCESSFUL", "SUBSTANDARD", "UNRESOLVED"] as const;
export type VerificationResult = (typeof VERIFICATION_RESULTS)[number];

export const resultBadgeClass = (result?: string | null): string => {
  switch (result) {
    case "SUCCESSFUL":
      return "bg-ri-success/15 text-ri-success border border-ri-success/50";
    case "SUBSTANDARD":
      return "bg-ri-danger/15 text-ri-danger border border-ri-danger/50";
    case "UNRESOLVED":
      return "bg-ri-warning/15 text-ri-warning border border-ri-warning/50";
    default:
      return "bg-ri-line-strong text-ri-muted border border-ri-line-strong";
  }
};

export const isPending = (v: RepairVerification): boolean =>
  v.verification_type === "AUTOMATED_IMAGE_ANALYSIS" &&
  (v.verification_status === "QUEUED" || v.verification_status === "PROCESSING");

export const automatedAnalyses = (all: RepairVerification[]): RepairVerification[] =>
  all.filter((v) => v.verification_type === "AUTOMATED_IMAGE_ANALYSIS");

export const reviewsOf = (all: RepairVerification[], automatedId: string): RepairVerification[] =>
  all.filter((v) => v.verification_type === "HUMAN_REVIEW" && v.reviewed_verification_id === automatedId);

/** Final outcome of an automated analysis: the latest human review if any, else the automated result. */
export const effectiveResult = (all: RepairVerification[], automated: RepairVerification): string | null => {
  const reviews = reviewsOf(all, automated.id).sort((a, b) => b.created_at.localeCompare(a.created_at));
  return reviews[0]?.result ?? automated.result ?? null;
};

export const fmtNumber = (value: unknown, digits = 2): string =>
  typeof value === "number" && Number.isFinite(value) ? value.toFixed(digits) : "—";

/** Client-side guard mirroring the API rule: a rejection needs a different outcome and notes. */
export const reviewInputError = (
  decision: "CONFIRMED" | "REJECTED" | "UNRESOLVED",
  automatedResult: string | null | undefined,
  finalResult: string,
  notes: string
): string | null => {
  if (decision !== "REJECTED") return null;
  if (!finalResult) return "Choose the outcome you consider correct.";
  if (finalResult === automatedResult) return "A rejection must give a different outcome than the automated result.";
  if (!notes.trim()) return "Explain why the automated result is rejected.";
  return null;
};

export const ACCEPTED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp"];
export const MAX_IMAGE_BYTES = 20 * 1024 * 1024;

export const imageFileError = (file: { type: string; size: number }): string | null => {
  if (!ACCEPTED_IMAGE_TYPES.includes(file.type)) return "Only JPEG, PNG or WebP images are accepted.";
  if (file.size > MAX_IMAGE_BYTES) return "Images must be at most 20 MB.";
  if (file.size === 0) return "The file is empty.";
  return null;
};
