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
    cyan: "bg-[#06B6D4]/15 text-[#4CD7F6] border-[#06B6D4]/30",
    green: "bg-[#10B981]/15 text-[#10B981] border-[#10B981]/30",
    amber: "bg-[#F59E0B]/15 text-[#F59E0B] border-[#F59E0B]/30",
    red: "bg-[#EF4444]/15 text-[#EF4444] border-[#EF4444]/30",
    blue: "bg-[#3B82F6]/15 text-[#ADC6FF] border-[#3B82F6]/30",
    neutral: "bg-[#232A39] text-[#94A3B8] border-[#3D494C]",
  }[resolvedVariant];

  const description = subtext || hint;

  const content = (
    <div
      className={`p-4 rounded-xl bg-[#111A2E] border border-[#26344F] hover:border-[#06B6D4]/50 transition-all shadow-sm flex flex-col justify-between h-full group ${className}`}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="font-label-sm text-[11px] uppercase tracking-wider text-[#94A3B8] font-semibold font-mono">
          {label}
        </span>
        <div
          className={`w-7 h-7 rounded-lg border flex items-center justify-center transition-transform group-hover:scale-110 ${iconVariants}`}
        >
          <Icon className="h-4 w-4" />
        </div>
      </div>
      <div>
        <div className="flex items-baseline gap-2">
          <div className="font-code-lg text-2xl font-bold text-[#F1F5F9] tracking-tight font-mono">
            {value}
          </div>
          {trend && (
            <div
              className={`flex items-center text-[10px] font-mono font-semibold ${
                trend.direction === "up" ? "text-amber-400" : "text-emerald-400"
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
          <p className="font-body-sm text-[11px] text-[#94A3B8] mt-1 truncate">
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
