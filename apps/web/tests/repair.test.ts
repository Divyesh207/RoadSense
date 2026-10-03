import { describe, expect, it } from "vitest";
import { effectiveResult, imageFileError, isPending, reviewInputError } from "@/lib/repair";
import { RepairVerification } from "@/types/api";

const auto = (over: Partial<RepairVerification> = {}): RepairVerification => ({
  id: "a1",
  organization_id: "o",
  maintenance_job_id: "j",
  verification_status: "COMPLETED",
  verification_type: "AUTOMATED_IMAGE_ANALYSIS",
  result: "SUCCESSFUL",
  created_at: "2026-10-04T10:00:00Z",
  ...over,
});

describe("repair verification helpers", () => {
  it("uses the latest human review as the final outcome, else the automated result", () => {
    const a = auto();
    expect(effectiveResult([a], a)).toBe("SUCCESSFUL");
    const review = auto({
      id: "r1",
      verification_type: "HUMAN_REVIEW",
      verification_status: "REVIEWED",
      reviewed_verification_id: "a1",
      result: "SUBSTANDARD",
      created_at: "2026-10-04T11:00:00Z",
    });
    expect(effectiveResult([a, review], a)).toBe("SUBSTANDARD");
  });

  it("flags queued and processing analyses as pending", () => {
    expect(isPending(auto({ verification_status: "QUEUED", result: null }))).toBe(true);
    expect(isPending(auto({ verification_status: "PROCESSING", result: null }))).toBe(true);
    expect(isPending(auto())).toBe(false);
  });

  it("requires a different outcome and notes to reject a result", () => {
    expect(reviewInputError("CONFIRMED", "SUCCESSFUL", "", "")).toBeNull();
    expect(reviewInputError("REJECTED", "SUCCESSFUL", "", "x")).not.toBeNull();
    expect(reviewInputError("REJECTED", "SUCCESSFUL", "SUCCESSFUL", "x")).not.toBeNull();
    expect(reviewInputError("REJECTED", "SUCCESSFUL", "SUBSTANDARD", " ")).not.toBeNull();
    expect(reviewInputError("REJECTED", "SUCCESSFUL", "SUBSTANDARD", "edge cracks")).toBeNull();
  });

  it("validates evidence image files before upload", () => {
    expect(imageFileError({ type: "image/jpeg", size: 1000 })).toBeNull();
    expect(imageFileError({ type: "application/pdf", size: 1000 })).not.toBeNull();
    expect(imageFileError({ type: "image/png", size: 21 * 1024 * 1024 })).not.toBeNull();
    expect(imageFileError({ type: "image/png", size: 0 })).not.toBeNull();
  });
});
