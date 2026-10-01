"use client";

import React, { useEffect, useState } from "react";
import { AppShell } from "@/components/shell";
import { api } from "@/lib/api-client";
import { GeneratedReport } from "@/types/api";
import {
  FileText,
  Download,
  Plus,
  RefreshCw,
  CheckCircle2,
  Clock,
  AlertTriangle,
  FileCheck,
  Filter,
  Sparkles,
} from "lucide-react";

export default function ReportsPage() {
  const [reports, setReports] = useState<GeneratedReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [showGenerateModal, setShowGenerateModal] = useState(false);
  const [filterType, setFilterType] = useState<string>("ALL");

  // Form State
  const [reportType, setReportType] = useState<string>("ROAD_HEALTH");
  const [format, setFormat] = useState<string>("PDF");
  const [timeframe, setTimeframe] = useState<string>("last_30_days");
  const [downloadingId, setDownloadingId] = useState<string | null>(null);

  async function loadReports() {
    try {
      setLoading(true);
      const res = await api.reports.list({ page_size: 50 });
      if (res.data) {
        setReports(res.data);
      }
    } catch (err) {
      console.error("Failed to load reports:", err);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadReports();
  }, []);

  async function handleGenerateReport(e: React.FormEvent) {
    e.preventDefault();
    try {
      setCreating(true);
      await api.reports.create({
        report_type: reportType,
        parameters: {
          format,
          timeframe,
        },
      });
      setShowGenerateModal(false);
      await loadReports();
    } catch (err) {
      console.error("Failed to generate report:", err);
    } finally {
      setCreating(false);
    }
  }

  async function handleDownload(reportId: string) {
    try {
      setDownloadingId(reportId);
      const res = await api.reports.getDownloadUrl(reportId);
      if (res.data?.download_url) {
        window.open(res.data.download_url, "_blank");
      }
    } catch (err) {
      console.error("Failed to download report:", err);
    } finally {
      setDownloadingId(null);
    }
  }

  const filteredReports = reports.filter((r) => {
    if (filterType === "ALL") return true;
    return r.report_type === filterType;
  });

  return (
    <AppShell>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              <span>Operational & Compliance Reports</span>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-cyan-950 text-cyan-400 border border-cyan-800/40">
                Phase 15
              </span>
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Asynchronous report generation, municipal audit exports, and road health summaries
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => loadReports()}
              className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-white transition-colors"
              title="Refresh Reports"
            >
              <RefreshCw className="h-4 w-4" />
            </button>
            <button
              onClick={() => setShowGenerateModal(true)}
              className="inline-flex items-center gap-2 px-3.5 py-2 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white rounded-lg text-xs font-semibold shadow-md shadow-cyan-600/20 transition-all"
            >
              <Plus className="h-3.5 w-3.5" />
              <span>Generate Report</span>
            </button>
          </div>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-cyan-950/60 border border-cyan-800/40 text-cyan-400">
              <FileText className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs font-medium text-slate-400">Generated Reports</p>
              <p className="text-xl font-bold text-white mt-0.5">{reports.length}</p>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-emerald-950/60 border border-emerald-800/40 text-emerald-400">
              <FileCheck className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs font-medium text-slate-400">Completed & Ready</p>
              <p className="text-xl font-bold text-emerald-400 mt-0.5">
                {reports.filter((r) => r.status === "COMPLETED").length}
              </p>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-purple-950/60 border border-purple-800/40 text-purple-400">
              <Sparkles className="h-5 w-5" />
            </div>
            <div>
              <p className="text-xs font-medium text-slate-400">Supported Formats</p>
              <p className="text-sm font-bold text-white mt-0.5">PDF • CSV • JSON</p>
            </div>
          </div>
        </div>

        {/* Filters and List */}
        <div className="p-5 rounded-xl bg-slate-900 border border-slate-800 space-y-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
            <div className="flex items-center gap-2 text-xs font-medium text-slate-400">
              <Filter className="h-3.5 w-3.5" />
              <span>Filter by Type:</span>
              {["ALL", "ROAD_HEALTH", "DAMAGE_SUMMARY", "MAINTENANCE_LOG"].map((t) => (
                <button
                  key={t}
                  onClick={() => setFilterType(t)}
                  className={`px-2.5 py-1 rounded-md text-xs font-medium transition-colors ${
                    filterType === t
                      ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/30"
                      : "text-slate-400 hover:text-slate-200"
                  }`}
                >
                  {t.replace("_", " ")}
                </button>
              ))}
            </div>
          </div>

          {loading ? (
            <div className="py-12 text-center text-slate-500 text-xs flex items-center justify-center gap-2">
              <RefreshCw className="h-4 w-4 animate-spin text-cyan-400" />
              <span>Loading reports...</span>
            </div>
          ) : filteredReports.length === 0 ? (
            <div className="py-12 text-center text-slate-500 text-xs">
              No reports found. Click "Generate Report" above to generate a new operational summary.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-slate-800 text-slate-500">
                    <th className="pb-3 font-medium">Report Title / Type</th>
                    <th className="pb-3 font-medium">Format</th>
                    <th className="pb-3 font-medium">Status</th>
                    <th className="pb-3 font-medium">Timeframe</th>
                    <th className="pb-3 font-medium">Generated At</th>
                    <th className="pb-3 font-medium text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {filteredReports.map((report) => (
                    <tr key={report.id} className="hover:bg-slate-800/30 transition-colors">
                      <td className="py-3.5 font-medium text-white flex items-center gap-2">
                        <FileText className="h-4 w-4 text-cyan-400 flex-shrink-0" />
                        <div>
                          <span>{report.report_type.replace("_", " ")}</span>
                          <span className="block text-[10px] text-slate-500 font-mono">
                            ID: {report.id.slice(0, 8)}...
                          </span>
                        </div>
                      </td>
                      <td className="py-3.5 text-slate-300">
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-[10px] font-mono font-semibold text-slate-300">
                          {report.parameters?.format || "PDF"}
                        </span>
                      </td>
                      <td className="py-3.5">
                        <span
                          className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-semibold ${
                            report.status === "COMPLETED"
                              ? "bg-emerald-950 text-emerald-400 border border-emerald-800/40"
                              : report.status === "QUEUED"
                              ? "bg-blue-950 text-blue-400 border border-blue-800/40 animate-pulse"
                              : "bg-red-950 text-red-400 border border-red-800/40"
                          }`}
                        >
                          {report.status === "COMPLETED" ? (
                            <CheckCircle2 className="h-3 w-3" />
                          ) : (
                            <Clock className="h-3 w-3" />
                          )}
                          <span>{report.status}</span>
                        </span>
                      </td>
                      <td className="py-3.5 text-slate-400">
                        {report.parameters?.timeframe?.replace("_", " ") || "Default"}
                      </td>
                      <td className="py-3.5 text-slate-400">
                        {report.generated_at
                          ? new Date(report.generated_at).toLocaleString()
                          : new Date(report.created_at).toLocaleString()}
                      </td>
                      <td className="py-3.5 text-right">
                        <button
                          onClick={() => handleDownload(report.id)}
                          disabled={report.status !== "COMPLETED" || downloadingId === report.id}
                          className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium disabled:opacity-40 transition-colors"
                        >
                          {downloadingId === report.id ? (
                            <RefreshCw className="h-3.5 w-3.5 animate-spin" />
                          ) : (
                            <Download className="h-3.5 w-3.5 text-cyan-400" />
                          )}
                          <span>Download</span>
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Generate Report Modal */}
      {showGenerateModal && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 shadow-2xl space-y-4">
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-cyan-400" />
              <span>Generate Operational Report</span>
            </h3>
            <p className="text-xs text-slate-400">
              Select parameters to compile persisted operational data into an exported intelligence report.
            </p>

            <form onSubmit={handleGenerateReport} className="space-y-4 pt-2">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Report Type
                </label>
                <select
                  value={reportType}
                  onChange={(e) => setReportType(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500"
                >
                  <option value="ROAD_HEALTH">Road Health & Segment PCI Index</option>
                  <option value="DAMAGE_SUMMARY">Damage & Defect Intelligence Summary</option>
                  <option value="MAINTENANCE_LOG">Maintenance Execution & Verification Audit</option>
                  <option value="RECURRENCE_INTELLIGENCE">Recurrence & Failure Cycle Intelligence</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Export Format
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {["PDF", "CSV", "JSON"].map((fmt) => (
                    <button
                      key={fmt}
                      type="button"
                      onClick={() => setFormat(fmt)}
                      className={`py-2 rounded-lg text-xs font-semibold border transition-all ${
                        format === fmt
                          ? "bg-cyan-500/10 text-cyan-400 border-cyan-500/40"
                          : "bg-slate-800 text-slate-400 border-slate-700 hover:text-white"
                      }`}
                    >
                      {fmt}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5">
                  Timeframe
                </label>
                <select
                  value={timeframe}
                  onChange={(e) => setTimeframe(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500"
                >
                  <option value="last_7_days">Last 7 Days</option>
                  <option value="last_30_days">Last 30 Days</option>
                  <option value="last_90_days">Last Quarter (90 Days)</option>
                  <option value="all_time">All Recorded History</option>
                </select>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowGenerateModal(false)}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-xs font-semibold disabled:opacity-40"
                >
                  {creating ? "Submitting Request..." : "Request Generation"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </AppShell>
  );
}
