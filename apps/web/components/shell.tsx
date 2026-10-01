"use client";

import React, { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/sidebar";
import { Topbar } from "@/components/topbar";
import { useAuth } from "@/lib/auth-context";

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
      <div className="min-h-screen bg-slate-950 flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-xs text-slate-400 font-medium">Loading Road Intelligence...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Topbar />
        <main className="flex-1 p-8 overflow-y-auto">{children}</main>
      </div>
    </div>
  );
}
