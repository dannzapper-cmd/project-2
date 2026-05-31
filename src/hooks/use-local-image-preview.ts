"use client"

import { useCallback, useEffect, useRef, useState } from "react"

export function useLocalImagePreview() {
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [imageFile, setImageFile] = useState<File | null>(null)
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
        setImageFile(null)
        return false
      }

      const url = URL.createObjectURL(file)
      objectUrlRef.current = url
      setPreviewUrl(url)
      setImageFile(file)
      return true
    },
    [revokeCurrent]
  )

  const setFromBlob = useCallback(
    (blob: Blob) => {
      revokeCurrent()
      setError(null)
      const file = new File([blob], "snapinsight-capture.jpg", {
        type: blob.type || "image/jpeg",
      })
      const url = URL.createObjectURL(file)
      objectUrlRef.current = url
      setPreviewUrl(url)
      setImageFile(file)
    },
    [revokeCurrent]
  )

  const clear = useCallback(() => {
    revokeCurrent()
    setPreviewUrl(null)
    setImageFile(null)
    setError(null)
  }, [revokeCurrent])

  useEffect(() => {
    return () => {
      revokeCurrent()
    }
  }, [revokeCurrent])

  return {
    previewUrl,
    imageFile,
    error,
    hasImage: previewUrl !== null && imageFile !== null,
    setFromFile,
    setFromBlob,
    clear,
  }
}
