"use client";

import React from "react";
import { useAuth } from "@/lib/auth-context";
import { Building2, Search } from "lucide-react";
import { ApiStatusBadge } from "@/components/landing-header";

export function Topbar() {
  const { user, organizationId } = useAuth();

  return (
    <header className="h-16 border-b border-[#26344F] bg-[#0C1321]/90 backdrop-blur-md px-6 flex items-center justify-between sticky top-0 z-40 select-none">
      {/* Search Input with Stitch Aesthetics */}
      <div className="relative w-80">
        <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-[#869397]" />
        <input
          type="text"
          placeholder="Search roads, damages, segments..."
          className="w-full pl-9 pr-4 py-2 bg-[#111A2E] border border-[#26344F] rounded-lg font-body-sm text-xs text-[#F1F5F9] placeholder:text-[#64748B] focus:outline-none focus:border-[#06B6D4] focus:ring-1 focus:ring-[#06B6D4] transition-all"
        />
      </div>

      {/* Right Controls */}
      <div className="flex items-center gap-3">
        {/* Active Organization Badge */}
        <div className="flex items-center gap-2 px-3 py-1.5 bg-[#111A2E] border border-[#26344F] rounded-lg text-xs text-[#DCE2F6]">
          <Building2 className="h-3.5 w-3.5 text-[#06B6D4]" />
          <span className="font-medium truncate max-w-[180px]">
            {user?.organization_name || "State Road Authority"}
          </span>
          <span className="font-code-sm text-[10px] text-[#869397]">
            {organizationId ? `${organizationId.slice(0, 8)}...` : ""}
          </span>
        </div>

        {/* API status from the live /health endpoints */}
        <ApiStatusBadge />
      </div>
    </header>
  );
}
