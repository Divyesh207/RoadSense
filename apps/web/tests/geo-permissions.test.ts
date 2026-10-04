import { describe, expect, it } from "vitest";
import { haversineMeters, lineLengthMeters } from "../lib/geo";
import { hasPermission } from "../lib/permissions";
import { UserProfile } from "../types/api";

describe("geo helpers", () => {
  it("measures a known distance (one degree of latitude is about 111.2 km)", () => {
    const d = haversineMeters([73.0, 18.0], [73.0, 19.0]);
    expect(d).toBeGreaterThan(111_000);
    expect(d).toBeLessThan(111_400);
  });

  it("sums the legs of a line and returns 0 for fewer than two points", () => {
    const a = [73.7647, 18.6461];
    const b = [73.7650, 18.6465];
    const c = [73.7655, 18.6470];
    expect(lineLengthMeters([a, b, c])).toBeCloseTo(haversineMeters(a, b) + haversineMeters(b, c), 6);
    expect(lineLengthMeters([a])).toBe(0);
    expect(lineLengthMeters([])).toBe(0);
  });
});

describe("hasPermission", () => {
  const base = { id: "u", email: "e", full_name: "n", is_active: true } as const;
  const membership = (permissions: string[]) => ({
    organization_id: "org",
    organization_name: "Org",
    organization_code: "ORG",
    role_id: "r",
    role_code: "X",
    status: "ACTIVE",
    permissions,
  });

  it("gives administrators every permission, as the API does", () => {
    const admin = { ...base, role: "ADMINISTRATOR", organization_id: "org", organizations: [membership([])] } as unknown as UserProfile;
    expect(hasPermission(admin, "roads:create")).toBe(true);
  });

  it("requires the permission code on the active membership for other roles", () => {
    const inspector = { ...base, role: "FIELD_INSPECTOR", organization_id: "org", organizations: [membership(["roads:read"])] } as unknown as UserProfile;
    expect(hasPermission(inspector, "roads:create")).toBe(false);
    expect(hasPermission(inspector, "roads:read")).toBe(true);
    expect(hasPermission(null, "roads:create")).toBe(false);
  });
});
