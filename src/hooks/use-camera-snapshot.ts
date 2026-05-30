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

export function useCameraSnapshot() {
  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const [status, setStatus] = useState<CameraStatus>("idle")
  const [message, setMessage] = useState<string | null>(null)

  const stopStream = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop())
      streamRef.current = null
    }
    const video = videoRef.current
    if (video) {
      video.srcObject = null
    }
  }, [])

  useEffect(() => {
    return () => {
      if (streamRef.current) {
        streamRef.current.getTracks().forEach((track) => track.stop())
        streamRef.current = null
      }
    }
  }, [])

  const startCamera = useCallback(async () => {
    stopStream()
    setMessage(null)

    if (!isSecureForCamera()) {
      setStatus("insecure")
      setMessage("Camera requires a secure connection (HTTPS).")
      return
    }

    if (typeof navigator === "undefined" || !navigator.mediaDevices?.getUserMedia) {
      setStatus("unsupported")
      setMessage("Camera not supported in this browser. Use upload instead.")
      return
    }

    try {
      let stream: MediaStream
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: { ideal: "environment" } },
          audio: false,
        })
      } catch {
        stream = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: false,
        })
      }

      streamRef.current = stream
      setStatus("active")

      const attachAndPlay = async () => {
        const video = videoRef.current
        if (!video) return
        video.srcObject = stream
        video.muted = true
        video.playsInline = true
        await video.play().catch(() => undefined)
      }

      await attachAndPlay()
      if (!videoRef.current?.srcObject) {
        requestAnimationFrame(() => {
          void attachAndPlay()
        })
      }
    } catch (err) {
      stopStream()
      const name = err instanceof DOMException ? err.name : ""

      if (name === "NotAllowedError" || name === "PermissionDeniedError") {
        setStatus("denied")
        setMessage("Camera permission denied. You can still upload an image.")
      } else if (name === "NotFoundError" || name === "DevicesNotFoundError") {
        setStatus("unsupported")
        setMessage("No camera found. Try upload instead.")
      } else if (name === "NotReadableError" || name === "TrackStartError") {
        setStatus("error")
        setMessage("Camera is in use or unavailable. Try upload instead.")
      } else {
        setStatus("error")
        setMessage("Could not start camera. Try upload instead.")
      }
    }
  }, [stopStream])

  const stopCamera = useCallback(() => {
    stopStream()
    setStatus("idle")
    setMessage(null)
  }, [stopStream])

  const captureSnapshot = useCallback(async (): Promise<Blob | null> => {
    const video = videoRef.current
    if (!video || !streamRef.current) return null

    const width = video.videoWidth
    const height = video.videoHeight
    if (!width || !height) return null

    const canvas = document.createElement("canvas")
    canvas.width = width
    canvas.height = height
    const ctx = canvas.getContext("2d")
    if (!ctx) return null

    ctx.drawImage(video, 0, 0, width, height)
    stopStream()
    setStatus("idle")
    setMessage(null)

    return new Promise<Blob | null>((resolve) => {
      canvas.toBlob((blob) => resolve(blob), "image/jpeg", 0.92)
    })
  }, [stopStream])

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
