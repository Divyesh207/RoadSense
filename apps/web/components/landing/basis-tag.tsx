import React from "react";

/** How a result is produced. The three are kept visibly distinct everywhere on the landing page. */
export type Basis = "TRAINED AI" | "RULE-BASED" | "HUMAN REVIEW";

const STYLE: Record<Basis, string> = {
  "TRAINED AI": "text-ri-info border-ri-info/30",
  "RULE-BASED": "text-ri-warning border-ri-warning/30",
  "HUMAN REVIEW": "text-ri-text border-ri-line-strong",
};

export function BasisTag({ basis, className = "" }: { basis: Basis; className?: string }) {
  return (
    <span className={`inline-flex font-code-sm text-[10px] tracking-wider rounded-md border px-2 py-0.5 ${STYLE[basis]} ${className}`}>
      {basis}
    </span>
  );
}
