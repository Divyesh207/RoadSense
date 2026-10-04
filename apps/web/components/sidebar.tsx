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

const navItems = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "Roads & Segments", href: "/roads", icon: Route },
  { name: "Field Inspections", href: "/inspections", icon: ClipboardList },
  { name: "Damage Intelligence", href: "/damages", icon: AlertTriangle },
  { name: "Maintenance Operations", href: "/maintenance", icon: Wrench },
  { name: "Priorities", href: "/priorities", icon: ListOrdered },
  { name: "Repairs & Verification", href: "/repairs", icon: BadgeCheck },
  { name: "Recurrence", href: "/recurrence", icon: Repeat },
  { name: "Spatial Map", href: "/map", icon: Map },
  { name: "Reports & Exports", href: "/reports", icon: FileText },
  { name: "Audit & Security", href: "/audit", icon: ShieldCheck },
];

export function Sidebar() {
  const pathname = usePathname();
  const { logout, user } = useAuth();

  return (
    <aside className="w-64 border-r border-[#26344F] bg-[#0B1220] flex flex-col h-screen sticky top-0 shrink-0 select-none z-30">
      {/* Brand Header with Official Logo */}
      <div className="h-16 px-5 flex items-center border-b border-[#26344F] bg-[#111A2E]/70 backdrop-blur">
        <Link href="/dashboard" className="flex items-center gap-3 group">
          <BrandLogo variant="horizontal" size="sm" showSubtitle={true} />
        </Link>
      </div>

      {/* Nav links */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href || pathname?.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-xs font-semibold transition-all ${
                isActive
                  ? "bg-[#06B6D4] text-[#003640] shadow-sm shadow-[#06B6D4]/25 font-bold"
                  : "text-[#BCC9CD] hover:text-[#F1F5F9] hover:bg-[#17223A]"
              }`}
            >
              <Icon
                className={`h-4 w-4 shrink-0 transition-colors ${
                  isActive ? "text-[#003640]" : "text-[#869397] group-hover:text-[#4CD7F6]"
                }`}
              />
              <span className="truncate">{item.name}</span>
            </Link>
          );
        })}
      </nav>

      {/* User profile & logout */}
      <div className="p-3 border-t border-[#26344F] bg-[#111A2E]/90">
        <div className="flex items-center justify-between p-2 rounded-xl bg-[#17223A]/80 border border-[#26344F]/60">
          <div className="flex items-center gap-2.5 min-w-0 pr-2">
            <div className="w-8 h-8 rounded-lg bg-[#06B6D4]/15 border border-[#06B6D4]/30 flex items-center justify-center text-[#4CD7F6] shrink-0">
              <UserIcon className="h-4 w-4" />
            </div>
            <div className="min-w-0">
              <p className="font-headline-sm text-xs font-semibold text-[#F1F5F9] truncate leading-tight">
                {user?.full_name || "Field Officer"}
              </p>
              <p className="font-code-sm text-[10px] text-[#94A3B8] truncate leading-tight mt-0.5">
                {user?.role || "ROAD_AUTHORITY"}
              </p>
            </div>
          </div>
          <button
            onClick={logout}
            title="Log Out"
            className="p-1.5 rounded-lg text-[#94A3B8] hover:text-[#EF4444] hover:bg-[#232A39] transition-colors shrink-0"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </aside>
  );
}
