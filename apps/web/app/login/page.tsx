"use client";

import React, { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { BrandLogo } from "@/components/brand-logo";
import { isValidEmail } from "@/lib/demo-request";
import {
  Lock,
  Mail,
  AlertCircle,
  Eye,
  EyeOff,
  ArrowRight,
  ArrowLeft,
  Loader2,
} from "lucide-react";

const focusRing =
  "focus:outline-none focus-visible:ring-2 focus-visible:ring-ri-primary-bright focus-visible:ring-offset-2 focus-visible:ring-offset-ri-bg";
const inputClass =
  "w-full h-12 bg-ri-input border border-ri-line text-ri-text text-sm pl-10 rounded-xl transition-colors hover:border-ri-line-strong focus:outline-none focus:ring-2 focus:ring-ri-primary/40 focus:border-ri-primary aria-[invalid=true]:border-ri-danger";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<{ email?: string; password?: string }>({});
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const { login } = useAuth();
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const found: { email?: string; password?: string } = {};
    if (!email.trim()) found.email = "Enter your email address.";
    else if (!isValidEmail(email)) found.email = "Enter a valid email address.";
    if (!password) found.password = "Enter your password.";
    setFieldErrors(found);
    if (found.email || found.password) return;

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
    <div className="ri-ambient min-h-screen flex flex-col justify-between text-ri-text-soft">
      <div className="px-4 sm:px-6 pt-4">
        <Link
          href="/"
          className={`inline-flex items-center gap-1.5 text-xs text-ri-muted hover:text-ri-text transition-colors rounded-lg px-2 py-2 ${focusRing}`}
        >
          <ArrowLeft className="h-4 w-4" />
          Back to home
        </Link>
      </div>

      {/* Main Authentication Flow */}
      <main className="flex-1 flex items-center justify-center p-4 sm:p-6 my-auto">
        <div className="w-full max-w-md space-y-6">
          {/* Header Branding */}
          <div className="flex items-start space-x-4">
            <BrandLogo variant="symbol" size="lg" />
            <div className="flex flex-col min-w-0">
              <h1 className="font-headline-sm text-xl font-bold text-ri-text tracking-tight mt-0.5">
                Road Intelligence Platform
              </h1>
              <p className="font-label-md text-xs text-ri-primary font-medium">
                Operations Console
              </p>
            </div>
          </div>

          {/* Operational Brief */}
          <div className="bg-ri-sunken p-3.5 rounded-xl border-l-2 border-ri-primary">
            <p className="font-body-sm text-xs text-ri-muted leading-relaxed">
              Sign in with your state or municipal road authority credentials.
            </p>
          </div>

          {/* Form Card */}
          <div className="glass glass-accent p-5 sm:p-6 space-y-5 transition-colors focus-within:border-ri-primary/40">
            {error && (
              <div
                role="alert"
                className="bg-ri-danger-deep/20 border border-ri-danger-deep/50 p-3.5 rounded-xl flex items-start space-x-3 text-ri-danger-soft"
              >
                <AlertCircle className="h-5 w-5 text-ri-danger shrink-0 mt-0.5" />
                <div className="flex flex-col text-xs">
                  <span className="font-label-md font-semibold text-ri-danger-soft">
                    Authentication Failed
                  </span>
                  <span className="font-body-sm text-ri-danger-soft mt-0.5">{error}</span>
                </div>
              </div>
            )}

            <form onSubmit={handleSubmit} noValidate className="space-y-4">
              {/* Email / ID */}
              <div className="space-y-1.5">
                <label htmlFor="login-email" className="block font-code-sm text-[11px] text-ri-muted uppercase tracking-wider">
                  Email Address
                </label>
                <div className="relative flex items-center">
                  <Mail className="absolute left-3.5 h-4 w-4 text-ri-muted pointer-events-none" />
                  <input
                    id="login-email"
                    type="email"
                    autoComplete="username"
                    value={email}
                    onChange={(e) => {
                      setEmail(e.target.value);
                      if (fieldErrors.email) setFieldErrors((p) => ({ ...p, email: undefined }));
                    }}
                    placeholder="name@authority.gov"
                    aria-invalid={fieldErrors.email ? true : undefined}
                    aria-describedby={fieldErrors.email ? "login-email-error" : undefined}
                    className={`${inputClass} pr-4`}
                  />
                </div>
                {fieldErrors.email && (
                  <p id="login-email-error" className="text-xs text-ri-danger-soft">
                    {fieldErrors.email}
                  </p>
                )}
              </div>

              {/* Password */}
              <div className="space-y-1.5">
                <label htmlFor="login-password" className="block font-code-sm text-[11px] text-ri-muted uppercase tracking-wider">
                  Password
                </label>
                <div className="relative flex items-center">
                  <Lock className="absolute left-3.5 h-4 w-4 text-ri-muted pointer-events-none" />
                  <input
                    id="login-password"
                    type={showPassword ? "text" : "password"}
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => {
                      setPassword(e.target.value);
                      if (fieldErrors.password) setFieldErrors((p) => ({ ...p, password: undefined }));
                    }}
                    placeholder="••••••••••••"
                    aria-invalid={fieldErrors.password ? true : undefined}
                    aria-describedby={fieldErrors.password ? "login-password-error" : undefined}
                    className={`${inputClass} pr-12 tracking-wider`}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    aria-label={showPassword ? "Hide password" : "Show password"}
                    aria-pressed={showPassword}
                    className={`absolute right-1.5 h-9 w-9 inline-flex items-center justify-center rounded-lg text-ri-muted hover:text-ri-text hover:bg-ri-raised transition-colors ${focusRing}`}
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
                {fieldErrors.password && (
                  <p id="login-password-error" className="text-xs text-ri-danger-soft">
                    {fieldErrors.password}
                  </p>
                )}
              </div>

              {/* Primary Action Button */}
              <button
                type="submit"
                disabled={loading}
                aria-busy={loading}
                className={`w-full h-14 bg-ri-primary hover:bg-ri-primary-bright motion-safe:active:scale-[0.99] text-ri-on-primary font-headline-sm text-sm rounded-xl font-bold flex items-center justify-center space-x-2 transition-all shadow-md shadow-ri-primary/20 hover:shadow-lg hover:shadow-ri-primary/30 disabled:opacity-60 disabled:cursor-not-allowed mt-2 ${focusRing}`}
              >
                <span>{loading ? "Authenticating..." : "Sign In to Operations"}</span>
                {loading ? (
                  <Loader2 className="h-5 w-5 motion-safe:animate-spin" />
                ) : (
                  <ArrowRight className="h-5 w-5 font-bold" />
                )}
              </button>
            </form>

            <div className="border-t border-ri-line pt-4 space-y-2 text-xs text-ri-muted">
              <p>
                Need an account? Accounts are created by your organization&apos;s administrator; this console has
                no self-registration.
              </p>
              <p>
                Evaluating the platform?{" "}
                <Link
                  href="/#request-demo"
                  className={`font-semibold text-ri-primary-bright hover:text-white underline-offset-2 hover:underline transition-colors rounded ${focusRing}`}
                >
                  Request a demo
                </Link>
              </p>
            </div>
          </div>
        </div>
      </main>

      <footer className="py-4 px-6 border-t border-ri-line/50 text-center bg-ri-sunken">
        <p className="text-[11px] text-ri-faint">
          Multi-tenant RBAC enforced. Contact your system administrator for access.
        </p>
      </footer>
    </div>
  );
}
