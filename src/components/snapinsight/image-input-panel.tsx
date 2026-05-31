"use client"

import { useCallback, useEffect, useId, useRef, useState } from "react"
import { Images, Zap } from "lucide-react"
import { cn } from "@/lib/utils"
import { useCameraSnapshot } from "@/hooks/use-camera-snapshot"
import { useLocalImagePreview } from "@/hooks/use-local-image-preview"
import {
  analyzeImage,
  type AnalysisResponse,
} from "@/lib/snapinsight-api"
import { preprocessImageForUpload } from "@/lib/image-preprocess"
import { EvidenceGraphPanel } from "@/components/snapinsight/evidence-graph-panel"
import { MockAnalysisResultCard } from "@/components/snapinsight/mock-analysis-result-card"
import { ProductChatPanel } from "@/components/snapinsight/product-chat-panel"
import { ProductComparePanel } from "@/components/snapinsight/product-compare-panel"
import { ProductSessionPanel } from "@/components/snapinsight/product-session-panel"
import { StatusMetricsPanel } from "@/components/snapinsight/status-metrics-panel"
import { GeminiLivePanel } from "@/components/snapinsight/gemini-live-panel"
import {
  addSnapshotToSession,
  createProductSession,
  MAX_SESSION_SNAPSHOTS,
  type ProductSession,
} from "@/lib/product-session"

function getStatusLabel(
  hasImage: boolean,
  cameraStatus: ReturnType<typeof useCameraSnapshot>["status"]
): string {
  if (hasImage) return "Image ready"
  if (cameraStatus === "active") return "Camera active"
  if (cameraStatus === "denied") return "Camera permission denied"
  if (cameraStatus === "insecure") return "Camera not available"
  if (cameraStatus === "unsupported") return "Camera not supported"
  if (cameraStatus === "error") return "Camera unavailable"
  return "No image selected"
}

interface ImageInputPanelProps {
  className?: string
}

const ANALYSIS_PRIVACY_COPY =
  "Images are processed for analysis and are not stored by SnapInsight. EXIF metadata is stripped in your browser where supported; compare uses analysis results only."

const ANALYSIS_COST_COPY =
  "Caching helps reduce repeated analysis cost and latency. Repeated identical images may return faster. No paid service beyond the configured AI model is added."

function getAnalysisModeLabel(mode: AnalysisResponse["mode"]): string {
  if (mode === "gemini") return "AI Analysis"
  if (mode === "mock_fallback") return "Mock Fallback"
  return "Mock"
}

function formatConfidence(result: AnalysisResponse): string {
  const { label, score } = result.product.confidence
  return `${label} · ${Math.round(score * 100)}%`
}

function hasNutritionData(result: AnalysisResponse): boolean {
  const summary = result.product_enrichment?.nutrition_summary
  if (!summary) return false
  return Object.values(summary).some((value) => Boolean(value))
}

function sourceConfidenceNote(result: AnalysisResponse): string | null {
  const confidence = result.product_enrichment?.enrichment_source_confidence
  if (confidence === "high") return "Source confidence: barcode-based source match"
  if (confidence === "medium") return "Source confidence: name-based source match"
  return null
}

function PreviewAnalysisOverlay({ result }: { result: AnalysisResponse }) {
  const chips = [
    getAnalysisModeLabel(result.mode),
    `Confidence ${formatConfidence(result)}`,
    result.grounding_status,
  ]

  if (hasNutritionData(result)) chips.push("Nutrition data")
  if ((result.product_enrichment?.labels.length ?? 0) > 0) chips.push("Labels")
  if ((result.product_enrichment?.additives.length ?? 0) > 0) chips.push("Additives")
  if (result.warnings.length > 0) chips.push(`${result.warnings.length} warning(s)`)

  const note = sourceConfidenceNote(result)

  return (
    <div className="pointer-events-none absolute inset-x-3 bottom-3 z-10">
      <div className="max-w-full rounded-2xl border border-white/10 bg-slate-950/65 p-3 shadow-2xl backdrop-blur-md">
        <div className="flex flex-wrap gap-2">
          {chips.map((chip) => (
            <span
              key={chip}
              className="rounded-full border border-white/10 bg-white/10 px-2.5 py-1 text-[11px] font-medium text-slate-100"
            >
              {chip}
            </span>
          ))}
        </div>
        {note && (
          <p className="mt-2 text-[11px] leading-relaxed text-slate-300">
            {note}
          </p>
        )}
      </div>
    </div>
  )
}

function isAbortError(err: unknown): boolean {
  return err instanceof Error && err.name === "AbortError"
}

function getAnalysisErrorMessage(err: unknown): string {
  if (err instanceof TypeError) {
    return "Analysis service unavailable. Start the backend or check the API URL."
  }

  if (err instanceof Error) {
    return err.message
  }

  return "Analysis service unavailable. Check the backend and try again."
}

export function ImageInputPanel({ className }: ImageInputPanelProps) {
  const fileInputId = useId()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)
  const [analysisResult, setAnalysisResult] =
    useState<AnalysisResponse | null>(null)
  const [compareProductA, setCompareProductA] =
    useState<AnalysisResponse | null>(null)
  const [compareProductB, setCompareProductB] =
    useState<AnalysisResponse | null>(null)
  const [compareReplacementPrompt, setCompareReplacementPrompt] =
    useState<AnalysisResponse | null>(null)
  const [analysisError, setAnalysisError] = useState<string | null>(null)
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [sessionModeEnabled, setSessionModeEnabled] = useState(false)
  const [productSession, setProductSession] = useState<ProductSession | null>(null)
  const [sessionLimitReached, setSessionLimitReached] = useState(false)
  const {
    previewUrl,
    imageFile,
    error: uploadError,
    hasImage,
    setFromFile,
    setFromBlob,
    clear,
  } = useLocalImagePreview()
  const {
    videoRef,
    status: cameraStatus,
    message: cameraMessage,
    isActive: isCameraActive,
    startCamera,
    stopCamera,
    captureSnapshot,
  } = useCameraSnapshot()

  const statusLabel = getStatusLabel(hasImage, cameraStatus)
  const showMockOverlay = !hasImage && !isCameraActive

  const abortActiveAnalysis = useCallback(() => {
    abortControllerRef.current?.abort()
    abortControllerRef.current = null
    setIsAnalyzing(false)
  }, [])

  const resetAnalysisState = useCallback(() => {
    abortActiveAnalysis()
    setAnalysisResult(null)
    setAnalysisError(null)
    setSessionLimitReached(false)
  }, [abortActiveAnalysis])

  const handleSessionModeChange = useCallback((enabled: boolean) => {
    setSessionModeEnabled(enabled)
    if (!enabled) {
      setProductSession(null)
      setSessionLimitReached(false)
    }
  }, [])

  const handleStartSession = useCallback(() => {
    setProductSession(createProductSession())
    setSessionLimitReached(false)
  }, [])

  const handleEndSession = useCallback(() => {
    setProductSession(null)
    setSessionLimitReached(false)
  }, [])

  const registerAnalysisForCompare = useCallback(
    (result: AnalysisResponse) => {
      // Compare slots are in-memory only: first new result fills A, second fills B,
      // and later analyses prompt instead of replacing saved products.
      if (!compareProductA) {
        setCompareProductA(result)
        setCompareReplacementPrompt(null)
        return
      }
      if (!compareProductB) {
        setCompareProductB(result)
        setCompareReplacementPrompt(null)
        return
      }
      setCompareReplacementPrompt(result)
    },
    [compareProductA, compareProductB]
  )

  const handleSaveCompareA = useCallback((result: AnalysisResponse) => {
    setCompareProductA(result)
    setCompareReplacementPrompt(null)
  }, [])

  const handleSaveCompareB = useCallback((result: AnalysisResponse) => {
    setCompareProductB(result)
    setCompareReplacementPrompt(null)
  }, [])

  const handleReplaceCompareA = useCallback(() => {
    if (!compareReplacementPrompt) return
    setCompareProductA(compareReplacementPrompt)
    setCompareReplacementPrompt(null)
  }, [compareReplacementPrompt])

  const handleReplaceCompareB = useCallback(() => {
    if (!compareReplacementPrompt) return
    setCompareProductB(compareReplacementPrompt)
    setCompareReplacementPrompt(null)
  }, [compareReplacementPrompt])

  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort()
    }
  }, [])

  const handleFileChange = useCallback(
    (event: React.ChangeEvent<HTMLInputElement>) => {
      const file = event.target.files?.[0]
      if (!file) return
      resetAnalysisState()
      stopCamera()
      setFromFile(file)
      event.target.value = ""
    },
    [resetAnalysisState, setFromFile, stopCamera]
  )

  const handleUploadClick = useCallback(() => {
    fileInputRef.current?.click()
  }, [])

  const handleCapture = useCallback(async () => {
    const blob = await captureSnapshot()
    if (blob) {
      resetAnalysisState()
      setFromBlob(blob)
      return
    }
    // captureSnapshot sets cameraMessage when video is not ready yet
  }, [captureSnapshot, resetAnalysisState, setFromBlob])

  const handleClear = useCallback(() => {
    resetAnalysisState()
    stopCamera()
    clear()
  }, [resetAnalysisState, stopCamera, clear])

  const handleRetake = useCallback(() => {
    resetAnalysisState()
    clear()
    void startCamera()
  }, [resetAnalysisState, clear, startCamera])

  const handleCenterAction = useCallback(() => {
    if (hasImage) return
    if (isCameraActive) {
      void handleCapture()
      return
    }
    void startCamera()
  }, [hasImage, isCameraActive, handleCapture, startCamera])

  const handleAnalyze = useCallback(async () => {
    if (!imageFile) {
      setAnalysisError("Select or capture an image before analysis.")
      return
    }

    abortActiveAnalysis()
    const controller = new AbortController()
    abortControllerRef.current = controller
    setIsAnalyzing(true)
    setAnalysisError(null)
    setAnalysisResult(null)

    try {
      // Privacy: strip EXIF / resize in-browser before the bytes leave the
      // device. Falls back to the original file if preprocessing is unavailable.
      const fileToSend = await preprocessImageForUpload(imageFile)
      if (controller.signal.aborted) return
      const result = await analyzeImage(fileToSend, controller.signal)
      if (controller.signal.aborted) return
      setAnalysisResult(result)
      registerAnalysisForCompare(result)

      if (sessionModeEnabled && productSession) {
        if (productSession.snapshots.length >= MAX_SESSION_SNAPSHOTS) {
          setSessionLimitReached(true)
        } else {
          const addResult = addSnapshotToSession(productSession, result, {
            localKey: crypto.randomUUID(),
          })
          setProductSession(addResult.session)
          if (!addResult.added) {
            setSessionLimitReached(true)
          } else {
            setSessionLimitReached(false)
          }
        }
      }
    } catch (err) {
      if (isAbortError(err)) {
        return
      }
      if (controller.signal.aborted) {
        return
      }
      setAnalysisError(getAnalysisErrorMessage(err))
    } finally {
      if (abortControllerRef.current === controller) {
        abortControllerRef.current = null
        setIsAnalyzing(false)
      }
    }
  }, [
    abortActiveAnalysis,
    imageFile,
    productSession,
    registerAnalysisForCompare,
    sessionModeEnabled,
  ])

  return (
    <div className={cn("flex flex-col", className)}>
      <input
        ref={fileInputRef}
        id={fileInputId}
        type="file"
        accept="image/*"
        className="sr-only"
        onChange={handleFileChange}
        aria-label="Upload product image"
      />

      {/* Viewfinder / preview */}
      <div className="relative min-h-[400px] max-h-[500px] flex-1 overflow-hidden rounded-3xl bg-gradient-to-b from-slate-800/40 to-slate-900/60">
        {showMockOverlay && (
          <div className="pointer-events-none absolute inset-4">
            <div className="absolute top-0 left-0 h-8 w-8 rounded-tl-xl border-l-2 border-t-2 border-violet-500" />
            <div className="absolute top-0 right-0 h-8 w-8 rounded-tr-xl border-r-2 border-t-2 border-violet-500" />
            <div className="absolute bottom-0 left-0 h-8 w-8 rounded-bl-xl border-l-2 border-b-2 border-violet-500" />
            <div className="absolute bottom-0 right-0 h-8 w-8 rounded-br-xl border-r-2 border-b-2 border-violet-500" />
            <div className="absolute inset-12 rounded-2xl border border-dashed border-white/10" />
          </div>
        )}

        <video
          ref={videoRef}
          className={cn(
            "absolute inset-0 h-full w-full object-cover",
            !isCameraActive && "pointer-events-none opacity-0"
          )}
          muted
          playsInline
          autoPlay
          aria-hidden={!isCameraActive}
          aria-label="Camera preview"
        />

        {hasImage && previewUrl && (
          // eslint-disable-next-line @next/next/no-img-element -- local blob preview only
          <img
            src={previewUrl}
            alt="Selected product preview"
            className="absolute inset-0 h-full w-full object-contain bg-slate-950/80"
          />
        )}

        {hasImage && analysisResult && (
          <PreviewAnalysisOverlay result={analysisResult} />
        )}

        {!hasImage && !isCameraActive && (
          <div className="absolute inset-0 flex flex-col items-center justify-center px-6 text-center">
            <p className="text-sm text-muted-foreground">
              Upload a photo or start the camera to capture a product image.
            </p>
          </div>
        )}

        <div className="absolute top-8 left-1/2 z-10 flex -translate-x-1/2 items-center gap-2 rounded-full border border-white/10 bg-slate-800/90 px-4 py-2">
          {isCameraActive && (
            <div className="h-2 w-2 animate-pulse rounded-full bg-violet-500" />
          )}
          <span className="mono-label text-slate-300">{statusLabel}</span>
        </div>
      </div>

      {/* Errors */}
      {(uploadError || cameraMessage) && (
        <p
          className="mt-3 text-center text-sm text-red-400"
          role="alert"
        >
          {uploadError ?? cameraMessage}
        </p>
      )}

      {/* Image actions */}
      {hasImage && (
        <div className="mt-3 flex flex-wrap items-center justify-center gap-2">
          <button
            type="button"
            onClick={handleClear}
            className="touch-target rounded-full border border-white/10 bg-slate-800/80 px-4 py-2 text-sm font-medium text-foreground hover:bg-slate-700/80"
          >
            Remove image
          </button>
          <button
            type="button"
            onClick={handleRetake}
            className="touch-target rounded-full border border-white/10 bg-slate-800/80 px-4 py-2 text-sm font-medium text-foreground hover:bg-slate-700/80"
          >
            Retake
          </button>
          <button
            type="button"
            onClick={handleAnalyze}
            disabled={isAnalyzing || !imageFile}
            className={cn(
              "touch-target rounded-full border border-violet-500/30 bg-violet-500/15 px-4 py-2 text-sm font-medium text-violet-300 hover:bg-violet-500/25",
              (isAnalyzing || !imageFile) &&
                "cursor-not-allowed opacity-60 hover:bg-violet-500/15"
            )}
          >
            {isAnalyzing ? "Analyzing..." : "Analyze image"}
          </button>
        </div>
      )}

      {/* Capture controls */}
      <div className="flex items-center justify-center gap-6 py-6 sm:gap-8">
        <button
          type="button"
          onClick={handleUploadClick}
          className="touch-target flex h-12 w-12 items-center justify-center rounded-full border border-white/10 bg-slate-800/80 hover:bg-slate-700/80"
          aria-label="Upload image from gallery"
        >
          <Images className="h-5 w-5 text-slate-400" />
        </button>

        <button
          type="button"
          onClick={handleCenterAction}
          disabled={hasImage}
          className={cn(
            "touch-target flex h-16 w-16 items-center justify-center rounded-full shadow-lg shadow-violet-500/30 transition-colors",
            hasImage
              ? "cursor-not-allowed bg-slate-700 opacity-50"
              : "bg-violet-400 hover:bg-violet-300"
          )}
          aria-label={
            isCameraActive ? "Capture snapshot" : "Start camera"
          }
        >
          <div className="h-14 w-14 rounded-full border-2 border-slate-900/30" />
        </button>

        <button
          type="button"
          disabled
          aria-disabled="true"
          title="Flash not available"
          className="touch-target flex h-12 w-12 cursor-not-allowed items-center justify-center rounded-full border border-white/10 bg-slate-800/80 opacity-50"
        >
          <Zap className="h-5 w-5 text-slate-400" />
        </button>
      </div>

      {isCameraActive && (
        <div className="mb-2 flex justify-center">
          <button
            type="button"
            onClick={stopCamera}
            className="touch-target rounded-full border border-white/10 px-4 py-2 text-sm font-medium text-muted-foreground hover:bg-white/5"
          >
            Stop camera
          </button>
        </div>
      )}

      <p className="text-center text-xs text-muted-foreground">
        {ANALYSIS_PRIVACY_COPY}
      </p>
      <p className="mt-1 text-center text-xs text-muted-foreground">
        {ANALYSIS_COST_COPY}
      </p>

      <ProductSessionPanel
        sessionModeEnabled={sessionModeEnabled}
        onSessionModeChange={handleSessionModeChange}
        session={productSession}
        onStartSession={handleStartSession}
        onEndSession={handleEndSession}
        sessionLimitReached={sessionLimitReached}
      />

      <GeminiLivePanel />

      <StatusMetricsPanel latestResult={analysisResult} className="mt-4" />

      {analysisError && (
        <div
          className="mt-3 rounded-2xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-center text-sm text-red-300"
          role="alert"
        >
          <span className="mb-2 inline-flex rounded-full border border-red-500/30 bg-red-500/15 px-3 py-1 text-xs font-medium text-red-200">
            Unavailable
          </span>
          <p>{analysisError || "Analysis unavailable."}</p>
        </div>
      )}

      {analysisResult && (
        <>
          <MockAnalysisResultCard result={analysisResult} />
          <EvidenceGraphPanel
            analysis={analysisResult}
            graphNote={
              sessionModeEnabled &&
              productSession &&
              productSession.snapshots.length > 1
                ? "Graph reflects the latest session snapshot."
                : null
            }
          />
          <ProductComparePanel
            currentResult={analysisResult}
            productA={compareProductA}
            productB={compareProductB}
            replacementPrompt={compareReplacementPrompt}
            onSaveA={handleSaveCompareA}
            onSaveB={handleSaveCompareB}
            onClearA={() => setCompareProductA(null)}
            onClearB={() => setCompareProductB(null)}
            onReplaceA={handleReplaceCompareA}
            onReplaceB={handleReplaceCompareB}
            onKeepBoth={() => setCompareReplacementPrompt(null)}
          />
          <ProductChatPanel analysis={analysisResult} />
        </>
      )}
    </div>
  )
}
