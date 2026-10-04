"use client";

import React from "react";
import { useAuth } from "@/lib/auth-context";
import { Building2, Search, User as UserIcon } from "lucide-react";
import { ApiStatusBadge } from "@/components/landing-header";

export function Topbar() {
  const { user, organizationId } = useAuth();

  return (
    <header className="sticky top-0 z-40 select-none px-4 sm:px-6 lg:px-8 pt-2 lg:pt-3">
      <div className="glass h-14 px-3 sm:px-4 flex items-center justify-between gap-3">
        {/* Search (display only: the console has no global search endpoint yet) */}
        <div className="relative w-full max-w-xs hidden md:block">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-ri-muted" />
          <input
            type="text"
            aria-label="Search"
            placeholder="Search roads, damages, segments..."
            className="w-full h-9 pl-9 pr-3 bg-ri-input border border-ri-line rounded-lg text-xs text-ri-text placeholder:text-ri-faint transition-colors hover:border-ri-line-strong focus:outline-none focus:border-ri-primary focus:ring-2 focus:ring-ri-primary/30"
          />
        </div>

        <div className="flex items-center gap-2 sm:gap-3 ml-auto min-w-0">
          {/* Organization of the signed-in account */}
          <div
            className="flex items-center gap-2 h-9 px-3 bg-ri-input border border-ri-line rounded-lg text-xs text-ri-text-soft min-w-0"
            title={user?.organization_name || undefined}
          >
            <Building2 className="h-3.5 w-3.5 text-ri-primary shrink-0" />
            <span className="font-medium truncate max-w-[120px] sm:max-w-[220px]">
              {user?.organization_name || "State Road Authority"}
            </span>
            <span className="font-code-sm text-[10px] text-ri-faint hidden xl:inline">
              {organizationId ? `${organizationId.slice(0, 8)}...` : ""}
            </span>
          </div>

          {/* Live API status from the /health endpoints */}
          <ApiStatusBadge />

          <div
            className="hidden sm:flex items-center gap-2 h-9 pl-1.5 pr-3 rounded-lg bg-ri-input border border-ri-line"
            title={user?.email || undefined}
          >
            <span className="h-6 w-6 rounded-md bg-ri-primary/15 border border-ri-primary/30 flex items-center justify-center text-ri-primary-bright">
              <UserIcon className="h-3.5 w-3.5" />
            </span>
            <span className="text-xs font-medium text-ri-text-soft truncate max-w-[140px]">{user?.full_name || "Signed in"}</span>
          </div>
        </div>
      </div>
    </header>
  );
}
