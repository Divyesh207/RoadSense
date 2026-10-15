"use client";

/**
 * Road Intelligence glass component system. All colours, blur and radii come from the
 * `ri-*` design tokens in app/globals.css; nothing here defines its own palette.
 */

import React, { useEffect, useId } from "react";
import { LucideIcon, X } from "lucide-react";

type Tone = "primary" | "success" | "warning" | "danger" | "info" | "review" | "neutral";

const cx = (...parts: (string | false | null | undefined)[]) => parts.filter(Boolean).join(" ");

const focusRing =
  "focus:outline-none focus-visible:ring-2 focus-visible:ring-ri-primary-bright focus-visible:ring-offset-2 focus-visible:ring-offset-ri-solid";

const TONE: Record<Tone, { text: string; bg: string; border: string; dot: string; rgb: string }> = {
  primary: { text: "text-ri-primary-bright", bg: "bg-ri-primary/15", border: "border-ri-primary/35", dot: "bg-ri-primary", rgb: "var(--ri-primary)" },
  success: { text: "text-ri-success", bg: "bg-ri-success/15", border: "border-ri-success/35", dot: "bg-ri-success", rgb: "var(--ri-success)" },
  warning: { text: "text-ri-warning", bg: "bg-ri-warning/15", border: "border-ri-warning/35", dot: "bg-ri-warning", rgb: "var(--ri-warning)" },
  danger: { text: "text-ri-danger", bg: "bg-ri-danger/15", border: "border-ri-danger/35", dot: "bg-ri-danger", rgb: "var(--ri-danger)" },
  info: { text: "text-ri-info-soft", bg: "bg-ri-info/15", border: "border-ri-info/35", dot: "bg-ri-info", rgb: "var(--ri-info)" },
  review: { text: "text-ri-review-soft", bg: "bg-ri-review/15", border: "border-ri-review/35", dot: "bg-ri-review", rgb: "var(--ri-review)" },
  neutral: { text: "text-ri-text-soft", bg: "bg-ri-raised", border: "border-ri-line", dot: "bg-ri-muted", rgb: "var(--ri-glass)" },
};

const accentStyle = (tone?: Tone) => (tone ? ({ ["--ri-accent" as string]: TONE[tone].rgb } as React.CSSProperties) : undefined);

/* ----------------------------------------------------------------------------- surfaces */

interface GlassCardProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Stronger glass for the most important cards. */
  strong?: boolean;
  /** Hover feedback, for cards that are clickable. */
  interactive?: boolean;
  /** Coloured hairline along the top edge. */
  accent?: Tone;
  padded?: boolean;
}

export function GlassCard({ strong, interactive, accent, padded = true, className, style, children, ...rest }: GlassCardProps) {
  return (
    <div
      className={cx(
        "glass",
        strong && "glass-strong",
        interactive && "glass-hover glass-lift",
        accent && "glass-accent",
        padded && "p-5",
        className
      )}
      style={{ ...accentStyle(accent), ...style }}
      {...rest}
    >
      {children}
    </div>
  );
}

interface GlassPanelProps extends Omit<React.HTMLAttributes<HTMLElement>, "title"> {
  title?: React.ReactNode;
  label?: string;
  icon?: LucideIcon;
  actions?: React.ReactNode;
  /** Body without padding, for tables and maps. */
  flush?: boolean;
}

/** A titled section: header row, then content. */
export function GlassPanel({ title, label, icon: Icon, actions, flush, className, children, ...rest }: GlassPanelProps) {
  return (
    <section className={cx("glass overflow-hidden", className)} {...rest}>
      {(title || actions) && (
        <header className="flex flex-wrap items-center justify-between gap-3 px-5 py-4 border-b border-ri-line">
          <div className="flex items-center gap-2.5 min-w-0">
            {Icon && <Icon className="h-4 w-4 text-ri-primary shrink-0" />}
            <div className="min-w-0">
              {label && <p className="ri-label">{label}</p>}
              {title && <h3 className="text-sm font-semibold text-ri-text truncate">{title}</h3>}
            </div>
          </div>
          {actions && <div className="flex items-center gap-2">{actions}</div>}
        </header>
      )}
      <div className={flush ? "" : "p-5"}>{children}</div>
    </section>
  );
}

/* ------------------------------------------------------------------------------ overlays */

interface GlassModalProps {
  open: boolean;
  onClose: () => void;
  title: React.ReactNode;
  icon?: LucideIcon;
  size?: "md" | "lg" | "xl" | "full";
  children: React.ReactNode;
  footer?: React.ReactNode;
}

const MODAL_WIDTH = { md: "max-w-lg", lg: "max-w-3xl", xl: "max-w-5xl", full: "max-w-[1400px]" };

function useEscape(open: boolean, onClose: () => void) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);
}

export function GlassModal({ open, onClose, title, icon: Icon, size = "md", children, footer }: GlassModalProps) {
  const titleId = useId();
  useEscape(open, onClose);
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-[2000] flex items-center justify-center p-4 bg-black/70 motion-safe:animate-in motion-safe:fade-in motion-safe:duration-200"
      onMouseDown={(e) => e.target === e.currentTarget && onClose()}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className={cx("glass-solid w-full max-h-[92vh] flex flex-col motion-safe:animate-in motion-safe:zoom-in-95 motion-safe:duration-200", MODAL_WIDTH[size])}
      >
        <div className="flex items-center justify-between gap-3 px-5 py-4 border-b border-ri-line">
          <div className="flex items-center gap-2.5 min-w-0">
            {Icon && <Icon className="h-5 w-5 text-ri-primary shrink-0" />}
            <h2 id={titleId} className="text-base font-semibold text-ri-text truncate">
              {title}
            </h2>
          </div>
          <button onClick={onClose} aria-label="Close" className={cx("p-1.5 rounded-lg text-ri-muted hover:text-ri-text hover:bg-ri-raised transition-colors", focusRing)}>
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="p-5 overflow-y-auto">{children}</div>
        {footer && <div className="px-5 py-4 border-t border-ri-line flex items-center justify-end gap-3">{footer}</div>}
      </div>
    </div>
  );
}

interface GlassDrawerProps {
  open: boolean;
  onClose: () => void;
  title: React.ReactNode;
  children: React.ReactNode;
  side?: "right" | "left";
}

export function GlassDrawer({ open, onClose, title, children, side = "right" }: GlassDrawerProps) {
  const titleId = useId();
  useEscape(open, onClose);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[2000] bg-black/60" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <aside
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className={cx(
          "glass-solid absolute top-0 bottom-0 w-full max-w-md rounded-none flex flex-col motion-safe:animate-in motion-safe:duration-200",
          side === "right" ? "right-0 motion-safe:slide-in-from-right" : "left-0 motion-safe:slide-in-from-left"
        )}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-ri-line">
          <h2 id={titleId} className="text-base font-semibold text-ri-text">
            {title}
          </h2>
          <button onClick={onClose} aria-label="Close" className={cx("p-1.5 rounded-lg text-ri-muted hover:text-ri-text hover:bg-ri-raised", focusRing)}>
            <X className="h-4 w-4" />
          </button>
        </div>
        <div className="p-5 overflow-y-auto flex-1">{children}</div>
      </aside>
    </div>
  );
}

/* ------------------------------------------------------------------------------ controls */

interface GlassButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  icon?: LucideIcon;
  loading?: boolean;
}

const BUTTON_VARIANT = {
  primary: "bg-ri-primary text-ri-on-primary hover:bg-ri-primary-bright font-bold",
  secondary: "bg-ri-raised border border-ri-line text-ri-text hover:border-ri-primary/50 font-semibold",
  ghost: "text-ri-muted hover:text-ri-text hover:bg-ri-raised font-semibold",
  danger: "bg-ri-danger/15 border border-ri-danger/40 text-ri-danger-soft hover:bg-ri-danger/25 font-semibold",
};
const BUTTON_SIZE = { sm: "h-8 px-3 text-xs rounded-lg", md: "h-10 px-4 text-xs rounded-xl", lg: "h-12 px-6 text-sm rounded-xl" };

export const GlassButton = React.forwardRef<HTMLButtonElement, GlassButtonProps>(function GlassButton(
  { variant = "secondary", size = "md", icon: Icon, loading, disabled, className, children, ...rest },
  ref
) {
  return (
    <button
      ref={ref}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cx(
        "inline-flex items-center justify-center gap-2 transition-all duration-200 motion-safe:active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed",
        BUTTON_VARIANT[variant],
        BUTTON_SIZE[size],
        focusRing,
        className
      )}
      {...rest}
    >
      {loading ? (
        <span className="h-3.5 w-3.5 rounded-full border-2 border-current border-t-transparent motion-safe:animate-spin" aria-hidden />
      ) : (
        Icon && <Icon className="h-4 w-4" />
      )}
      {children}
    </button>
  );
});

const fieldClass =
  "w-full h-10 bg-ri-input border border-ri-line rounded-xl px-3 text-xs text-ri-text placeholder:text-ri-faint transition-colors hover:border-ri-line-strong focus:outline-none focus:border-ri-primary focus:ring-2 focus:ring-ri-primary/30 disabled:opacity-50 aria-[invalid=true]:border-ri-danger";

export const GlassInput = React.forwardRef<HTMLInputElement, React.InputHTMLAttributes<HTMLInputElement>>(function GlassInput(
  { className, ...rest },
  ref
) {
  return <input ref={ref} className={cx(fieldClass, className)} {...rest} />;
});

export const GlassSelect = React.forwardRef<HTMLSelectElement, React.SelectHTMLAttributes<HTMLSelectElement>>(function GlassSelect(
  { className, children, ...rest },
  ref
) {
  return (
    <select ref={ref} className={cx(fieldClass, "[&>option]:bg-[rgb(var(--ri-solid))]", className)} {...rest}>
      {children}
    </select>
  );
});

/* -------------------------------------------------------------------------------- status */

interface GlassBadgeProps {
  tone?: Tone;
  icon?: LucideIcon;
  children: React.ReactNode;
  className?: string;
}

/** A small label for a category or a source (for example TRAINED AI, RULE-BASED). */
export function GlassBadge({ tone = "neutral", icon: Icon, children, className }: GlassBadgeProps) {
  const t = TONE[tone];
  return (
    <span className={cx("inline-flex items-center gap-1 rounded-full border px-2 py-0.5 font-code-sm text-[10px] tracking-wider", t.bg, t.border, t.text, className)}>
      {Icon && <Icon className="h-3 w-3" />}
      {children}
    </span>
  );
}

/** A state with a dot (for example VERIFIED, AWAITING REVIEW). */
export function GlassStatusPill({ tone = "neutral", children, pulse }: { tone?: Tone; children: React.ReactNode; pulse?: boolean }) {
  const t = TONE[tone];
  return (
    <span className={cx("inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-semibold", t.bg, t.border, t.text)}>
      <span className={cx("h-1.5 w-1.5 rounded-full", t.dot, pulse && "motion-safe:animate-pulse")} aria-hidden />
      {children}
    </span>
  );
}

/* ------------------------------------------------------------------------------- metrics */

interface GlassMetricCardProps {
  label: string;
  value: React.ReactNode;
  icon: LucideIcon;
  tone?: Tone;
  /** Plain explanation of what the number counts. */
  caption?: string;
  /** A status line taken from the data (never an invented trend). */
  status?: React.ReactNode;
  className?: string;
}

export function GlassMetricCard({ label, value, icon: Icon, tone = "primary", caption, status, className }: GlassMetricCardProps) {
  const t = TONE[tone];
  return (
    <div
      className={cx("glass glass-accent glass-hover p-4 flex flex-col justify-between gap-3 h-full", className)}
      style={{
        ...accentStyle(tone),
        backgroundImage: `radial-gradient(240px 120px at 100% 0%, rgb(${t.rgb} / 0.13), transparent 70%)`,
      }}
    >
      <div className="flex items-center justify-between gap-3">
        <span className="ri-label">{label}</span>
        <span className={cx("h-8 w-8 rounded-lg border flex items-center justify-center shrink-0", t.bg, t.border, t.text)}>
          <Icon className="h-4 w-4" />
        </span>
      </div>
      <div>
        <div className="font-mono text-[28px] leading-8 font-bold tracking-tight text-ri-text tabular-nums">{value}</div>
        {status && <div className={cx("mt-1.5 text-[11px] font-semibold", t.text)}>{status}</div>}
        {caption && <p className="mt-1 text-[11px] text-ri-muted leading-snug">{caption}</p>}
      </div>
    </div>
  );
}

export function GlassProgress({ value, tone = "primary", label }: { value: number; tone?: Tone; label?: string }) {
  const pct = Math.max(0, Math.min(100, value));
  return (
    <div
      role="progressbar"
      aria-valuenow={Math.round(pct)}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={label}
      className="h-2 w-full rounded-full bg-ri-input border border-ri-line overflow-hidden"
    >
      <div className={cx("h-full rounded-full transition-[width] duration-300", TONE[tone].dot)} style={{ width: `${pct}%` }} />
    </div>
  );
}

/* ---------------------------------------------------------------------------------- data */

/** Scroll container and base styling for a data table. Use ordinary <thead>/<tbody> inside. */
export function GlassTable({ className, children, ...rest }: React.TableHTMLAttributes<HTMLTableElement>) {
  return (
    <div className="glass overflow-hidden">
      <div className="overflow-x-auto">
        <table
          className={cx(
            "w-full text-left text-xs text-ri-text-soft",
            "[&_thead]:bg-ri-bg [&_th]:px-4 [&_th]:py-3 [&_th]:font-semibold [&_th]:text-ri-muted [&_th]:font-code-sm [&_th]:uppercase [&_th]:tracking-wider",
            "[&_td]:px-4 [&_td]:py-3 [&_tbody_tr]:border-t [&_tbody_tr]:border-ri-line [&_tbody_tr:hover]:bg-ri-raised/60 [&_tbody_tr]:transition-colors",
            className
          )}
          {...rest}
        >
          {children}
        </table>
      </div>
    </div>
  );
}

interface GlassTabsProps<T extends string> {
  tabs: { id: T; label: string; icon?: LucideIcon; count?: number }[];
  value: T;
  onChange: (id: T) => void;
  label: string;
}

export function GlassTabs<T extends string>({ tabs, value, onChange, label }: GlassTabsProps<T>) {
  return (
    <div role="tablist" aria-label={label} className="inline-flex items-center gap-1 p-1 rounded-xl bg-ri-input border border-ri-line">
      {tabs.map(({ id, label: text, icon: Icon, count }) => {
        const active = id === value;
        return (
          <button
            key={id}
            role="tab"
            aria-selected={active}
            onClick={() => onChange(id)}
            className={cx(
              "inline-flex items-center gap-1.5 h-8 px-3 rounded-lg text-xs font-semibold transition-colors",
              active ? "bg-ri-primary text-ri-on-primary" : "text-ri-muted hover:text-ri-text hover:bg-ri-raised",
              focusRing
            )}
          >
            {Icon && <Icon className="h-3.5 w-3.5" />}
            {text}
            {count !== undefined && <span className="font-mono text-[10px] opacity-80">{count}</span>}
          </button>
        );
      })}
    </div>
  );
}

/** Text shown on hover and on keyboard focus. The trigger must be focusable. */
export function GlassTooltip({ text, children }: { text: string; children: React.ReactNode }) {
  const id = useId();
  return (
    <span className="relative inline-flex group/tip" aria-describedby={id}>
      {children}
      <span
        id={id}
        role="tooltip"
        className="glass-solid pointer-events-none absolute bottom-full left-1/2 -translate-x-1/2 mb-2 px-2.5 py-1.5 rounded-lg text-[11px] text-ri-text-soft whitespace-nowrap opacity-0 group-hover/tip:opacity-100 group-focus-within/tip:opacity-100 transition-opacity duration-150 z-50"
      >
        {text}
      </span>
    </span>
  );
}

export interface GlassTimelineItem {
  key: string;
  title: React.ReactNode;
  meta?: React.ReactNode;
  body?: React.ReactNode;
  tone?: Tone;
  icon?: LucideIcon;
}

/** A vertical chain of events, top to bottom. */
export function GlassTimeline({ items }: { items: GlassTimelineItem[] }) {
  return (
    <ol className="relative">
      {items.map((item, i) => {
        const t = TONE[item.tone ?? "neutral"];
        const Icon = item.icon;
        return (
          <li key={item.key} className="relative flex gap-3 pb-5 last:pb-0">
            {i < items.length - 1 && <span className="absolute left-[15px] top-8 bottom-0 w-px bg-ri-line" aria-hidden />}
            <span className={cx("relative z-10 h-8 w-8 rounded-full border flex items-center justify-center shrink-0", t.bg, t.border, t.text)}>
              {Icon ? <Icon className="h-4 w-4" /> : <span className={cx("h-2 w-2 rounded-full", t.dot)} />}
            </span>
            <div className="min-w-0 pt-1">
              <div className="text-xs font-semibold text-ri-text">{item.title}</div>
              {item.meta && <div className="font-code-sm text-[10px] text-ri-muted mt-0.5">{item.meta}</div>}
              {item.body && <div className="text-xs text-ri-text-soft mt-1.5 leading-relaxed">{item.body}</div>}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

/* -------------------------------------------------------------------------------- states */

export function GlassEmptyState({ icon: Icon, title, description, action }: { icon: LucideIcon; title: string; description?: string; action?: React.ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-12 px-6">
      <span className="h-12 w-12 rounded-xl bg-ri-raised border border-ri-line flex items-center justify-center text-ri-muted mb-4">
        <Icon className="h-5 w-5" />
      </span>
      <p className="text-sm font-semibold text-ri-text">{title}</p>
      {description && <p className="text-xs text-ri-muted mt-1.5 max-w-sm leading-relaxed">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function GlassSkeleton({ className }: { className?: string }) {
  return <div className={cx("ri-skeleton", className ?? "h-4 w-full")} aria-hidden />;
}

/** Page heading used by every console page: small label, title, one-line description, actions. */
export function PageHeader({ label, title, description, actions }: { label?: string; title: string; description?: string; actions?: React.ReactNode }) {
  return (
    <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4">
      <div className="min-w-0">
        {label && <p className="ri-label text-ri-primary-bright">{label}</p>}
        <h1 className="text-2xl lg:text-[28px] font-bold tracking-tight text-ri-text mt-1">{title}</h1>
        {description && <p className="text-sm text-ri-muted mt-1.5 max-w-3xl leading-relaxed">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2 shrink-0">{actions}</div>}
    </div>
  );
}
