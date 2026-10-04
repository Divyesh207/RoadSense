"use client";

import React, { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { motion, useReducedMotion } from "framer-motion";
import { Sidebar } from "@/components/sidebar";
import { Topbar } from "@/components/topbar";
import { useAuth } from "@/lib/auth-context";
import { BrandLogo } from "@/components/brand-logo";

export function AppShell({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const reduceMotion = useReducedMotion();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  if (isLoading) {
    return (
      <div className="ri-ambient min-h-screen flex items-center justify-center">
        <div className="glass px-8 py-7 flex flex-col items-center gap-4">
          <BrandLogo variant="symbol" size="lg" className="motion-safe:animate-pulse" />
          <div className="flex items-center gap-2">
            <div className="h-4 w-4 border-2 border-ri-primary border-t-transparent rounded-full motion-safe:animate-spin" />
            <p className="font-code-sm text-xs text-ri-muted">Loading Road Intelligence...</p>
          </div>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="ri-ambient flex min-h-screen text-ri-text-soft">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Topbar />
        {/* A short entrance per page; skipped for users who ask for reduced motion. */}
        <motion.main
          key={pathname}
          initial={reduceMotion ? false : { opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.22, ease: [0.2, 0.8, 0.2, 1] }}
          className="flex-1 px-4 py-5 sm:px-6 lg:px-8 lg:py-6 overflow-y-auto"
        >
          <div className="w-full max-w-[1800px] mx-auto">{children}</div>
        </motion.main>
      </div>
    </div>
  );
}
