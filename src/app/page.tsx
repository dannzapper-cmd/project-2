export default function Home() {
  return (
    <div className="flex min-h-full flex-1 flex-col items-center justify-center bg-[hsl(var(--color-surface))] px-4">
      <div className="w-full max-w-sm rounded-xl border border-white/10 bg-[hsl(var(--color-card))] p-8 text-center shadow-lg">
        <h1 className="text-2xl font-semibold tracking-tight text-foreground">
          SnapInsight
        </h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Point. Ask. Understand.
        </p>
        <p className="mt-6 text-xs text-muted-foreground">
          Frontend foundation ready — Block 1A complete.
        </p>
      </div>
    </div>
  );
}
