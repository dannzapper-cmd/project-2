import { cn } from "@/lib/utils"

interface PreviewBannerProps {
  className?: string
}

export function PreviewBanner({ className }: PreviewBannerProps) {
  return (
    <div
      role="status"
      className={cn(
        "mx-5 rounded-lg border border-violet-500/20 bg-violet-500/10 px-3 py-2 text-center",
        className
      )}
    >
      <span className="mono-label text-violet-400">UI preview · mock data</span>
    </div>
  )
}
