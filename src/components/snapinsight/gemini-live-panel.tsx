"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { Camera, Loader2, Mic, Send, ShieldCheck, Square, Waves } from "lucide-react"

import {
  getGeminiLiveConfig,
  requestGeminiLiveToken,
  sendGeminiLiveTelemetry,
  type GeminiLiveConfigResponse,
} from "@/lib/snapinsight-api"
import {
  buildLiveWebSocketUrl,
  canStartLiveSession,
  cleanupGeminiLiveHandles,
  createLiveAudioChunkMessage,
  createLiveImageFrameMessage,
  createLiveSetupMessage,
  createLiveTextMessage,
  extractGeminiLiveServerEventParts,
  float32ToPcm16Base64,
  getLiveOperationalMessage,
  pcm16Base64ToFloat32,
  requiresLiveAccessCode,
} from "@/lib/gemini-live"
import { cn } from "@/lib/utils"

type LiveUiState = "loading" | "idle" | "starting" | "connected" | "error"

interface LiveMessage {
  id: string
  role: "user" | "assistant" | "system"
  text: string
}

function liveStateLabel(state: LiveUiState): string {
  if (state === "loading") return "Checking"
  if (state === "starting") return "Starting"
  if (state === "connected") return "Live"
  if (state === "error") return "Needs attention"
  return "Ready"
}

function getAudioSampleRate(mimeType: string): number {
  const match = mimeType.match(/rate=(\d+)/i)
  if (!match) return 24000
  const parsed = Number.parseInt(match[1], 10)
  return Number.isFinite(parsed) && parsed > 0 ? parsed : 24000
}

async function acquireLiveMedia(config: GeminiLiveConfigResponse): Promise<MediaStream> {
  if (!config.audio_enabled && !config.vision_enabled) {
    return new MediaStream()
  }
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new Error("Camera or microphone is not supported in this browser.")
  }
  return navigator.mediaDevices.getUserMedia({
    audio: config.audio_enabled,
    video: config.vision_enabled
      ? { facingMode: { ideal: "environment" } }
      : false,
  })
}

export function GeminiLivePanel({ className }: { className?: string }) {
  const [config, setConfig] = useState<GeminiLiveConfigResponse | null>(null)
  const [uiState, setUiState] = useState<LiveUiState>("loading")
  const [accessCode, setAccessCode] = useState("")
  const [textInput, setTextInput] = useState("")
  const [messages, setMessages] = useState<LiveMessage[]>([])
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [audioFallback, setAudioFallback] = useState<string | null>(null)
  const [elapsedSeconds, setElapsedSeconds] = useState(0)
  const [framesSentCount, setFramesSentCount] = useState(0)
  const [textMessagesCount, setTextMessagesCount] = useState(0)

  const videoRef = useRef<HTMLVideoElement>(null)
  const websocketRef = useRef<WebSocket | null>(null)
  const mediaStreamRef = useRef<MediaStream | null>(null)
  const frameTimerRef = useRef<number | null>(null)
  const maxSessionTimerRef = useRef<number | null>(null)
  const elapsedTimerRef = useRef<number | null>(null)
  const audioInputContextRef = useRef<AudioContext | null>(null)
  const audioOutputContextRef = useRef<AudioContext | null>(null)
  const audioProcessorRef = useRef<ScriptProcessorNode | null>(null)
  const audioSourceRef = useRef<MediaStreamAudioSourceNode | null>(null)
  const nextAudioTimeRef = useRef(0)
  const startedAtRef = useRef<number | null>(null)
  const connectedRef = useRef(false)

  const appendMessage = useCallback((message: Omit<LiveMessage, "id">) => {
    setMessages((current) => [
      ...current.slice(-8),
      { ...message, id: crypto.randomUUID() },
    ])
  }, [])

  const refreshConfig = useCallback(async () => {
    setUiState("loading")
    setErrorMessage(null)
    try {
      const nextConfig = await getGeminiLiveConfig()
      setConfig(nextConfig)
      setUiState("idle")
    } catch {
      setUiState("error")
      setErrorMessage("Could not load Live mode configuration.")
    }
  }, [])

  useEffect(() => {
    let active = true
    getGeminiLiveConfig()
      .then((nextConfig) => {
        if (!active) return
        setConfig(nextConfig)
        setUiState("idle")
      })
      .catch(() => {
        if (!active) return
        setUiState("error")
        setErrorMessage("Could not load Live mode configuration.")
      })
    return () => {
      active = false
    }
  }, [])

  const sendTelemetry = useCallback(
    (event: Parameters<typeof sendGeminiLiveTelemetry>[0]["event"], overrides = {}) => {
      const duration =
        startedAtRef.current === null
          ? null
          : Math.round((Date.now() - startedAtRef.current) / 1000)
      void sendGeminiLiveTelemetry({
        event,
        duration_seconds: duration,
        frames_sent_count: framesSentCount,
        audio_enabled: config?.audio_enabled ?? null,
        vision_enabled: config?.vision_enabled ?? null,
        text_messages_count: textMessagesCount,
        model: config?.model ?? null,
        status: event,
        ...overrides,
      })
    },
    [config, framesSentCount, textMessagesCount]
  )

  const clearTimers = useCallback(() => {
    if (frameTimerRef.current) window.clearInterval(frameTimerRef.current)
    if (maxSessionTimerRef.current) window.clearTimeout(maxSessionTimerRef.current)
    if (elapsedTimerRef.current) window.clearInterval(elapsedTimerRef.current)
    frameTimerRef.current = null
    maxSessionTimerRef.current = null
    elapsedTimerRef.current = null
  }, [])

  const stopAudioInput = useCallback(() => {
    audioProcessorRef.current?.disconnect()
    audioSourceRef.current?.disconnect()
    audioProcessorRef.current = null
    audioSourceRef.current = null
    void audioInputContextRef.current?.close().catch(() => undefined)
    audioInputContextRef.current = null
  }, [])

  const stopSession = useCallback(
    (reason: "manual" | "timeout" | "error" | "unmount" = "manual") => {
      const wasConnected = connectedRef.current
      connectedRef.current = false
      clearTimers()
      stopAudioInput()
      cleanupGeminiLiveHandles({
        websocket: websocketRef.current,
        mediaStream: mediaStreamRef.current,
        frameTimer: null,
        maxSessionTimer: null,
        audioContext: audioOutputContextRef.current,
      })
      websocketRef.current = null
      mediaStreamRef.current = null
      audioOutputContextRef.current = null
      nextAudioTimeRef.current = 0
      if (videoRef.current) videoRef.current.srcObject = null
      if (wasConnected) {
        sendTelemetry("live_session_ended", {
          status: reason === "timeout" ? "timeout" : "ended",
          error_type: reason === "error" ? "live_session_error" : null,
        })
      }
      setUiState(reason === "error" ? "error" : "idle")
      setElapsedSeconds(0)
    },
    [clearTimers, sendTelemetry, stopAudioInput]
  )

  useEffect(() => {
    return () => stopSession("unmount")
  }, [stopSession])

  const sendJson = useCallback((payload: unknown): boolean => {
    const ws = websocketRef.current
    if (!ws || ws.readyState !== WebSocket.OPEN) return false
    ws.send(JSON.stringify(payload))
    return true
  }, [])

  const playAudioChunk = useCallback((base64: string, mimeType: string) => {
    try {
      const AudioContextCtor =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext?: typeof AudioContext })
          .webkitAudioContext
      if (!AudioContextCtor) {
        setAudioFallback("Audio playback is unavailable; showing transcript instead.")
        return
      }
      const context = audioOutputContextRef.current ?? new AudioContextCtor()
      audioOutputContextRef.current = context
      const samples = pcm16Base64ToFloat32(base64)
      const sampleRate = getAudioSampleRate(mimeType)
      const buffer = context.createBuffer(1, samples.length, sampleRate)
      const channelData = new Float32Array(samples.length)
      channelData.set(samples)
      buffer.copyToChannel(channelData, 0)
      const source = context.createBufferSource()
      source.buffer = buffer
      source.connect(context.destination)
      const startAt = Math.max(context.currentTime, nextAudioTimeRef.current)
      source.start(startAt)
      nextAudioTimeRef.current = startAt + buffer.duration
    } catch {
      setAudioFallback("Audio playback failed; showing transcript instead.")
    }
  }, [])

  const handleServerMessage = useCallback(
    (event: MessageEvent) => {
      try {
        const parsed = JSON.parse(String(event.data))
        const parts = extractGeminiLiveServerEventParts(parsed)
        for (const transcript of parts.transcripts) {
          appendMessage({ role: "assistant", text: transcript })
        }
        for (const audioChunk of parts.audioChunks) {
          playAudioChunk(audioChunk.data, audioChunk.mimeType)
        }
      } catch {
        // Ignore malformed server events; the WebSocket close/error handlers
        // surface connection-level failures.
      }
    },
    [appendMessage, playAudioChunk]
  )

  const startVisionFrames = useCallback(
    (stream: MediaStream, liveConfig: GeminiLiveConfigResponse) => {
      if (!liveConfig.vision_enabled || !videoRef.current) return
      const video = videoRef.current
      video.srcObject = stream
      video.muted = true
      video.playsInline = true
      void video.play().catch(() => undefined)

      const fps = Math.max(1, liveConfig.max_frames_per_second)
      const intervalMs = Math.max(1000 / fps, 1000)
      frameTimerRef.current = window.setInterval(() => {
        if (!video.videoWidth || !video.videoHeight) return
        const canvas = document.createElement("canvas")
        canvas.width = Math.min(video.videoWidth, 640)
        canvas.height = Math.round((canvas.width / video.videoWidth) * video.videoHeight)
        const ctx = canvas.getContext("2d")
        if (!ctx) return
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height)
        const dataUrl = canvas.toDataURL("image/jpeg", 0.65)
        const base64 = dataUrl.split(",", 2)[1]
        if (base64 && sendJson(createLiveImageFrameMessage(base64))) {
          setFramesSentCount((count) => count + 1)
        }
      }, intervalMs)
    },
    [sendJson]
  )

  const startAudioStreaming = useCallback(
    async (stream: MediaStream, liveConfig: GeminiLiveConfigResponse) => {
      if (!liveConfig.audio_enabled || stream.getAudioTracks().length === 0) return
      try {
        const context = new AudioContext()
        audioInputContextRef.current = context
        const source = context.createMediaStreamSource(stream)
        const processor = context.createScriptProcessor(4096, 1, 1)
        audioSourceRef.current = source
        audioProcessorRef.current = processor
        processor.onaudioprocess = (event) => {
          if (!connectedRef.current) return
          const input = event.inputBuffer.getChannelData(0)
          const payload = float32ToPcm16Base64(input)
          sendJson(createLiveAudioChunkMessage(payload, context.sampleRate))
        }
        source.connect(processor)
        processor.connect(context.destination)
      } catch {
        setAudioFallback("Microphone streaming is unavailable; text and camera frames still work.")
      }
    },
    [sendJson]
  )

  const startSession = useCallback(async () => {
    if (!config || !canStartLiveSession(config)) return
    setUiState("starting")
    setErrorMessage(null)
    setAudioFallback(null)
    setFramesSentCount(0)
    setTextMessagesCount(0)
    setMessages([])

    try {
      const token = await requestGeminiLiveToken(
        requiresLiveAccessCode(config) ? accessCode : undefined
      )
      if (token.status !== "ready") {
        setUiState("error")
        setErrorMessage(token.message ?? "Live session token was not created.")
        sendTelemetry("live_session_error", {
          status: token.status,
          error_type: token.status,
        })
        return
      }

      const stream = await acquireLiveMedia(config)
      mediaStreamRef.current = stream
      const ws = new WebSocket(buildLiveWebSocketUrl(token))
      websocketRef.current = ws
      startedAtRef.current = Date.now()
      sendTelemetry("live_session_started", { status: "started" })

      ws.onopen = () => {
        connectedRef.current = true
        setUiState("connected")
        appendMessage({
          role: "system",
          text: "Live session connected. Ask about the product by voice or text.",
        })
        sendJson(createLiveSetupMessage())
        sendTelemetry("live_session_connected", { status: "connected" })
        startVisionFrames(stream, config)
        void startAudioStreaming(stream, config)
        elapsedTimerRef.current = window.setInterval(() => {
          if (startedAtRef.current !== null) {
            setElapsedSeconds(Math.round((Date.now() - startedAtRef.current) / 1000))
          }
        }, 1000)
        maxSessionTimerRef.current = window.setTimeout(() => {
          appendMessage({
            role: "system",
            text: "Live session ended at the configured session limit.",
          })
          stopSession("timeout")
        }, config.max_session_seconds * 1000)
      }
      ws.onmessage = handleServerMessage
      ws.onerror = () => {
        setErrorMessage("Live WebSocket connection failed.")
        sendTelemetry("live_session_error", {
          status: "websocket_error",
          error_type: "websocket_error",
        })
      }
      ws.onclose = () => {
        if (connectedRef.current) {
          stopSession("error")
        }
      }
    } catch (error) {
      const message =
        error instanceof Error ? error.message : "Could not start Live session."
      setUiState("error")
      setErrorMessage(message)
      sendTelemetry("live_session_error", {
        status: "start_error",
        error_type: error instanceof Error ? error.name : "start_error",
      })
      stopSession("error")
    }
  }, [
    accessCode,
    appendMessage,
    config,
    handleServerMessage,
    sendJson,
    sendTelemetry,
    startAudioStreaming,
    startVisionFrames,
    stopSession,
  ])

  const sendText = useCallback(() => {
    const trimmed = textInput.trim()
    if (!trimmed || uiState !== "connected") return
    if (sendJson(createLiveTextMessage(trimmed))) {
      appendMessage({ role: "user", text: trimmed })
      setTextMessagesCount((count) => count + 1)
      setTextInput("")
    }
  }, [appendMessage, sendJson, textInput, uiState])

  const ready = canStartLiveSession(config)
  const requiresCode = requiresLiveAccessCode(config)
  const operationalMessage = getLiveOperationalMessage(config)

  return (
    <section className={cn("glass-card mt-4 p-4 sm:p-5", className)}>
      <div className="mb-4 flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-3">
          <Waves className="mt-0.5 h-4 w-4 shrink-0 text-violet-300" />
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <h3 className="text-sm font-semibold text-foreground">
                Gemini Live Voice + Vision
              </h3>
              <span className="rounded-full border border-white/10 bg-slate-800/70 px-2.5 py-1 text-[11px] font-medium text-muted-foreground">
                {liveStateLabel(uiState)}
              </span>
            </div>
            <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
              {operationalMessage}
            </p>
          </div>
        </div>
        {uiState === "loading" && (
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        )}
      </div>

      {config && (
        <div className="mb-4 grid grid-cols-2 gap-2 text-[11px] text-muted-foreground">
          <span className="rounded-xl bg-slate-950/30 px-3 py-2">
            Model: <span className="text-foreground">{config.model}</span>
          </span>
          <span className="rounded-xl bg-slate-950/30 px-3 py-2">
            Limit: <span className="text-foreground">{config.max_session_seconds}s</span>
          </span>
          <span className="inline-flex items-center gap-1 rounded-xl bg-slate-950/30 px-3 py-2">
            <Mic className="h-3 w-3" />
            Audio {config.audio_enabled ? "on" : "off"}
          </span>
          <span className="inline-flex items-center gap-1 rounded-xl bg-slate-950/30 px-3 py-2">
            <Camera className="h-3 w-3" />
            Vision {config.vision_enabled ? `${config.max_frames_per_second} FPS` : "off"}
          </span>
        </div>
      )}

      {requiresCode && uiState !== "connected" && (
        <label className="mb-3 block text-xs text-muted-foreground">
          Live access code
          <input
            type="password"
            value={accessCode}
            onChange={(event) => setAccessCode(event.target.value)}
            className="mt-1 w-full rounded-2xl border border-white/10 bg-slate-950/60 px-3 py-2 text-sm text-foreground outline-none focus:border-violet-400/60"
            autoComplete="off"
          />
        </label>
      )}

      <div className="flex flex-col gap-2 sm:flex-row">
        {uiState === "connected" ? (
          <button
            type="button"
            onClick={() => stopSession("manual")}
            className="touch-target inline-flex items-center justify-center gap-2 rounded-full border border-white/10 bg-slate-800/80 px-4 py-3 text-sm font-medium text-foreground hover:bg-slate-700/80"
          >
            <Square className="h-4 w-4" />
            Stop Live
          </button>
        ) : (
          <button
            type="button"
            onClick={() => void startSession()}
            disabled={
              !ready ||
              uiState === "starting" ||
              (requiresCode && accessCode.trim().length === 0)
            }
            className={cn(
              "touch-target inline-flex items-center justify-center gap-2 rounded-full border border-violet-500/30 bg-violet-500/15 px-4 py-3 text-sm font-medium text-violet-200 hover:bg-violet-500/25",
              (!ready ||
                uiState === "starting" ||
                (requiresCode && accessCode.trim().length === 0)) &&
                "cursor-not-allowed opacity-60"
            )}
          >
            {uiState === "starting" ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Waves className="h-4 w-4" />
            )}
            Start Live session
          </button>
        )}
        <button
          type="button"
          onClick={() => void refreshConfig()}
          disabled={uiState === "connected" || uiState === "starting"}
          className="touch-target rounded-full border border-white/10 px-4 py-3 text-sm font-medium text-muted-foreground hover:bg-white/5 disabled:opacity-50"
        >
          Refresh config
        </button>
      </div>

      <video
        ref={videoRef}
        className={cn(
          "mt-4 aspect-video w-full rounded-2xl border border-white/10 bg-slate-950/60 object-cover",
          uiState !== "connected" && "hidden"
        )}
        muted
        playsInline
      />

      {uiState === "connected" && (
        <div className="mt-4 space-y-3">
          <div className="flex items-center justify-between rounded-xl bg-slate-950/30 px-3 py-2 text-xs text-muted-foreground">
            <span>Elapsed {elapsedSeconds}s</span>
            <span>{framesSentCount} frame(s) sent</span>
            <span>{textMessagesCount} text turn(s)</span>
          </div>
          <div className="flex gap-2">
            <input
              value={textInput}
              onChange={(event) => setTextInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") sendText()
              }}
              placeholder="Ask about the visible product..."
              className="min-w-0 flex-1 rounded-full border border-white/10 bg-slate-950/60 px-4 py-3 text-sm text-foreground outline-none focus:border-violet-400/60"
            />
            <button
              type="button"
              onClick={sendText}
              className="touch-target inline-flex h-11 w-11 items-center justify-center rounded-full bg-violet-500 text-white"
              aria-label="Send Live text message"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {(errorMessage || audioFallback) && (
        <div className="mt-3 space-y-2">
          {errorMessage && (
            <p className="rounded-xl border border-amber-500/25 bg-amber-500/10 px-3 py-2 text-xs text-amber-100">
              {errorMessage}
            </p>
          )}
          {audioFallback && (
            <p className="rounded-xl border border-white/10 bg-slate-950/30 px-3 py-2 text-xs text-muted-foreground">
              {audioFallback}
            </p>
          )}
        </div>
      )}

      {messages.length > 0 && (
        <div className="mt-4 max-h-72 space-y-2 overflow-y-auto rounded-2xl border border-white/5 bg-slate-950/30 p-3">
          {messages.map((message) => (
            <div
              key={message.id}
              className={cn(
                "rounded-2xl px-3 py-2 text-sm leading-relaxed",
                message.role === "user"
                  ? "ml-8 bg-violet-500/15 text-violet-50"
                  : message.role === "assistant"
                    ? "mr-8 bg-slate-800/80 text-foreground"
                    : "bg-slate-900/80 text-muted-foreground"
              )}
            >
              {message.text}
            </div>
          ))}
        </div>
      )}

      <p className="mt-4 flex items-start gap-1.5 text-xs leading-relaxed text-muted-foreground">
        <ShieldCheck className="mt-0.5 h-3.5 w-3.5 shrink-0 text-violet-300" />
        Live media streams directly to Gemini with a short-lived token. SnapInsight
        does not store audio, video, frames, transcripts, or Live messages.
      </p>
    </section>
  )
}
