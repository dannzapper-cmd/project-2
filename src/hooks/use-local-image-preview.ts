"use client"

import { useCallback, useEffect, useRef, useState } from "react"

export function useLocalImagePreview() {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const objectUrlRef = useRef<string | null>(null)

  const revokeCurrent = useCallback(() => {
    if (objectUrlRef.current) {
      URL.revokeObjectURL(objectUrlRef.current)
      objectUrlRef.current = null
    }
  }, [])

  const setFromFile = useCallback(
    (file: File): boolean => {
      revokeCurrent()
      setError(null)

      if (!file.type.startsWith("image/")) {
        setError("Please select an image file (JPEG, PNG, WebP, etc.).")
        setPreviewUrl(null)
        return false
      }

      const url = URL.createObjectURL(file)
      objectUrlRef.current = url
      setPreviewUrl(url)
      return true
    },
    [revokeCurrent]
  )

  const setFromBlob = useCallback(
    (blob: Blob) => {
      revokeCurrent()
      setError(null)
      const url = URL.createObjectURL(blob)
      objectUrlRef.current = url
      setPreviewUrl(url)
    },
    [revokeCurrent]
  )

  const clear = useCallback(() => {
    revokeCurrent()
    setPreviewUrl(null)
    setError(null)
  }, [revokeCurrent])

  useEffect(() => {
    return () => {
      revokeCurrent()
    }
  }, [revokeCurrent])

  return {
    previewUrl,
    error,
    hasImage: previewUrl !== null,
    setFromFile,
    setFromBlob,
    clear,
  }
}
