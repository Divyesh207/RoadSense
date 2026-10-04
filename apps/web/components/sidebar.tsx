"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Route,
  ClipboardList,
  AlertTriangle,
  Map,
  Wrench,
  FileText,
  ShieldCheck,
  LogOut,
  Repeat,
  BadgeCheck,
  ListOrdered,
  User as UserIcon,
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";
import { BrandLogo } from "@/components/brand-logo";

const navGroups = [
  {
    label: "Overview",
    items: [{ name: "Dashboard", href: "/dashboard", icon: LayoutDashboard }],
  },
  {
    label: "Network",
    items: [
      { name: "Roads & Segments", href: "/roads", icon: Route },
      { name: "Field Inspections", href: "/inspections", icon: ClipboardList },
      { name: "Damage Intelligence", href: "/damages", icon: AlertTriangle },
    ],
  },
  {
    label: "Operations",
    items: [
      { name: "Maintenance Operations", href: "/maintenance", icon: Wrench },
      { name: "Priorities", href: "/priorities", icon: ListOrdered },
      { name: "Repairs & Verification", href: "/repairs", icon: BadgeCheck },
      { name: "Recurrence", href: "/recurrence", icon: Repeat },
    ],
  },
  {
    label: "Intelligence",
    items: [
      { name: "Spatial Map", href: "/map", icon: Map },
      { name: "Reports & Exports", href: "/reports", icon: FileText },
      { name: "Audit & Security", href: "/audit", icon: ShieldCheck },
    ],
  },
];

const focusRing =
  "focus:outline-none focus-visible:ring-2 focus-visible:ring-ri-primary-bright focus-visible:ring-offset-2 focus-visible:ring-offset-ri-solid";

export function Sidebar() {
  const pathname = usePathname();
  const { logout, user } = useAuth();

  return (
    <aside className="w-16 lg:w-64 shrink-0 h-screen sticky top-0 z-30 select-none p-2 lg:p-3">
      <div className="glass h-full flex flex-col overflow-hidden">
        {/* Brand */}
        <div className="h-16 px-3 lg:px-4 flex items-center border-b border-ri-line shrink-0">
          <Link href="/dashboard" aria-label="Road Intelligence dashboard" className={`rounded-xl ${focusRing}`}>
            <span className="hidden lg:block">
              <BrandLogo variant="horizontal" size="sm" showSubtitle={true} />
            </span>
            <span className="lg:hidden">
              <BrandLogo variant="symbol" size="sm" />
            </span>
          </Link>
        </div>

        {/* Navigation */}
        <nav aria-label="Main" className="flex-1 px-2 lg:px-2.5 py-3 overflow-y-auto space-y-4">
          {navGroups.map((group) => (
            <div key={group.label}>
              <p className="ri-label hidden lg:block px-2.5 mb-1.5 text-[9.5px] text-ri-faint">{group.label}</p>
              <ul className="space-y-0.5">
                {group.items.map((item) => {
                  const Icon = item.icon;
                  const isActive = pathname === item.href || pathname?.startsWith(`${item.href}/`);
                  return (
                    <li key={item.name}>
                      <Link
                        href={item.href}
                        title={item.name}
                        aria-current={isActive ? "page" : undefined}
                        className={`group relative flex items-center justify-center lg:justify-start gap-3 h-10 px-2.5 rounded-xl text-xs font-semibold transition-colors duration-200 ${focusRing} ${
                          isActive
                            ? "bg-ri-primary/15 text-ri-text border border-ri-primary/35 shadow-[0_0_24px_-10px_rgb(var(--ri-primary))]"
                            : "text-ri-muted border border-transparent hover:text-ri-text hover:bg-ri-raised"
                        }`}
                      >
                        {isActive && (
                          <span className="absolute left-0 top-2 bottom-2 w-[3px] rounded-full bg-ri-primary-bright" aria-hidden />
                        )}
                        <Icon
                          className={`h-4 w-4 shrink-0 transition-colors ${
                            isActive
                              ? "text-ri-primary-bright drop-shadow-[0_0_6px_rgb(var(--ri-primary)/0.7)]"
                              : "text-ri-faint group-hover:text-ri-primary-bright"
                          }`}
                        />
                        <span className="hidden lg:block truncate">{item.name}</span>
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </nav>

        {/* User */}
        <div className="p-2 lg:p-2.5 border-t border-ri-line shrink-0">
          <div className="flex items-center justify-center lg:justify-between gap-2 p-1.5 lg:p-2 rounded-xl bg-ri-bg border border-ri-line">
            <div className="hidden lg:flex items-center gap-2.5 min-w-0">
              <div className="w-8 h-8 rounded-lg bg-ri-primary/15 border border-ri-primary/30 flex items-center justify-center text-ri-primary-bright shrink-0">
                <UserIcon className="h-4 w-4" />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-semibold text-ri-text truncate leading-tight">{user?.full_name || "Field Officer"}</p>
                <p className="font-code-sm text-[10px] text-ri-muted truncate leading-tight mt-0.5">
                  {user?.role || "ROAD_AUTHORITY"}
                </p>
              </div>
            </div>
            <button
              onClick={logout}
              title="Log out"
              aria-label="Log out"
              className={`p-2 rounded-lg text-ri-muted hover:text-ri-danger hover:bg-ri-raised transition-colors shrink-0 ${focusRing}`}
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </aside>
  );
}
