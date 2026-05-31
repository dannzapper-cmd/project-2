import { afterEach, describe, expect, it, vi } from "vitest"
import { readdirSync, readFileSync, statSync } from "node:fs"
import { join } from "node:path"

import {
  buildLiveWebSocketUrl,
  canStartLiveSession,
  cleanupGeminiLiveHandles,
  createLiveSetupMessage,
  extractGeminiLiveServerEventParts,
  getLiveOperationalMessage,
  requiresLiveAccessCode,
} from "@/lib/gemini-live"
import type {
  GeminiLiveConfigResponse,
  GeminiLiveTokenResponse,
} from "@/lib/snapinsight-api"

function liveConfig(
  overrides: Partial<GeminiLiveConfigResponse> = {}
): GeminiLiveConfigResponse {
  return {
    enabled: false,
    configured: false,
    provider: "gemini_live",
    model: "gemini-3.1-flash-live-preview",
    audio_enabled: true,
    vision_enabled: true,
    max_session_seconds: 120,
    max_frames_per_second: 1,
    requires_access_code: false,
    status: "disabled",
    ...overrides,
  }
}

function tokenResponse(
  overrides: Partial<GeminiLiveTokenResponse> = {}
): GeminiLiveTokenResponse {
  return {
    status: "ready",
    enabled: true,
    configured: true,
    provider: "gemini_live",
    model: "gemini-3.1-flash-live-preview",
    token: "short-lived-token",
    websocket_url: "wss://example.test/live",
    expires_in_seconds: 90,
    modality: "audio_with_transcription",
    audio_enabled: true,
    vision_enabled: true,
    max_session_seconds: 120,
    max_frames_per_second: 1,
    requires_access_code: false,
    message: null,
    ...overrides,
  }
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe("Gemini Live client helpers", () => {
  it("reports operational disabled state", () => {
    const config = liveConfig()

    expect(canStartLiveSession(config)).toBe(false)
    expect(getLiveOperationalMessage(config)).toBe(
      "Live mode is disabled in this deployment configuration."
    )
  })

  it("reports enabled config as startable and access-code-gated", () => {
    const config = liveConfig({
      enabled: true,
      configured: true,
      requires_access_code: true,
      status: "ready",
    })

    expect(canStartLiveSession(config)).toBe(true)
    expect(requiresLiveAccessCode(config)).toBe(true)
  })

  it("builds WebSocket URL from token response", () => {
    expect(buildLiveWebSocketUrl(tokenResponse())).toBe(
      "wss://example.test/live?access_token=short-lived-token"
    )
  })

  it("does not send system instruction from frontend setup", () => {
    const setup = createLiveSetupMessage()

    expect(setup).toEqual({ setup: {} })
    expect(JSON.stringify(setup)).not.toContain("system")
  })

  it("extracts transcript and audio from a single server event", () => {
    const parts = extractGeminiLiveServerEventParts({
      serverContent: {
        outputTranscription: { text: "Assistant transcript" },
        modelTurn: {
          parts: [
            {
              inlineData: {
                mimeType: "audio/pcm;rate=24000",
                data: "AAAA",
              },
            },
            { text: "Fallback text" },
          ],
        },
      },
    })

    expect(parts.transcripts).toContain("Assistant transcript")
    expect(parts.transcripts).toContain("Fallback text")
    expect(parts.audioChunks).toEqual([
      { mimeType: "audio/pcm;rate=24000", data: "AAAA" },
    ])
  })

  it("cleanup closes websocket and stops media tracks", () => {
    const close = vi.fn()
    const stop = vi.fn()
    vi.stubGlobal("WebSocket", { CLOSING: 2, CLOSED: 3 })
    vi.stubGlobal("window", {
      clearInterval: vi.fn(),
      clearTimeout: vi.fn(),
    })

    cleanupGeminiLiveHandles({
      websocket: { readyState: 1, close },
      mediaStream: { getTracks: () => [{ stop }] },
      frameTimer: 1,
      maxSessionTimer: 2,
      audioContext: null,
    })

    expect(close).toHaveBeenCalled()
    expect(stop).toHaveBeenCalled()
  })

  it("frontend code does not reference Gemini API key env vars", () => {
    const srcRoot = join(process.cwd(), "src")
    const files = readdirSync(srcRoot, { recursive: true })
      .map((entry) => join(srcRoot, String(entry)))
      .filter((path) => statSync(path).isFile())
      .filter((path) => !path.endsWith(".test.ts") && !path.endsWith(".test.tsx"))

    const combined = files.map((path) => readFileSync(path, "utf8")).join("\n")

    expect(combined).not.toContain("GEMINI_API_KEY")
    expect(combined).not.toContain("NEXT_PUBLIC_GEMINI")
    expect(combined).not.toContain("SNAPINSIGHT_LIVE_ACCESS_CODE")
  })
})
