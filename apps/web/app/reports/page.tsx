"use client";

import React, { useEffect, useState } from "react";
import { AppShell } from "@/components/shell";
import { api } from "@/lib/api-client";
import { GeneratedReport } from "@/types/api";
import { BentoMetricTile } from "@/components/bento-metric-tile";
import { EmptyState } from "@/components/empty-state";
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
  ShieldCheck,
  Layers,
  X,
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
        window.location.assign(res.data.download_url);
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

  const completedCount = reports.filter((r) => r.status === "COMPLETED").length;

  return (
    <AppShell>
      <div className="space-y-6 animate-in fade-in duration-300">
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-2 rounded-lg bg-[#06B6D4]/10 border border-[#06B6D4]/30 text-[#06B6D4]">
                <FileText className="h-5 w-5" />
              </span>
              <h1 className="text-xl md:text-2xl font-bold tracking-tight text-white">
                Operational Reports & Exports
              </h1>
            </div>
            <p className="text-xs text-slate-400 mt-1 max-w-3xl leading-relaxed">
              Generate reports from stored operational records (road health, damage, maintenance and recurrence) and
              download them as PDF, CSV or JSON.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => loadReports()}
              disabled={loading}
              className="p-2 rounded-xl bg-[#111A2E] border border-[#26344F] text-slate-400 hover:text-white hover:border-slate-600 transition-colors disabled:opacity-50"
              title="Refresh Reports"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin text-[#06B6D4]" : ""}`} />
            </button>
            <button
              onClick={() => setShowGenerateModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-[#06B6D4] to-[#2563EB] hover:from-[#4CD7F6] hover:to-[#3B82F6] text-[#0C1321] font-bold rounded-xl text-xs shadow-lg shadow-[#06B6D4]/20 transition-all"
            >
              <Plus className="h-4 w-4 stroke-[3]" />
              <span>Generate Report</span>
            </button>
          </div>
        </div>

        {/* Bento Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <BentoMetricTile label="Generated Reports" value={loading ? "..." : reports.length} icon={FileText} />
          <BentoMetricTile
            label="Completed & Ready"
            value={loading ? "..." : completedCount}
            icon={FileCheck}
            status="nominal"
          />
          <BentoMetricTile label="Supported Formats" value="PDF · CSV · JSON" icon={Layers} />
        </div>

        {/* Filter and List Container */}
        <div className="p-5 rounded-2xl bg-[#111A2E] border border-[#26344F] space-y-4 shadow-xl">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-[#26344F]">
            <div className="flex flex-wrap items-center gap-2 text-xs font-mono text-slate-400">
              <Filter className="h-3.5 w-3.5 text-[#06B6D4]" />
              <span>Filter by Type:</span>
              {["ALL", "ROAD_HEALTH", "DAMAGE_SUMMARY", "MAINTENANCE_LOG", "RECURRENCE_INTELLIGENCE"].map((t) => (
                <button
                  key={t}
                  onClick={() => setFilterType(t)}
                  className={`px-2.5 py-1 rounded-full text-xs font-mono font-medium transition-all ${
                    filterType === t
                      ? "bg-[#06B6D4]/15 text-[#4CD7F6] border border-[#06B6D4]/40"
                      : "text-slate-400 hover:text-slate-200 bg-[#0C1321] border border-[#26344F]"
                  }`}
                >
                  {t.replace(/_/g, " ")}
                </button>
              ))}
            </div>
            <div className="text-xs font-mono text-slate-400">
              Showing <span className="text-white font-semibold">{filteredReports.length}</span> reports
            </div>
          </div>

          {loading ? (
            <div className="py-16 text-center text-slate-400 text-xs font-mono flex flex-col items-center justify-center gap-2">
              <RefreshCw className="h-6 w-6 animate-spin text-[#06B6D4]" />
              <span>Loading reports...</span>
            </div>
          ) : filteredReports.length === 0 ? (
            <EmptyState
              title="No Reports Generated"
              description="No reports match the selected filter. Use 'Generate Report' to create one from stored records."
              icon={FileText}
            />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs border-collapse">
                <thead>
                  <tr className="border-b border-[#26344F] bg-[#0C1321]/60 text-slate-400 text-[11px] font-mono uppercase tracking-wider">
                    <th className="px-4 py-3.5">Report Title / Type</th>
                    <th className="px-4 py-3.5">Format</th>
                    <th className="px-4 py-3.5">Status</th>
                    <th className="px-4 py-3.5">Timeframe</th>
                    <th className="px-4 py-3.5">Generated At</th>
                    <th className="px-4 py-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#26344F]/60">
                  {filteredReports.map((report) => (
                    <tr key={report.id} className="hover:bg-[#17223A]/50 transition-colors">
                      <td className="px-4 py-3.5 font-medium text-white flex items-center gap-2.5">
                        <span className="p-1.5 rounded-lg bg-[#0C1321] border border-[#26344F] text-[#06B6D4]">
                          <FileText className="h-4 w-4" />
                        </span>
                        <div>
                          <span className="font-semibold text-slate-200">{report.report_type.replace(/_/g, " ")}</span>
                          <span className="block text-[10px] text-slate-500 font-mono mt-0.5">
                            REF: {report.id}
                          </span>
                        </div>
                      </td>

                      <td className="px-4 py-3.5 text-slate-300">
                        <span className="px-2 py-0.5 rounded-md bg-[#0C1321] border border-[#26344F] text-[10px] font-mono font-bold text-[#4CD7F6]">
                          {report.parameters?.artifact_format || report.parameters?.format || "PDF"}
                        </span>
                      </td>

                      <td className="px-4 py-3.5">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-mono font-semibold ${
                            report.status === "COMPLETED"
                              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                              : report.status === "QUEUED"
                              ? "bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 animate-pulse"
                              : "bg-red-500/10 text-red-400 border border-red-500/30"
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

                      <td className="px-4 py-3.5 text-slate-300 font-mono text-xs">
                        {report.parameters?.timeframe?.replace(/_/g, " ") || "Default Window"}
                      </td>

                      <td className="px-4 py-3.5 text-slate-400 font-mono text-xs">
                        {report.generated_at
                          ? new Date(report.generated_at).toLocaleString()
                          : new Date(report.created_at).toLocaleString()}
                      </td>

                      <td className="px-4 py-3.5 text-right">
                        <button
                          onClick={() => handleDownload(report.id)}
                          disabled={report.status !== "COMPLETED" || downloadingId === report.id}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-[#0C1321] hover:bg-[#17223A] border border-[#26344F] text-slate-200 text-xs font-semibold disabled:opacity-40 transition-all hover:border-[#06B6D4]/40"
                        >
                          {downloadingId === report.id ? (
                            <RefreshCw className="h-3.5 w-3.5 animate-spin text-[#06B6D4]" />
                          ) : (
                            <Download className="h-3.5 w-3.5 text-[#06B6D4]" />
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
        <div className="fixed inset-0 z-50 bg-[#0C1321]/80 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="bg-[#111A2E] border border-[#26344F] rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#26344F]">
              <div className="flex items-center gap-2">
                <span className="p-1.5 rounded-lg bg-[#06B6D4]/10 border border-[#06B6D4]/30 text-[#06B6D4]">
                  <Sparkles className="h-4 w-4" />
                </span>
                <h3 className="text-base font-bold text-white">Generate Operational Report</h3>
              </div>
              <button
                type="button"
                onClick={() => setShowGenerateModal(false)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-[#17223A] transition"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <p className="text-xs text-slate-400">
              Select parameters to compile persisted operational data into an exported intelligence report.
            </p>

            <form onSubmit={handleGenerateReport} className="space-y-4 pt-1">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5 font-mono">
                  Report Type
                </label>
                <select
                  value={reportType}
                  onChange={(e) => setReportType(e.target.value)}
                  className="w-full bg-[#0C1321] border border-[#26344F] rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-[#06B6D4]"
                >
                  <option value="ROAD_HEALTH">Road & Segment Health Scores (rule-based)</option>
                  <option value="DAMAGE_SUMMARY">Damage & Defect Intelligence Summary</option>
                  <option value="MAINTENANCE_LOG">Maintenance Execution & Verification Audit</option>
                  <option value="RECURRENCE_INTELLIGENCE">Recurrence & Failure Cycle Intelligence</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5 font-mono">
                  Export Format
                </label>
                <div className="grid grid-cols-3 gap-2">
                  {["PDF", "CSV", "JSON"].map((fmt) => (
                    <button
                      key={fmt}
                      type="button"
                      onClick={() => setFormat(fmt)}
                      className={`py-2 rounded-xl text-xs font-mono font-bold border transition-all ${
                        format === fmt
                          ? "bg-[#06B6D4]/15 text-[#4CD7F6] border-[#06B6D4] shadow-sm shadow-[#06B6D4]/20"
                          : "bg-[#0C1321] text-slate-400 border-[#26344F] hover:text-white"
                      }`}
                    >
                      {fmt}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1.5 font-mono">
                  Timeframe
                </label>
                <select
                  value={timeframe}
                  onChange={(e) => setTimeframe(e.target.value)}
                  className="w-full bg-[#0C1321] border border-[#26344F] rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-[#06B6D4]"
                >
                  <option value="last_7_days">Last 7 Days</option>
                  <option value="last_30_days">Last 30 Days</option>
                  <option value="last_90_days">Last Quarter (90 Days)</option>
                  <option value="all_time">All Recorded History</option>
                </select>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-[#26344F]">
                <button
                  type="button"
                  onClick={() => setShowGenerateModal(false)}
                  className="px-3.5 py-2 rounded-xl text-xs font-medium text-slate-400 hover:text-white transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="px-4 py-2 bg-[#06B6D4] hover:bg-[#4CD7F6] text-[#0C1321] font-bold rounded-xl text-xs disabled:opacity-40 transition-all shadow-md shadow-[#06B6D4]/20"
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
