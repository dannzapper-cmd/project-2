"use client"

import { useCallback, useEffect, useRef, useState } from "react"

export type CameraStatus =
  | "idle"
  | "active"
  | "denied"
  | "unsupported"
  | "insecure"
  | "error"

function isSecureForCamera(): boolean {
  if (typeof window === "undefined") return false
  return (
    window.location.protocol === "https:" ||
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1"
  )
}

function getErrorName(err: unknown): string {
  return err instanceof DOMException ? err.name : ""
}

function isPermissionDenied(err: unknown): boolean {
  const name = getErrorName(err)
  return name === "NotAllowedError" || name === "PermissionDeniedError"
}

/** Retry generic video only when environment-facing constraints likely failed. */
function shouldRetryWithGenericVideo(err: unknown): boolean {
  const name = getErrorName(err)
  return (
    name === "OverconstrainedError" ||
    name === "ConstraintNotSatisfiedError" ||
    name === "NotFoundError" ||
    name === "DevicesNotFoundError"
  )
}

function stopMediaStream(stream: MediaStream): void {
  stream.getTracks().forEach((track) => track.stop())
}

async function acquireVideoStream(
  getUserMedia: typeof navigator.mediaDevices.getUserMedia
): Promise<MediaStream> {
  try {
    return await getUserMedia({
      video: { facingMode: { ideal: "environment" } },
      audio: false,
    })
  } catch (firstError) {
    if (isPermissionDenied(firstError)) {
      throw firstError
    }
    if (!shouldRetryWithGenericVideo(firstError)) {
      throw firstError
    }
    return getUserMedia({
      video: true,
      audio: false,
    })
  }
}

export function useCameraSnapshot() {
  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const mountedRef = useRef(true)
  const requestIdRef = useRef(0)
  const [status, setStatus] = useState<CameraStatus>("idle")
  const [message, setMessage] = useState<string | null>(null)

  const safeSetState = useCallback((update: () => void) => {
    if (mountedRef.current) {
      update()
    }
  }, [])

  const stopStream = useCallback(() => {
    if (streamRef.current) {
      stopMediaStream(streamRef.current)
      streamRef.current = null
    }
    const video = videoRef.current
    if (video) {
      video.srcObject = null
    }
  }, [])

  const invalidatePending = useCallback(() => {
    requestIdRef.current += 1
  }, [])

  useEffect(() => {
    mountedRef.current = true
    return () => {
      mountedRef.current = false
      invalidatePending()
      if (streamRef.current) {
        stopMediaStream(streamRef.current)
        streamRef.current = null
      }
    }
  }, [invalidatePending])

  const applyCameraError = useCallback(
    (err: unknown) => {
      stopStream()
      const name = getErrorName(err)

      if (isPermissionDenied(err)) {
        safeSetState(() => {
          setStatus("denied")
          setMessage("Camera permission denied. You can still upload an image.")
        })
      } else if (name === "NotFoundError" || name === "DevicesNotFoundError") {
        safeSetState(() => {
          setStatus("unsupported")
          setMessage("No camera found. Try upload instead.")
        })
      } else if (name === "NotReadableError" || name === "TrackStartError") {
        safeSetState(() => {
          setStatus("error")
          setMessage("Camera is in use or unavailable. Try upload instead.")
        })
      } else {
        safeSetState(() => {
          setStatus("error")
          setMessage("Could not start camera. Try upload instead.")
        })
      }
    },
    [stopStream, safeSetState]
  )

  const attachStreamToVideo = useCallback(
    async (stream: MediaStream, requestId: number) => {
      if (requestId !== requestIdRef.current) {
        stopMediaStream(stream)
        return false
      }

      const video = videoRef.current
      if (!video) {
        stopMediaStream(stream)
        return false
      }

      video.srcObject = stream
      video.muted = true
      video.playsInline = true
      await video.play().catch(() => undefined)

      if (requestId !== requestIdRef.current) {
        video.srcObject = null
        stopMediaStream(stream)
        return false
      }

      return true
    },
    []
  )

  const startCamera = useCallback(async () => {
    const requestId = ++requestIdRef.current
    stopStream()
    safeSetState(() => {
      setMessage(null)
    })

    if (!isSecureForCamera()) {
      safeSetState(() => {
        setStatus("insecure")
        setMessage("Camera requires a secure connection (HTTPS).")
      })
      return
    }

    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      safeSetState(() => {
        setStatus("unsupported")
        setMessage("Camera not supported in this browser. Use upload instead.")
      })
      return
    }

    try {
      const stream = await acquireVideoStream(
        navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices)
      )

      if (requestId !== requestIdRef.current) {
        stopMediaStream(stream)
        return
      }

      streamRef.current = stream
      safeSetState(() => {
        setStatus("active")
        setMessage(null)
      })

      const attached = await attachStreamToVideo(stream, requestId)
      if (!attached && requestId === requestIdRef.current) {
        stopStream()
        safeSetState(() => {
          setStatus("error")
          setMessage("Could not start camera preview. Try upload instead.")
        })
      }

      if (!attached && requestId !== requestIdRef.current) {
        stopStream()
        return
      }

      if (attached && !videoRef.current?.srcObject) {
        requestAnimationFrame(() => {
          if (requestId !== requestIdRef.current || !streamRef.current) return
          void attachStreamToVideo(streamRef.current, requestId)
        })
      }
    } catch (err) {
      if (requestId !== requestIdRef.current) {
        return
      }
      applyCameraError(err)
    }
  }, [stopStream, safeSetState, attachStreamToVideo, applyCameraError])

  const stopCamera = useCallback(() => {
    invalidatePending()
    stopStream()
    safeSetState(() => {
      setStatus("idle")
      setMessage(null)
    })
  }, [invalidatePending, stopStream, safeSetState])

  const captureSnapshot = useCallback(async (): Promise<Blob | null> => {
    const video = videoRef.current
    if (!video || !streamRef.current) {
      return null
    }

    const width = video.videoWidth
    const height = video.videoHeight
    if (!width || !height) {
      safeSetState(() => {
        setMessage("Camera is still starting. Try again in a moment.")
      })
      return null
    }

    const canvas = document.createElement("canvas")
    canvas.width = width
    canvas.height = height
    const ctx = canvas.getContext("2d")
    if (!ctx) {
      return null
    }

    ctx.drawImage(video, 0, 0, width, height)
    stopStream()
    safeSetState(() => {
      setStatus("idle")
      setMessage(null)
    })

    return new Promise<Blob | null>((resolve) => {
      canvas.toBlob((blob) => resolve(blob), "image/jpeg", 0.92)
    })
  }, [stopStream, safeSetState])

  return {
    videoRef,
    status,
    message,
    isActive: status === "active",
    startCamera,
    stopCamera,
    captureSnapshot,
  }
}
