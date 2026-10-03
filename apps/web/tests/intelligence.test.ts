import { describe, expect, it } from "vitest";
import { countEntries, deductionBars, filterTimeline, healthSeries, MAINTENANCE_ORDER } from "@/lib/intelligence";
import { HealthPoint, TimelineEvent } from "@/types/api";

const point = (score: number | null, at: string): HealthPoint => ({
  id: at,
  road_segment_id: null,
  health_score: score,
  health_status: score == null ? "INSUFFICIENT_DATA" : "FAIR",
  calculation_version: "health-v1.1.0",
  calculated_at: at,
  score_deductions: {},
});

describe("road intelligence chart helpers", () => {
  it("never plots insufficient-data snapshots as a score", () => {
    const s = healthSeries([point(null, "2026-10-01T00:00:00Z"), point(72, "2026-10-02T00:00:00Z")]);
    expect(s).toHaveLength(1);
    expect(s[0].score).toBe(72);
  });

  it("shows per-factor deductions only, without totals or zero entries", () => {
    const bars = deductionBars({ critical: 25, high: 0, medium: 7, recurrence: 5, damage_after_traffic: 32, total_deduction: 37 });
    expect(bars).toEqual([
      { factor: "Critical damage", points: 25 },
      { factor: "Medium damage", points: 7 },
      { factor: "Recurrence", points: 5 },
    ]);
    expect(deductionBars(null)).toEqual([]);
  });

  it("orders status counts in lifecycle order", () => {
    const out = countEntries({ VERIFIED: 1, OPEN: 2, IN_PROGRESS: 3 }, MAINTENANCE_ORDER);
    expect(out.map((o) => o.name)).toEqual(["OPEN", "IN PROGRESS", "VERIFIED"]);
  });

  it("filters the timeline by event type", () => {
    const ev = (type: TimelineEvent["type"]): TimelineEvent => ({ type, at: "2026-10-01T00:00:00Z", title: type, entity_id: "x", data: {} });
    const all = [ev("DAMAGE"), ev("HEALTH"), ev("RECURRENCE")];
    expect(filterTimeline(all, new Set())).toHaveLength(3);
    expect(filterTimeline(all, new Set(["RECURRENCE"])).map((e) => e.type)).toEqual(["RECURRENCE"]);
  });
});
