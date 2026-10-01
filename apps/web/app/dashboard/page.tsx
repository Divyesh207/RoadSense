"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/shell";
import { api } from "@/lib/api-client";
import { DamageRecord, Inspection, Road } from "@/types/api";
import {
  Route,
  AlertTriangle,
  ClipboardList,
  ShieldAlert,
  ArrowRight,
  TrendingUp,
  Activity,
  CheckCircle2,
} from "lucide-react";

export default function DashboardPage() {
  const [roads, setRoads] = useState<Road[]>([]);
  const [damages, setDamages] = useState<DamageRecord[]>([]);
  const [inspections, setInspections] = useState<Inspection[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [roadsRes, damagesRes, inspRes] = await Promise.all([
          api.roads.list({ page_size: 100 }),
          api.damages.list({ page_size: 100 }),
          api.inspections.list({ page_size: 5 }),
        ]);

        if (roadsRes.data) setRoads(roadsRes.data);
        if (damagesRes.data) setDamages(damagesRes.data);
        if (inspRes.data) setInspections(inspRes.data);
      } catch (err) {
        console.error("Failed to load dashboard operational data:", err);
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, []);

  const totalRoads = roads.length;
  const activeDamages = damages.filter((d) => d.status === "CONFIRMED").length;
  const pendingReviews = damages.filter((d) => d.status === "PENDING_REVIEW").length;
  const criticalDamages = damages.filter((d) => d.severity === "CRITICAL").length;

  return (
    <AppShell>
      <div className="space-y-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white">Operational Intelligence Dashboard</h1>
            <p className="text-xs text-slate-400 mt-1">
              Live municipal road condition metrics, AI detections, and review queues
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/damages"
              className="inline-flex items-center gap-2 px-3 py-2 bg-blue-600 hover:bg-blue-500 rounded-lg text-xs font-semibold text-white shadow-md shadow-blue-500/20 transition-all"
            >
              <span>Review Damage Queue</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>

        {/* Metric Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <div className="p-5 rounded-xl bg-slate-900 border border-slate-800">
            <div className="flex items-center justify-between text-slate-400 mb-3">
              <span className="text-xs font-medium">Roads Monitored</span>
              <Route className="h-4 w-4 text-blue-400" />
            </div>
            <p className="text-2xl font-bold text-white">{loading ? "..." : totalRoads}</p>
            <p className="text-[11px] text-slate-500 mt-1">Across active municipal network</p>
          </div>

          <div className="p-5 rounded-xl bg-slate-900 border border-slate-800">
            <div className="flex items-center justify-between text-slate-400 mb-3">
              <span className="text-xs font-medium">Active Damages</span>
              <AlertTriangle className="h-4 w-4 text-amber-400" />
            </div>
            <p className="text-2xl font-bold text-amber-400">{loading ? "..." : activeDamages}</p>
            <p className="text-[11px] text-slate-500 mt-1">Confirmed defects in pavement</p>
          </div>

          <div className="p-5 rounded-xl bg-slate-900 border border-slate-800">
            <div className="flex items-center justify-between text-slate-400 mb-3">
              <span className="text-xs font-medium">Critical Hazards</span>
              <ShieldAlert className="h-4 w-4 text-red-400" />
            </div>
            <p className="text-2xl font-bold text-red-400">{loading ? "..." : criticalDamages}</p>
            <p className="text-[11px] text-slate-500 mt-1">Severe potholes requiring patch</p>
          </div>

          <div className="p-5 rounded-xl bg-slate-900 border border-slate-800">
            <div className="flex items-center justify-between text-slate-400 mb-3">
              <span className="text-xs font-medium">Pending Human Review</span>
              <ClipboardList className="h-4 w-4 text-purple-400" />
            </div>
            <p className="text-2xl font-bold text-purple-400">{loading ? "..." : pendingReviews}</p>
            <p className="text-[11px] text-slate-500 mt-1">Candidate AI detections awaiting check</p>
          </div>
        </div>

        {/* Operational Overview Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Damage Severity Breakdown */}
          <div className="lg:col-span-1 p-6 rounded-xl bg-slate-900 border border-slate-800 space-y-4">
            <h2 className="text-sm font-semibold text-white">Severity Distribution</h2>
            <div className="space-y-3 pt-2">
              {[
                { label: "Critical", count: damages.filter((d) => d.severity === "CRITICAL").length, color: "bg-red-500", text: "text-red-400" },
                { label: "High", count: damages.filter((d) => d.severity === "HIGH").length, color: "bg-orange-500", text: "text-orange-400" },
                { label: "Medium", count: damages.filter((d) => d.severity === "MEDIUM").length, color: "bg-amber-500", text: "text-amber-400" },
                { label: "Low", count: damages.filter((d) => d.severity === "LOW").length, color: "bg-emerald-500", text: "text-emerald-400" },
              ].map((item) => (
                <div key={item.label} className="space-y-1">
                  <div className="flex justify-between text-xs">
                    <span className="text-slate-400">{item.label}</span>
                    <span className={`font-semibold ${item.text}`}>{item.count}</span>
                  </div>
                  <div className="h-1.5 w-full bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${item.color} rounded-full transition-all duration-500`}
                      style={{
                        width: damages.length > 0 ? `${(item.count / damages.length) * 100}%` : "0%",
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Recent Field Inspections */}
          <div className="lg:col-span-2 p-6 rounded-xl bg-slate-900 border border-slate-800 space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold text-white">Recent Field Inspections</h2>
              <Link href="/inspections" className="text-xs text-blue-400 hover:text-blue-300 font-medium">
                View All
              </Link>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-500">
                    <th className="pb-2 font-medium">Inspection ID</th>
                    <th className="pb-2 font-medium">Road</th>
                    <th className="pb-2 font-medium">Status</th>
                    <th className="pb-2 font-medium">Media</th>
                    <th className="pb-2 font-medium">Captured</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {inspections.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="py-6 text-center text-slate-500">
                        No recent inspections recorded.
                      </td>
                    </tr>
                  ) : (
                    inspections.map((insp) => (
                      <tr key={insp.id} className="hover:bg-slate-800/30 transition-colors">
                        <td className="py-3 font-mono text-[11px] text-slate-300">
                          <Link href={`/inspections/${insp.id}`} className="hover:text-blue-400">
                            {insp.id.slice(0, 8)}...
                          </Link>
                        </td>
                        <td className="py-3 text-slate-200">{insp.road_name || "Unassigned"}</td>
                        <td className="py-3">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                              insp.status === "COMPLETED"
                                ? "bg-emerald-950 text-emerald-400 border border-emerald-800/50"
                                : insp.status === "PROCESSING"
                                ? "bg-blue-950 text-blue-400 border border-blue-800/50 animate-pulse"
                                : "bg-slate-800 text-slate-400"
                            }`}
                          >
                            {insp.status}
                          </span>
                        </td>
                        <td className="py-3 text-slate-400">
                          {insp.media_summary?.media_count || 0} files
                        </td>
                        <td className="py-3 text-slate-500">
                          {new Date(insp.captured_at).toLocaleDateString()}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
