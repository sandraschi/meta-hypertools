import type React from "react";
import type { FleetBadge, FleetBadgeKind } from "../utils/fleetStatusBadges";

const BADGE_STYLES: Record<FleetBadgeKind, string> = {
  healthy: "bg-green-500/20 text-green-300 border-green-500/30",
  offline: "bg-white/10 text-white/55 border-white/20",
  "404": "bg-orange-500/20 text-orange-300 border-orange-500/30",
  "500": "bg-red-500/20 text-red-300 border-red-500/30",
  unavailable: "bg-red-500/15 text-red-200/85 border-red-500/25",
  parse: "bg-red-500/20 text-red-300 border-red-500/30",
  backend: "bg-green-500/20 text-green-300 border-green-500/30",
  frontend: "bg-green-500/20 text-green-300 border-green-500/30",
  proxy: "bg-green-500/20 text-green-300 border-green-500/30",
  teardown: "bg-orange-500/20 text-orange-300 border-orange-500/30",
  down: "bg-slate-500/20 text-slate-300 border-slate-500/30",
};

type FleetStatusBadgeProps = {
  badge: FleetBadge;
  className?: string;
};

export const FleetStatusBadge: React.FC<FleetStatusBadgeProps> = ({ badge, className = "" }) => (
  <span
    title={badge.title}
    className={`px-2 py-1 rounded border text-[9px] font-black uppercase tracking-widest ${BADGE_STYLES[badge.kind]} ${className}`}
  >
    {badge.label}
  </span>
);

type FleetStatusBadgeRowProps = {
  badges: FleetBadge[];
  className?: string;
};

export const FleetStatusBadgeRow: React.FC<FleetStatusBadgeRowProps> = ({
  badges,
  className = "",
}) => {
  if (badges.length === 0) return null;
  return (
    <div className={`flex flex-wrap gap-2 items-center ${className}`}>
      {badges.map((badge, idx) => (
        <FleetStatusBadge key={`${badge.kind}-${badge.label}-${idx}`} badge={badge} />
      ))}
    </div>
  );
};

type FleetBadgeFilterChipsProps = {
  filters: { id: string; label: string }[];
  active: string;
  onChange: (id: string) => void;
};

export const FleetBadgeFilterChips: React.FC<FleetBadgeFilterChipsProps> = ({
  filters,
  active,
  onChange,
}) => (
  <div className="flex flex-wrap gap-2">
    {filters.map((f) => (
      <button
        key={f.id}
        type="button"
        onClick={() => onChange(f.id)}
        className={`px-3 py-1.5 rounded-lg text-[9px] font-black uppercase tracking-widest border transition-all ${
          active === f.id
            ? "bg-white/10 border-white/30 text-white"
            : "border-white/5 text-white/40 hover:text-white/70 hover:bg-white/5"
        }`}
      >
        {f.label}
      </button>
    ))}
  </div>
);
