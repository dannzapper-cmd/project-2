"use client"

import { Header } from "@/components/shared/header"
import { BottomNav } from "@/components/shared/bottom-nav"
import { PreviewBanner } from "@/components/shared/preview-banner"
import { ImageInputPanel } from "@/components/snapinsight/image-input-panel"

export function ScanScreen() {
  return (
    <div className="flex min-h-screen flex-col bg-background pb-24">
      <Header variant="default" />
      <PreviewBanner className="mb-2" />

      <main className="flex flex-1 flex-col px-5 py-4">
        <ImageInputPanel />
      </main>

      <BottomNav activeTab="scan" />
    </div>
  )
}
