/**
 * Realtime update hook — polls for changes until WebSocket is set up.
 *
 * In production this would use Supabase Realtime (WebSocket subscriptions).
 * For now, polls the API at intervals to simulate live updates.
 */

import { useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'

export function useRealtimeUpdates(enabled: boolean = true) {
  const qc = useQueryClient()
  const intervalRef = useRef<number | null>(null)

  useEffect(() => {
    if (!enabled) return

    // Poll every 5 seconds to refresh data
    // In production: replace with Supabase Realtime subscription
    intervalRef.current = window.setInterval(() => {
      qc.invalidateQueries({ queryKey: ['batches'] })
      qc.invalidateQueries({ queryKey: ['review-stats'] })
      qc.invalidateQueries({ queryKey: ['dashboard-stats'] })
    }, 5000)

    return () => {
      if (intervalRef.current) window.clearInterval(intervalRef.current)
    }
  }, [enabled, qc])
}

// For specific batch monitoring (more frequent polling)
export function useBatchProgress(batchId: string | null) {
  const qc = useQueryClient()
  const intervalRef = useRef<number | null>(null)

  useEffect(() => {
    if (!batchId) return

    intervalRef.current = window.setInterval(() => {
      qc.invalidateQueries({ queryKey: ['batch', batchId] })
    }, 2000)

    return () => {
      if (intervalRef.current) window.clearInterval(intervalRef.current)
    }
  }, [batchId, qc])
}
