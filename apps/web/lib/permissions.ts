import { UserProfile } from "@/types/api";

/**
 * Mirrors the API's permission check (core/auth.py require_permission): the ADMINISTRATOR role
 * has implicit full access; any other role needs the permission code on its active membership.
 * This only decides what the UI offers; the API enforces the same rule on every request.
 */
export function hasPermission(user: UserProfile | null | undefined, permission: string): boolean {
  if (!user) return false;
  if ((user.role || "").toUpperCase() === "ADMINISTRATOR") return true;
  const membership = user.organizations?.find((m) => m.organization_id === user.organization_id);
  return !!membership?.permissions?.includes(permission);
}
