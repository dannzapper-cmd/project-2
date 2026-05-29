"use client"

import { Menu, ArrowLeft, User } from "lucide-react"
import Link from "next/link"
import { cn } from "@/lib/utils"

interface HeaderProps {
  variant?: "default" | "back"
  className?: string
}

const iconButtonClass =
  "touch-target flex h-11 w-11 items-center justify-center rounded-full transition-colors"

export function Header({ variant = "default", className }: HeaderProps) {
  return (
    <header
      className={cn(
        "sticky top-0 z-50 flex items-center justify-between px-5 py-4 safe-area-top",
        className
      )}
    >
      {variant === "back" ? (
        <Link
          href="/home"
          aria-label="Back to home"
          className={cn(iconButtonClass, "hover:bg-white/5")}
        >
          <ArrowLeft className="h-6 w-6 text-slate-400" />
        </Link>
      ) : (
        <button
          type="button"
          disabled
          aria-disabled="true"
          aria-label="Menu (preview — not available)"
          className={cn(iconButtonClass, "cursor-not-allowed opacity-50")}
        >
          <Menu className="h-6 w-6 text-slate-400" />
        </button>
      )}

      <h1 className="text-lg font-semibold tracking-tight text-foreground">
        SnapInsight
      </h1>

      <button
        type="button"
        disabled
        aria-disabled="true"
        aria-label="Account (preview — not available)"
        className={cn(iconButtonClass, "cursor-not-allowed opacity-50")}
      >
        <User className="h-6 w-6 text-slate-400" />
      </button>
    </header>
  )
}
