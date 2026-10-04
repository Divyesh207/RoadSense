import React from "react";

const LEGEND = [
  { color: "#EF4444", label: "Damage record (severity colour)" },
  { color: "#38BDF8", label: "Field inspection capture point", ring: true },
  { color: "#10B981", label: "Road segment (health status colour)", line: true },
];

/**
 * Schematic of the Spatial Map screen. It is a drawing of the layout, not a screenshot and
 * not live data; the positions are arbitrary.
 */
export function PlatformPreview() {
  const gridId = `ri-grid-${React.useId().replace(/:/g, "")}`;
  return (
    <figure className="rounded-2xl border border-ri-line bg-ri-surface overflow-hidden shadow-2xl shadow-black/40 transition-[transform,box-shadow,border-color] duration-300 motion-safe:hover:scale-[1.012] hover:border-ri-primary/40 hover:shadow-[0_30px_70px_-30px_rgb(var(--ri-primary)/0.55)]">
      <div className="flex items-center justify-between gap-3 px-4 py-2.5 border-b border-ri-line bg-ri-bg">
        <span className="font-code-sm text-ri-muted uppercase tracking-wider">Spatial Map</span>
        <span className="font-code-sm text-[10px] text-ri-warning border border-ri-warning/30 bg-ri-warning/10 rounded-full px-2 py-0.5">
          Illustration, not live data
        </span>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-[200px_1fr]">
        <div className="hidden md:block border-r border-ri-line p-4 space-y-3 bg-ri-bg/60">
          <p className="font-code-sm text-ri-faint uppercase tracking-wider">Layers</p>
          {["Damage Points", "Road Segments", "Field Inspections"].map((l) => (
            <div key={l} className="flex items-center justify-between rounded-lg border border-ri-line bg-ri-surface px-2.5 py-2">
              <span className="text-xs text-ri-text-soft">{l}</span>
              <span className="h-3.5 w-3.5 rounded-[4px] bg-ri-primary" aria-hidden />
            </div>
          ))}
          <p className="font-code-sm text-ri-faint uppercase tracking-wider pt-2">Filters</p>
          {["Severity", "Status", "Road / Segment"].map((l) => (
            <div key={l} className="h-8 rounded-lg border border-ri-line bg-ri-input px-2.5 flex items-center text-xs text-ri-muted">
              {l}
            </div>
          ))}
        </div>
        <svg
          viewBox="0 0 640 360"
          role="img"
          aria-label="Schematic map with road segments, damage markers and inspection capture points"
          className="w-full h-auto block bg-ri-bg"
        >
          <defs>
            <pattern id={gridId} width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M40 0H0V40" fill="none" stroke="#17223A" strokeWidth="1" />
            </pattern>
          </defs>
          <rect width="640" height="360" fill={`url(#${gridId})`} />
          {/* minor streets */}
          <g stroke="#1E2A44" strokeWidth="6" strokeLinecap="round" fill="none">
            <path d="M20 300 L240 250 L420 290 L620 240" />
            <path d="M120 20 L160 180 L140 340" />
            <path d="M480 20 L450 150 L520 340" />
          </g>
          {/* road segments coloured by health status */}
          <g strokeWidth="7" strokeLinecap="round" fill="none">
            <path d="M30 120 L200 100" stroke="#10B981" />
            <path d="M200 100 L360 150" stroke="#F59E0B" />
            <path d="M360 150 L610 110" stroke="#EF4444" />
            <path d="M300 340 L330 230 L360 150" stroke="#10B981" />
          </g>
          {/* damage records */}
          <g stroke="#0A1120" strokeWidth="2">
            <circle cx="420" cy="140" r="9" fill="#EF4444" className="ri-pulse" stroke="none" />
            <circle cx="420" cy="140" r="9" fill="#EF4444" />
            <circle cx="505" cy="127" r="9" fill="#FB923C" />
            <circle cx="270" cy="124" r="8" fill="#F59E0B" />
            <circle cx="322" cy="258" r="7" fill="#10B981" />
          </g>
          {/* inspection capture points */}
          <g fill="#0F172A" stroke="#38BDF8" strokeWidth="2.5">
            <circle cx="110" cy="111" r="6" />
            <circle cx="560" cy="118" r="6" />
            <circle cx="312" cy="300" r="6" />
          </g>
        </svg>
      </div>
      <figcaption className="flex flex-wrap gap-x-5 gap-y-2 px-4 py-3 border-t border-ri-line text-xs text-ri-muted">
        {LEGEND.map((l) => (
          <span key={l.label} className="inline-flex items-center gap-2">
            {l.line ? (
              <span className="h-1 w-5 rounded-full" style={{ background: l.color }} aria-hidden />
            ) : (
              <span
                className="h-3 w-3 rounded-full"
                style={l.ring ? { border: `2px solid ${l.color}` } : { background: l.color }}
                aria-hidden
              />
            )}
            {l.label}
          </span>
        ))}
      </figcaption>
    </figure>
  );
}
