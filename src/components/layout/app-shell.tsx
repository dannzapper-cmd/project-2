import { cn } from "@/lib/utils"

interface AppShellProps {
  children: React.ReactNode
  className?: string
}

/** Centers mobile-first UI on wider viewports without a desktop layout. */
export function AppShell({ children, className }: AppShellProps) {
  return (
    <div className={cn("mx-auto flex min-h-full w-full max-w-lg flex-col", className)}>
      {children}
    </div>
  )
}
