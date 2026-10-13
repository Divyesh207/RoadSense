import React from "react";
import Link from "next/link";
import { ArrowRight, Camera, Map as MapIcon, MapPin, Route, UploadCloud, WifiOff } from "lucide-react";
import { BrandLogo } from "@/components/brand-logo";
import { LandingNav } from "@/components/landing/landing-nav";
import { DemoMap } from "@/components/landing/demo-map";
import { CursorAmbient } from "@/components/landing/cursor-effects";
import { Hero } from "@/components/landing/hero";
import { RequestDemoForm } from "@/components/landing/request-demo-form";
import { RevealObserver } from "@/components/landing/motion";
import { ApiStatusBadge } from "@/components/landing-header";
import { BasisTag, type Basis } from "@/components/landing/basis-tag";
import { CapabilityExplorer } from "@/components/landing/capability-explorer";
import { WorkflowTimeline } from "@/components/landing/workflow-timeline";

// Everything on this page describes behaviour that exists in the platform. It carries no
// metrics: live figures for an organization are on the authenticated dashboard.
//
// Layout rules: one content width, one heading scale, hairlines instead of boxes. Each section
// takes the form that suits what it says (numbered columns, a timeline, an explorer, a
// comparison, a strip, definition rows) rather than repeating a card grid.

const focusRing =
  "focus:outline-none focus-visible:ring-2 focus-visible:ring-white focus-visible:ring-offset-2 focus-visible:ring-offset-black";
const eyebrow = "font-code-sm text-ri-muted uppercase tracking-widest";
const sectionTitle = "text-3xl sm:text-4xl lg:text-5xl font-normal tracking-[-0.035em] leading-[1.08] text-ri-text";
const sectionLead = "text-base text-ri-muted leading-relaxed max-w-2xl";
const container = "max-w-7xl mx-auto px-6 md:px-12 lg:px-16";

const OVERVIEW = [
  {
    title: "Field capture",
    text: "Inspectors record a road, an optional segment, the phone's GPS position and photos in the Android field app.",
  },
  {
    title: "Detection and review",
    text: "Photos are analysed into damage candidates. A reviewer confirms or rejects them before they count.",
  },
  {
    title: "Maintenance and verification",
    text: "Confirmed damage is prioritised, scheduled, repaired and verified with after-repair evidence.",
  },
];

const SOURCES: { basis: Basis; rule: string; title: string; text: string }[] = [
  {
    basis: "TRAINED AI",
    rule: "border-ri-info",
    title: "Damage detection",
    text: "A YOLO11s model trained on the RDD2022 India road-damage dataset proposes crack and pothole candidates with a model confidence. Candidates below the configured threshold are not reported.",
  },
  {
    basis: "RULE-BASED",
    rule: "border-ri-warning",
    title: "Severity, health, priority, deterioration",
    text: "These are calculated from fixed, documented rules, not from a trained model. Where the heuristic image fallback is configured, its results are labelled as heuristic scores, not probabilities.",
  },
  {
    basis: "HUMAN REVIEW",
    rule: "border-white",
    title: "Confirmation and sign-off",
    text: "A reviewer decides whether a detection becomes a damage record, and a person signs off each repair verification. The original detection is kept alongside the decision.",
  },
];

const FIELD_FLOW = [
  { icon: Route, title: "Select road and segment", text: "The app lists the roads and segments defined on the web console." },
  { icon: MapPin, title: "Record position", text: "The phone's GPS fix and its reported accuracy are saved with the inspection." },
  { icon: Camera, title: "Capture photos", text: "Photos are taken in the app and attached to the inspection." },
  { icon: WifiOff, title: "Work offline", text: "Inspections are stored on the device and queued when there is no connection." },
  { icon: UploadCloud, title: "Sync", text: "Queued inspections upload in the background and show their sync status." },
];

const OPERATIONS: { title: string; text: string; basis?: Basis }[] = [
  {
    title: "Road health",
    text: "Each segment gets a health score with the deductions that produced it, and a trend from earlier snapshots.",
    basis: "RULE-BASED",
  },
  {
    title: "Prioritisation",
    text: "Damage is ranked for repair with the contributing factors listed. Traffic is used only where a documented figure has been entered.",
    basis: "RULE-BASED",
  },
  {
    title: "Maintenance operations",
    text: "Jobs follow a fixed set of states from creation to completion, with each change recorded in the audit history.",
  },
  {
    title: "Repair verification",
    text: "After-repair photos and their location are checked against the original damage, then a person approves or rejects the repair.",
    basis: "HUMAN REVIEW",
  },
  {
    title: "Recurrence monitoring",
    text: "New damage near a previously repaired location is matched to it, counted as a recurrence and escalated when it keeps returning.",
    basis: "RULE-BASED",
  },
];

function Heading({ id, label, title, lead }: { id: string; label: string; title: string; lead?: string }) {
  return (
    <div data-reveal="stagger" className="space-y-4">
      <p className={eyebrow}>{label}</p>
      <h2 id={`${id}-title`} className={`${sectionTitle} max-w-4xl`}>
        {title}
      </h2>
      {lead && <p className={sectionLead}>{lead}</p>}
    </div>
  );
}

export default function HomePage() {
  return (
    <div className="ri-ambient min-h-screen text-ri-text-soft overflow-x-clip">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-[60] focus:px-4 focus:py-2 focus:rounded-lg focus:bg-white focus:text-black focus:text-sm focus:font-medium"
      >
        Skip to content
      </a>
      <LandingNav />
      <RevealObserver />
      <CursorAmbient />

      <main id="main">
        <Hero />

        {/* Platform overview: three numbered columns, no boxes */}
        <section id="overview" aria-labelledby="overview-title" className={`${container} scroll-mt-24 pt-20 sm:pt-28`}>
          <Heading
            id="overview"
            label="Platform overview"
            title="One record from the roadside to the verified repair"
            lead="An Android field app, an AI worker and a web operations console share one set of roads, segments, inspections and damage records. Each step keeps the evidence and the decision that led to the next."
          />
          <div data-reveal="stagger" className="mt-12 grid grid-cols-1 border-t border-ri-line md:grid-cols-3">
            {OVERVIEW.map((o, i) => (
              <div key={o.title} className="border-b border-ri-line py-8 md:border-b-0 md:border-l md:px-8 md:first:border-l-0 md:first:pl-0 md:last:pr-0">
                <p className="font-code-sm text-ri-faint">{String(i + 1).padStart(2, "0")}</p>
                <h3 className="mt-6 text-xl font-medium tracking-[-0.01em] text-ri-text">{o.title}</h3>
                <p className="mt-3 text-sm leading-relaxed text-ri-muted">{o.text}</p>
              </div>
            ))}
          </div>
        </section>

        {/* How it works: connected timeline */}
        <section id="how-it-works" aria-labelledby="how-it-works-title" className={`${container} scroll-mt-24 pt-28 sm:pt-40`}>
          <Heading
            id="how-it-works"
            label="How it works"
            title="Eight steps, each with its source stated"
            lead="Steps that depend on a trained model, on fixed rules or on a person's decision are marked."
          />
          <div className="mt-14 lg:mt-20">
            <WorkflowTimeline />
          </div>
        </section>

        {/* Core capabilities: explorer on a raised band */}
        <section id="capabilities" aria-labelledby="capabilities-title" className="scroll-mt-24 mt-28 border-y border-ri-line bg-ri-surface sm:mt-40">
          <div className={`${container} py-20 sm:py-24`}>
            <CapabilityExplorer>
              <Heading
                id="capabilities"
                label="Core capabilities"
                title="What the platform does today"
                lead="Fourteen capabilities in four groups. Choose a group to see what it covers."
              />
            </CapabilityExplorer>
          </div>
        </section>

        {/* AI + GIS: three-way comparison */}
        <section id="ai-gis" aria-labelledby="ai-gis-title" className={`${container} scroll-mt-24 pt-28 sm:pt-40`}>
          <Heading
            id="ai-gis"
            label="AI + GIS"
            title="Clear about what is a model, what is a rule and what is a decision"
            lead="The console never presents a rule-based score as a model prediction, and never treats an unreviewed detection as confirmed damage."
          />
          <div data-reveal="stagger" className="mt-12 grid grid-cols-1 gap-x-10 gap-y-10 lg:grid-cols-3">
            {SOURCES.map((s) => (
              <div key={s.basis} className={`border-t-2 pt-6 ${s.rule}`}>
                <BasisTag basis={s.basis} />
                <h3 className="mt-5 text-xl font-medium tracking-[-0.01em] text-ri-text">{s.title}</h3>
                <p className="mt-3 text-sm leading-relaxed text-ri-muted">{s.text}</p>
              </div>
            ))}
          </div>
          <div data-reveal className="mt-14 grid grid-cols-1 gap-6 border-t border-ri-line pt-8 md:grid-cols-[auto_1fr] md:gap-10">
            <p className="flex items-center gap-3 text-xl font-medium tracking-[-0.01em] text-ri-text">
              <MapIcon className="h-5 w-5 text-ri-muted" /> GIS on PostGIS
            </p>
            <p className="max-w-3xl text-sm leading-relaxed text-ri-muted">
              Roads, segment geometry, inspections and damage are stored with coordinates and drawn on the Spatial Map at
              exactly the stored position. Positions come from the phone&apos;s GPS, so their accuracy is whatever the
              device reports.
            </p>
          </div>
        </section>

        {/* Field inspection workflow: a numbered strip */}
        <section id="field-workflow" aria-labelledby="field-workflow-title" className={`${container} scroll-mt-24 pt-28 sm:pt-40`}>
          <Heading
            id="field-workflow"
            label="Field inspection workflow"
            title="Built for inspectors on the road"
            lead="The Android field app keeps working without a connection and uploads when it can."
          />
          <ol data-reveal="stagger" className="mt-12 grid grid-cols-1 gap-y-8 sm:grid-cols-2 lg:grid-cols-5">
            {FIELD_FLOW.map(({ icon: Icon, title, text }, i) => (
              <li key={title} className="group relative border-t border-ri-line pt-6 sm:pr-8">
                <span aria-hidden className="absolute left-0 top-[-1px] h-px w-10 bg-white transition-[width] duration-500 ease-out motion-safe:group-hover:w-full" />
                <div className="flex items-center justify-between">
                  <span className="font-code-sm text-ri-faint">{String(i + 1).padStart(2, "0")}</span>
                  <Icon className="h-4 w-4 text-ri-muted transition-colors duration-300 group-hover:text-ri-text" />
                </div>
                <h3 className="mt-5 text-base font-medium text-ri-text">{title}</h3>
                <p className="mt-2 text-sm leading-relaxed text-ri-muted">{text}</p>
              </li>
            ))}
          </ol>
        </section>

        {/* Road health, maintenance, verification and recurrence: definition rows */}
        <section id="health-maintenance" aria-labelledby="health-maintenance-title" className={`${container} scroll-mt-24 pt-28 sm:pt-40`}>
          <div className="grid grid-cols-1 gap-12 lg:grid-cols-[minmax(0,4fr)_minmax(0,7fr)] lg:gap-20">
            <div className="lg:sticky lg:top-32 lg:self-start">
              <Heading
                id="health-maintenance"
                label="Road health and maintenance"
                title="From condition to a ranked work list"
              />
              <p id="verification" data-reveal className="mt-6 scroll-mt-24 text-xl font-normal leading-snug tracking-[-0.01em] text-ri-text-soft">
                A repair is closed with evidence, and watched afterwards.
              </p>
            </div>
            <dl data-reveal="stagger" className="border-t border-ri-line">
              {OPERATIONS.map((o) => (
                <div key={o.title} className="grid grid-cols-1 gap-x-8 gap-y-2 border-b border-ri-line py-7 sm:grid-cols-[minmax(0,2fr)_minmax(0,5fr)]">
                  <dt className="text-base font-medium text-ri-text">
                    {o.title}
                    {o.basis && (
                      <span className="mt-2 block">
                        <BasisTag basis={o.basis} />
                      </span>
                    )}
                  </dt>
                  <dd className="text-sm leading-relaxed text-ri-muted">{o.text}</dd>
                </div>
              ))}
            </dl>
          </div>
        </section>

        {/* Console preview: the interactive map, full width */}
        <section id="preview" aria-labelledby="preview-title" className={`${container} scroll-mt-24 pt-28 sm:pt-40`}>
          <Heading
            id="preview"
            label="Console preview"
            title="The operations console"
            lead="The web console includes a dashboard, the Spatial Map, damage review, priorities, maintenance, repairs, recurrence, reports and audit. The map below is an interactive 3D preview on a real base map with sample shapes; sign in to see your organization's data."
          />
          <div data-reveal="clip" className="mt-12">
            <DemoMap />
          </div>
        </section>

        {/* Request demo */}
        <section id="request-demo" aria-labelledby="request-demo-title" className={`${container} scroll-mt-24 py-28 sm:py-40`}>
          <div className="grid grid-cols-1 gap-12 border-t border-ri-line pt-14 lg:grid-cols-[minmax(0,5fr)_minmax(0,6fr)] lg:gap-20">
            <div data-reveal="stagger" className="space-y-5">
              <p className={eyebrow}>Request demo</p>
              <h2 id="request-demo-title" className={sectionTitle}>
                See it with your own roads
              </h2>
              <p className="max-w-md text-base leading-relaxed text-ri-muted">
                Tell us about your road network and how you inspect it today. Already have an account?
              </p>
              <Link href="/login" className={`group inline-flex items-center gap-2 rounded text-sm font-medium text-ri-text transition-colors hover:text-ri-muted ${focusRing}`}>
                Go to login <ArrowRight className="h-4 w-4 transition-transform duration-200 motion-safe:group-hover:translate-x-1" />
              </Link>
            </div>
            <div data-reveal>
              <RequestDemoForm />
            </div>
          </div>
        </section>
      </main>

      <footer className="border-t border-ri-line bg-ri-sunken">
        <div className={`${container} py-8 flex flex-col md:flex-row md:items-center justify-between gap-6`}>
          <div className="flex flex-col items-start gap-3">
            <BrandLogo variant="horizontal" size="sm" />
            <ApiStatusBadge />
          </div>
          <nav aria-label="Footer" className="flex flex-wrap gap-x-5 gap-y-2 text-sm text-ri-muted">
            <a href="#overview" className={`hover:text-ri-text transition-colors rounded ${focusRing}`}>Platform</a>
            <a href="#capabilities" className={`hover:text-ri-text transition-colors rounded ${focusRing}`}>Capabilities</a>
            <a href="#request-demo" className={`hover:text-ri-text transition-colors rounded ${focusRing}`}>Request Demo</a>
            <Link href="/login" className={`hover:text-ri-text transition-colors rounded ${focusRing}`}>Login</Link>
          </nav>
          <p className="text-xs text-ri-faint max-w-sm">
            AI detections are candidates until reviewed. Health, priority and deterioration figures are
            rule-based estimates.
          </p>
        </div>
      </footer>
    </div>
  );
}
