"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { LayoutDashboard, LogIn, Menu, X } from "lucide-react";
import { BrandLogo } from "@/components/brand-logo";
import { ApiStatusBadge } from "@/components/landing-header";
import { useAuth } from "@/lib/auth-context";

const LINKS = [
  { href: "#overview", label: "Platform" },
  { href: "#how-it-works", label: "How it works" },
  { href: "#capabilities", label: "Capabilities" },
  { href: "#ai-gis", label: "AI + GIS" },
  { href: "#request-demo", label: "Request Demo" },
];

const focusRing =
  "focus:outline-none focus-visible:ring-2 focus-visible:ring-[#4CD7F6] focus-visible:ring-offset-2 focus-visible:ring-offset-[#0C1321]";

/** Public landing navigation: section links, login, and a mobile menu. */
export function LandingNav() {
  const [open, setOpen] = useState(false);
  const { isAuthenticated, isLoading } = useAuth();
  const signedIn = !isLoading && isAuthenticated;

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  const authLink = (
    <Link
      href={signedIn ? "/dashboard" : "/login"}
      className={`inline-flex items-center justify-center gap-1.5 h-10 px-4 rounded-xl bg-[#06B6D4] hover:bg-[#4CD7F6] text-[#003640] text-sm font-bold transition-colors ${focusRing}`}
    >
      {signedIn ? <LayoutDashboard className="h-4 w-4" /> : <LogIn className="h-4 w-4" />}
      {signedIn ? "Dashboard" : "Login"}
    </Link>
  );

  return (
    <header className="sticky top-0 z-50 border-b border-[#26344F] bg-[#0C1321]/90 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
        <Link href="/" aria-label="Road Intelligence home" className={`rounded-xl ${focusRing}`}>
          <BrandLogo variant="horizontal" size="md" />
        </Link>

        <nav aria-label="Primary" className="hidden lg:flex items-center gap-1">
          {LINKS.map((l) => (
            <a
              key={l.href}
              href={l.href}
              className={`px-3 py-2 rounded-lg text-sm text-[#94A3B8] hover:text-[#F1F5F9] hover:bg-[#17223A] transition-colors ${focusRing}`}
            >
              {l.label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-3">
          <ApiStatusBadge />
          <div className="hidden sm:block">{authLink}</div>
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            aria-controls="landing-mobile-menu"
            aria-label={open ? "Close menu" : "Open menu"}
            className={`lg:hidden inline-flex items-center justify-center h-10 w-10 rounded-xl border border-[#26344F] bg-[#111A2E] text-[#DCE2F6] hover:border-[#06B6D4]/50 transition-colors ${focusRing}`}
          >
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {open && (
        <nav
          id="landing-mobile-menu"
          aria-label="Mobile"
          className="lg:hidden border-t border-[#26344F] bg-[#0C1321] px-4 sm:px-6 py-3 space-y-1"
        >
          {LINKS.map((l) => (
            <a
              key={l.href}
              href={l.href}
              onClick={() => setOpen(false)}
              className={`block px-3 py-3 rounded-lg text-sm text-[#DCE2F6] hover:bg-[#17223A] transition-colors ${focusRing}`}
            >
              {l.label}
            </a>
          ))}
          <div className="pt-2 sm:hidden">{authLink}</div>
        </nav>
      )}
    </header>
  );
}
