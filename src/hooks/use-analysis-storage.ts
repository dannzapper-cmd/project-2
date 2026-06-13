"use client"

import { useSyncExternalStore } from "react"

import {
  getActivityLog,
  getAnalysisHistory,
  getLatestAnalysis,
  getLatestAnalysisStoredAt,
  type AnalysisActivityEntry,
  type AnalysisStorageSnapshot,
  type StoredAnalysisRecord,
} from "@/lib/analysis-storage"
import type { AnalysisResponse } from "@/lib/snapinsight-api"

const EMPTY_SNAPSHOT: AnalysisStorageSnapshot = {
  latest: null,
  storedAt: null,
  history: [],
  activity: [],
}

function subscribeToAnalysisStorage(onStoreChange: () => void): () => void {
  window.addEventListener("snapinsight-storage-change", onStoreChange)
  window.addEventListener("storage", onStoreChange)
  return () => {
    window.removeEventListener("snapinsight-storage-change", onStoreChange)
    window.removeEventListener("storage", onStoreChange)
  }
}

function getClientSnapshot(): AnalysisStorageSnapshot {
  return {
    latest: getLatestAnalysis(),
    storedAt: getLatestAnalysisStoredAt(),
    history: getAnalysisHistory(),
    activity: getActivityLog(),
  }
}

export function useAnalysisStorage(): AnalysisStorageSnapshot {
  return useSyncExternalStore(
    subscribeToAnalysisStorage,
    getClientSnapshot,
    () => EMPTY_SNAPSHOT
  )
}

export type { AnalysisActivityEntry, AnalysisResponse, StoredAnalysisRecord }
