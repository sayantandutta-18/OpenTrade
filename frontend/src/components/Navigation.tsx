"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, BarChart3, BookOpen, Layers, ShieldAlert } from "lucide-react";

export function DisclaimerBanner() {
  return (
    <div className="bg-amber-950/40 border-b border-amber-500/20 px-4 py-2 text-xs text-amber-200/90 text-center flex items-center justify-center gap-2">
      <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0" />
      <span>
        <strong>Simulated Research Tool:</strong> Results are generated from synthetic order flow under simplifying assumptions. Not financial or trading advice.
      </span>
    </div>
  );
}

export function Navbar() {
  const pathname = usePathname();

  const links = [
    { href: "/simulator", label: "Simulator", icon: Activity },
    { href: "/impact", label: "Impact Analysis", icon: Layers },
    { href: "/experiments", label: "Experiments", icon: BarChart3 },
    { href: "/about", label: "Methodology", icon: BookOpen },
  ];

  return (
    <header className="sticky top-0 z-50 backdrop-blur-md bg-neutral-950/80 border-b border-neutral-800">
      <DisclaimerBanner />
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-3 group">
          <div className="w-9 h-9 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 font-mono font-bold text-lg group-hover:border-emerald-400 transition-colors">
            IL
          </div>
          <div>
            <div className="font-bold text-neutral-100 tracking-tight flex items-center gap-2">
              ImpactLab
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                NSE-STYLE
              </span>
            </div>
            <p className="text-xs text-neutral-400 font-mono">Microstructure & Impact Lab</p>
          </div>
        </Link>

        <nav className="flex items-center gap-1 sm:gap-2">
          {links.map((link) => {
            const Icon = link.icon;
            const active = pathname === link.href;
            return (
              <Link
                key={link.href}
                href={link.href}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                  active
                    ? "bg-neutral-800 text-emerald-400 border border-neutral-700"
                    : "text-neutral-400 hover:text-neutral-200 hover:bg-neutral-900"
                }`}
              >
                <Icon className="w-4 h-4" />
                <span className="hidden sm:inline">{link.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
