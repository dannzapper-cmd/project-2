import type {
  GeminiLiveConfigResponse,
  GeminiLiveTokenResponse,
} from "@/lib/snapinsight-api"

export interface GeminiLiveSetupMessage {
  setup: Record<string, never>
}

export interface GeminiLiveHandles {
  websocket?: Pick<WebSocket, "close" | "readyState"> | null
  mediaStream?: Pick<MediaStream, "getTracks"> | null
  frameTimer?: ReturnType<typeof window.setInterval> | null
  maxSessionTimer?: ReturnType<typeof window.setTimeout> | null
  audioContext?: Pick<AudioContext, "close"> | null
}

export interface GeminiLiveServerEventParts {
  transcripts: string[]
  audioChunks: Array<{ data: string; mimeType: string }>
}

export function canStartLiveSession(config: GeminiLiveConfigResponse | null): boolean {
  return Boolean(config?.enabled && config.configured && config.status === "ready")
}

export function requiresLiveAccessCode(
  config: GeminiLiveConfigResponse | null
): boolean {
  return Boolean(config?.requires_access_code)
}

export function getLiveOperationalMessage(
  config: GeminiLiveConfigResponse | null
): string {
  if (!config) return "Checking Live mode configuration..."
  if (!config.enabled) {
    return "Live mode is disabled in this deployment configuration."
  }
  if (!config.configured) {
    return "Live mode is enabled but not configured on the backend."
  }
  return "Live mode is ready. Media streams directly from this browser to Gemini using a short-lived token."
}

export function buildLiveWebSocketUrl(token: GeminiLiveTokenResponse): string {
  if (!token.websocket_url || !token.token) {
    throw new Error("Live token response did not include connection details.")
  }
  const separator = token.websocket_url.includes("?") ? "&" : "?"
  return `${token.websocket_url}${separator}access_token=${encodeURIComponent(
    token.token
  )}`
}

export function createLiveSetupMessage(): GeminiLiveSetupMessage {
  // System instruction, model, modality, and transcription settings are locked
  // into the backend-minted ephemeral token via liveConnectConstraints.
  return { setup: {} }
}

export function createLiveTextMessage(text: string) {
  return {
    clientContent: {
      turns: [
        {
          role: "user",
          parts: [{ text }],
        },
      ],
      turnComplete: true,
    },
  }
}

export function createLiveImageFrameMessage(data: string, mimeType = "image/jpeg") {
  return {
    realtimeInput: {
      mediaChunks: [
        {
          mimeType,
          data,
        },
      ],
    },
  }
}

export function createLiveAudioChunkMessage(
  data: string,
  sampleRate: number
) {
  return {
    realtimeInput: {
      mediaChunks: [
        {
          mimeType: `audio/pcm;rate=${sampleRate}`,
          data,
        },
      ],
    },
  }
}

function collectServerEventParts(
  value: unknown,
  output: GeminiLiveServerEventParts,
  parentKey = ""
): void {
  if (!value || typeof value !== "object") return

  if (Array.isArray(value)) {
    value.forEach((item) => collectServerEventParts(item, output, parentKey))
    return
  }

  const record = value as Record<string, unknown>
  const inlineData = record.inlineData ?? record.inline_data
  if (inlineData && typeof inlineData === "object") {
    const inlineRecord = inlineData as Record<string, unknown>
    const data = inlineRecord.data
    const mimeType = inlineRecord.mimeType ?? inlineRecord.mime_type
    if (
      typeof data === "string" &&
      typeof mimeType === "string" &&
      mimeType.startsWith("audio/")
    ) {
      output.audioChunks.push({ data, mimeType })
    }
  }

  for (const [key, nested] of Object.entries(record)) {
    if (
      (key === "text" || key.toLowerCase().includes("transcript")) &&
      typeof nested === "string" &&
      nested.trim()
    ) {
      output.transcripts.push(nested.trim())
      continue
    }
    collectServerEventParts(nested, output, key || parentKey)
  }
}

export function extractGeminiLiveServerEventParts(
  event: unknown
): GeminiLiveServerEventParts {
  const output: GeminiLiveServerEventParts = {
    transcripts: [],
    audioChunks: [],
  }
  collectServerEventParts(event, output)
  return output
}

export function base64ToBytes(base64: string): Uint8Array {
  const binary = window.atob(base64)
  const bytes = new Uint8Array(binary.length)
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index)
  }
  return bytes
}

export function pcm16Base64ToFloat32(base64: string): Float32Array {
  const bytes = base64ToBytes(base64)
  const samples = new Float32Array(Math.floor(bytes.length / 2))
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength)
  for (let index = 0; index < samples.length; index += 1) {
    samples[index] = view.getInt16(index * 2, true) / 32768
  }
  return samples
}

export function float32ToPcm16Base64(input: Float32Array): string {
  const buffer = new ArrayBuffer(input.length * 2)
  const view = new DataView(buffer)
  for (let index = 0; index < input.length; index += 1) {
    const sample = Math.max(-1, Math.min(1, input[index]))
    view.setInt16(index * 2, sample < 0 ? sample * 0x8000 : sample * 0x7fff, true)
  }
  const bytes = new Uint8Array(buffer)
  let binary = ""
  for (const byte of bytes) {
    binary += String.fromCharCode(byte)
  }
  return window.btoa(binary)
}

export function cleanupGeminiLiveHandles(handles: GeminiLiveHandles): void {
  if (handles.frameTimer) window.clearInterval(handles.frameTimer)
  if (handles.maxSessionTimer) window.clearTimeout(handles.maxSessionTimer)
  if (
    handles.websocket &&
    handles.websocket.readyState !== WebSocket.CLOSING &&
    handles.websocket.readyState !== WebSocket.CLOSED
  ) {
    handles.websocket.close()
  }
  handles.mediaStream?.getTracks().forEach((track) => track.stop())
  void handles.audioContext?.close().catch(() => undefined)
}
