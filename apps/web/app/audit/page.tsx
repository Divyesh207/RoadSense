"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  ArrowLeft,
  ShieldCheck,
  Search,
  Filter,
  RefreshCw,
  FileCheck2,
  Lock,
  Server,
  Activity,
  User,
  Clock,
  ChevronLeft,
  ChevronRight,
  Eye,
  AlertCircle,
  X,
  Terminal,
} from "lucide-react";
import { AppShell } from "@/components/shell";
import { api } from "@/lib/api-client";
import { AuditLogItem } from "@/types/api";
import { BentoMetricTile } from "@/components/bento-metric-tile";
import { EmptyState } from "@/components/empty-state";

export default function AuditLogsPage() {
  const router = useRouter();

  const goBack = () => {
    if (typeof window === "undefined") return;
    const nav = (window as Window & { navigation?: { canGoBack?: boolean } }).navigation;
    const canGoBack =
      typeof nav?.canGoBack === "boolean" ? nav.canGoBack : document.referrer.startsWith(window.location.origin);
    if (canGoBack) router.back();
    else router.push("/dashboard");
  };

  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [currentPage, setCurrentPage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [actionFilter, setActionFilter] = useState("");
  const [entityFilter, setEntityFilter] = useState("");
  const [selectedLog, setSelectedLog] = useState<AuditLogItem | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const fetchLogs = async (page: number = 1) => {
    try {
      setLoading(true);
      setErrorMessage(null);
      const params: Record<string, any> = {
        page,
        page_size: 20,
      };
      if (actionFilter) params.action = actionFilter;
      if (entityFilter) params.entity_type = entityFilter;

      const res = await api.auditLogs.list(params);
      if (res.success && res.data) {
        setLogs(res.data);
        setTotalCount(res.meta.total_count);
        setTotalPages(res.meta.total_pages);
        setCurrentPage(page);
      } else {
        setErrorMessage(res.error?.message || "Failed to load audit logs.");
      }
    } catch (err: any) {
      setErrorMessage(err.message || "An unexpected error occurred while fetching audit trail.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLogs(1);
  }, [actionFilter, entityFilter]);

  const getActionBadgeColor = (action: string) => {
    if (action.includes("DELETE") || action.includes("REJECT")) {
      return "bg-rose-500/10 text-rose-400 border-rose-500/30";
    }
    if (action.includes("CREATE") || action.includes("CONFIRM") || action.includes("VERIF")) {
      return "bg-emerald-500/10 text-emerald-400 border-emerald-500/30";
    }
    if (action.includes("UPDATE") || action.includes("ASSIGN")) {
      return "bg-amber-500/10 text-amber-400 border-amber-500/30";
    }
    return "bg-[#06B6D4]/10 text-[#4CD7F6] border-[#06B6D4]/30";
  };

  return (
    <AppShell>
      <div className="space-y-6 animate-in fade-in duration-300">
        {/* Navigation Breadcrumb */}
        <nav aria-label="Breadcrumb" className="flex items-center gap-2 text-xs font-mono">
          <button
            type="button"
            onClick={goBack}
            className="inline-flex items-center gap-1 text-[#4CD7F6] hover:underline"
          >
            <ArrowLeft className="h-3 w-3" />
            Back
          </button>
          <span className="text-slate-600">/</span>
          <Link href="/dashboard" className="text-slate-400 hover:text-slate-200">
            Operations
          </Link>
          <span className="text-slate-600">/</span>
          <span className="text-slate-200">Audit &amp; Security</span>
        </nav>

        {/* Page Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="p-2 rounded-lg bg-[#06B6D4]/10 border border-[#06B6D4]/30 text-[#06B6D4]">
                <ShieldCheck className="h-5 w-5" />
              </span>
              <h1 className="text-xl md:text-2xl font-bold tracking-tight text-white">
                Audit & Security
              </h1>
            </div>
            <p className="text-xs text-slate-400 mt-1 max-w-3xl leading-relaxed">
              Operational audit log: recorded actions with actor, entity, client IP and stored before/after values.
            </p>
          </div>
          <button
            onClick={() => fetchLogs(currentPage)}
            disabled={loading}
            className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-[#111A2E] border border-[#26344F] text-slate-200 text-xs font-semibold hover:border-[#06B6D4]/40 hover:text-white transition-all disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin text-[#06B6D4]" : ""}`} />
            Refresh Audit Trail
          </button>
        </div>

        {/* Security Bento Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          <BentoMetricTile label="RBAC & Isolation" value="Enforced Multi-Tenant" icon={Lock} />
          <BentoMetricTile label="OWASP Headers" value="CSP, HSTS & Anti-Sniff" icon={Server} />
          <BentoMetricTile label="Rate Limiter" value="Sliding-Window Active" icon={Activity} />
          <BentoMetricTile
            label="Audited Records"
            value={loading ? "..." : totalCount}
            subtext="Matching the current filters"
            icon={FileCheck2}
          />
        </div>

        {/* Filter Bar */}
        <div className="p-4 rounded-xl bg-[#111A2E] border border-[#26344F] flex flex-wrap items-center gap-4">
          <div className="flex items-center gap-2 flex-1 min-w-[220px]">
            <Search className="h-4 w-4 text-[#06B6D4]" />
            <input
              type="text"
              placeholder="Filter by action (e.g. DAMAGE_CONFIRMED, LOGIN)..."
              value={actionFilter}
              onChange={(e) => setActionFilter(e.target.value)}
              className="w-full bg-[#0C1321] border border-[#26344F] rounded-xl px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#06B6D4] font-mono"
            />
          </div>
          <div className="flex items-center gap-2 min-w-[200px]">
            <Filter className="h-4 w-4 text-[#06B6D4]" />
            <input
              type="text"
              placeholder="Filter by entity type..."
              value={entityFilter}
              onChange={(e) => setEntityFilter(e.target.value)}
              className="w-full bg-[#0C1321] border border-[#26344F] rounded-xl px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-[#06B6D4] font-mono"
            />
          </div>
          <div className="text-xs font-mono text-slate-400">
            Total records: <span className="text-white font-semibold">{totalCount}</span>
          </div>
        </div>

        {/* Error state */}
        {errorMessage && (
          <div className="p-4 rounded-xl bg-red-950/40 border border-red-800 text-red-200 text-xs flex items-center gap-2">
            <AlertCircle className="h-4 w-4 shrink-0 text-red-400" />
            <p>{errorMessage}</p>
          </div>
        )}

        {/* Audit Log Table */}
        <div className="rounded-2xl border border-[#26344F] bg-[#111A2E] overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse text-xs">
              <thead>
                <tr className="border-b border-[#26344F] bg-[#0C1321]/60 text-[11px] font-semibold text-slate-400 uppercase tracking-wider font-mono">
                  <th className="px-5 py-3.5">Timestamp</th>
                  <th className="px-5 py-3.5">Action</th>
                  <th className="px-5 py-3.5">Entity</th>
                  <th className="px-5 py-3.5">Actor</th>
                  <th className="px-5 py-3.5">Client IP</th>
                  <th className="px-5 py-3.5 text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#26344F]/60">
                {loading ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-16 text-center text-slate-400">
                      <RefreshCw className="h-5 w-5 animate-spin mx-auto text-[#06B6D4] mb-2" />
                      <p className="font-mono text-xs">Loading audit records...</p>
                    </td>
                  </tr>
                ) : logs.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-6 py-12">
                      <EmptyState
                        title="No Audit Records Located"
                        description="No audit records found matching your filters."
                        icon={ShieldCheck}
                      />
                    </td>
                  </tr>
                ) : (
                  logs.map((log) => (
                    <tr key={log.id} className="hover:bg-[#17223A]/50 transition-colors">
                      <td className="px-5 py-3.5 text-slate-300 font-mono text-[11px] whitespace-nowrap">
                        <div className="flex items-center gap-1.5">
                          <Clock className="h-3 w-3 text-slate-500" />
                          <span>{new Date(log.created_at).toLocaleString()}</span>
                        </div>
                      </td>

                      <td className="px-5 py-3.5 whitespace-nowrap">
                        <span className={`inline-flex px-2.5 py-1 rounded-full text-[11px] font-mono font-bold border ${getActionBadgeColor(log.action)}`}>
                          {log.action}
                        </span>
                      </td>

                      <td className="px-5 py-3.5 whitespace-nowrap font-mono text-[11px]">
                        <span className="text-white font-medium">{log.entity_type}</span>
                        {log.entity_id && (
                          <span className="text-slate-500 block truncate max-w-[140px] text-[10px]">
                            {log.entity_id}
                          </span>
                        )}
                      </td>

                      <td className="px-5 py-3.5 whitespace-nowrap text-slate-300 font-mono text-[11px]">
                        <div className="flex items-center gap-1.5">
                          <User className="h-3 w-3 text-slate-500" />
                          <span className="truncate max-w-[140px]">
                            {log.actor_user_id || "System"}
                          </span>
                        </div>
                      </td>

                      <td className="px-5 py-3.5 whitespace-nowrap text-slate-400 font-mono text-[11px]">
                        {log.ip_address || "—"}
                      </td>

                      <td className="px-5 py-3.5 whitespace-nowrap text-right">
                        <button
                          onClick={() => setSelectedLog(log)}
                          className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-[#0C1321] hover:bg-[#17223A] border border-[#26344F] text-[#4CD7F6] text-xs font-semibold transition hover:border-[#06B6D4]/40"
                        >
                          <Eye className="h-3 w-3 text-[#06B6D4]" />
                          <span>Inspect</span>
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Footer */}
          {totalPages > 1 && (
            <div className="px-5 py-3.5 border-t border-[#26344F] bg-[#0C1321]/60 flex items-center justify-between font-mono text-xs">
              <span className="text-slate-400">
                Page <span className="text-white font-semibold">{currentPage}</span> of {totalPages} ({totalCount} total events)
              </span>
              <div className="flex items-center gap-2">
                <button
                  disabled={currentPage <= 1 || loading}
                  onClick={() => fetchLogs(currentPage - 1)}
                  className="p-1.5 rounded-lg border border-[#26344F] bg-[#111A2E] text-slate-400 hover:text-white hover:border-slate-600 disabled:opacity-40 disabled:cursor-not-allowed transition"
                >
                  <ChevronLeft className="h-4 w-4" />
                </button>
                <button
                  disabled={currentPage >= totalPages || loading}
                  onClick={() => fetchLogs(currentPage + 1)}
                  className="p-1.5 rounded-lg border border-[#26344F] bg-[#111A2E] text-slate-400 hover:text-white hover:border-slate-600 disabled:opacity-40 disabled:cursor-not-allowed transition"
                >
                  <ChevronRight className="h-4 w-4" />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Modal / Detail Drawer for selected log */}
        {selectedLog && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#0C1321]/80 backdrop-blur-md animate-in fade-in duration-200">
            <div className="bg-[#111A2E] border border-[#26344F] rounded-2xl p-6 max-w-2xl w-full shadow-2xl space-y-4">
              <div className="flex items-center justify-between border-b border-[#26344F] pb-3">
                <div className="flex items-center gap-2">
                  <span className="p-1.5 rounded-lg bg-[#06B6D4]/10 border border-[#06B6D4]/30 text-[#06B6D4]">
                    <Terminal className="h-4 w-4" />
                  </span>
                  <h3 className="text-base font-bold text-white">Audit Event Details</h3>
                </div>
                <button
                  onClick={() => setSelectedLog(null)}
                  className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-[#17223A] transition"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              <div className="grid grid-cols-2 gap-4 text-xs font-mono">
                <div className="p-2.5 rounded-xl bg-[#0C1321] border border-[#26344F]">
                  <span className="text-slate-500 block text-[10px]">Action</span>
                  <span className="font-bold text-white">{selectedLog.action}</span>
                </div>
                <div className="p-2.5 rounded-xl bg-[#0C1321] border border-[#26344F]">
                  <span className="text-slate-500 block text-[10px]">Entity</span>
                  <span className="font-bold text-white">
                    {selectedLog.entity_type} ({selectedLog.entity_id ? `${selectedLog.entity_id.slice(0, 8)}...` : "N/A"})
                  </span>
                </div>
                <div className="p-2.5 rounded-xl bg-[#0C1321] border border-[#26344F]">
                  <span className="text-slate-500 block text-[10px]">Actor ID</span>
                  <span className="text-[#4CD7F6] truncate block">{selectedLog.actor_user_id || "System"}</span>
                </div>
                <div className="p-2.5 rounded-xl bg-[#0C1321] border border-[#26344F]">
                  <span className="text-slate-500 block text-[10px]">Request ID</span>
                  <span className="text-slate-300 truncate block">{selectedLog.request_id || "N/A"}</span>
                </div>
              </div>

              {selectedLog.before_data && (
                <div>
                  <span className="text-xs text-amber-400 font-mono font-semibold block mb-1">State Before Mutation:</span>
                  <pre className="p-3 rounded-xl bg-[#0C1321] border border-[#26344F] text-[11px] font-mono text-amber-300/90 overflow-x-auto max-h-36">
                    {JSON.stringify(selectedLog.before_data, null, 2)}
                  </pre>
                </div>
              )}

              {selectedLog.after_data && (
                <div>
                  <span className="text-xs text-emerald-400 font-mono font-semibold block mb-1">State After Mutation:</span>
                  <pre className="p-3 rounded-xl bg-[#0C1321] border border-[#26344F] text-[11px] font-mono text-emerald-300/90 overflow-x-auto max-h-36">
                    {JSON.stringify(selectedLog.after_data, null, 2)}
                  </pre>
                </div>
              )}

              {selectedLog.metadata && (
                <div>
                  <span className="text-xs text-slate-400 font-mono font-semibold block mb-1">Contextual Metadata:</span>
                  <pre className="p-3 rounded-xl bg-[#0C1321] border border-[#26344F] text-[11px] font-mono text-slate-300 overflow-x-auto max-h-28">
                    {JSON.stringify(selectedLog.metadata, null, 2)}
                  </pre>
                </div>
              )}

              <div className="flex justify-end pt-2">
                <button
                  type="button"
                  onClick={() => setSelectedLog(null)}
                  className="px-4 py-2 bg-[#17223A] hover:bg-slate-700 text-slate-200 rounded-xl text-xs font-semibold transition"
                >
                  Dismiss
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppShell>
  );
}
