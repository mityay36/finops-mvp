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
  has_preemptible_nodes: boolean
  by_service: { service: string; cost: number }[]   // держим как массив для UI
  by_namespace: { namespace: string; cost: number }[]
  top_resources: {
    resource_name: string
    resource_id: string
    service_name: string
    cost: number
    is_preemptible: boolean
    namespace: string | null
  }[]
}

export const api = {
  summary: (w = '30d') => get<Summary>(`/api/v1/summary?window=${w}`),
  allocations: (w = '30d') => get<{ items: AllocationItem[] }>(`/api/v1/allocations?window=${w}`),
  recommendations: () => get<RecommendationsResponse>(`/api/v1/recommendations`),
  // трансформируем объект в массив прямо в клиенте
  billing: () => get<Record<string, unknown>>(`/api/v1/billing/actual`).then(raw => ({
    total: raw.total as number,
    has_preemptible_nodes: raw.has_preemptible_nodes as boolean,
    by_service: Object.entries((raw.by_service ?? {}) as Record<string, number>)
      .map(([service, cost]) => ({ service, cost }))
      .sort((a, b) => b.cost - a.cost),
    by_namespace: Object.entries((raw.by_namespace ?? {}) as Record<string, number>)
      .map(([namespace, cost]) => ({ namespace, cost }))
      .sort((a, b) => b.cost - a.cost),
    top_resources: (raw.top_resources ?? []) as BillingResponse['top_resources'],
  } as BillingResponse)),
}
