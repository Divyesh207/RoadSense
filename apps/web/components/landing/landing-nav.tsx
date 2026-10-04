"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { LayoutDashboard, LogIn, Menu, X } from "lucide-react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
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
  "focus:outline-none focus-visible:ring-2 focus-visible:ring-ri-primary-bright focus-visible:ring-offset-2 focus-visible:ring-offset-ri-bg";

/** Public landing navigation: section links, login, and a mobile menu. */
export function LandingNav() {
  const [open, setOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);
  const [active, setActive] = useState("");
  const reduce = useReducedMotion();

  // Stronger glass once the page has scrolled; highlight the section being read.
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    const sections = LINKS.map((l) => document.querySelector(l.href)).filter(Boolean) as Element[];
    const observer =
      typeof IntersectionObserver === "undefined"
        ? null
        : new IntersectionObserver(
            (entries) => entries.forEach((e) => e.isIntersecting && setActive(`#${e.target.id}`)),
            { rootMargin: "-45% 0px -50% 0px" }
          );
    sections.forEach((el) => observer?.observe(el));
    return () => {
      window.removeEventListener("scroll", onScroll);
      observer?.disconnect();
    };
  }, []);
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
      className={`inline-flex items-center justify-center gap-1.5 h-10 px-4 rounded-xl bg-ri-primary hover:bg-ri-primary-bright text-ri-on-primary text-sm font-bold transition-all duration-200 motion-safe:hover:-translate-y-0.5 hover:shadow-[0_12px_28px_-12px_rgb(var(--ri-primary)/0.85)] ${focusRing}`}
    >
      {signedIn ? <LayoutDashboard className="h-4 w-4" /> : <LogIn className="h-4 w-4" />}
      {signedIn ? "Dashboard" : "Login"}
    </Link>
  );

  return (
    <header
      className={`sticky top-0 z-50 border-b backdrop-blur-xl transition-[background-color,border-color,box-shadow] duration-300 ${
        scrolled
          ? "bg-ri-solid/85 border-ri-line shadow-[0_10px_30px_-18px_rgb(0_0_0/0.9)]"
          : "bg-ri-solid/40 border-transparent"
      }`}
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 h-16 flex items-center justify-between gap-4">
        <Link href="/" aria-label="Road Intelligence home" className={`rounded-xl ${focusRing}`}>
          <BrandLogo variant="horizontal" size="md" />
        </Link>

        <nav aria-label="Primary" className="hidden lg:flex items-center gap-1">
          {LINKS.map((l) => (
            <a
              key={l.href}
              href={l.href}
              aria-current={active === l.href ? "true" : undefined}
              className={`relative px-3 py-2 rounded-lg text-sm transition-colors duration-200 hover:text-ri-text hover:bg-ri-raised ${
                active === l.href ? "text-ri-text" : "text-ri-muted"
              } after:absolute after:left-3 after:right-3 after:-bottom-0.5 after:h-px after:rounded-full after:bg-ri-primary-bright after:transition-transform after:duration-200 after:origin-left ${
                active === l.href ? "after:scale-x-100" : "after:scale-x-0"
              } ${focusRing}`}
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
            className={`lg:hidden inline-flex items-center justify-center h-10 w-10 rounded-xl border border-ri-line bg-ri-surface text-ri-text-soft hover:border-ri-primary/50 transition-colors ${focusRing}`}
          >
            {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      <AnimatePresence initial={false}>
        {open && (
          <motion.nav
            id="landing-mobile-menu"
            aria-label="Mobile"
            initial={reduce ? false : { height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={reduce ? { opacity: 0 } : { height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: [0.2, 0.8, 0.2, 1] }}
            className="lg:hidden overflow-hidden border-t border-ri-line bg-ri-solid/95"
          >
            <div className="px-4 sm:px-6 py-3 space-y-1">
          {LINKS.map((l) => (
            <a
              key={l.href}
              href={l.href}
              onClick={() => setOpen(false)}
              className={`block px-3 py-3 rounded-lg text-sm text-ri-text-soft hover:bg-ri-raised transition-colors ${focusRing}`}
            >
              {l.label}
            </a>
          ))}
          <div className="pt-2 sm:hidden">{authLink}</div>
                    </div>
          </motion.nav>
        )}
      </AnimatePresence>
    </header>
  );
}
