"use client";

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
} from "lucide-react";
import { useAuth } from "@/lib/auth-context";

const navItems = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "Roads & Segments", href: "/roads", icon: Route },
  { name: "Field Inspections", href: "/inspections", icon: ClipboardList },
  { name: "Damage Intelligence", href: "/damages", icon: AlertTriangle },
  { name: "Maintenance Operations", href: "/maintenance", icon: Wrench },
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
    <aside className="w-64 border-r border-slate-800 bg-slate-950 flex flex-col h-screen sticky top-0">
      {/* Brand */}
      <div className="h-16 px-6 flex items-center gap-3 border-b border-slate-800 bg-slate-900/50">
        <div className="h-9 w-9 rounded-lg bg-blue-600 flex items-center justify-center font-bold text-white shadow-md shadow-blue-500/30">
          RI
        </div>
        <div>
          <h1 className="text-sm font-semibold text-white leading-none">Road Intelligence</h1>
          <p className="text-[11px] text-slate-400 mt-1">Operations Platform</p>
        </div>
      </div>

      {/* Nav links */}
      <nav className="flex-1 px-4 py-6 space-y-1.5 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href || pathname?.startsWith(`${item.href}/`);
          return (
            <Link
              key={item.name}
              href={item.href}
              className={`flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-xs font-medium transition-all ${
                isActive
                  ? "bg-blue-600 text-white shadow-sm shadow-blue-500/20"
                  : "text-slate-400 hover:text-white hover:bg-slate-900"
              }`}
            >
              <Icon className="h-4 w-4 shrink-0" />
              <span>{item.name}</span>
            </Link>
          );
        })}
      </nav>

      {/* User profile & logout */}
      <div className="p-4 border-t border-slate-800 bg-slate-900/30">
        <div className="flex items-center justify-between">
          <div className="min-w-0 pr-2">
            <p className="text-xs font-medium text-white truncate">{user?.full_name || "Field Officer"}</p>
            <p className="text-[11px] text-slate-400 truncate">{user?.role || "ROAD_AUTHORITY"}</p>
          </div>
          <button
            onClick={logout}
            title="Log Out"
            className="p-1.5 rounded-md text-slate-400 hover:text-red-400 hover:bg-slate-900 transition-colors"
          >
            <LogOut className="h-4 w-4" />
          </button>
        </div>
      </div>
    </aside>
  );
}
