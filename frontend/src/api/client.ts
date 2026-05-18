// API client for FinOps backend.
// Auth is handled at ingress level (basic auth). Browser includes credentials
// automatically once the user has authenticated. We don't set Authorization
// headers from the frontend.

const API_BASE = import.meta.env.VITE_API_URL ?? ''

// ── Error class with typed status ──────────────────────────────────────────
export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public body?: unknown,
  ) {
    super(`API ${status}: ${statusText}`)
  }
}

type QueryParams = Record<string, string | number | boolean | string[] | number[] | null | undefined>

// ── Core fetch ─────────────────────────────────────────────────────────────
async function request<T>(
  method: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE',
  path: string,
  opts: { params?: QueryParams; body?: unknown } = {},
): Promise<T> {
  const url = new URL(`${API_BASE}${path}`, window.location.origin)
  if (opts.params) {
    for (const [k, v] of Object.entries(opts.params)) {
      if (v === null || v === undefined || v === '') continue
      if (Array.isArray(v)) {
        for (const item of v) {
          if (item !== null && item !== undefined && item !== '') {
            url.searchParams.append(k, String(item))
          }
        }
      } else {
        url.searchParams.set(k, String(v))
      }
    }
  }

  const headers: Record<string, string> = {}
  let body: BodyInit | undefined
  if (opts.body !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(opts.body)
  }

  const res = await fetch(url.toString(), {
    method,
    headers,
    body,
    credentials: 'same-origin',
  })

  if (!res.ok) {
    let parsed: unknown
    try { parsed = await res.json() } catch { /* ignore */ }
    throw new ApiError(res.status, res.statusText, parsed)
  }

  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

// ── Types matching OpenAPI ─────────────────────────────────────────────────

export type ProviderType = 'yc' | 'onprem'

export interface ClusterRead {
  id: string
  name: string
  provider_type: ProviderType
  opencost_url: string
  vm_url: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ClusterDetailedRead extends ClusterRead {
  credential_keys: string[]
}

export interface ClusterCreate {
  name: string
  provider_type: ProviderType
  opencost_url: string
  vm_url: string
  is_active?: boolean
}

export interface ClusterUpdate {
  name?: string
  opencost_url?: string
  vm_url?: string
  is_active?: boolean
}

export interface CredentialMaskedRead {
  key_name: string
  has_value: boolean
  masked_preview: string
}

export interface CredentialUpsert {
  values: Record<string, string>
}

export interface ProviderCredentialFieldRead {
  name: string
  label: string
  is_secret: boolean
  required: boolean
  help_text?: string | null
  placeholder?: string | null
}

export interface ProviderRead {
  type: ProviderType
  name: string
  description?: string | null
  credentials: ProviderCredentialFieldRead[]
}

export interface Page<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}

export interface CoverageInfo {
  requested_from: string
  requested_to: string
  days_requested: number
  days_with_data: number
  missing_days: string[]
  partial_days?: string[]
  completeness_ratio: number
}

export interface CostBreakdown {
  cpu: string
  ram: string
  gpu: string
  pv: string
  network: string
  load_balancer: string
  shared: string
  external: string
  total: string
}

// ── Billing ───────────────────────────────────────────────────────────────
export interface ServiceCostBreakdown {
  service_name: string
  cost: string
  share: number
}

export interface BillingSummary {
  cluster_id: string
  period_start: string
  period_end: string
  currency: string
  total_cost: string
  preemptible_cost: string
  preemptible_share: number
  by_service: ServiceCostBreakdown[]
}

export interface TimeseriesPoint {
  date: string
  total: string
  by_service?: Record<string, string>
}

export interface BillingTimeseries {
  cluster_id: string
  period_start: string
  period_end: string
  granularity: 'daily' | 'weekly'
  group_by: 'total' | 'service'
  currency: string
  points: TimeseriesPoint[]
}

export interface TopResource {
  resource_name: string
  resource_id: string
  service_name: string
  cost: string
  is_preemptible: boolean
}

export interface BillingTopResources {
  cluster_id: string
  period_start: string
  period_end: string
  currency: string
  items: TopResource[]
}

// ── Allocations ───────────────────────────────────────────────────────────
export interface AllocationsTotalsResponse {
  cluster_id: string
  period: CoverageInfo
  breakdown: CostBreakdown
  cpu_efficiency: number | null
  ram_efficiency: number | null
  generated_at: string
}

export interface AggregatedItem {
  key: string
  breakdown: CostBreakdown
  cpu_efficiency: number | null
  ram_efficiency: number | null
  share_of_total: number
}

export interface AllocationsAggregatedResponse {
  cluster_id: string
  period: CoverageInfo
  group_by: 'namespace' | 'controller' | 'node'
  items: AggregatedItem[]
  other: AggregatedItem | null
  cluster_total: string
  generated_at: string
}

export interface TimeseriesPointDTO {
  date: string
  total?: string
  by_key?: Record<string, string>
}

export interface AllocationsTimeseriesResponse {
  cluster_id: string
  period: CoverageInfo
  group_by: 'namespace' | 'controller' | 'node' | null
  series_keys?: string[]
  points: TimeseriesPointDTO[]
  generated_at: string
}

// ── Recommendations ───────────────────────────────────────────────────────
export type RecSeverity = 'low' | 'medium' | 'high' | 'critical'
export type RecStatus = 'open' | 'applied' | 'dismissed' | 'stale'
export type ImpactKind = 'saving' | 'cost_of_safety'

export interface RecommendationListItem {
  id: string
  cluster_id: string
  rule_id: string
  severity: RecSeverity
  status: RecStatus
  title: string
  target_kind: string
  target_namespace?: string | null
  target_name?: string | null
  monthly_impact: string
  impact_kind: ImpactKind
  currency: string
  created_at: string
  updated_at: string
}

export interface RecommendationListResponse {
  items: RecommendationListItem[]
  pagination: { total: number; limit: number; offset: number; has_more: boolean }
}

export interface RecommendationDetail extends RecommendationListItem {
  description: string
  evidence: Record<string, unknown>
  remediation?: Record<string, unknown> | null
  dismissed_reason?: string | null
}

// ── Sync runs ─────────────────────────────────────────────────────────────
export interface BillingSyncRunRead {
  id: string
  cluster_id: string
  status: string
  window_start: string
  window_end: string
  started_at: string
  finished_at: string | null
  records_imported: number
  error_message?: string | null
}

export interface AllocationsSnapshotRunRead {
  id: string
  cluster_id: string
  status: string
  trigger: string
  window_start: string
  window_end: string
  days_processed: number
  rows_upserted: number
  error: string | null
  started_at: string
  finished_at: string | null
}

// ── Diagnostics ───────────────────────────────────────────────────────────
export interface DiagnosticsResponse {
  [key: string]: unknown
}

// ── API surface ───────────────────────────────────────────────────────────
export const api = {
  // Providers
  listProviders: () => request<ProviderRead[]>('GET', '/api/v1/providers'),

  // Clusters
  listClusters: (params?: { limit?: number; offset?: number }) =>
    request<Page<ClusterRead>>('GET', '/api/v1/clusters', { params }),
  getCluster: (id: string) =>
    request<ClusterDetailedRead>('GET', `/api/v1/clusters/${id}`),
  createCluster: (body: ClusterCreate) =>
    request<ClusterRead>('POST', '/api/v1/clusters', { body }),
  updateCluster: (id: string, body: ClusterUpdate) =>
    request<ClusterRead>('PATCH', `/api/v1/clusters/${id}`, { body }),
  deleteCluster: (id: string) =>
    request<void>('DELETE', `/api/v1/clusters/${id}`),

  // Credentials
  listCredentials: (id: string) =>
    request<CredentialMaskedRead[]>('GET', `/api/v1/clusters/${id}/credentials`),
  upsertCredentials: (id: string, body: CredentialUpsert) =>
    request<CredentialMaskedRead[]>('PUT', `/api/v1/clusters/${id}/credentials`, { body }),

  // Diagnostics
  getDiagnostics: (id: string) =>
    request<DiagnosticsResponse>('GET', `/api/v1/clusters/${id}/diagnostics`),

  // Billing
  getBillingSummary: (id: string, params?: { period_start?: string; period_end?: string }) =>
    request<BillingSummary>('GET', `/api/v1/clusters/${id}/billing/summary`, { params }),
  getBillingTimeseries: (id: string, params?: { period_start?: string; period_end?: string; granularity?: 'daily' | 'weekly'; group_by?: 'total' | 'service' }) =>
    request<BillingTimeseries>('GET', `/api/v1/clusters/${id}/billing/timeseries`, { params }),
  getBillingTopResources: (id: string, params?: { period_start?: string; period_end?: string; limit?: number }) =>
    request<BillingTopResources>('GET', `/api/v1/clusters/${id}/billing/top-resources`, { params }),

  // Allocations
  getAllocationsTotals: (id: string, params?: { from?: string; to?: string }) =>
    request<AllocationsTotalsResponse>('GET', `/api/v1/clusters/${id}/allocations/totals`, { params }),
  getAllocationsAggregated: (id: string, params?: { from?: string; to?: string; group_by?: 'namespace' | 'controller' | 'node'; top?: number }) =>
    request<AllocationsAggregatedResponse>('GET', `/api/v1/clusters/${id}/allocations`, { params }),
  getAllocationsTimeseries: (id: string, params?: { from?: string; to?: string; group_by?: 'namespace' | 'controller' | 'node'; top?: number }) =>
    request<AllocationsTimeseriesResponse>('GET', `/api/v1/clusters/${id}/allocations/timeseries`, { params }),

  // Recommendations
  listRecommendations: (id: string, params?: { limit?: number; offset?: number; status?: string[]; severity?: string[]; rule_id?: string[]; namespace?: string[]; min_saving_usd?: number }) =>
    request<RecommendationListResponse>('GET', `/api/v1/clusters/${id}/recommendations`, { params }),
  getRecommendation: (id: string, recId: string) =>
    request<RecommendationDetail>('GET', `/api/v1/clusters/${id}/recommendations/${recId}`),
  applyRecommendation: (id: string, recId: string) =>
    request<RecommendationDetail>('POST', `/api/v1/clusters/${id}/recommendations/${recId}/apply`),
  dismissRecommendation: (id: string, recId: string, reason: string) =>
    request<RecommendationDetail>('POST', `/api/v1/clusters/${id}/recommendations/${recId}/dismiss`, { body: { reason } }),
  refreshRecommendations: (id: string) =>
    request<{ status: string }>('POST', `/api/v1/clusters/${id}/recommendations/refresh`),

  // Sync
  triggerBillingSync: (id: string, force_full = false) =>
    request<BillingSyncRunRead>('POST', `/api/v1/clusters/${id}/sync/billing`, { params: { force_full } }),
  getLatestBillingSync: (id: string) =>
    request<BillingSyncRunRead>('GET', `/api/v1/clusters/${id}/sync/billing/runs/latest`),
  triggerAllocationsSync: (id: string, backfill_days?: number) =>
    request<AllocationsSnapshotRunRead>('POST', `/api/v1/clusters/${id}/sync/allocations`, { params: { backfill_days } }),
  getLatestAllocationsSync: (id: string) =>
    request<AllocationsSnapshotRunRead>('GET', `/api/v1/clusters/${id}/sync/allocations/runs/latest`),
}
