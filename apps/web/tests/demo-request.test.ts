import { describe, expect, it } from "vitest";
import { demoRequestSummary, isValidEmail, validateDemoRequest } from "@/lib/demo-request";

const valid = {
  name: "A. Reviewer",
  organization: "Road Authority",
  email: "reviewer@authority.example",
  phone: "",
  message: "We want to evaluate field inspections for our network.",
};

describe("demo request form", () => {
  it("accepts a complete request with an empty optional phone", () => {
    expect(validateDemoRequest(valid)).toEqual({});
  });

  it("reports each missing required field", () => {
    const errors = validateDemoRequest({ name: "", organization: "", email: "", phone: "", message: "" });
    expect(Object.keys(errors).sort()).toEqual(["email", "message", "name", "organization"]);
  });

  it("rejects malformed email and phone", () => {
    expect(isValidEmail("not-an-email")).toBe(false);
    expect(isValidEmail("a@b.co")).toBe(true);
    const errors = validateDemoRequest({ ...valid, email: "a@b", phone: "abc" });
    expect(errors.email).toBeDefined();
    expect(errors.phone).toBeDefined();
  });

  it("builds a summary that omits an empty phone", () => {
    const summary = demoRequestSummary(valid);
    expect(summary).toContain("Organization: Road Authority");
    expect(summary).not.toContain("Phone:");
  });
});
