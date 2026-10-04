import { HealthPoint, TimelineEvent } from "@/types/api";

// Shapes API data for charts. Snapshots without a score (INSUFFICIENT_DATA) are left out
// of trend lines rather than plotted as a number.

export type HealthChartPoint = { at: string; label: string; score: number; status: string };

export const healthSeries = (points: HealthPoint[]): HealthChartPoint[] =>
  points
    .filter((p) => typeof p.health_score === "number")
    .map((p) => ({
      at: p.calculated_at,
      label: new Date(p.calculated_at).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }),
      score: p.health_score as number,
      status: p.health_status,
    }));

const DEDUCTION_LABELS: Record<string, string> = {
  critical: "Critical damage",
  high: "High damage",
  medium: "Medium damage",
  low: "Low damage",
  recurrence: "Recurrence",
};

/** Per-factor deductions of one snapshot (traffic-scaled total and grand total excluded). */
export const deductionBars = (deductions: Record<string, number> | undefined | null) =>
  Object.entries(deductions || {})
    .filter(([k]) => k in DEDUCTION_LABELS)
    .map(([k, v]) => ({ factor: DEDUCTION_LABELS[k], points: v }))
    .filter((d) => d.points > 0);

export const countEntries = (counts: Record<string, number> | undefined | null, order?: string[]) => {
  const entries = Object.entries(counts || {});
  if (order) entries.sort((a, b) => order.indexOf(a[0]) - order.indexOf(b[0]));
  return entries.map(([name, value]) => ({ name: name.replace(/_/g, " "), value }));
};

export const filterTimeline = (events: TimelineEvent[], types: Set<string>): TimelineEvent[] =>
  types.size === 0 ? events : events.filter((e) => types.has(e.type));

export const MAINTENANCE_ORDER = ["OPEN", "ASSIGNED", "IN_PROGRESS", "COMPLETED", "VERIFICATION_PENDING", "VERIFIED", "REJECTED", "CANCELLED"];
export const HEALTH_ORDER = ["GOOD", "FAIR", "POOR", "CRITICAL", "INSUFFICIENT_DATA"];

export const escalationClass = (level?: string | null): string =>
  level === "CRITICAL"
    ? "bg-ri-danger/15 text-ri-danger border border-ri-danger/50"
    : level === "ELEVATED"
      ? "bg-ri-warning/15 text-ri-warning border border-ri-warning/50"
      : "bg-ri-line-strong text-ri-muted border border-ri-line-strong";

export const healthClass = (status?: string | null): string =>
  ({
    GOOD: "text-ri-success",
    FAIR: "text-ri-warning",
    POOR: "text-ri-orange",
    CRITICAL: "text-ri-danger",
  })[status || ""] || "text-ri-muted";
