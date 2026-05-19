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
  name?: string | null
  opencost_url?: string | null
  vm_url?: string | null
  is_active?: boolean | null
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
  description: string
  credentials: ProviderCredentialFieldRead[]
}

export interface Page<T> {
  items: T[]
  total: number
  limit: number
  offset: number
}

export interface CoverageInfo {
  requested_from: string  // YYYY-MM-DD
  requested_to: string
  days_requested: number
  days_with_data: number
  missing_days: string[]
  partial_days?: string[]
  completeness_ratio: number  // 0..1
}

export interface PaginationMeta {
  total: number
  limit: number
  offset: number
  has_more: boolean
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
  timestamp: string
  cost: string
  service_name?: string | null
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
  resource_id: string | null
  resource_name: string | null
  service_name: string
  sku_name: string
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
  bucket_date: string
  key?: string | null
  breakdown: CostBreakdown
}

export interface AllocationsTimeseriesResponse {
  cluster_id: string
  period: CoverageInfo
  group_by?: 'namespace' | 'controller' | 'node' | null
  series_keys?: string[]
  points: TimeseriesPointDTO[]
  generated_at: string
}

// ── Recommendations ───────────────────────────────────────────────────────
export type RecSeverity = 'info' | 'warning' | 'critical'
export type RecStatus = 'open' | 'applied' | 'dismissed' | 'closed_resolved'
export type ImpactKind = 'saving' | 'cost_of_safety'

export interface RecommendationItem {
  id: string
  cluster_id: string
  rule_id: string
  target_kind: string
  target_namespace: string
  target_controller: string
  status: RecStatus
  severity: RecSeverity
  monthly_impact_usd: string
  impact_kind: ImpactKind
  first_seen_at: string
  last_seen_at: string
  resolved_at?: string | null
  dismissed_reason?: string | null
}

export interface RecommendationListResponse {
  items: RecommendationItem[]
  pagination: PaginationMeta
}

export interface RecommendationRefreshResponse {
  cluster_id: string
  accepted: boolean
  message: string
}

export interface RecommendationDetail extends RecommendationItem {
  evidence: Record<string, unknown>
}

// ── Sync runs ─────────────────────────────────────────────────────────────
export type SyncRunStatus = 'running' | 'success' | 'failed'

// /sync/billing/runs/latest — урезанная схема (только успешные)
export interface LatestBillingSyncRun {
  id: string
  cluster_id: string
  finished_at: string
  records_imported: number
  window_start: string
  window_end: string
}

export interface BillingSyncRunRead {
  id: string
  cluster_id: string
  status: SyncRunStatus
  window_start: string
  window_end: string
  started_at: string
  finished_at?: string | null
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
  error?: string | null
  started_at: string
  finished_at?: string | null
}

// /sync/allocations/runs/latest — та же схема
export type LatestAllocationsSnapshotRun = AllocationsSnapshotRunRead

// ── Diagnostics ───────────────────────────────────────────────────────────
export interface DiagnosticsEndpoint {
  base_url: string
  reachable: boolean
}

export interface DiagnosticsResponse {
  cluster_id: string
  cluster_name: string
  opencost: DiagnosticsEndpoint
  victoria_metrics: DiagnosticsEndpoint
}

// ── API surface ───────────────────────────────────────────────────────────
function qs(params: Record<string, unknown>): string {
  const sp = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null) continue
    if (Array.isArray(v)) v.forEach(x => sp.append(k, String(x)))
    else sp.append(k, String(v))
  }
  const s = sp.toString()
  return s ? `?${s}` : ''
}

export const api = {
  // Providers
  listProviders: () => request<ProviderRead[]>('GET', '/providers'),

  // Clusters
  listClusters: (limit = 100) =>
    request<{ items: ClusterRead[]; total: number; limit: number; offset: number }>('GET', `/clusters?limit=${limit}`),
  getCluster: (id: string) => request<ClusterDetailedRead>('GET', `/clusters/${id}`),
  createCluster: (body: ClusterCreate) => request<ClusterRead>('POST', '/clusters', {body}),
  updateCluster: (id: string, body: ClusterUpdate) => request<ClusterRead>('PATCH', `/clusters/${id}`, {body}),
  deleteCluster: (id: string) => request<void>('DELETE', `/clusters/${id}`),

  // Credentials
  listCredentials: (id: string) => request<CredentialMaskedRead[]>('GET', `/clusters/${id}/credentials`),
  upsertCredentials: (id: string, body: CredentialUpsert) =>
    request<CredentialMaskedRead[]>('PUT', `/clusters/${id}/credentials`, {body}),

  // Diagnostics
  getDiagnostics: (id: string) => request<DiagnosticsResponse>('GET', `/clusters/${id}/diagnostics`),

  // Sync
  triggerBillingSync: (id: string, forceFull = false) =>
    request<BillingSyncRunRead>('POST', `/clusters/${id}/sync/billing${qs({ force_full: forceFull })}`),
  getLatestBillingSync: (id: string) =>
    request<LatestBillingSyncRun>('GET', `/clusters/${id}/sync/billing/runs/latest`),

  triggerAllocationsSync: (id: string, backfillDays?: number) =>
    request<AllocationsSnapshotRunRead>('POST', `/clusters/${id}/sync/allocations${qs({ backfill_days: backfillDays })}`),
  getLatestAllocationsSync: (id: string) =>
    request<LatestAllocationsSnapshotRun>('GET', `/clusters/${id}/sync/allocations/runs/latest`),

  // Billing
  getBillingSummary: (id: string, p: { period_start?: string; period_end?: string } = {}) =>
    request<BillingSummary>('GET', `/clusters/${id}/billing/summary${qs(p)}`),
  getBillingTimeseries: (id: string, p: { period_start?: string; period_end?: string; granularity?: 'daily' | 'weekly'; group_by?: 'total' | 'service' } = {}) =>
    request<BillingTimeseries>('GET', `/clusters/${id}/billing/timeseries${qs(p)}`),
  getBillingTopResources: (id: string, p: { period_start?: string; period_end?: string; limit?: number } = {}) =>
    request<BillingTopResources>('GET', `/clusters/${id}/billing/top-resources${qs(p)}`),

  // Allocations
  getAllocationsTotals: (id: string, p: { from?: string; to?: string } = {}) =>
    request<AllocationsTotalsResponse>('GET', `/clusters/${id}/allocations/totals${qs(p)}`),
  getAllocationsAggregated: (id: string, p: { from?: string; to?: string; group_by?: 'namespace' | 'controller' | 'node'; top?: number }) =>
    request<AllocationsAggregatedResponse>('GET', `/clusters/${id}/allocations${qs(p)}`),
  getAllocationsTimeseries: (id: string, p: { from?: string; to?: string; group_by?: 'namespace' | 'controller' | 'node'; top?: number } = {}) =>
    request<AllocationsTimeseriesResponse>('GET', `/clusters/${id}/allocations/timeseries${qs(p)}`),

  // Recommendations
  listRecommendations: (id: string, p: { limit?: number; offset?: number; status?: RecStatus[]; severity?: RecSeverity[]; rule_id?: string[]; namespace?: string[]; min_saving_usd?: number } = {}) =>
    request<RecommendationListResponse>('GET', `/clusters/${id}/recommendations${qs(p)}`),
  getRecommendation: (clusterId: string, recId: string) =>
    request<RecommendationDetail>('GET', `/clusters/${clusterId}/recommendations/${recId}`),
  applyRecommendation: (clusterId: string, recId: string) =>
    request<RecommendationDetail>('POST', `/clusters/${clusterId}/recommendations/${recId}/apply`),
  dismissRecommendation: (clusterId: string, recId: string, reason: string) =>
    request<RecommendationDetail>('POST', `/clusters/${clusterId}/recommendations/${recId}/dismiss`, { body: { reason } },),
  refreshRecommendations: (id: string) =>
    request<RecommendationRefreshResponse>('POST', `/clusters/${id}/recommendations/refresh`),
}
