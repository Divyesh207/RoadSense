"use client";

import React, { useState } from "react";
import { CheckCircle2, ClipboardCopy, Info } from "lucide-react";
import {
  DemoRequest,
  DemoRequestErrors,
  EMPTY_DEMO_REQUEST,
  demoRequestSummary,
  validateDemoRequest,
} from "@/lib/demo-request";

const inputClass =
  "w-full bg-ri-input border border-ri-line rounded-xl px-3.5 text-sm text-ri-text placeholder:text-ri-faint transition-colors hover:border-ri-line-strong focus:outline-none focus:ring-2 focus:ring-ri-primary/40 focus:border-ri-primary aria-[invalid=true]:border-ri-danger";
const labelClass = "block font-code-sm text-[11px] text-ri-muted uppercase tracking-wider";

function Field({
  id,
  label,
  error,
  children,
}: {
  id: string;
  label: string;
  error?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1.5">
      <label htmlFor={id} className={labelClass}>
        {label}
      </label>
      {children}
      {error && (
        <p id={`${id}-error`} className="text-xs text-ri-danger-soft">
          {error}
        </p>
      )}
    </div>
  );
}

/**
 * Frontend-only demo request form. The platform API has no demo-request endpoint, so nothing
 * is transmitted: the form validates the entry and offers the summary to copy.
 */
export function RequestDemoForm() {
  const [form, setForm] = useState<DemoRequest>(EMPTY_DEMO_REQUEST);
  const [errors, setErrors] = useState<DemoRequestErrors>({});
  const [prepared, setPrepared] = useState<string | null>(null);
  const [copyState, setCopyState] = useState<"idle" | "copied" | "failed">("idle");

  const set = (key: keyof DemoRequest) => (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setForm((prev) => ({ ...prev, [key]: e.target.value }));
    if (errors[key]) setErrors((prev) => ({ ...prev, [key]: undefined }));
  };

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const found = validateDemoRequest(form);
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    setPrepared(demoRequestSummary(form));
    setCopyState("idle");
  };

  const copy = async () => {
    if (!prepared) return;
    try {
      await navigator.clipboard.writeText(prepared);
      setCopyState("copied");
    } catch {
      setCopyState("failed");
    }
  };

  const aria = (key: keyof DemoRequest, id: string) => ({
    "aria-invalid": errors[key] ? true : undefined,
    "aria-describedby": errors[key] ? `${id}-error` : undefined,
  });

  if (prepared) {
    return (
      <div role="status" className="space-y-4">
        <div className="flex items-start gap-3 rounded-xl border border-ri-success/30 bg-ri-success/10 p-4">
          <CheckCircle2 className="h-5 w-5 text-ri-success shrink-0 mt-0.5" />
          <div className="text-sm">
            <p className="font-semibold text-ri-text">Your request is ready.</p>
            <p className="text-ri-muted mt-1 text-xs leading-relaxed">
              This form is not connected to an email or CRM system, so nothing has been sent. Copy the summary
              below and share it with your Road Intelligence contact.
            </p>
          </div>
        </div>
        <pre className="whitespace-pre-wrap break-words rounded-xl border border-ri-line bg-ri-sunken p-4 text-xs text-ri-text-soft font-mono">
          {prepared}
        </pre>
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={copy}
            className="inline-flex items-center gap-2 h-11 px-4 rounded-xl bg-ri-primary hover:bg-ri-primary-bright text-ri-on-primary text-sm font-bold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ri-primary-bright focus-visible:ring-offset-2 focus-visible:ring-offset-ri-surface"
          >
            <ClipboardCopy className="h-4 w-4" />
            {copyState === "copied" ? "Copied" : "Copy summary"}
          </button>
          <button
            type="button"
            onClick={() => setPrepared(null)}
            className="h-11 px-4 rounded-xl border border-ri-line bg-ri-raised text-sm font-semibold text-ri-text-soft hover:border-ri-primary/50 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-ri-primary-bright"
          >
            Edit request
          </button>
          {copyState === "failed" && (
            <span className="text-xs text-ri-warning">Copy was blocked by the browser. Select the text above instead.</span>
          )}
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={submit} noValidate className="space-y-4">
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Field id="demo-name" label="Name *" error={errors.name}>
          <input
            id="demo-name"
            value={form.name}
            onChange={set("name")}
            autoComplete="name"
            maxLength={120}
            className={`${inputClass} h-11`}
            {...aria("name", "demo-name")}
          />
        </Field>
        <Field id="demo-organization" label="Organization *" error={errors.organization}>
          <input
            id="demo-organization"
            value={form.organization}
            onChange={set("organization")}
            autoComplete="organization"
            maxLength={160}
            className={`${inputClass} h-11`}
            {...aria("organization", "demo-organization")}
          />
        </Field>
        <Field id="demo-email" label="Email *" error={errors.email}>
          <input
            id="demo-email"
            type="email"
            value={form.email}
            onChange={set("email")}
            autoComplete="email"
            maxLength={200}
            className={`${inputClass} h-11`}
            {...aria("email", "demo-email")}
          />
        </Field>
        <Field id="demo-phone" label="Phone (optional)" error={errors.phone}>
          <input
            id="demo-phone"
            type="tel"
            value={form.phone}
            onChange={set("phone")}
            autoComplete="tel"
            maxLength={24}
            className={`${inputClass} h-11`}
            {...aria("phone", "demo-phone")}
          />
        </Field>
      </div>
      <Field id="demo-message" label="Message / use case *" error={errors.message}>
        <textarea
          id="demo-message"
          rows={4}
          value={form.message}
          onChange={set("message")}
          maxLength={1000}
          placeholder="Road network size, inspection process, what you want to evaluate"
          className={`${inputClass} py-3 resize-y`}
          {...aria("message", "demo-message")}
        />
      </Field>

      <p className="flex items-start gap-2 text-xs text-ri-muted leading-relaxed">
        <Info className="h-4 w-4 text-ri-primary-bright shrink-0 mt-0.5" />
        This form stays in your browser. It prepares a request summary for you to copy; it does not send an
        email or store your details.
      </p>

      <button
        type="submit"
        className="inline-flex items-center justify-center h-12 px-6 rounded-xl bg-ri-primary hover:bg-ri-primary-bright text-ri-on-primary text-sm font-bold transition-colors motion-safe:active:scale-[0.99] focus:outline-none focus-visible:ring-2 focus-visible:ring-ri-primary-bright focus-visible:ring-offset-2 focus-visible:ring-offset-ri-surface w-full sm:w-auto"
      >
        Prepare Demo Request
      </button>
    </form>
  );
}
