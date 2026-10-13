"use client";

import React, { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { ArrowDown, Camera, Check, FileText, MapPin, WifiOff } from "lucide-react";
import { BasisTag } from "@/components/landing/basis-tag";

/**
 * The platform's 14 capabilities, explored by category instead of read as a grid. Choosing a
 * category swaps the description, its capabilities and a large illustration of that part of the
 * product. The illustrations are drawn here and labelled as such: they are not screenshots and
 * carry no live data.
 *
 * On large screens the explorer stays in view while its section scrolls past, and the scroll
 * position chooses the category (A, then B, C, D). Choosing a category by hand scrolls to that
 * part of the section, so the two never disagree. On small screens the categories are tabs.
 */

const GROUPS: { id: "field" | "road" | "maintenance" | "governance"; label: string; text: string; items: { title: string; text: string }[] }[] = [
  {
    id: "field",
    label: "Field intelligence",
    text: "Capture road condition where it happens, and turn inspection photos into reviewed damage records.",
    items: [
      { title: "Field inspections", text: "Photo inspections recorded against roads and segments from the Android field app." },
      { title: "GPS-based capture", text: "Each inspection stores the phone's reported position and accuracy, shown unchanged on the map." },
      { title: "AI road-damage detection", text: "A trained YOLO11s model detects cracks and potholes in inspection photos." },
      { title: "Damage review", text: "Detections stay candidates until a reviewer promotes or rejects them." },
    ],
  },
  {
    id: "road",
    label: "Road intelligence",
    text: "See where the damage is, how each segment is doing, and how its condition is likely to change.",
    items: [
      { title: "Spatial damage map", text: "Damage, segments and inspection points on a filterable map." },
      { title: "Road and segment management", text: "Administrators add roads and draw segment geometry on the map." },
      { title: "Road health assessment", text: "A rule-based health score per segment and road, with the deductions shown." },
      { title: "Deterioration estimate", text: "A rule-based condition estimate from damage, health trend, recurrence and repair history." },
    ],
  },
  {
    id: "maintenance",
    label: "Maintenance operations",
    text: "Decide what to fix first, run the repair, and confirm that it held.",
    items: [
      { title: "Maintenance prioritisation", text: "A ranked queue with the factors behind each priority." },
      { title: "Maintenance operations", text: "Jobs tracked from creation through assignment, work and completion." },
      { title: "Repair verification", text: "After-repair evidence and location checks, then human sign-off." },
      { title: "Recurrence monitoring", text: "Damage that reappears at a repaired location is linked and escalated." },
    ],
  },
  {
    id: "governance",
    label: "Governance and reporting",
    text: "Keep the trail of who did what, and take the recorded data out as reports.",
    items: [
      { title: "Audit and history", text: "A record of who did what, and a timeline per road segment." },
      { title: "Reports and exports", text: "Reports generated from the recorded data, available to download." },
    ],
  },
];

const frame = "rounded-xl border border-ri-line bg-ri-bg";
const row = "flex items-center justify-between gap-3 border-b border-ri-line py-2.5 last:border-b-0";
const mono = "font-code-sm text-[10.5px] text-ri-faint uppercase tracking-wider";

function FieldVisual() {
  return (
    <div className="grid h-full grid-cols-1 items-center gap-5 sm:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)] sm:gap-8">
      <div className="mx-auto w-full max-w-[210px] rounded-[26px] border border-ri-line-strong bg-black p-2.5">
        <div className="rounded-[18px] bg-ri-solid p-3">
          <p className="text-sm font-medium text-ri-text">New inspection</p>
          <p className={`${mono} mt-3`}>Road and segment</p>
          <p className="mt-1 rounded-lg border border-ri-line px-2.5 py-2 text-xs text-ri-text-soft">Sample road · Segment 2</p>
          <p className={`${mono} mt-3`}>GPS</p>
          <p className="mt-1 flex items-center gap-1.5 text-xs text-ri-text-soft">
            <MapPin className="h-3.5 w-3.5 text-ri-success" /> Fix held · ±6 m
          </p>
          <p className={`${mono} mt-3`}>Photos</p>
          <div className="mt-1 grid grid-cols-3 gap-1.5">
            {[0, 1, 2].map((i) => (
              <div key={i} className="flex aspect-square items-center justify-center rounded-md bg-ri-raised text-ri-faint">
                <Camera className="h-3.5 w-3.5" />
              </div>
            ))}
          </div>
          <p className="mt-3 flex items-center gap-1.5 rounded-lg bg-ri-raised px-2.5 py-2 text-[11px] text-ri-muted">
            <WifiOff className="h-3.5 w-3.5" /> Queued until online
          </p>
        </div>
      </div>
      <div className="hidden space-y-3 sm:block">
        <div className={`${frame} p-3`}>
          <div className="relative aspect-[4/3] rounded-lg bg-[linear-gradient(160deg,#3a3b3e,#232426)]">
            <div className="absolute left-[30%] top-[48%] h-[30%] w-[38%] rounded-sm border-2 border-ri-info" />
            <span className="absolute left-[30%] top-[38%] rounded-sm bg-ri-info px-1 text-[10px] font-medium text-black">pothole 0.71</span>
          </div>
          <div className="mt-2.5 flex flex-wrap items-center gap-2">
            <BasisTag basis="TRAINED AI" />
            <span className="text-xs text-ri-muted">proposes a candidate</span>
          </div>
        </div>
        <div className={`${frame} flex items-center justify-between gap-3 p-3`}>
          <div>
            <BasisTag basis="HUMAN REVIEW" />
            <p className="mt-1.5 text-xs text-ri-muted">A reviewer confirms or rejects it.</p>
          </div>
          <span className="flex h-8 w-8 items-center justify-center rounded-full border border-ri-line-strong text-ri-text">
            <Check className="h-4 w-4" />
          </span>
        </div>
      </div>
    </div>
  );
}

function RoadVisual() {
  const segments = [
    ["Segment 1", 92, "Good", "bg-ri-success"],
    ["Segment 2", 76, "Fair", "bg-ri-warning"],
    ["Segment 3", 52, "Poor", "bg-ri-orange"],
    ["Segment 4", 34, "Critical", "bg-ri-danger"],
  ] as const;
  return (
    <div className="flex h-full flex-col justify-center gap-4">
      <div className={`${frame} p-4`}>
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-ri-text">Health by segment</p>
          <BasisTag basis="RULE-BASED" />
        </div>
        <div className="mt-3">
          {segments.map(([name, score, band, color]) => (
            <div key={name} className={row}>
              <span className="w-20 shrink-0 text-xs text-ri-text-soft">{name}</span>
              <span className="h-1.5 flex-1 overflow-hidden rounded-full bg-ri-raised">
                <span className={`block h-full rounded-full ${color}`} style={{ width: `${score}%` }} />
              </span>
              <span className="w-8 text-right font-code-sm text-ri-text">{score}</span>
              <span className="hidden w-14 text-right text-[11px] text-ri-muted sm:block">{band}</span>
            </div>
          ))}
        </div>
        <p className="mt-3 text-[11px] leading-relaxed text-ri-faint">Each score starts at 100 and loses points for every open defect, with the deductions listed.</p>
      </div>
      <a href="#preview" className="group inline-flex w-fit items-center gap-2 rounded-lg border border-ri-line px-3.5 py-2.5 text-sm text-ri-text transition-colors hover:border-ri-line-strong hover:bg-ri-raised focus:outline-none focus-visible:ring-2 focus-visible:ring-white">
        Open the interactive map preview
        <ArrowDown className="h-4 w-4 transition-transform duration-200 motion-safe:group-hover:translate-y-0.5" />
      </a>
    </div>
  );
}

function MaintenanceVisual() {
  const queue = [
    ["1", "Segment 4 · pothole", "Critical", "text-ri-danger"],
    ["2", "Segment 3 · pothole", "High", "text-ri-orange"],
    ["3", "Segment 2 · crack", "Medium", "text-ri-warning"],
  ] as const;
  const states = ["Created", "Assigned", "In progress", "Completed", "Verified"];
  return (
    <div className="flex h-full flex-col justify-center gap-4">
      <div className={`${frame} p-4`}>
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-ri-text">Priority queue</p>
          <BasisTag basis="RULE-BASED" />
        </div>
        <div className="mt-3">
          {queue.map(([rank, what, level, color]) => (
            <div key={rank} className={row}>
              <span className="font-code-sm w-5 text-ri-faint">{rank}</span>
              <span className="flex-1 text-xs text-ri-text-soft">{what}</span>
              <span className={`text-[11px] font-medium ${color}`}>{level}</span>
            </div>
          ))}
        </div>
      </div>
      <div className={`${frame} p-4`}>
        <div className="flex items-center justify-between">
          <p className="text-sm font-medium text-ri-text">A job, from creation to sign-off</p>
          <BasisTag basis="HUMAN REVIEW" />
        </div>
        <ol className="mt-4 flex items-start">
          {states.map((s, i) => (
            <li key={s} className="relative flex-1 text-center">
              {i > 0 && <span aria-hidden className={`absolute right-1/2 top-[5px] h-px w-full ${i <= 2 ? "bg-white" : "bg-ri-line-strong"}`} />}
              <span className={`relative mx-auto block h-[11px] w-[11px] rounded-full border ${i <= 2 ? "border-white bg-white" : "border-ri-line-strong bg-ri-solid"}`} />
              <span className="mt-2 block text-[10px] leading-tight text-ri-muted">{s}</span>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}

function GovernanceVisual() {
  const trail = [
    ["Detection confirmed", "Reviewer"],
    ["Maintenance job assigned", "Supervisor"],
    ["Repair verified", "Engineer"],
  ];
  return (
    <div className="grid h-full grid-cols-1 items-center gap-4 sm:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)]">
      <div className="mx-auto w-full max-w-[230px] rounded-lg bg-white p-4 text-black shadow-2xl shadow-black/50">
        <div className="-mx-4 -mt-4 mb-3 rounded-t-lg bg-[#0b0b0c] px-4 py-3 text-white">
          <p className="text-[8px] tracking-wider">ROAD INTELLIGENCE</p>
          <p className="mt-2 text-[13px] font-semibold leading-tight">Road Health Assessment Report</p>
        </div>
        <FileText className="h-4 w-4 text-zinc-500" />
        {[80, 62, 90, 48].map((w, i) => (
          <span key={i} className="mt-2 block h-1.5 rounded-full bg-zinc-200" style={{ width: `${w}%` }} />
        ))}
        <p className="mt-3 text-[9px] text-zinc-500">PDF · CSV · JSON</p>
      </div>
      <div className={`${frame} p-4`}>
        <p className="text-sm font-medium text-ri-text">Audit trail</p>
        <ol className="mt-3 space-y-3 border-l border-ri-line pl-4">
          {trail.map(([what, who]) => (
            <li key={what} className="relative">
              <span aria-hidden className="absolute -left-[20.5px] top-1.5 h-2 w-2 rounded-full bg-white" />
              <p className="text-xs text-ri-text-soft">{what}</p>
              <p className="text-[11px] text-ri-faint">{who} · time recorded</p>
            </li>
          ))}
        </ol>
      </div>
    </div>
  );
}

const VISUALS = { field: FieldVisual, road: RoadVisual, maintenance: MaintenanceVisual, governance: GovernanceVisual };

/** `children` is the section heading: it stays in view with the explorer while the categories change. */
export function CapabilityExplorer({ children }: { children?: React.ReactNode }) {
  const [active, setActive] = useState(0);
  const tabs = useRef<(HTMLButtonElement | null)[]>([]);
  const track = useRef<HTMLDivElement>(null);

  // How far the section has scrolled, as 0..1 (large screens only).
  const span = () => (track.current ? track.current.offsetHeight - window.innerHeight : 0);
  useEffect(() => {
    const el = track.current;
    if (!el) return;
    const wide = window.matchMedia("(min-width: 1024px)");
    // Scroll events already arrive once per frame, and setting the same category again is free.
    const read = () => {
      if (!wide.matches || span() <= 0) return;
      const progress = Math.min(0.999, Math.max(0, -el.getBoundingClientRect().top / span()));
      setActive(Math.floor(progress * GROUPS.length));
    };
    read();
    window.addEventListener("scroll", read, { passive: true });
    window.addEventListener("resize", read);
    return () => {
      window.removeEventListener("scroll", read);
      window.removeEventListener("resize", read);
    };
  }, []);

  // Choosing a category: on large screens go to its part of the section, elsewhere just switch.
  const select = (i: number) => {
    const el = track.current;
    if (el && window.matchMedia("(min-width: 1024px)").matches && span() > 0) {
      const top = el.getBoundingClientRect().top + window.scrollY + ((i + 0.5) / GROUPS.length) * span();
      window.scrollTo({ top, behavior: reduce ? "auto" : "smooth" });
    }
    setActive(i);
  };
  const reduce = useReducedMotion();
  const group = GROUPS[active];
  const Visual = VISUALS[group.id];

  const onKeyDown = (e: React.KeyboardEvent) => {
    const step = e.key === "ArrowDown" || e.key === "ArrowRight" ? 1 : e.key === "ArrowUp" || e.key === "ArrowLeft" ? -1 : 0;
    const next = e.key === "Home" ? 0 : e.key === "End" ? GROUPS.length - 1 : step ? (active + step + GROUPS.length) % GROUPS.length : -1;
    if (next < 0) return;
    e.preventDefault();
    select(next);
    tabs.current[next]?.focus();
  };
  const swap = reduce
    ? { initial: false as const, animate: { opacity: 1 }, exit: { opacity: 1 }, transition: { duration: 0 } }
    : { initial: { opacity: 0, y: 14 }, animate: { opacity: 1, y: 0 }, exit: { opacity: 0, y: -8 }, transition: { duration: 0.32, ease: [0.2, 0.8, 0.2, 1] as const } };

  return (
    <div ref={track} className="lg:h-[280vh]">
    <div className="lg:sticky lg:top-24">
    {children}
    <div className="mt-10 grid grid-cols-1 gap-8 lg:mt-8 lg:grid-cols-[minmax(0,4fr)_minmax(0,7fr)] lg:gap-14">
      <div
        role="tablist"
        aria-label="Capability categories"
        aria-orientation="vertical"
        onKeyDown={onKeyDown}
        className="-mx-6 flex gap-2 overflow-x-auto px-6 pb-1 lg:mx-0 lg:flex-col lg:gap-0 lg:overflow-visible lg:border-t lg:border-ri-line lg:px-0 lg:pb-0"
      >
        {GROUPS.map((g, i) => {
          const selected = i === active;
          return (
            <button
              key={g.id}
              ref={(el) => {
                tabs.current[i] = el;
              }}
              type="button"
              role="tab"
              id={`cap-tab-${g.id}`}
              aria-selected={selected}
              aria-controls="cap-panel"
              tabIndex={selected ? 0 : -1}
              onClick={() => select(i)}
              className={`group relative shrink-0 rounded-lg border px-4 py-2.5 text-left transition-colors duration-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-white lg:rounded-none lg:border-0 lg:border-b lg:border-ri-line lg:px-0 lg:py-4 ${
                selected ? "border-white bg-white text-black lg:bg-transparent lg:text-ri-text" : "border-ri-line text-ri-muted hover:text-ri-text"
              }`}
            >
              <span aria-hidden className={`absolute left-0 top-0 hidden h-px bg-white transition-[width] duration-500 ease-out lg:block ${selected ? "w-full" : "w-0"}`} />
              <span className="flex items-baseline gap-4">
                <span className={`hidden font-code-sm lg:inline ${selected ? "text-ri-text" : "text-ri-faint"}`}>{String.fromCharCode(65 + i)}</span>
                <span className="whitespace-nowrap text-sm font-medium lg:whitespace-normal lg:text-2xl lg:font-normal lg:tracking-[-0.02em]">{g.label}</span>
                <span className={`ml-auto hidden font-code-sm lg:inline ${selected ? "text-ri-muted" : "text-ri-faint"}`}>{g.items.length}</span>
              </span>
              <span className={`hidden overflow-hidden text-sm leading-relaxed text-ri-muted transition-[max-height,opacity,margin] duration-500 ease-out lg:block lg:pl-[26px] ${selected ? "mt-3 max-h-24 opacity-100" : "max-h-0 opacity-0"}`}>
                {g.text}
              </span>
            </button>
          );
        })}
      </div>

      <div id="cap-panel" role="tabpanel" aria-labelledby={`cap-tab-${group.id}`} className="min-w-0">
        <p className="mb-5 text-sm leading-relaxed text-ri-muted lg:hidden">{group.text}</p>
        <figure className="overflow-hidden rounded-xl border border-ri-line bg-ri-surface">
          <div className="relative h-[430px] p-5 sm:h-[400px] sm:p-8 lg:h-[min(330px,34vh)]">
            <AnimatePresence mode="wait" initial={false}>
              <motion.div key={group.id} {...swap} className="h-full">
                <Visual />
              </motion.div>
            </AnimatePresence>
          </div>
          <figcaption className="border-t border-ri-line px-5 py-2.5 text-[11px] text-ri-faint sm:px-8">
            Illustration of this part of the product. It is not a screenshot and shows no live data.
          </figcaption>
        </figure>

        <div className="mt-6 min-h-[236px] sm:min-h-[150px] lg:mt-4">
          <AnimatePresence mode="wait" initial={false}>
            <motion.dl key={group.id} {...swap} className="grid grid-cols-1 gap-x-10 sm:grid-cols-2">
              {group.items.map((item) => (
                <div key={item.title} className="border-t border-ri-line py-4">
                  <dt className="text-sm font-medium text-ri-text">{item.title}</dt>
                  <dd className="mt-1 text-[13px] leading-relaxed text-ri-muted">{item.text}</dd>
                </div>
              ))}
            </motion.dl>
          </AnimatePresence>
        </div>
      </div>

      {/* Every capability stays in the page for search engines and assistive technology, whichever category is open. */}
      <ul className="sr-only">
        {GROUPS.flatMap((g) => g.items).map((item) => (
          <li key={item.title}>
            {item.title}: {item.text}
          </li>
        ))}
      </ul>
    </div>
    </div>
    </div>
  );
}
