"use client";

import Link from "next/link";
import { Menu, User, ArrowLeft } from "lucide-react";

interface HeaderProps {
  showBack?: boolean;
  backHref?: string;
}

export function Header({ showBack = false, backHref = "/home" }: HeaderProps) {
  return (
    <header className="sticky top-0 z-40 glass-card pt-safe">
      <div className="flex items-center justify-between h-14 px-4 max-w-md mx-auto">
        {showBack ? (
          <Link
            href={backHref}
            className="flex items-center justify-center w-10 h-10 rounded-full hover:bg-white/5 transition-colors"
          >
            <ArrowLeft className="w-5 h-5 text-foreground" />
          </Link>
        ) : (
          <button
            type="button"
            className="flex items-center justify-center w-10 h-10 rounded-full hover:bg-white/5 transition-colors"
          >
            <Menu className="w-5 h-5 text-foreground" />
          </button>
        )}

        <h1 className="text-lg font-semibold text-foreground">SnapInsight</h1>

        <button
          type="button"
          className="flex items-center justify-center w-10 h-10 rounded-full hover:bg-white/5 transition-colors"
        >
          <User className="w-5 h-5 text-foreground" />
        </button>
      </div>
    </header>
  );
}
