import { useMemo } from 'react'
import { useApi } from '../hooks/useApi'
import { api, type ServiceCostBreakdown } from '../api/client'
import { useCluster } from '../state/cluster'
import { useCurrency } from '../state/currency'
import { usePeriod } from '../state/period'
import { Card } from '../components/UI/Card'
import { KPICard } from '../components/UI/KPICard'
import { Skeleton } from '../components/UI/Skeleton'
import { Badge } from '../components/UI/Badge'
import { CostTrendChart } from '../components/Charts/CostTrendChart'
import { CoverageBadge } from '../components/CoverageBadge'
import { fmtMoney, fmtPercent, periodFromWindow, allocPeriodFromWindow } from '../lib/format'
import {
  Wallet, Cpu, MemoryStick, TrendingDown, ArrowDown, Layers, Building2, Boxes,
} from 'lucide-react'

export default function Overview() {
  const { currentClusterId } = useCluster()
  const { currency } = useCurrency()
  const { period } = usePeriod()

  const days = period === '7d' ? 7 : period === '90d' ? 90 : 30
  const billingPeriod = useMemo(() => periodFromWindow({ days }), [days])
  const allocPeriod = useMemo(() => allocPeriodFromWindow({ days }), [days])

  const billingSeries = useApi(
    () => api.getBillingTimeseries(currentClusterId!, { ...billingPeriod, granularity: 'daily', group_by: 'total' }),
    [currentClusterId, billingPeriod.period_start, billingPeriod.period_end],
  )

  const billingSummary = useApi(
    () => api.getBillingSummary(currentClusterId!, billingPeriod),
    [currentClusterId, billingPeriod.period_start, billingPeriod.period_end],
)

  const allocTotals = useApi(
    () => api.getAllocationsTotals(currentClusterId!, allocPeriod),
    [currentClusterId, allocPeriod.from, allocPeriod.to],
  )
  const allocByNs = useApi(
    () => api.getAllocationsAggregated(currentClusterId!, { ...allocPeriod, group_by: 'namespace', top: 10 }),
    [currentClusterId, allocPeriod.from, allocPeriod.to],
  )
  const recs = useApi(
    () => api.listRecommendations(currentClusterId!, { limit: 200, status: ['open'] }),
    [currentClusterId],
  )

  const billingTotal = parseFloat(billingSummary.data?.total_cost ?? '0') || 0
  const preemptibleShare = billingSummary.data?.preemptible_share ?? 0
  const allocTotal = parseFloat(allocTotals.data?.breakdown.total ?? '0') || 0

  const reconcile = useMemo(() => {
    if (!billingSummary.data || !allocTotals.data) return null
    const allocated = allocTotal
    const unallocated = Math.max(0, billingTotal - allocated)
    const allocatedShare = billingTotal > 0 ? allocated / billingTotal : 0
    return { allocated, unallocated, allocatedShare }
  }, [billingSummary.data, allocTotals.data, billingTotal, allocTotal])

  const totalSavings = useMemo(() => recs.data?.items
    .filter(r => r.impact_kind === 'saving')
    .reduce((s, r) => s + (parseFloat(r.monthly_impact_usd) || 0), 0) ?? 0, [recs.data])

  const cpuEff = allocTotals.data?.cpu_efficiency
  const ramEff = allocTotals.data?.ram_efficiency

  if (!currentClusterId) {
    return <div className="p-6 text-sm text-[var(--color-muted)]">Выберите кластер</div>
  }

  return (
    <div className="p-6 flex flex-col gap-8 max-w-[1400px]">
      {/* ==================== BLOCK 1: CLOUD BILL ==================== */}
      <section className="flex flex-col gap-4">
        <SectionHeader
          icon={<Building2 size={16} />}
          title="Облачные затраты"
          subtitle={`Yandex Cloud · ${billingSummary.data?.currency ?? currency} · из биллинга провайдера`}
          coverage={billingSummary.loading ? null : { period: undefined, fallback: `период: ${days} дн` }}
        />

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <KPICard
            label="Общие затраты"
            value={billingSummary.loading ? <Skeleton className="h-7 w-32" /> : fmtMoney(billingTotal, currency)}
            sublabel={billingSummary.data && `${fmtPercent(preemptibleShare)} preemptible`}
            icon={<Wallet size={16} />}
          />
          <KPICard
            label="Preemptible-экономия"
            value={billingSummary.loading
              ? <Skeleton className="h-7 w-32" />
              : fmtMoney(parseFloat(billingSummary.data?.preemptible_cost ?? '0') || 0, currency)}
            sublabel="фактическая стоимость прерываемых ресурсов"
            icon={<TrendingDown size={16} />}
            tone="savings"
          />
          <KPICard
            label="Потенциал экономии"
            value={recs.loading ? <Skeleton className="h-7 w-32" /> : fmtMoney(totalSavings, currency)}
            sublabel={`${recs.data?.items.length ?? 0} рекомендаций`}
            icon={<ArrowDown size={16} />}
            tone="savings"
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <Card title="Динамика затрат" subtitle="По дням, биллинг провайдера" className="lg:col-span-2">
            {billingSeries.loading
              ? <Skeleton className="h-[260px] w-full" />
              : <CostTrendChart points={billingSeries.data?.points ?? []} currency={currency} />}
          </Card>

          <Card title="Структура затрат" subtitle="По сервисам облака">
            {billingSummary.loading ? (
              <div className="flex flex-col gap-2">{[...Array(5)].map((_, i) => <Skeleton key={i} className="h-5 w-full" />)}</div>
            ) : (
              <ServicesList items={billingSummary.data?.by_service ?? []} currency={currency} />
            )}
          </Card>
        </div>
      </section>

      {/* ==================== BLOCK 2: RECONCILIATION ==================== */}
      <section>
        <Card padding={false}>
          <div className="p-5 border-b border-[var(--color-border)]">
            <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-[var(--color-muted)] mb-1">
              <Layers size={13} /> Сверка биллинга и кластера
            </div>
            <h2 className="text-base font-semibold">Что из облачных трат распределяется по кластеру</h2>
          </div>

          {(billingSummary.loading || allocTotals.loading) ? (
            <div className="p-5"><Skeleton className="h-20 w-full" /></div>
          ) : reconcile ? (
            <div className="p-5 flex flex-col gap-4">
              <ReconcileBar allocated={reconcile.allocated} unallocated={reconcile.unallocated} total={billingTotal} currency={currency} />

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <ReconcileItem
                  tone="allocated"
                  icon={<Boxes size={14} />}
                  label="Распределено по кластеру"
                  value={fmtMoney(reconcile.allocated, currency)}
                  share={reconcile.allocatedShare}
                  hint="Compute, PV, in-cluster network — то, что OpenCost разносит по namespace и pod'ам."
                />
                <ReconcileItem
                  tone="unallocated"
                  icon={<Building2 size={14} />}
                  label="Не привязано к подам"
                  value={fmtMoney(reconcile.unallocated, currency)}
                  share={1 - reconcile.allocatedShare}
                  hint="Control plane MK8s, Container Registry, VPC/NAT, KMS, Cloud DNS, Object Storage и прочая инфраструктура — невидима для OpenCost."
                />
              </div>

              <p className="text-xs text-[var(--color-muted)] leading-relaxed pt-1">
                OpenCost видит только потребление подов в Kubernetes. Сервисы вне кластера (managed control plane, реестр образов, VPC) учитываются провайдером отдельно — отсюда разница между биллингом и аллокацией. Это нормальное поведение, не баг.
              </p>
            </div>
          ) : (
            <div className="p-5 text-sm text-[var(--color-muted)]">Нет данных для сверки.</div>
          )}
        </Card>
      </section>

      {/* ==================== BLOCK 3: ALLOCATIONS ==================== */}
      <section className="flex flex-col gap-4">
        <SectionHeader
          icon={<Boxes size={16} />}
          title="Аллокация по кластеру"
          subtitle="OpenCost · что потребили поды в Kubernetes"
          coverage={allocTotals.data
            ? <CoverageBadge coverage={allocTotals.data.period} />
            : null}
        />

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <KPICard
            label="Затраты кластера"
            value={allocTotals.loading ? <Skeleton className="h-7 w-32" /> : fmtMoney(allocTotal, currency)}
            sublabel="за выбранный период"
            icon={<Boxes size={16} />}
          />
          <KPICard
            label="CPU эффективность"
            value={allocTotals.loading
              ? <Skeleton className="h-7 w-32" />
              : (cpuEff !== null && cpuEff !== undefined ? fmtPercent(cpuEff) : '—')}
            sublabel={cpuEff !== null && cpuEff !== undefined && cpuEff < 0.2 ? 'низкая usage / requests' : 'usage / requests'}
            icon={<Cpu size={16} />}
            tone={cpuEff !== null && cpuEff !== undefined && cpuEff < 0.2 ? 'warning' : undefined}
          />
          <KPICard
            label="RAM эффективность"
            value={allocTotals.loading
              ? <Skeleton className="h-7 w-32" />
              : (ramEff !== null && ramEff !== undefined ? fmtPercent(ramEff) : '—')}
            sublabel="usage / requests"
            icon={<MemoryStick size={16} />}
          />
        </div>

        <Card title="Топ namespace по затратам" subtitle="Top 10">
          {allocByNs.loading
            ? <div className="flex flex-col gap-2">{[...Array(7)].map((_, i) => <Skeleton key={i} className="h-6 w-full" />)}</div>
            : <NamespaceBars items={allocByNs.data?.items ?? []} currency={currency} />}
        </Card>
      </section>
    </div>
  )
}

// ==================== Subcomponents ====================

function SectionHeader({
  icon, title, subtitle, coverage,
}: { icon: React.ReactNode; title: string; subtitle: string; coverage?: React.ReactNode | { period: undefined; fallback: string } | null }) {
  const cov = coverage && typeof coverage === 'object' && 'fallback' in coverage
    ? <span className="text-xs text-[var(--color-muted)]">{coverage.fallback}</span>
    : coverage as React.ReactNode
  return (
    <div className="flex items-end justify-between gap-3 border-b border-[var(--color-border)] pb-2">
      <div>
        <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-[var(--color-muted)] mb-1">
          {icon} {title}
        </div>
        <div className="text-sm">{subtitle}</div>
      </div>
      {cov}
    </div>
  )
}

function ServicesList({ items, currency }: { items: ServiceCostBreakdown[]; currency: string }) {
  const visible = items.filter(i => parseFloat(i.cost) > 0)
  if (visible.length === 0) return <div className="text-sm text-[var(--color-muted)]">Нет данных</div>
  return (
    <div className="flex flex-col gap-2">
      {visible.map(s => (
        <div key={s.service_name} className="flex items-center gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex justify-between text-xs mb-1 gap-2">
              <span className="truncate">{s.service_name}</span>
              <span className="text-[var(--color-muted)]">{fmtPercent(s.share)}</span>
            </div>
            <div className="h-1.5 bg-[var(--color-bg)] rounded-full overflow-hidden">
              <div className="h-full bg-[var(--color-accent-primary)]" style={{ width: `${s.share * 100}%` }} />
            </div>
          </div>
          <span className="text-xs tabular w-20 text-right">{fmtMoney(parseFloat(s.cost), currency)}</span>
        </div>
      ))}
    </div>
  )
}

function ReconcileBar({
  allocated, unallocated, total, currency,
}: { allocated: number; unallocated: number; total: number; currency: string }) {
  if (total <= 0) return null
  const ap = (allocated / total) * 100
  return (
    <div>
      <div className="flex justify-between text-xs text-[var(--color-muted)] mb-1.5">
        <span>{fmtMoney(0, currency)}</span>
        <span>Всего {fmtMoney(total, currency)}</span>
      </div>
      <div className="h-3 rounded-full overflow-hidden flex bg-[var(--color-bg)]">
        <div style={{ width: `${ap}%`, backgroundColor: 'var(--color-accent-primary)' }} title={`Распределено: ${fmtMoney(allocated, currency)}`} />
        <div style={{ width: `${100 - ap}%`, backgroundColor: 'var(--color-border)' }} title={`Не привязано: ${fmtMoney(unallocated, currency)}`} />
      </div>
    </div>
  )
}

function ReconcileItem({
  tone, icon, label, value, share, hint,
}: { tone: 'allocated' | 'unallocated'; icon: React.ReactNode; label: string; value: string; share: number; hint: string }) {
  const color = tone === 'allocated'
  ? 'var(--color-accent-primary)'
  : 'var(--color-text)'
  return (
    <div className="border border-[var(--color-border)] rounded-md p-3.5 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-xs text-[var(--color-muted)]">
          <span style={{ color }}>{icon}</span>
          <span>{label}</span>
        </div>
        <Badge tone="neutral">{fmtPercent(share)}</Badge>
      </div>
      <div className="text-xl font-semibold tabular" style={{ color }}>{value}</div>c
      <p className="text-xs text-[var(--color-muted)] leading-relaxed">{hint}</p>
    </div>
  )
}

function NamespaceBars({
  items, currency,
}: { items: { key: string; breakdown: { total: string }; share_of_total: number }[]; currency: string }) {
  if (items.length === 0) return <div className="text-sm text-[var(--color-muted)]">Нет данных</div>
  const max = Math.max(...items.map(i => parseFloat(i.breakdown.total)))
  return (
    <div className="flex flex-col gap-2.5">
      {items.map(i => {
        const cost = parseFloat(i.breakdown.total)
        return (
          <div key={i.key} className="flex items-center gap-3">
            <div className="flex-1 min-w-0">
              <div className="flex justify-between text-sm mb-1 gap-2">
                <span className="truncate font-medium">{i.key}</span>
                <span className="text-xs text-[var(--color-muted)]">{fmtPercent(i.share_of_total)}</span>
              </div>
              <div className="h-1.5 bg-[var(--color-bg)] rounded-full overflow-hidden">
                <div className="h-full bg-[var(--color-accent-primary)]" style={{ width: `${(cost / max) * 100}%` }} />
              </div>
            </div>
            <span className="text-xs tabular w-24 text-right font-medium">{fmtMoney(cost, currency)}</span>
          </div>
        )
      })}
    </div>
  )
}
