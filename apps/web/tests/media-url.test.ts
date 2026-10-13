import { describe, expect, it } from "vitest";
import { resolveMediaUrl } from "@/lib/media-url";

const API = "http://localhost:8000/api/v1";

describe("resolveMediaUrl", () => {
  it("re-addresses the platform's own storage URLs to the API base and keeps the signature", () => {
    const signed = "http://192.168.1.104:8000/api/v1/storage/local/repair-evidence/org/job/a.jpg?expires=1&signature=abc";
    expect(resolveMediaUrl(signed, API)).toBe(
      "http://localhost:8000/api/v1/storage/local/repair-evidence/org/job/a.jpg?expires=1&signature=abc"
    );
  });

  it("leaves external storage URLs unchanged", () => {
    const external = "https://project.supabase.co/storage/v1/object/sign/bucket/a.jpg?token=t";
    expect(resolveMediaUrl(external, API)).toBe(external);
  });

  it("returns null for a missing URL and passes through anything that is not a URL", () => {
    expect(resolveMediaUrl(null, API)).toBeNull();
    expect(resolveMediaUrl(undefined, API)).toBeNull();
    expect(resolveMediaUrl("not a url", API)).toBe("not a url");
  });
});
