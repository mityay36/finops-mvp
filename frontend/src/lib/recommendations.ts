import type { RecommendationItem, RecommendationDetail, ImpactKind } from '../api/client'

// ==================== Existing helpers ====================

const RULE_LABELS: Record<string, string> = {
  rightsizing_cpu: 'Снижение запрошенного CPU',
  rightsizing_ram: 'Снижение запрошенного RAM',
  oom_risk_ram:    'Риск OOMKilled (мало RAM)',
}

export function ruleLabel(ruleId: string): string {
  return RULE_LABELS[ruleId] ?? ruleId
    .split('_')
    .map(s => s.charAt(0).toUpperCase() + s.slice(1))
    .join(' ')
}

export function targetLabel(item: Pick<RecommendationItem, 'target_kind' | 'target_namespace' | 'target_controller'>): string {
  const parts = [item.target_kind]
  if (item.target_namespace) parts.push(item.target_namespace)
  if (item.target_controller) parts.push(item.target_controller)
  return parts.join(' / ')
}

// ==================== Action builder ====================

export interface RecommendedAction {
  /** Headline action: что сделать одной фразой */
  headline: string
  /** Конкретные изменения в манифесте (yaml-like). Пары current → recommended. */
  changes: Array<{ field: string; from: string; to: string; note?: string }>
  /** Почему — explanation в bullets. */
  why: string[]
  /** Как формируется потенциал — формула. */
  formula?: string
  /** Команда для kubectl, если есть. */
  kubectl?: string
  /** Тон действия — saving (зелёный) или cost_of_safety (янтарный). */
  tone: ImpactKind
  rawEvidence?: Record<string, unknown>   
}

const ev = (e: Record<string, unknown>, k: string): string | undefined => {
  const v = e[k]
  return v === undefined || v === null ? undefined : String(v)
}

const mCores = (s: string | undefined): string => {
  if (!s) return '—'
  const n = parseFloat(s)
  if (isNaN(n)) return s
  if (n >= 1) return `${n.toFixed(2)} cores`
  return `${Math.round(n * 1000)}m`
}

const mPercent = (s: string | undefined, digits = 1): string => {
  if (!s) return '—'
  const n = parseFloat(s)
  if (isNaN(n)) return s
  return `${(n * 100).toFixed(digits)}%`
}

const mBytes = (s: string | undefined): string => {
  if (!s) return '—'
  const n = parseFloat(s)
  if (isNaN(n)) return s
  if (n >= 1024 ** 3) return `${(n / 1024 ** 3).toFixed(2)} Gi`
  if (n >= 1024 ** 2) return `${(n / 1024 ** 2).toFixed(0)} Mi`
  if (n >= 1024) return `${(n / 1024).toFixed(0)} Ki`
  return `${n.toFixed(0)} B`
}

export function buildAction(rec: RecommendationDetail): RecommendedAction | null {
  const e = rec.evidence ?? {}
  switch (rec.rule_id) {
    case 'rightsizing_cpu': return buildRightsizingCpu(rec, e)
    case 'rightsizing_ram': return buildRightsizingRam(rec, e)
    case 'oom_risk_ram':    return buildOomRiskRam(rec, e)
    default:                return null
  }
}

function buildRightsizingCpu(rec: RecommendationDetail, e: Record<string, unknown>): RecommendedAction {
  const reqCurrent = ev(e, 'cores_requested_median')
  const recCores   = ev(e, 'cores_recommended')
  const usedP95    = ev(e, 'cores_used_p95')
  const days       = ev(e, 'days_evaluated')
  const margin     = ev(e, 'safety_margin')
  const pods       = ev(e, 'pods_per_day_avg')
  const hours      = ev(e, 'monthly_hours')
  const rate       = ev(e, 'cpu_unit_cost_per_core_hour')
  const delta      = ev(e, 'cores_delta')
  const kind       = ev(e, 'controller_kind') ?? rec.target_kind
  const ns         = rec.target_namespace
  const ctl        = rec.target_controller

  return {
    headline: `Уменьшить request CPU у ${kind}/${ctl} с ${mCores(reqCurrent)} до ${mCores(recCores)}`,
    changes: [
      {
        field: 'spec.template.spec.containers[*].resources.requests.cpu',
        from: mCores(reqCurrent),
        to: mCores(recCores),
        note: `safety margin ${mPercent(margin, 0)}`,
      },
    ],
    why: [
      `За ${days ?? '—'} дней p95 потребления CPU: ${mCores(usedP95)}`,
      `Текущий request (медиана): ${mCores(reqCurrent)}`,
      reqCurrent && usedP95
        ? `Используется ~${mPercent(String(parseFloat(usedP95) / parseFloat(reqCurrent)), 1)} от запрошенного`
        : '',
      `Безопасный request с margin ${mPercent(margin, 0)}: ${mCores(recCores)}`,
      `Подов в среднем за день: ${pods ?? '—'}`,
    ].filter(Boolean) as string[],
    formula: delta && pods && hours && rate
      ? `${parseFloat(delta).toFixed(3)} cores × ${parseFloat(pods).toFixed(2)} pods × ${hours} ч/мес × ${parseFloat(rate).toFixed(2)} ₽/core·ч = ${parseFloat(rec.monthly_impact_usd).toFixed(2)} ₽/мес`
      : undefined,
    kubectl: ns && ctl
      ? `kubectl -n ${ns} set resources ${kind}/${ctl} --requests=cpu=${mCores(recCores)}`
      : undefined,
    tone: 'saving',
    rawEvidence: e,
  }
}

function buildRightsizingRam(rec: RecommendationDetail, e: Record<string, unknown>): RecommendedAction {
  const reqCurrent = ev(e, 'ram_requested_median')
  const recRam     = ev(e, 'ram_recommended')
  const usedP95    = ev(e, 'ram_used_p95')
  const days       = ev(e, 'days_evaluated')
  const margin     = ev(e, 'safety_margin')
  const pods       = ev(e, 'pods_per_day_avg')
  const kind       = ev(e, 'controller_kind') ?? rec.target_kind
  const ns         = rec.target_namespace
  const ctl        = rec.target_controller

  return {
    headline: `Уменьшить request RAM у ${kind}/${ctl} с ${mBytes(reqCurrent)} до ${mBytes(recRam)}`,
    changes: [
      {
        field: 'spec.template.spec.containers[*].resources.requests.memory',
        from: mBytes(reqCurrent),
        to: mBytes(recRam),
        note: `safety margin ${mPercent(margin, 0)}`,
      },
    ],
    why: [
      `За ${days ?? '—'} дней p95 потребления RAM: ${mBytes(usedP95)}`,
      `Текущий request (медиана): ${mBytes(reqCurrent)}`,
      `Безопасный request с margin ${mPercent(margin, 0)}: ${mBytes(recRam)}`,
      `Подов в среднем за день: ${pods ?? '—'}`,
    ].filter(Boolean) as string[],
    kubectl: ns && ctl
      ? `kubectl -n ${ns} set resources ${kind}/${ctl} --requests=memory=${mBytes(recRam)}`
      : undefined,
    tone: 'saving',
    rawEvidence: e,
  }
}

function buildOomRiskRam(rec: RecommendationDetail, e: Record<string, unknown>): RecommendedAction {
  const reqCurrent = ev(e, 'ram_requested_median')
  const recRam     = ev(e, 'ram_recommended')
  const usedP95    = ev(e, 'ram_used_p95')
  const oomEvents  = ev(e, 'oom_events') ?? ev(e, 'oom_kills')
  const days       = ev(e, 'days_evaluated')
  const kind       = ev(e, 'controller_kind') ?? rec.target_kind
  const ns         = rec.target_namespace
  const ctl        = rec.target_controller

  return {
    headline: `Увеличить request RAM у ${kind}/${ctl} до ${mBytes(recRam)} для предотвращения OOMKill`,
    changes: [
      {
        field: 'spec.template.spec.containers[*].resources.requests.memory',
        from: mBytes(reqCurrent),
        to: mBytes(recRam),
        note: 'инвестиция в стабильность, не экономия',
      },
    ],
    why: [
      oomEvents ? `Зафиксировано OOM-событий: ${oomEvents}` : `Риск OOMKill при текущем request`,
      usedP95 && reqCurrent
        ? `p95 потребления (${mBytes(usedP95)}) близок или превышает request (${mBytes(reqCurrent)})`
        : '',
      `Период наблюдения: ${days ?? '—'} дней`,
    ].filter(Boolean) as string[],
    kubectl: ns && ctl
      ? `kubectl -n ${ns} set resources ${kind}/${ctl} --requests=memory=${mBytes(recRam)}`
      : undefined,
    tone: 'cost_of_safety',
    rawEvidence: e,
  }
}
