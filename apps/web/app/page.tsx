import React from "react";
import Link from "next/link";
import {
  Activity,
  ArrowRight,
  BarChart3,
  Brain,
  Camera,
  ClipboardCheck,
  FileText,
  History,
  ListOrdered,
  LogIn,
  Map as MapIcon,
  MapPin,
  RotateCcw,
  Route,
  Ruler,
  ShieldCheck,
  Smartphone,
  UploadCloud,
  UserCheck,
  WifiOff,
  Wrench,
} from "lucide-react";
import { BrandLogo } from "@/components/brand-logo";
import { LandingNav } from "@/components/landing/landing-nav";
import { PlatformPreview } from "@/components/landing/platform-preview";
import { RequestDemoForm } from "@/components/landing/request-demo-form";

// Everything on this page describes behaviour that exists in the platform. It carries no
// metrics: live figures for an organization are on the authenticated dashboard.

const focusRing =
  "focus:outline-none focus-visible:ring-2 focus-visible:ring-[#4CD7F6] focus-visible:ring-offset-2 focus-visible:ring-offset-[#0C1321]";
const card =
  "rounded-2xl border border-[#26344F] bg-[#111A2E] p-5 transition-all duration-200 hover:border-[#06B6D4]/50 hover:bg-[#17223A]/70 motion-safe:hover:-translate-y-0.5 hover:shadow-lg hover:shadow-black/30";
const eyebrow = "font-code-sm text-[#4CD7F6] uppercase tracking-widest";
const sectionTitle = "text-2xl sm:text-3xl font-bold tracking-tight text-[#F1F5F9]";
const sectionLead = "text-sm sm:text-base text-[#94A3B8] leading-relaxed max-w-3xl";

type Basis = "TRAINED AI" | "RULE-BASED" | "HUMAN REVIEW";

const BASIS_STYLE: Record<Basis, string> = {
  "TRAINED AI": "text-[#4CD7F6] border-[#06B6D4]/40 bg-[#06B6D4]/10",
  "RULE-BASED": "text-[#F59E0B] border-[#F59E0B]/40 bg-[#F59E0B]/10",
  "HUMAN REVIEW": "text-[#A78BFA] border-[#A78BFA]/40 bg-[#A78BFA]/10",
};

function BasisTag({ basis }: { basis: Basis }) {
  return (
    <span className={`inline-flex font-code-sm text-[10px] tracking-wider rounded-full border px-2 py-0.5 ${BASIS_STYLE[basis]}`}>
      {basis}
    </span>
  );
}

const OVERVIEW = [
  {
    icon: Smartphone,
    title: "Field capture",
    text: "Inspectors record a road, an optional segment, the phone's GPS position and photos in the Android field app.",
  },
  {
    icon: Brain,
    title: "Detection and review",
    text: "Photos are analysed into damage candidates. A reviewer confirms or rejects them before they count.",
  },
  {
    icon: Wrench,
    title: "Maintenance and verification",
    text: "Confirmed damage is prioritised, scheduled, repaired and verified with after-repair evidence.",
  },
];

const STEPS = [
  { name: "Inspect", text: "Capture photos and the GPS position against a road and segment in the field app." },
  { name: "Upload", text: "Inspections queue on the device and upload when a connection is available." },
  { name: "Detect", text: "A trained YOLO11s model proposes damage candidates on each photo.", basis: "TRAINED AI" as Basis },
  { name: "Review", text: "An authorized reviewer confirms or rejects each candidate.", basis: "HUMAN REVIEW" as Basis },
  { name: "Map", text: "Confirmed damage and inspection capture points appear at their recorded coordinates." },
  { name: "Assess", text: "Severity, road health and priority are calculated from documented rules.", basis: "RULE-BASED" as Basis },
  { name: "Repair", text: "Maintenance jobs move through assignment, field repair and after-repair evidence." },
  { name: "Verify", text: "Repairs are signed off by a person; damage that returns is tracked as a recurrence.", basis: "HUMAN REVIEW" as Basis },
];

const CAPABILITIES = [
  { icon: Camera, title: "Field inspections", text: "Photo inspections recorded against roads and segments from the Android field app." },
  { icon: MapPin, title: "GPS-based capture", text: "Each inspection stores the phone's reported position and accuracy, shown unchanged on the map." },
  { icon: Brain, title: "AI road-damage detection", text: "A trained YOLO11s model detects cracks and potholes in inspection photos." },
  { icon: UserCheck, title: "Damage review", text: "Detections stay candidates until a reviewer promotes or rejects them." },
  { icon: MapIcon, title: "Spatial damage map", text: "Damage, segments and inspection points on a filterable map." },
  { icon: Route, title: "Road and segment management", text: "Administrators add roads and draw segment geometry on the map." },
  { icon: Activity, title: "Road health assessment", text: "A rule-based health score per segment and road, with the deductions shown." },
  { icon: BarChart3, title: "Deterioration estimate", text: "A rule-based condition estimate from damage, health trend, recurrence and repair history." },
  { icon: ListOrdered, title: "Maintenance prioritisation", text: "A ranked queue with the factors behind each priority." },
  { icon: Wrench, title: "Maintenance operations", text: "Jobs tracked from creation through assignment, work and completion." },
  { icon: ClipboardCheck, title: "Repair verification", text: "After-repair evidence and location checks, then human sign-off." },
  { icon: RotateCcw, title: "Recurrence monitoring", text: "Damage that reappears at a repaired location is linked and escalated." },
  { icon: History, title: "Audit and history", text: "A record of who did what, and a timeline per road segment." },
  { icon: FileText, title: "Reports and exports", text: "Reports generated from the recorded data, available to download." },
];

const FIELD_FLOW = [
  { icon: Route, title: "Select road and segment", text: "The app lists the roads and segments defined on the web console." },
  { icon: MapPin, title: "Record position", text: "The phone's GPS fix and its reported accuracy are saved with the inspection." },
  { icon: Camera, title: "Capture photos", text: "Photos are taken in the app and attached to the inspection." },
  { icon: WifiOff, title: "Work offline", text: "Inspections are stored on the device and queued when there is no connection." },
  { icon: UploadCloud, title: "Sync", text: "Queued inspections upload in the background and show their sync status." },
];

function Section({
  id,
  label,
  title,
  lead,
  children,
}: {
  id: string;
  label: string;
  title: string;
  lead?: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} aria-labelledby={`${id}-title`} className="scroll-mt-20 space-y-8">
      <div className="space-y-3">
        <p className={eyebrow}>{label}</p>
        <h2 id={`${id}-title`} className={sectionTitle}>
          {title}
        </h2>
        {lead && <p className={sectionLead}>{lead}</p>}
      </div>
      {children}
    </section>
  );
}

export default function HomePage() {
  return (
    <div className="min-h-screen bg-[#0C1321] text-[#DCE2F6] selection:bg-[#06B6D4]/30 selection:text-white overflow-x-hidden">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:top-3 focus:left-3 focus:z-[60] focus:px-4 focus:py-2 focus:rounded-lg focus:bg-[#06B6D4] focus:text-[#003640] focus:text-sm focus:font-bold"
      >
        Skip to content
      </a>
      <LandingNav />

      <main id="main">
        {/* Hero */}
        <section className="relative border-b border-[#26344F]">
          <div
            aria-hidden
            className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_right,rgba(6,182,212,0.14),transparent_55%)] pointer-events-none"
          />
          <div className="relative max-w-7xl mx-auto px-4 sm:px-6 py-14 sm:py-20 grid grid-cols-1 lg:grid-cols-[1.1fr_0.9fr] gap-10 lg:gap-14 items-center">
            <div className="space-y-6">
              <BrandLogo variant="full" size="md" />
              <h1 className="text-3xl sm:text-4xl lg:text-5xl font-extrabold tracking-tight text-white leading-tight">
                Turn Road Inspections Into Actionable Infrastructure Intelligence.
              </h1>
              <p className="text-sm sm:text-base text-[#94A3B8] leading-relaxed max-w-2xl">
                Road Intelligence connects field inspections, AI-assisted damage detection, GPS and GIS mapping,
                road health assessment, maintenance prioritisation, repair verification and recurrence monitoring
                in one platform.
              </p>
              <div className="flex flex-col sm:flex-row gap-3 pt-1">
                <Link
                  href="/login"
                  className={`inline-flex items-center justify-center gap-2 h-12 px-6 rounded-xl bg-[#06B6D4] hover:bg-[#4CD7F6] text-[#003640] text-sm font-bold shadow-lg shadow-[#06B6D4]/20 transition-all motion-safe:hover:-translate-y-0.5 ${focusRing}`}
                >
                  <LogIn className="h-4 w-4" />
                  Login
                </Link>
                <a
                  href="#request-demo"
                  className={`inline-flex items-center justify-center gap-2 h-12 px-6 rounded-xl border border-[#26344F] bg-[#111A2E] hover:border-[#06B6D4]/60 hover:bg-[#17223A] text-[#F1F5F9] text-sm font-bold transition-all motion-safe:hover:-translate-y-0.5 ${focusRing}`}
                >
                  Request Demo
                  <ArrowRight className="h-4 w-4" />
                </a>
              </div>
              <div className="flex flex-wrap gap-2 pt-2">
                <BasisTag basis="TRAINED AI" />
                <BasisTag basis="RULE-BASED" />
                <BasisTag basis="HUMAN REVIEW" />
                <span className="text-xs text-[#64748B]">Every result is labelled with how it was produced.</span>
              </div>
            </div>
            <PlatformPreview />
          </div>
        </section>

        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-14 sm:py-20 space-y-20 sm:space-y-24">
          {/* Platform overview */}
          <Section
            id="overview"
            label="Platform overview"
            title="One record from the roadside to the verified repair"
            lead="An Android field app, an AI worker and a web operations console share one set of roads, segments, inspections and damage records. Each step keeps the evidence and the decision that led to the next."
          >
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {OVERVIEW.map(({ icon: Icon, title, text }) => (
                <div key={title} className={card}>
                  <div className="inline-flex p-2.5 rounded-xl bg-[#0C1321] border border-[#26344F] text-[#06B6D4] mb-4">
                    <Icon className="h-5 w-5" />
                  </div>
                  <h3 className="text-base font-bold text-[#F1F5F9]">{title}</h3>
                  <p className="text-sm text-[#94A3B8] mt-2 leading-relaxed">{text}</p>
                </div>
              ))}
            </div>
          </Section>

          {/* How it works */}
          <Section
            id="how-it-works"
            label="How it works"
            title="Eight steps, each with its source stated"
            lead="Steps that depend on a trained model, on fixed rules or on a person's decision are marked."
          >
            <ol className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {STEPS.map((s, i) => (
                <li key={s.name} className={card}>
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-code-md text-[#4CD7F6]">{String(i + 1).padStart(2, "0")}</span>
                    {s.basis && <BasisTag basis={s.basis} />}
                  </div>
                  <h3 className="text-sm font-bold text-[#F1F5F9] mt-3">{s.name}</h3>
                  <p className="text-xs text-[#94A3B8] mt-1.5 leading-relaxed">{s.text}</p>
                </li>
              ))}
            </ol>
          </Section>

          {/* Core capabilities */}
          <Section id="capabilities" label="Core capabilities" title="What the platform does today">
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {CAPABILITIES.map(({ icon: Icon, title, text }) => (
                <div key={title} className={card}>
                  <Icon className="h-5 w-5 text-[#06B6D4]" />
                  <h3 className="text-sm font-bold text-[#F1F5F9] mt-3">{title}</h3>
                  <p className="text-xs text-[#94A3B8] mt-1.5 leading-relaxed">{text}</p>
                </div>
              ))}
            </div>
          </Section>

          {/* AI + GIS */}
          <Section
            id="ai-gis"
            label="AI + GIS"
            title="Clear about what is a model, what is a rule and what is a decision"
            lead="The console never presents a rule-based score as a model prediction, and never treats an unreviewed detection as confirmed damage."
          >
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              <div className={`${card} border-t-2 border-t-[#06B6D4]`}>
                <BasisTag basis="TRAINED AI" />
                <h3 className="text-base font-bold text-[#F1F5F9] mt-3">Damage detection</h3>
                <p className="text-sm text-[#94A3B8] mt-2 leading-relaxed">
                  A YOLO11s model trained on the RDD2022 India road-damage dataset proposes crack and pothole
                  candidates with a model confidence. Candidates below the configured threshold are not reported.
                </p>
              </div>
              <div className={`${card} border-t-2 border-t-[#F59E0B]`}>
                <BasisTag basis="RULE-BASED" />
                <h3 className="text-base font-bold text-[#F1F5F9] mt-3">Severity, health, priority, deterioration</h3>
                <p className="text-sm text-[#94A3B8] mt-2 leading-relaxed">
                  These are calculated from fixed, documented rules, not from a trained model. Where the
                  heuristic image fallback is configured, its results are labelled as heuristic scores, not
                  probabilities.
                </p>
              </div>
              <div className={`${card} border-t-2 border-t-[#A78BFA]`}>
                <BasisTag basis="HUMAN REVIEW" />
                <h3 className="text-base font-bold text-[#F1F5F9] mt-3">Confirmation and sign-off</h3>
                <p className="text-sm text-[#94A3B8] mt-2 leading-relaxed">
                  A reviewer decides whether a detection becomes a damage record, and a person signs off each
                  repair verification. The original detection is kept alongside the decision.
                </p>
              </div>
            </div>
            <div className={`${card} flex flex-col sm:flex-row gap-4 sm:items-center`}>
              <div className="inline-flex p-3 rounded-xl bg-[#0C1321] border border-[#26344F] text-[#06B6D4] self-start">
                <MapIcon className="h-6 w-6" />
              </div>
              <div>
                <h3 className="text-base font-bold text-[#F1F5F9]">GIS on PostGIS</h3>
                <p className="text-sm text-[#94A3B8] mt-1.5 leading-relaxed">
                  Roads, segment geometry, inspections and damage are stored with coordinates and drawn on the
                  Spatial Map at exactly the stored position. Positions come from the phone&apos;s GPS, so their
                  accuracy is whatever the device reports.
                </p>
              </div>
            </div>
          </Section>

          {/* Field inspection workflow */}
          <Section
            id="field-workflow"
            label="Field inspection workflow"
            title="Built for inspectors on the road"
            lead="The Android field app keeps working without a connection and uploads when it can."
          >
            <ol className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
              {FIELD_FLOW.map(({ icon: Icon, title, text }) => (
                <li key={title} className={card}>
                  <Icon className="h-5 w-5 text-[#06B6D4]" />
                  <h3 className="text-sm font-bold text-[#F1F5F9] mt-3">{title}</h3>
                  <p className="text-xs text-[#94A3B8] mt-1.5 leading-relaxed">{text}</p>
                </li>
              ))}
            </ol>
          </Section>

          {/* Road health + maintenance */}
          <Section
            id="health-maintenance"
            label="Road health and maintenance"
            title="From condition to a ranked work list"
          >
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className={card}>
                <Ruler className="h-5 w-5 text-[#06B6D4]" />
                <h3 className="text-base font-bold text-[#F1F5F9] mt-3">Road health</h3>
                <p className="text-sm text-[#94A3B8] mt-2 leading-relaxed">
                  Each segment gets a health score with the deductions that produced it, and a trend from
                  earlier snapshots.
                </p>
                <div className="mt-3">
                  <BasisTag basis="RULE-BASED" />
                </div>
              </div>
              <div className={card}>
                <ListOrdered className="h-5 w-5 text-[#06B6D4]" />
                <h3 className="text-base font-bold text-[#F1F5F9] mt-3">Prioritisation</h3>
                <p className="text-sm text-[#94A3B8] mt-2 leading-relaxed">
                  Damage is ranked for repair with the contributing factors listed. Traffic is used only where a
                  documented figure has been entered.
                </p>
                <div className="mt-3">
                  <BasisTag basis="RULE-BASED" />
                </div>
              </div>
              <div className={card}>
                <Wrench className="h-5 w-5 text-[#06B6D4]" />
                <h3 className="text-base font-bold text-[#F1F5F9] mt-3">Maintenance operations</h3>
                <p className="text-sm text-[#94A3B8] mt-2 leading-relaxed">
                  Jobs follow a fixed set of states from creation to completion, with each change recorded in
                  the audit history.
                </p>
              </div>
            </div>
          </Section>

          {/* Repair verification + recurrence */}
          <Section
            id="verification"
            label="Repair verification and recurrence"
            title="A repair is closed with evidence, and watched afterwards"
          >
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className={card}>
                <ShieldCheck className="h-5 w-5 text-[#06B6D4]" />
                <h3 className="text-base font-bold text-[#F1F5F9] mt-3">Repair verification</h3>
                <p className="text-sm text-[#94A3B8] mt-2 leading-relaxed">
                  After-repair photos and their location are checked against the original damage, then a person
                  approves or rejects the repair.
                </p>
                <div className="mt-3">
                  <BasisTag basis="HUMAN REVIEW" />
                </div>
              </div>
              <div className={card}>
                <RotateCcw className="h-5 w-5 text-[#06B6D4]" />
                <h3 className="text-base font-bold text-[#F1F5F9] mt-3">Recurrence monitoring</h3>
                <p className="text-sm text-[#94A3B8] mt-2 leading-relaxed">
                  New damage near a previously repaired location is matched to it, counted as a recurrence and
                  escalated when it keeps returning.
                </p>
                <div className="mt-3">
                  <BasisTag basis="RULE-BASED" />
                </div>
              </div>
            </div>
          </Section>

          {/* Dashboard / map preview */}
          <Section
            id="preview"
            label="Console preview"
            title="The operations console"
            lead="The web console includes a dashboard, the Spatial Map, damage review, priorities, maintenance, repairs, recurrence, reports and audit. The drawing below shows the map layout; sign in to see your organization's data."
          >
            <PlatformPreview />
          </Section>

          {/* Request demo */}
          <section
            id="request-demo"
            aria-labelledby="request-demo-title"
            className="scroll-mt-20 rounded-3xl border border-[#26344F] bg-[#111A2E] p-6 sm:p-10 grid grid-cols-1 lg:grid-cols-[0.8fr_1.2fr] gap-8 lg:gap-12"
          >
            <div className="space-y-4">
              <p className={eyebrow}>Request demo</p>
              <h2 id="request-demo-title" className={sectionTitle}>
                See it with your own roads
              </h2>
              <p className="text-sm text-[#94A3B8] leading-relaxed">
                Tell us about your road network and how you inspect it today. Already have an account?
              </p>
              <Link
                href="/login"
                className={`inline-flex items-center gap-2 text-sm font-bold text-[#4CD7F6] hover:text-white transition-colors rounded ${focusRing}`}
              >
                Go to login <ArrowRight className="h-4 w-4" />
              </Link>
            </div>
            <RequestDemoForm />
          </section>
        </div>
      </main>

      <footer className="border-t border-[#26344F] bg-[#070E1C]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <BrandLogo variant="horizontal" size="sm" />
          <nav aria-label="Footer" className="flex flex-wrap gap-x-5 gap-y-2 text-sm text-[#94A3B8]">
            <a href="#overview" className={`hover:text-[#F1F5F9] transition-colors rounded ${focusRing}`}>Platform</a>
            <a href="#capabilities" className={`hover:text-[#F1F5F9] transition-colors rounded ${focusRing}`}>Capabilities</a>
            <a href="#request-demo" className={`hover:text-[#F1F5F9] transition-colors rounded ${focusRing}`}>Request Demo</a>
            <Link href="/login" className={`hover:text-[#F1F5F9] transition-colors rounded ${focusRing}`}>Login</Link>
          </nav>
          <p className="text-xs text-[#64748B] max-w-sm">
            AI detections are candidates until reviewed. Health, priority and deterioration figures are
            rule-based estimates.
          </p>
        </div>
      </footer>
    </div>
  );
}
