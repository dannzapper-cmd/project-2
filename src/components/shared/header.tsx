"use client"

import { Menu, ArrowLeft, User } from "lucide-react"
import Link from "next/link"
import { cn } from "@/lib/utils"

interface HeaderProps {
  variant?: "default" | "back"
  className?: string
}

export function Header({ variant = "default", className }: HeaderProps) {
  return (
    <header
      className={cn(
        "sticky top-0 z-50 flex items-center justify-between px-5 py-4 safe-area-top",
        className
      )}
    >
      {/* Left slot */}
      <button className="touch-target flex items-center justify-center w-11 h-11 rounded-full hover:bg-white/5 transition-colors">
        {variant === "back" ? (
          <Link href="/home">
            <ArrowLeft className="w-6 h-6 text-slate-400" />
          </Link>
        ) : (
          <Menu className="w-6 h-6 text-slate-400" />
        )}
      </button>

      {/* Center wordmark */}
      <h1 className="text-lg font-semibold text-foreground tracking-tight">
        SnapInsight
      </h1>

      {/* Right slot */}
      <button className="touch-target flex items-center justify-center w-11 h-11 rounded-full hover:bg-white/5 transition-colors">
        <User className="w-6 h-6 text-slate-400" />
      </button>
    </header>
  )
}
