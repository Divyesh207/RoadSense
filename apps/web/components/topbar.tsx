"use client";

import { useAuth } from "@/lib/auth-context";
import { Building2, Search, Bell, Shield } from "lucide-react";

export function Topbar() {
  const { user, organizationId } = useAuth();

  return (
    <header className="h-16 border-b border-slate-800 bg-slate-950/80 backdrop-blur px-6 flex items-center justify-between sticky top-0 z-40">
      {/* Search Input */}
      <div className="relative w-80">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-slate-500" />
        <input
          type="text"
          placeholder="Search roads, damages, segments..."
          className="w-full pl-9 pr-4 py-1.5 bg-slate-900 border border-slate-800 rounded-md text-xs text-slate-200 placeholder:text-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
        />
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-4">
        {/* Active Organization Badge */}
        <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-md text-xs text-slate-300">
          <Building2 className="h-3.5 w-3.5 text-blue-400" />
          <span className="font-medium">{user?.organization_name || "State Road Authority"}</span>
          <span className="text-[10px] text-slate-500 font-mono">
            {organizationId ? `${organizationId.slice(0, 8)}...` : ""}
          </span>
        </div>

        {/* Live Status indicator */}
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-950/40 border border-emerald-800/60 text-emerald-400 text-[11px] font-medium">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 animate-pulse" />
          API Live
        </div>
      </div>
    </header>
  );
}
