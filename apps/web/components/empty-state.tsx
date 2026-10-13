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
      className={`flex flex-col items-center justify-center p-8 sm:p-12 rounded-xl bg-ri-surface border border-ri-line text-center select-none ${className}`}
    >
      <div className="w-12 h-12 rounded-xl bg-ri-raised border border-ri-line flex items-center justify-center text-ri-primary-bright mb-4 shadow-inner">
        <Icon className="h-6 w-6" />
      </div>
      <h3 className="font-headline-sm text-base font-semibold text-ri-text mb-1.5">
        {title}
      </h3>
      <p className="font-body-sm text-xs text-ri-muted max-w-md leading-relaxed">
        {description}
      </p>
      {action && (
        <button
          onClick={action.onClick}
          className="mt-5 h-10 px-4 rounded-lg bg-ri-primary hover:bg-ri-primary-bright text-ri-on-primary font-headline-sm text-xs font-bold transition-all shadow-sm active:scale-95"
        >
          {action.label}
        </button>
      )}
    </div>
  );
}
