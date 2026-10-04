"use client";

/**
 * Motion for the public landing page. Only opacity and transforms are animated. Everything
 * here does nothing when the visitor asks for reduced motion.
 */

import React, { useEffect, useRef } from "react";
import { motion, useReducedMotion, useScroll, useTransform } from "framer-motion";

const EASE = [0.2, 0.8, 0.2, 1] as const;

/* ------------------------------------------------------------------ hero entrance */

const heroContainer = {
  hidden: {},
  show: { transition: { staggerChildren: 0.11, delayChildren: 0.05 } },
};
const heroItem = {
  hidden: { opacity: 0, y: 18 },
  show: { opacity: 1, y: 0, transition: { duration: 0.45, ease: EASE } },
};

/** Staggers its <HeroItem> children on first load (logo, headline, text, buttons: about 0.9 s in all). */
export function HeroStagger({ children, className }: { children: React.ReactNode; className?: string }) {
  const reduce = useReducedMotion();
  return (
    <motion.div className={className} variants={heroContainer} initial={reduce ? false : "hidden"} animate="show">
      {children}
    </motion.div>
  );
}

export function HeroItem({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <motion.div className={className} variants={heroItem}>
      {children}
    </motion.div>
  );
}

/** The product preview: enters last, from slightly further away. */
export function HeroVisual({ children, className }: { children: React.ReactNode; className?: string }) {
  const reduce = useReducedMotion();
  return (
    <motion.div
      className={className}
      initial={reduce ? false : { opacity: 0, y: 28, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.55, delay: 0.5, ease: EASE }}
    >
      {children}
    </motion.div>
  );
}

/* ------------------------------------------------------------------- hero parallax */

/**
 * Subtle scroll-linked movement in the hero: the ambient glow and the network lines drift at
 * different speeds, the text eases back, the preview rises a little. All of it is small.
 */
export function HeroParallax({ content, visual }: { content: React.ReactNode; visual: React.ReactNode }) {
  const ref = useRef<HTMLElement>(null);
  const reduce = useReducedMotion();
  const { scrollYProgress } = useScroll({ target: ref, offset: ["start start", "end start"] });
  const glowY = useTransform(scrollYProgress, [0, 1], [0, 140]);
  const linesY = useTransform(scrollYProgress, [0, 1], [0, 70]);
  const contentY = useTransform(scrollYProgress, [0, 1], [0, 44]);
  const contentOpacity = useTransform(scrollYProgress, [0, 0.85], [1, 0.55]);
  const visualY = useTransform(scrollYProgress, [0, 1], [0, -34]);
  const still = Boolean(reduce);

  return (
    <section ref={ref} className="relative border-b border-ri-line overflow-hidden">
      <motion.div
        aria-hidden
        style={still ? undefined : { y: glowY }}
        className="absolute -top-24 right-[-10%] h-[520px] w-[720px] rounded-full pointer-events-none bg-[radial-gradient(closest-side,rgb(var(--ri-primary)/0.20),transparent)]"
      />
      {/* Decorative road / network lines */}
      <motion.svg
        aria-hidden
        style={still ? undefined : { y: linesY }}
        className="absolute inset-0 h-full w-full pointer-events-none opacity-60"
        viewBox="0 0 1200 600"
        preserveAspectRatio="xMidYMid slice"
      >
        <g fill="none" stroke="rgb(var(--ri-glass))" strokeOpacity="0.10" strokeWidth="1.2">
          <path d="M-40 470 C 220 420, 380 520, 620 440 S 1040 360, 1260 420" />
          <path d="M-40 250 C 180 300, 420 180, 640 240 S 1000 320, 1260 220" />
          <path d="M300 -20 C 340 160, 260 320, 340 620" />
          <path d="M880 -20 C 820 200, 940 360, 860 620" />
        </g>
        <g fill="rgb(var(--ri-primary-bright))" fillOpacity="0.45">
          <circle cx="322" cy="252" r="3" />
          <circle cx="620" cy="440" r="3" />
          <circle cx="872" cy="286" r="3" />
          <circle cx="340" cy="478" r="3" />
        </g>
      </motion.svg>

      <div className="relative max-w-7xl mx-auto px-4 sm:px-6 py-14 sm:py-20 grid grid-cols-1 lg:grid-cols-[1.1fr_0.9fr] gap-10 lg:gap-14 items-center">
        <motion.div style={still ? undefined : { y: contentY, opacity: contentOpacity }}>{content}</motion.div>
        <motion.div style={still ? undefined : { y: visualY }}>{visual}</motion.div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ scroll reveals */

/**
 * Mounted once on the page. Finds every element marked `data-reveal` (or
 * `data-reveal="stagger"`, whose direct children then appear one after another) and reveals it
 * when it scrolls into view. The hidden state is applied only after hydration and only to
 * elements still below the viewport, so nothing is hidden without JavaScript and nothing
 * flashes. The CSS lives in app/globals.css (.ri-reveal / .ri-stagger).
 */
export function RevealObserver() {
  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const timers: number[] = [];
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (!entry.isIntersecting) continue;
          const el = entry.target as HTMLElement;
          el.classList.add("is-visible");
          observer.unobserve(el);
          // Hand the element back to its own hover transitions once the reveal has played.
          timers.push(window.setTimeout(() => el.classList.add("is-done"), 1100));
        }
      },
      { rootMargin: "0px 0px -10% 0px", threshold: 0.08 }
    );

    document.querySelectorAll<HTMLElement>("[data-reveal]").forEach((el) => {
      if (el.getBoundingClientRect().top < window.innerHeight * 0.92) return; // already on screen
      el.classList.add(el.dataset.reveal === "stagger" ? "ri-stagger" : "ri-reveal");
      observer.observe(el);
    });

    return () => {
      observer.disconnect();
      timers.forEach((t) => window.clearTimeout(t));
    };
  }, []);

  return null;
}
