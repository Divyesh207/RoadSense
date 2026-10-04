import React from "react";
import { LucideIcon, Inbox } from "lucide-react";

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description: string;
  action?: {
    label: string;
    onClick: () => void;
  };
  className?: string;
}

export function EmptyState({
  icon: Icon = Inbox,
  title,
  description,
  action,
  className = "",
}: EmptyStateProps) {
  return (
    <div
      className={`flex flex-col items-center justify-center p-8 sm:p-12 rounded-xl bg-[#111A2E] border border-[#26344F] text-center select-none ${className}`}
    >
      <div className="w-12 h-12 rounded-2xl bg-[#17223A] border border-[#26344F] flex items-center justify-center text-[#4CD7F6] mb-4 shadow-inner">
        <Icon className="h-6 w-6" />
      </div>
      <h3 className="font-headline-sm text-base font-semibold text-[#F1F5F9] mb-1.5">
        {title}
      </h3>
      <p className="font-body-sm text-xs text-[#94A3B8] max-w-md leading-relaxed">
        {description}
      </p>
      {action && (
        <button
          onClick={action.onClick}
          className="mt-5 h-10 px-4 rounded-lg bg-[#06B6D4] hover:bg-[#4CD7F6] text-[#003640] font-headline-sm text-xs font-bold transition-all shadow-sm active:scale-95"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}
