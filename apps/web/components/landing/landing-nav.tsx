"use client";

import React, { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { Menu, X } from "lucide-react";
import { useAuth } from "@/lib/auth-context";

const LINKS = [
  { href: "#overview", label: "Platform" },
  { href: "#how-it-works", label: "How it works" },
  { href: "#capabilities", label: "Capabilities" },
  { href: "#ai-gis", label: "AI + GIS" },
];

const focusRing = "focus:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-black";

/**
 * Public landing navigation: a liquid-glass bar with the brand, section links (medium screens
 * and up) and the sign-in action. It stays at the top while the page scrolls and turns more
 * opaque once it leaves the hero video, so it stays readable over text.
 */
export function LandingNav() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const { isAuthenticated, isLoading } = useAuth();
  const signedIn = !isLoading && isAuthenticated;

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > window.innerHeight * 0.6);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  const solid: React.CSSProperties | undefined = scrolled || open
    ? { background: "rgba(0, 0, 0, 0.78)", backdropFilter: "blur(14px)", WebkitBackdropFilter: "blur(14px)" }
    : undefined;

  return (
    <header className="fixed inset-x-0 top-0 z-50 px-6 md:px-12 lg:px-16 pt-6 text-white pointer-events-none">
      <div
        className="liquid-glass rounded-xl px-4 py-2 flex items-center justify-between gap-4 pointer-events-auto transition-[background] duration-300"
        style={solid}
      >
        <Link href="/" aria-label="Road Intelligence home" className={`inline-flex items-center gap-2.5 rounded-lg ${focusRing}`}>
          <Image src="/logo-icon.png" alt="" width={28} height={28} priority className="h-7 w-7 rounded-md object-contain" />
          <span className="text-lg md:text-2xl font-semibold tracking-tight whitespace-nowrap">Road Intelligence</span>
        </Link>

        <nav aria-label="Primary" className="hidden md:flex items-center gap-8 text-sm">
          {LINKS.map((l) => (
            <a key={l.href} href={l.href} className={`transition-colors hover:text-gray-300 rounded ${focusRing}`}>
              {l.label}
            </a>
          ))}
        </nav>

        <div className="flex items-center gap-2">
          <Link
            href={signedIn ? "/dashboard" : "/login"}
            className={`bg-white text-black px-4 sm:px-6 py-2 rounded-lg text-sm font-medium transition-colors hover:bg-gray-100 ${focusRing}`}
          >
            {signedIn ? "Dashboard" : "Login"}
          </Link>
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            aria-controls="landing-mobile-menu"
            aria-label={open ? "Close menu" : "Open menu"}
            className={`md:hidden inline-flex items-center justify-center h-9 w-9 rounded-lg border border-white/20 transition-colors hover:bg-white hover:text-black ${focusRing}`}
          >
            {open ? <X className="h-4 w-4" /> : <Menu className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {open && (
        <nav
          id="landing-mobile-menu"
          aria-label="Mobile"
          className="md:hidden liquid-glass rounded-xl mt-2 p-2 pointer-events-auto"
          style={{ background: "rgba(0, 0, 0, 0.82)", backdropFilter: "blur(14px)", WebkitBackdropFilter: "blur(14px)" }}
        >
          {[...LINKS, { href: "#request-demo", label: "Request Demo" }].map((l) => (
            <a
              key={l.href}
              href={l.href}
              onClick={() => setOpen(false)}
              className={`block px-3 py-3 rounded-lg text-sm transition-colors hover:bg-white/10 ${focusRing}`}
            >
              {l.label}
            </a>
          ))}
        </nav>
      )}
    </header>
  );
}
