const API_BASE = import.meta.env.VITE_API_URL ?? ''

async function apiFetch<T>(path: string, params?: Record<string, string | number>): Promise<T> {
  const url = new URL(`${API_BASE}${path}`, window.location.origin)
  if (params) {
    Object.entries(params).forEach(([k, v]) => url.searchParams.set(k, String(v)))
  }
  const res = await fetch(url.toString())
  if (!res.ok) throw new Error(`API error ${res.status}: ${res.statusText}`)
  return res.json() as Promise<T>
}

export interface AllocationItem {
  name: string
  cpu_cost: number
  ram_cost: number
  pv_cost: number
  network_cost: number
  total_cost: number
}

export interface AllocationsResponse {
  window: string
  aggregate: string
  count: number
  items: AllocationItem[]
}

export interface SummaryResponse {
  total_cost: number
  namespace_count: number
  top_namespaces: { namespace: string; cost: number }[]
}

export interface RecommendationItem {
  type: string
  resource: string
  description: string
  current_ratio?: number
  potential_saving: number | null
  risk: 'low' | 'medium' | 'high'
  action: string
  notes?: string
  recommended_value?: number
}

export interface RecommendationsResponse {
  window: string
  count: number
  estimated_monthly_saving: number
  items: RecommendationItem[]
}

export interface BillingResponse {
  total: number
  has_preemptible_nodes: boolean
  by_service: Record<string, number>
  by_namespace: Record<string, number>
  top_resources: {
    resource_name: string
    resource_id: string
    service_name: string
    cost: number
    is_preemptible: boolean
  }[]
}

export const api = {
  getSummary: (window: string) =>
    apiFetch<SummaryResponse>('/api/v1/summary', { window }),

  getAllocations: (window: string) =>
    apiFetch<AllocationsResponse>('/api/v1/allocations', { window }),

  getRecommendations: () =>
    apiFetch<RecommendationsResponse>('/api/v1/recommendations'),

  getBilling: (days: number) =>
    apiFetch<BillingResponse>('/api/v1/billing/actual', { days }),
}
