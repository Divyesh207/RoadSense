"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/sidebar";
import { Topbar } from "@/components/topbar";
import { useAuth } from "@/lib/auth-context";
import { BrandLogo } from "@/components/brand-logo";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#0C1321] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <BrandLogo variant="symbol" size="lg" className="animate-pulse" />
          <div className="flex items-center gap-2">
            <div className="h-4 w-4 border-2 border-[#06B6D4] border-t-transparent rounded-full animate-spin" />
            <p className="font-code-sm text-xs text-[#94A3B8]">
              Loading Road Intelligence...
            </p>
          </div>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="flex min-h-screen bg-[#0C1321] text-[#DCE2F6]">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Topbar />
        <main className="flex-1 p-6 lg:p-8 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}
