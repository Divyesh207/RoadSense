import Link from "next/link";
import { 
  Activity, 
  AlertTriangle, 
  CheckCircle2, 
  MapPin, 
  Layers, 
  ShieldAlert, 
  TrendingUp, 
  Wrench 
} from "lucide-react";

export default function HomePage() {
  const stats = [
    { label: "Tracked Road Segments", value: "1,248", icon: Layers, change: "+12 this month" },
    { label: "Active Detections", value: "342", icon: AlertTriangle, change: "48 high severity" },
    { label: "Pending AI Review", value: "29", icon: ShieldAlert, change: "Requires attention" },
    { label: "Verified Repairs", value: "891", icon: CheckCircle2, change: "96.4% success rate" },
  ];

  const lifecycleStages = [
    { step: "01", name: "Data Collection", desc: "GPS & visual evidence capture via Android field app" },
    { step: "02", name: "AI Damage Detection", desc: "Local YOLO inference detects damage & bounding boxes" },
    { step: "03", name: "Severity Assessment", desc: "Multi-factor severity scoring (depth, area, traffic)" },
    { step: "04", name: "GIS Segment Mapping", desc: "PostGIS spatial alignment to authoritative road segments" },
    { step: "05", name: "Human Review", desc: "Authority confirmation preserving raw AI provenance" },
    { step: "06", name: "Health & Prediction", desc: "Road health indices & XGBoost deterioration prediction" },
    { step: "07", name: "Maintenance & Repair", desc: "Work order dispatch, field repair, and after-evidence" },
    { step: "08", name: "AI Repair Verification", desc: "Automated before/after evidence validation & recurrence" },
  ];

  return (
    <main className="min-h-screen bg-slate-950 text-slate-50">
      {/* Top Navigation */}
      <header className="border-b border-slate-800 bg-slate-900/60 backdrop-blur sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-lg bg-blue-600 flex items-center justify-center font-bold text-white shadow-lg shadow-blue-500/30">
              RI
            </div>
            <div>
              <h1 className="text-base font-semibold tracking-tight text-white leading-none">
                Road Intelligence Platform
              </h1>
              <p className="text-xs text-slate-400 mt-1">Infrastructure Condition & Pothole Management</p>
            </div>
          </div>
          <div className="flex items-center gap-4 text-sm">
            <span className="flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-950/60 border border-emerald-800/80 text-emerald-400 text-xs">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
              API Connected: v1.0.0
            </span>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-7xl mx-auto px-6 py-10 space-y-10">
        {/* Hero Section */}
        <section className="space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-md bg-blue-950/50 border border-blue-800/50 text-blue-400 text-xs font-medium">
            <Activity className="h-3.5 w-3.5" />
            Autonomous Road Infrastructure Operations
          </div>
          <h2 className="text-3xl lg:text-4xl font-extrabold tracking-tight text-white">
            End-to-End Road Condition Intelligence
          </h2>
          <p className="text-slate-400 max-w-3xl text-base leading-relaxed">
            A unified municipal intelligence platform that traces road damage from initial field capture,
            local AI damage detection, PostGIS segment association, deterioration forecasting, to maintenance
            dispatch and AI-verified repairs.
          </p>
        </section>

        {/* Operational Stats */}
        <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {stats.map((stat, idx) => {
            const Icon = stat.icon;
            return (
              <div 
                key={idx}
                className="p-5 rounded-xl border border-slate-800 bg-slate-900/40 backdrop-blur hover:border-slate-700 transition"
              >
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs font-medium text-slate-400">{stat.label}</span>
                  <div className="p-2 rounded-lg bg-slate-800/60 text-slate-300">
                    <Icon className="h-4 w-4" />
                  </div>
                </div>
                <div className="text-2xl font-bold text-white tracking-tight">{stat.value}</div>
                <div className="text-xs text-slate-400 mt-2">{stat.change}</div>
              </div>
            );
          })}
        </section>

        {/* Lifecycle Pipeline */}
        <section className="p-6 rounded-2xl border border-slate-800 bg-slate-900/30 space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-white">Production Road Intelligence Lifecycle</h3>
              <p className="text-xs text-slate-400 mt-1">Authoritative 8-stage traceability chain</p>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {lifecycleStages.map((stage) => (
              <div 
                key={stage.step}
                className="p-4 rounded-xl border border-slate-800/80 bg-slate-900/60 space-y-2 hover:border-blue-500/40 transition"
              >
                <div className="text-xs font-mono font-bold text-blue-400">{stage.step}</div>
                <div className="text-sm font-semibold text-slate-200">{stage.name}</div>
                <p className="text-xs text-slate-400 leading-normal">{stage.desc}</p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </main>
  );
}
