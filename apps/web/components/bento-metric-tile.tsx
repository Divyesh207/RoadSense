import React from "react";
import Link from "next/link";
import { LucideIcon, ArrowUpRight, ArrowDownRight } from "lucide-react";

export interface BentoMetricTileProps {
  label: string;
  value: React.ReactNode;
  icon: LucideIcon;
  hint?: string;
  subtext?: string;
  href?: string;
  status?: "nominal" | "warning" | "critical" | string;
  trend?: { direction: "up" | "down" | string; label: string };
  colorVariant?: "cyan" | "green" | "amber" | "red" | "blue" | "neutral";
  className?: string;
}

export function BentoMetricTile({
  label,
  value,
  icon: Icon,
  hint,
  subtext,
  href,
  status,
  trend,
  colorVariant,
  className = "",
}: BentoMetricTileProps) {
  // If status is provided, map to an appropriate color variant if colorVariant not explicitly set
  const resolvedVariant =
    colorVariant ||
    (status === "nominal"
      ? "green"
      : status === "warning"
      ? "amber"
      : status === "critical"
      ? "red"
      : "cyan");

  const iconVariants = {
    cyan: "bg-ri-primary/15 text-ri-primary-bright border-ri-primary/30",
    green: "bg-ri-success/15 text-ri-success border-ri-success/30",
    amber: "bg-ri-warning/15 text-ri-warning border-ri-warning/30",
    red: "bg-ri-danger/15 text-ri-danger border-ri-danger/30",
    blue: "bg-ri-info/15 text-ri-info-soft border-ri-info/30",
    neutral: "bg-ri-raised text-ri-muted border-ri-line-strong",
  }[resolvedVariant];

  // Token behind the tile's accent line and ambient corner gradient.
  const accent = {
    cyan: "var(--ri-primary)",
    green: "var(--ri-success)",
    amber: "var(--ri-warning)",
    red: "var(--ri-danger)",
    blue: "var(--ri-info)",
    neutral: "var(--ri-glass)",
  }[resolvedVariant];

  const description = subtext || hint;

  const content = (
    <div
      className={`glass glass-accent glass-hover p-4 flex flex-col justify-between h-full group ${className}`}
      style={
        {
          "--ri-accent": accent,
          backgroundImage: `radial-gradient(240px 120px at 100% 0%, rgb(${accent} / 0.13), transparent 70%)`,
        } as React.CSSProperties
      }
    >
      <div className="flex items-center justify-between mb-2">
        <span className="ri-label">
          {label}
        </span>
        <div
          className={`w-8 h-8 rounded-lg border flex items-center justify-center shrink-0 ${iconVariants}`}
        >
          <Icon className="h-4 w-4" />
        </div>
      </div>
      <div>
        <div className="flex items-baseline gap-2">
          <div className="font-mono text-[28px] leading-8 font-bold text-ri-text tracking-tight tabular-nums">
            {value}
          </div>
          {trend && (
            <div
              className={`flex items-center text-[10px] font-mono font-semibold ${
                trend.direction === "up" ? "text-ri-warning" : "text-ri-success"
              }`}
            >
              {trend.direction === "up" ? (
                <ArrowUpRight className="h-3 w-3" />
              ) : (
                <ArrowDownRight className="h-3 w-3" />
              )}
              <span>{trend.label}</span>
            </div>
          )}
        </div>
        {description && (
          <p className="text-[11px] text-ri-muted mt-1.5 leading-snug">
            {description}
          </p>
        )}
      </div>
    </div>
  );

  if (href) {
    return (
      <Link href={href} className="block h-full">
        {content}
      </Link>
    );
  }

  return content;
}
