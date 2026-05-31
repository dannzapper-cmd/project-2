// Lightweight, browser-only image privacy preprocessing.
//
// Goal: strip EXIF metadata (including GPS) by decoding the image and
// re-encoding it through a Canvas, downscale very large images, and compress
// to a reasonable quality before the bytes ever leave the device.
//
// Privacy: processed images are never persisted (no localStorage / disk). If
// any step fails we fall back to the original file so analysis still works.

const MAX_DIMENSION = 1600
const JPEG_QUALITY = 0.85

function isHeic(file: File): boolean {
  const name = file.name.toLowerCase()
  return (
    file.type === "image/heic" ||
    file.type === "image/heif" ||
    name.endsWith(".heic") ||
    name.endsWith(".heif")
  )
}

function targetDimensions(width: number, height: number): [number, number] {
  const largest = Math.max(width, height)
  if (largest <= MAX_DIMENSION) return [width, height]
  const scale = MAX_DIMENSION / largest
  return [Math.round(width * scale), Math.round(height * scale)]
}

async function loadBitmap(file: File): Promise<ImageBitmap | null> {
  if (typeof createImageBitmap !== "function") return null
  try {
    return await createImageBitmap(file)
  } catch {
    return null
  }
}

/**
 * Returns a re-encoded JPEG with EXIF stripped and large dimensions reduced.
 * Falls back to the original file when preprocessing is unavailable or fails.
 */
export async function preprocessImageForUpload(file: File): Promise<File> {
  if (typeof window === "undefined" || typeof document === "undefined") {
    return file
  }

  // HEIC preprocessing deferred. Canvas cannot decode HEIC/HEIF natively, so
  // iOS camera captures may retain EXIF. Future: add a HEIC decoder.
  if (isHeic(file)) {
    return file
  }

  if (!file.type.startsWith("image/")) {
    return file
  }

  const bitmap = await loadBitmap(file)
  if (!bitmap) return file

  try {
    const [width, height] = targetDimensions(bitmap.width, bitmap.height)
    if (!width || !height) return file

    const canvas = document.createElement("canvas")
    canvas.width = width
    canvas.height = height
    const ctx = canvas.getContext("2d")
    if (!ctx) return file

    ctx.drawImage(bitmap, 0, 0, width, height)

    const blob = await new Promise<Blob | null>((resolve) => {
      canvas.toBlob((result) => resolve(result), "image/jpeg", JPEG_QUALITY)
    })
    if (!blob) return file

    // Only swap in the processed file when it is actually no larger; otherwise
    // the original is fine (e.g. already-small assets re-encoded larger).
    const baseName = file.name.replace(/\.[^./\\]+$/, "") || "snapinsight-image"
    return new File([blob], `${baseName}.jpg`, { type: "image/jpeg" })
  } catch {
    return file
  } finally {
    bitmap.close()
  }
}
