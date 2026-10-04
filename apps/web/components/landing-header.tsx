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
    checking: "bg-[#111A2E] border-[#26344F] text-slate-400",
    online: "bg-emerald-500/10 border-emerald-500/30 text-emerald-400",
    degraded: "bg-amber-500/10 border-amber-500/30 text-amber-400",
    offline: "bg-red-500/10 border-red-500/30 text-red-400",
  }[state.kind];

  const dot = {
    checking: "bg-slate-500",
    online: "bg-emerald-400 animate-pulse",
    degraded: "bg-amber-400",
    offline: "bg-red-400",
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
      className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-gradient-to-r from-[#06B6D4] to-[#2563EB] hover:from-[#4CD7F6] hover:to-[#3B82F6] text-[#0C1321] text-xs font-bold shadow-lg shadow-[#06B6D4]/20 transition-all"
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
