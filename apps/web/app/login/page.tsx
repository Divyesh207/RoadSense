"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Activity, Lock, Mail, AlertCircle } from "lucide-react";

export default function LoginPage() {
  const [email, setEmail] = useState("authority@example.com");
  const [password, setPassword] = useState("AuthoritySecret123!");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const { login } = useAuth();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err: any) {
      setError(err?.message || "Invalid credentials or authorization failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 flex flex-col justify-center py-12 sm:px-6 lg:px-8 text-slate-100">
      <div className="sm:mx-auto sm:w-full sm:max-w-md text-center">
        <div className="inline-flex h-12 w-12 rounded-xl bg-blue-600 items-center justify-center font-bold text-white shadow-xl shadow-blue-500/30 mb-4">
          <Activity className="h-6 w-6 text-white" />
        </div>
        <h2 className="text-2xl font-bold tracking-tight text-white">Road Intelligence Platform</h2>
        <p className="mt-1 text-xs text-slate-400">
          Sign in with your state or municipal road authority credentials
        </p>
      </div>

      <div className="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div className="bg-slate-900 border border-slate-800 py-8 px-6 shadow-2xl rounded-xl sm:px-10">
          {error && (
            <div className="mb-6 p-3 rounded-lg bg-red-950/50 border border-red-800/80 flex items-center gap-3 text-red-300 text-xs">
              <AlertCircle className="h-4 w-4 shrink-0 text-red-400" />
              <span>{error}</span>
            </div>
          )}

          <form className="space-y-5" onSubmit={handleSubmit}>
            <div>
              <label className="block text-xs font-medium text-slate-300">Email Address</label>
              <div className="mt-1.5 relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
                <input
                  type="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full pl-10 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
                  placeholder="name@authority.gov"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-medium text-slate-300">Password</label>
              <div className="mt-1.5 relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-500" />
                <input
                  type="password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full pl-10 pr-3 py-2 bg-slate-950 border border-slate-800 rounded-lg text-xs text-white placeholder:text-slate-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
                  placeholder="••••••••••••"
                />
              </div>
            </div>

            <div>
              <button
                type="submit"
                disabled={loading}
                className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-xs font-semibold text-white bg-blue-600 hover:bg-blue-500 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 transition-all"
              >
                {loading ? "Authenticating..." : "Sign In to Operations"}
              </button>
            </div>
          </form>

          <div className="mt-6 pt-6 border-t border-slate-800 text-center">
            <p className="text-[11px] text-slate-500">
              Multi-tenant RBAC enforced. Contact your system administrator for access.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
