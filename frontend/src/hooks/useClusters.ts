import { useEffect } from 'react'
import { useApi } from './useApi'
import { api } from '../api/client'
import { useCluster } from '../state/cluster'

// Loads all clusters and auto-selects the first one if currentClusterId is null
// or points to a stale cluster that no longer exists.
export function useClusters() {
  const { currentClusterId, setCurrentClusterId } = useCluster()
  const state = useApi(() => api.listClusters(100), [])

  useEffect(() => {
    if (!state.data) return
    const items = state.data.items
    if (items.length === 0) {
      if (currentClusterId !== null) setCurrentClusterId(null)
      return
    }
    const stillExists = items.some(c => c.id === currentClusterId)
    if (!currentClusterId || !stillExists) {
      setCurrentClusterId(items[0].id)
    }
  }, [state.data, currentClusterId, setCurrentClusterId])

  return state
}
