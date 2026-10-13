import React from "react";
import Image from "next/image";

interface BrandLogoProps {
  variant?: "full" | "symbol" | "horizontal";
  size?: "sm" | "md" | "lg" | "xl";
  className?: string;
  showSubtitle?: boolean;
}

export function BrandLogo({
  variant = "horizontal",
  size = "md",
  className = "",
  showSubtitle = true,
}: BrandLogoProps) {
  // Sizing definitions
  const symbolDimensions = {
    sm: { width: 28, height: 28, class: "w-7 h-7" },
    md: { width: 36, height: 36, class: "w-9 h-9" },
    lg: { width: 48, height: 48, class: "w-12 h-12" },
    xl: { width: 64, height: 64, class: "w-16 h-16" },
  }[size];

  const fullDimensions = {
    sm: { width: 140, height: 40, class: "w-36 h-auto" },
    md: { width: 180, height: 52, class: "w-44 h-auto" },
    lg: { width: 240, height: 70, class: "w-60 h-auto" },
    xl: { width: 320, height: 92, class: "w-80 h-auto" },
  }[size];

  if (variant === "symbol") {
    return (
      <div className={`relative inline-flex items-center justify-center shrink-0 ${className}`}>
        <Image
          src="/logo-icon.png"
          alt="Road Intelligence RI"
          width={symbolDimensions.width}
          height={symbolDimensions.height}
          priority
          className={`${symbolDimensions.class} rounded-xl object-contain drop-shadow-md`}
        />
      </div>
    );
  }

  if (variant === "full") {
    return (
      <div className={`relative inline-flex flex-col items-center justify-center ${className}`}>
        <Image
          src="/logo.png"
          alt="Road Intelligence Operations Platform"
          width={fullDimensions.width}
          height={fullDimensions.height}
          priority
          className={`${fullDimensions.class} rounded-xl object-contain drop-shadow-lg`}
        />
      </div>
    );
  }

  // Horizontal variant (Emblem Symbol + Clean Typography)
  return (
    <div className={`inline-flex items-center gap-3 select-none ${className}`}>
      <Image
        src="/logo-icon.png"
        alt="Road Intelligence"
        width={symbolDimensions.width}
        height={symbolDimensions.height}
        priority
        className={`${symbolDimensions.class} rounded-xl object-contain shadow-sm border border-ri-line/60 shrink-0`}
      />
      <div className="flex flex-col min-w-0">
        <div className="flex items-center gap-1.5">
          <span className="font-sans font-bold tracking-tight text-white leading-none">
            Road <span className="text-ri-primary">Intelligence</span>
          </span>
        </div>
        {showSubtitle && (
          <span className="font-code-sm text-[10px] tracking-widest text-ri-muted uppercase mt-1 leading-none">
            Operations Platform
          </span>
        )}
      </div>
    </div>
  );
}
