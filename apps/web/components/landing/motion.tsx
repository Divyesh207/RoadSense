"use client";

/**
 * Scroll reveals for the public landing page. Only opacity and transforms are animated, and
 * nothing happens when the visitor asks for reduced motion.
 */

import { useEffect } from "react";

/**
 * Mounted once on the page. Finds every element marked `data-reveal` (or
 * `data-reveal="stagger"`, whose direct children then appear one after another, or
 * `data-reveal="clip"`, which opens a large visual from a slightly inset frame) and reveals it
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
      el.classList.add(el.dataset.reveal === "stagger" ? "ri-stagger" : el.dataset.reveal === "clip" ? "ri-clip" : "ri-reveal");
      observer.observe(el);
    });

    return () => {
      observer.disconnect();
      timers.forEach((t) => window.clearTimeout(t));
    };
  }, []);

  return null;
}
