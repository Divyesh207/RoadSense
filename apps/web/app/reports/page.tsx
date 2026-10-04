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
              <span className="p-2 rounded-lg bg-ri-primary/10 border border-ri-primary/30 text-ri-primary">
                <FileText className="h-5 w-5" />
              </span>
              <h1 className="text-xl md:text-2xl font-bold tracking-tight text-white">
                Operational Reports & Exports
              </h1>
            </div>
            <p className="text-xs text-ri-muted mt-1 max-w-3xl leading-relaxed">
              Generate reports from stored operational records (road health, damage, maintenance and recurrence) and
              download them as PDF, CSV or JSON.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={() => loadReports()}
              disabled={loading}
              className="p-2 rounded-xl bg-ri-surface border border-ri-line text-ri-muted hover:text-white hover:border-ri-faint transition-colors disabled:opacity-50"
              title="Refresh Reports"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin text-ri-primary" : ""}`} />
            </button>
            <button
              onClick={() => setShowGenerateModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-ri-primary to-ri-info hover:from-ri-primary-bright hover:to-ri-info text-ri-bg font-bold rounded-xl text-xs shadow-lg shadow-ri-primary/20 transition-all"
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
        <div className="p-5 rounded-2xl bg-ri-surface border border-ri-line space-y-4 shadow-xl">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-ri-line">
            <div className="flex flex-wrap items-center gap-2 text-xs font-mono text-ri-muted">
              <Filter className="h-3.5 w-3.5 text-ri-primary" />
              <span>Filter by Type:</span>
              {["ALL", "ROAD_HEALTH", "DAMAGE_SUMMARY", "MAINTENANCE_LOG", "RECURRENCE_INTELLIGENCE"].map((t) => (
                <button
                  key={t}
                  onClick={() => setFilterType(t)}
                  className={`px-2.5 py-1 rounded-full text-xs font-mono font-medium transition-all ${
                    filterType === t
                      ? "bg-ri-primary/15 text-ri-primary-bright border border-ri-primary/40"
                      : "text-ri-muted hover:text-ri-text-soft bg-ri-bg border border-ri-line"
                  }`}
                >
                  {t.replace(/_/g, " ")}
                </button>
              ))}
            </div>
            <div className="text-xs font-mono text-ri-muted">
              Showing <span className="text-white font-semibold">{filteredReports.length}</span> reports
            </div>
          </div>

          {loading ? (
            <div className="py-16 text-center text-ri-muted text-xs font-mono flex flex-col items-center justify-center gap-2">
              <RefreshCw className="h-6 w-6 animate-spin text-ri-primary" />
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
                  <tr className="border-b border-ri-line bg-ri-bg/60 text-ri-muted text-[11px] font-mono uppercase tracking-wider">
                    <th className="px-4 py-3.5">Report Title / Type</th>
                    <th className="px-4 py-3.5">Format</th>
                    <th className="px-4 py-3.5">Status</th>
                    <th className="px-4 py-3.5">Timeframe</th>
                    <th className="px-4 py-3.5">Generated At</th>
                    <th className="px-4 py-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-ri-line/60">
                  {filteredReports.map((report) => (
                    <tr key={report.id} className="hover:bg-ri-raised/50 transition-colors">
                      <td className="px-4 py-3.5 font-medium text-white flex items-center gap-2.5">
                        <span className="p-1.5 rounded-lg bg-ri-bg border border-ri-line text-ri-primary">
                          <FileText className="h-4 w-4" />
                        </span>
                        <div>
                          <span className="font-semibold text-ri-text-soft">{report.report_type.replace(/_/g, " ")}</span>
                          <span className="block text-[10px] text-ri-faint font-mono mt-0.5">
                            REF: {report.id}
                          </span>
                        </div>
                      </td>

                      <td className="px-4 py-3.5 text-ri-text-soft">
                        <span className="px-2 py-0.5 rounded-md bg-ri-bg border border-ri-line text-[10px] font-mono font-bold text-ri-primary-bright">
                          {report.parameters?.artifact_format || report.parameters?.format || "PDF"}
                        </span>
                      </td>

                      <td className="px-4 py-3.5">
                        <span
                          className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-mono font-semibold ${
                            report.status === "COMPLETED"
                              ? "bg-ri-success/10 text-ri-success border border-ri-success/30"
                              : report.status === "QUEUED"
                              ? "bg-ri-primary/10 text-ri-primary-bright border border-ri-primary/30 animate-pulse"
                              : "bg-ri-danger/10 text-ri-danger border border-ri-danger/30"
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

                      <td className="px-4 py-3.5 text-ri-text-soft font-mono text-xs">
                        {report.parameters?.timeframe?.replace(/_/g, " ") || "Default Window"}
                      </td>

                      <td className="px-4 py-3.5 text-ri-muted font-mono text-xs">
                        {report.generated_at
                          ? new Date(report.generated_at).toLocaleString()
                          : new Date(report.created_at).toLocaleString()}
                      </td>

                      <td className="px-4 py-3.5 text-right">
                        <button
                          onClick={() => handleDownload(report.id)}
                          disabled={report.status !== "COMPLETED" || downloadingId === report.id}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-ri-bg hover:bg-ri-raised border border-ri-line text-ri-text-soft text-xs font-semibold disabled:opacity-40 transition-all hover:border-ri-primary/40"
                        >
                          {downloadingId === report.id ? (
                            <RefreshCw className="h-3.5 w-3.5 animate-spin text-ri-primary" />
                          ) : (
                            <Download className="h-3.5 w-3.5 text-ri-primary" />
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
        <div className="fixed inset-0 z-50 bg-ri-bg/80 backdrop-blur-md flex items-center justify-center p-4 animate-in fade-in duration-200">
          <div className="bg-ri-surface border border-ri-line rounded-2xl max-w-lg w-full p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-ri-line">
              <div className="flex items-center gap-2">
                <span className="p-1.5 rounded-lg bg-ri-primary/10 border border-ri-primary/30 text-ri-primary">
                  <Sparkles className="h-4 w-4" />
                </span>
                <h3 className="text-base font-bold text-white">Generate Operational Report</h3>
              </div>
              <button
                type="button"
                onClick={() => setShowGenerateModal(false)}
                className="p-1.5 rounded-lg text-ri-muted hover:text-white hover:bg-ri-raised transition"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            <p className="text-xs text-ri-muted">
              Select parameters to compile persisted operational data into an exported intelligence report.
            </p>

            <form onSubmit={handleGenerateReport} className="space-y-4 pt-1">
              <div>
                <label className="block text-xs font-semibold text-ri-text-soft mb-1.5 font-mono">
                  Report Type
                </label>
                <select
                  value={reportType}
                  onChange={(e) => setReportType(e.target.value)}
                  className="w-full bg-ri-bg border border-ri-line rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-ri-primary"
                >
                  <option value="ROAD_HEALTH">Road & Segment Health Scores (rule-based)</option>
                  <option value="DAMAGE_SUMMARY">Damage & Defect Intelligence Summary</option>
                  <option value="MAINTENANCE_LOG">Maintenance Execution & Verification Audit</option>
                  <option value="RECURRENCE_INTELLIGENCE">Recurrence & Failure Cycle Intelligence</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold text-ri-text-soft mb-1.5 font-mono">
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
                          ? "bg-ri-primary/15 text-ri-primary-bright border-ri-primary shadow-sm shadow-ri-primary/20"
                          : "bg-ri-bg text-ri-muted border-ri-line hover:text-white"
                      }`}
                    >
                      {fmt}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-ri-text-soft mb-1.5 font-mono">
                  Timeframe
                </label>
                <select
                  value={timeframe}
                  onChange={(e) => setTimeframe(e.target.value)}
                  className="w-full bg-ri-bg border border-ri-line rounded-xl px-3 py-2 text-xs text-white focus:outline-none focus:border-ri-primary"
                >
                  <option value="last_7_days">Last 7 Days</option>
                  <option value="last_30_days">Last 30 Days</option>
                  <option value="last_90_days">Last Quarter (90 Days)</option>
                  <option value="all_time">All Recorded History</option>
                </select>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-ri-line">
                <button
                  type="button"
                  onClick={() => setShowGenerateModal(false)}
                  className="px-3.5 py-2 rounded-xl text-xs font-medium text-ri-muted hover:text-white transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="px-4 py-2 bg-ri-primary hover:bg-ri-primary-bright text-ri-bg font-bold rounded-xl text-xs disabled:opacity-40 transition-all shadow-md shadow-ri-primary/20"
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
