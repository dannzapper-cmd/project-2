"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { motion } from "framer-motion";
import { ScanLine, Lightbulb, GitCompare, Activity } from "lucide-react";

const navItems = [
  { href: "/home", label: "Scan", icon: ScanLine },
  { href: "/insights", label: "Insights", icon: Lightbulb },
  { href: "/compare", label: "Compare", icon: GitCompare },
  { href: "/activity", label: "Activity", icon: Activity },
];

export function BottomNav() {
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (href === "/home") {
      return pathname === "/home" || pathname === "/scan" || pathname === "/result";
    }
    return pathname === href;
  };

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 glass-card pb-safe">
      <div className="flex items-center justify-around h-16 max-w-md mx-auto px-4">
        {navItems.map((item) => {
          const active = isActive(item.href);
          const Icon = item.icon;
          
          return (
            <Link
              key={item.href}
              href={item.href}
              className="flex flex-col items-center justify-center min-w-[64px] min-h-[44px] relative"
            >
              {active && (
                <motion.div
                  layoutId="nav-indicator"
                  className="absolute -top-1 left-1/2 -translate-x-1/2 w-12 h-12 rounded-full bg-violet-500/20"
                  transition={{ type: "spring", stiffness: 500, damping: 30 }}
                />
              )}
              <div
                className={`relative z-10 flex flex-col items-center gap-1 transition-colors ${
                  active ? "text-violet-400" : "text-muted-foreground"
                }`}
              >
                <Icon className={`w-5 h-5 ${active ? "fill-violet-500/30" : ""}`} />
                <span className="text-xs font-medium">{item.label}</span>
              </div>
            </Link>
          );
        })}
      </div>
    </nav>
  );
}
