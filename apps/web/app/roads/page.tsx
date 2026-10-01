"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { AppShell } from "@/components/shell";
import { api } from "@/lib/api-client";
import { Road } from "@/types/api";
import { Route, Search, MapPin, ChevronRight, Plus } from "lucide-react";

export default function RoadsPage() {
  const [roads, setRoads] = useState<Road[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadRoads() {
      try {
        const res = await api.roads.list({ search: search || undefined });
        if (res.data) {
          setRoads(res.data);
        }
      } catch (err) {
        console.error("Failed to load roads:", err);
      } finally {
        setLoading(false);
      }
    }

    loadRoads();
  }, [search]);

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white">Roads & Segments Management</h1>
            <p className="text-xs text-slate-400 mt-1">
              Authoritative road network inventory, geometries, and operational segments
            </p>
          </div>
        </div>

        {/* Filter bar */}
        <div className="flex items-center gap-4 bg-slate-900 p-3 rounded-lg border border-slate-800">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search roads by name, road code, or district..."
              className="w-full pl-9 pr-4 py-2 bg-slate-950 border border-slate-800 rounded-md text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>

        {/* Roads Table */}
        <div className="bg-slate-900 border border-slate-800 rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/60 border-b border-slate-800 text-slate-400">
                <tr>
                  <th className="py-3 px-4 font-semibold">Road Name</th>
                  <th className="py-3 px-4 font-semibold">Road Code</th>
                  <th className="py-3 px-4 font-semibold">Classification</th>
                  <th className="py-3 px-4 font-semibold">Administrative Area</th>
                  <th className="py-3 px-4 font-semibold">Status</th>
                  <th className="py-3 px-4 text-right font-semibold">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 text-slate-300">
                {loading ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-slate-500">
                      Loading road inventory...
                    </td>
                  </tr>
                ) : roads.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="py-8 text-center text-slate-500">
                      No roads found matching criteria.
                    </td>
                  </tr>
                ) : (
                  roads.map((road) => (
                    <tr key={road.id} className="hover:bg-slate-800/40 transition-colors">
                      <td className="py-3 px-4 font-medium text-white flex items-center gap-2">
                        <Route className="h-4 w-4 text-blue-400 shrink-0" />
                        <span>{road.name}</span>
                      </td>
                      <td className="py-3 px-4 font-mono text-[11px] text-slate-400">
                        {road.road_code || "—"}
                      </td>
                      <td className="py-3 px-4 text-slate-400">{road.road_type || "URBAN"}</td>
                      <td className="py-3 px-4 text-slate-400">{road.administrative_area || "—"}</td>
                      <td className="py-3 px-4">
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-950 text-emerald-400 border border-emerald-800/50">
                          Active
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right">
                        <span className="inline-flex items-center text-xs font-semibold text-blue-400 hover:text-blue-300">
                          Segments <ChevronRight className="h-3.5 w-3.5 ml-1" />
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </AppShell>
  );
}
