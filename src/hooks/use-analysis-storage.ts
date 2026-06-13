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

let cachedClientSnapshot: AnalysisStorageSnapshot = EMPTY_SNAPSHOT
let cachedClientSnapshotKey = ""

function buildSnapshotKey(snapshot: AnalysisStorageSnapshot): string {
  return JSON.stringify({
    latestId: snapshot.latest?.request_id ?? null,
    storedAt: snapshot.storedAt,
    historyIds: snapshot.history.map((item) => item.analysis.request_id),
    activityIds: snapshot.activity.map((item) => item.request_id),
  })
}

function subscribeToAnalysisStorage(onStoreChange: () => void): () => void {
  const handleStoreChange = () => {
    cachedClientSnapshotKey = ""
    onStoreChange()
  }

  window.addEventListener("snapinsight-storage-change", handleStoreChange)
  window.addEventListener("storage", handleStoreChange)
  return () => {
    window.removeEventListener("snapinsight-storage-change", handleStoreChange)
    window.removeEventListener("storage", handleStoreChange)
  }
}

function getClientSnapshot(): AnalysisStorageSnapshot {
  const nextSnapshot: AnalysisStorageSnapshot = {
    latest: getLatestAnalysis(),
    storedAt: getLatestAnalysisStoredAt(),
    history: getAnalysisHistory(),
    activity: getActivityLog(),
  }
  const nextKey = buildSnapshotKey(nextSnapshot)
  if (nextKey !== cachedClientSnapshotKey) {
    cachedClientSnapshotKey = nextKey
    cachedClientSnapshot = nextSnapshot
  }
  return cachedClientSnapshot
}

export function useAnalysisStorage(): AnalysisStorageSnapshot {
  return useSyncExternalStore(
    subscribeToAnalysisStorage,
    getClientSnapshot,
    () => EMPTY_SNAPSHOT
  )
}

export type { AnalysisActivityEntry, AnalysisResponse, StoredAnalysisRecord }
