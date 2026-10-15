"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, LayoutDashboard } from "lucide-react";
import { api } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";

type ApiState =
  | { kind: "checking" }
  | { kind: "online"; version: string }
  | { kind: "degraded"; version: string | null }
  | { kind: "offline" };

/** Live API indicator backed by the public /health/live and /health/ready endpoints. */
export function ApiStatusBadge() {
  const [state, setState] = useState<ApiState>({ kind: "checking" });

  useEffect(() => {
    let cancelled = false;
    const check = async () => {
      const [live, ready] = await Promise.allSettled([api.health.live(), api.health.ready()]);
      if (cancelled) return;
      const version = live.status === "fulfilled" ? live.value.data?.version ?? null : null;
      if (live.status === "rejected" && ready.status === "rejected") {
        setState({ kind: "offline" });
      } else if (ready.status === "fulfilled" && ready.value.data?.status === "ready" && version) {
        setState({ kind: "online", version });
      } else {
        // Reachable, but /health/ready answered 503 (e.g. database down).
        setState({ kind: "degraded", version });
      }
    };
    check();
    return () => {
      cancelled = true;
    };
  }, []);

  const styles = {
    checking: "bg-ri-surface border-ri-line text-ri-muted",
    online: "bg-ri-success/10 border-ri-success/30 text-ri-success",
    degraded: "bg-ri-warning/10 border-ri-warning/30 text-ri-warning",
    offline: "bg-ri-danger/10 border-ri-danger/30 text-ri-danger",
  }[state.kind];

  const dot = {
    checking: "bg-ri-faint",
    online: "bg-ri-success animate-pulse",
    degraded: "bg-ri-warning",
    offline: "bg-ri-danger",
  }[state.kind];

  const label =
    state.kind === "checking"
      ? "Checking API..."
      : state.kind === "online"
      ? `API ONLINE · v${state.version}`
      : state.kind === "degraded"
      ? "API DEGRADED"
      : "API OFFLINE";

  return (
    <span
      className={`hidden sm:flex items-center gap-2 px-3 py-1 rounded-full border text-xs font-mono font-medium ${styles}`}
      title="Live check of the platform API health endpoints"
    >
      <span className={`h-2 w-2 rounded-full ${dot}`} />
      {label}
    </span>
  );
}

/** "Dashboard" for an existing session, otherwise "Sign In". */
export function AuthNavButton() {
  const { isAuthenticated, isLoading } = useAuth();
  const signedIn = !isLoading && isAuthenticated;

  return (
    <Link
      href={signedIn ? "/dashboard" : "/login"}
      className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-ri-primary hover:bg-ri-primary-bright text-ri-on-primary text-xs font-bold transition-all"
    >
      {signedIn ? (
        <>
          <LayoutDashboard className="h-4 w-4" />
          Dashboard
        </>
      ) : (
        <>
          Sign In
          <ArrowRight className="h-4 w-4" />
        </>
      )}
    </Link>
  );
}
