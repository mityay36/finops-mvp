const BASE = import.meta.env.VITE_API_URL ?? ''

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`API error ${res.status}`)
  return res.json()
}

export interface AllocationItem {
  name: string
  cpu_cost: number
  ram_cost: number
  pv_cost: number
  total_cost: number
}

export interface Summary {
  total_cost: number
  namespace_count: number
  top_namespaces: { namespace: string; cost: number }[]
}

export interface Recommendation {
  type: string
  resource: string
  description: string
  potential_saving: number | null
  risk: 'low' | 'medium' | 'high'
  action: string
}

export interface RecommendationsResponse {
  count: number
  estimated_monthly_saving: number
  items: Recommendation[]
}

export interface BillingResponse {
  total: number
  currency: string
  period_days: number
  by_service: { service: string; cost: number }[]
}

export const api = {
  summary: (w = '30d') => get<Summary>(`/api/v1/summary?window=${w}`),
  allocations: (w = '30d') => get<{ items: AllocationItem[] }>(`/api/v1/allocations?window=${w}`),
  recommendations: () => get<RecommendationsResponse>(`/api/v1/recommendations`),
  billing: () => get<BillingResponse>(`/api/v1/billing/actual`),
}
