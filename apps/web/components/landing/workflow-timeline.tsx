"use client";

import React, { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion, useScroll, useSpring } from "framer-motion";
import { BasisTag, type Basis } from "@/components/landing/basis-tag";

/**
 * The eight steps as one connected timeline. Every step, its description and its source label is
 * always on the page. On large screens a panel beside the list stays in view and shows the step
 * being read, and the connecting line fills with the scroll position. Nothing is pinned and
 * scrolling is never held: the visitor can pass through at any speed. On small screens it is a
 * plain vertical timeline.
 */

const STEPS: { name: string; text: string; basis?: Basis }[] = [
  { name: "Inspect", text: "Capture photos and the GPS position against a road and segment in the field app." },
  { name: "Upload", text: "Inspections queue on the device and upload when a connection is available." },
  { name: "Detect", text: "A trained YOLO11s model proposes damage candidates on each photo.", basis: "TRAINED AI" },
  { name: "Review", text: "An authorized reviewer confirms or rejects each candidate.", basis: "HUMAN REVIEW" },
  { name: "Map", text: "Confirmed damage and inspection capture points appear at their recorded coordinates." },
  { name: "Assess", text: "Severity, road health and priority are calculated from documented rules.", basis: "RULE-BASED" },
  { name: "Repair", text: "Maintenance jobs move through assignment, field repair and after-repair evidence." },
  { name: "Verify", text: "Repairs are signed off by a person; damage that returns is tracked as a recurrence.", basis: "HUMAN REVIEW" },
];

const two = (n: number) => String(n).padStart(2, "0");

export function WorkflowTimeline() {
  const list = useRef<HTMLOListElement>(null);
  const items = useRef<(HTMLLIElement | null)[]>([]);
  const [active, setActive] = useState(0);
  const reduce = useReducedMotion();

  // The connecting line follows the scroll position directly (no React state while scrolling).
  const { scrollYProgress } = useScroll({ target: list, offset: ["start 55%", "end 55%"] });
  const fill = useSpring(scrollYProgress, { stiffness: 140, damping: 30, mass: 0.4 });

  // The step crossing the middle of the viewport is the active one.
  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver(
      (entries) => {
        for (const e of entries) if (e.isIntersecting) setActive(Number((e.target as HTMLElement).dataset.index));
      },
      { rootMargin: "-48% 0px -48% 0px" }
    );
    items.current.forEach((el) => el && observer.observe(el));
    return () => observer.disconnect();
  }, []);

  const step = STEPS[active];
  const go = (i: number) => {
    setActive(i);
    items.current[i]?.scrollIntoView({ block: "center", behavior: reduce ? "auto" : "smooth" });
  };

  return (
    <div className="grid grid-cols-1 gap-10 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)] lg:gap-20">
      {/* The step being read. Large screens only: the list beside it already carries all the text. */}
      <div aria-hidden className="hidden lg:block">
        <div className="sticky top-40">
          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={active}
              initial={reduce ? false : { opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={reduce ? { opacity: 0 } : { opacity: 0, y: -10 }}
              transition={{ duration: reduce ? 0 : 0.28, ease: [0.2, 0.8, 0.2, 1] }}
            >
              <p className="text-[96px] font-light leading-none tracking-[-0.06em] text-ri-text">{two(active + 1)}</p>
              <p className="mt-6 text-4xl font-normal tracking-[-0.03em] text-ri-text">{step.name}</p>
              <p className="mt-4 max-w-md text-base leading-relaxed text-ri-muted">{step.text}</p>
              <div className="mt-5 h-6">{step.basis ? <BasisTag basis={step.basis} /> : <span className="font-code-sm text-[10px] tracking-wider text-ri-faint">RECORDED AS ENTERED</span>}</div>
            </motion.div>
          </AnimatePresence>
          <div className="mt-10 flex items-center gap-1.5">
            {STEPS.map((s, i) => (
              <span key={s.name} className={`h-0.5 flex-1 rounded-full transition-colors duration-300 ${i <= active ? "bg-white" : "bg-ri-line-strong"}`} />
            ))}
            <span className="ml-3 font-code-sm text-ri-faint">
              {two(active + 1)} / {two(STEPS.length)}
            </span>
          </div>
        </div>
      </div>

      <ol ref={list} className="relative">
        <span aria-hidden className="absolute bottom-3 left-[5px] top-3 w-px bg-ri-line" />
        <motion.span aria-hidden style={{ scaleY: fill }} className="absolute bottom-3 left-[5px] top-3 w-px origin-top bg-white" />
        {STEPS.map((s, i) => {
          const current = i === active;
          return (
            <li
              key={s.name}
              ref={(el) => {
                items.current[i] = el;
              }}
              data-index={i}
              className="relative pb-7 pl-9 last:pb-0 lg:pb-14 lg:pl-12"
            >
              <span aria-hidden className={`absolute left-0 top-[7px] h-[11px] w-[11px] rounded-full border transition-colors duration-300 ${i <= active ? "border-white bg-white" : "border-ri-line-strong bg-ri-solid"}`} />
              <button
                type="button"
                onClick={() => go(i)}
                aria-current={current ? "step" : undefined}
                className="group block w-full rounded-lg text-left focus:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-4 focus-visible:ring-offset-black"
              >
                <span className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
                  <span className="font-code-sm text-ri-faint">{two(i + 1)}</span>
                  <span className={`text-lg font-medium transition-colors duration-300 lg:text-xl ${current ? "text-ri-text" : "text-ri-text-soft lg:text-ri-muted"} group-hover:text-ri-text`}>{s.name}</span>
                  {s.basis && <BasisTag basis={s.basis} />}
                </span>
                <span className={`mt-1.5 block max-w-xl text-sm leading-relaxed transition-colors duration-300 ${current ? "text-ri-text-soft" : "text-ri-muted lg:text-ri-faint"}`}>{s.text}</span>
              </button>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
