import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import { useCluster } from '../state/cluster'
import { usePeriod } from '../state/period'
import { periodFromWindow, periodFromWindowISO, fmtMoney, fmtPercent } from '../lib/format'
import { Card } from '../components/UI/Card'
import { Skeleton } from '../components/UI/Skeleton'
import { KpiCard } from '../components/KpiCard'
import { useCurrency } from '../state/currency'
import { CoverageBadge } from '../components/CoverageBadge'
import { CostTrendChart } from '../components/Charts/CostTrendChart'
import { CostBreakdownChart } from '../components/Charts/CostBreakdownChart'
import { TopItemsBar } from '../components/Charts/TopItemsBar'
import { Wallet, Cpu, MemoryStick, TrendingDown } from 'lucide-react'

export default function Overview() {
  const { currentClusterId } = useCluster()
  const { period } = usePeriod()
  const { currency } = useCurrency()

  const allocPeriod = periodFromWindow(period)
  const billingPeriod = periodFromWindowISO(period)

  const totals = useApi(
    () => api.getAllocationsTotals(currentClusterId!, allocPeriod),
    [currentClusterId, period],
  )

  const billingSummary = useApi(
    () => api.getBillingSummary(currentClusterId!, billingPeriod),
    [currentClusterId, period],
  )

  const billingTs = useApi(
    () => api.getBillingTimeseries(currentClusterId!, { ...billingPeriod, granularity: 'daily', group_by: 'total' }),
    [currentClusterId, period],
  )

  const topNs = useApi(
    () => api.getAllocationsAggregated(currentClusterId!, { ...allocPeriod, group_by: 'namespace', top: 10 }),
    [currentClusterId, period],
  )

  const recs = useApi(
    () => api.listRecommendations(currentClusterId!, { status: ['open'], limit: 100 }),
    [currentClusterId],
  )

  if (!currentClusterId) {
    return <div className="p-6 text-sm text-[var(--color-muted)]">Выберите кластер</div>
  }

  const totalCost = billingSummary.data?.total_cost ?? totals.data?.breakdown.total ?? null
  const cpuEff = totals.data?.cpu_efficiency ?? null
  const ramEff = totals.data?.ram_efficiency ?? null
  const preemptShare = billingSummary.data?.preemptible_share ?? null

  // Считаем потенциальные savings из открытых рекомендаций (только impact_kind === 'saving')
  const totalSavings = recs.data?.items
  .filter(r => r.impact_kind === 'saving' && r.status === 'open')
  .reduce((sum, r) => sum + (parseFloat(r.monthly_impact_usd) || 0), 0) ?? 0
  const recsCount = recs.data?.items.length ?? 0

  return (
    <div className="p-6 flex flex-col gap-6 max-w-[1400px]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold">Обзор</h1>
          <p className="text-xs text-[var(--color-muted)] mt-0.5">
            Затраты и эффективность за {period === '7d' ? '7 дней' : period === '30d' ? '30 дней' : '90 дней'}
          </p>
        </div>
        {totals.data && <CoverageBadge coverage={totals.data.period} />}
      </div>

      {/* KPI Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <KpiCard
          label="Общие затраты"
          icon={<Wallet size={16} />}
          value={totalCost ? fmtMoney(totalCost, currency) : '—'}
          subtitle={preemptShare !== null && preemptShare > 0
            ? `${fmtPercent(preemptShare)} preemptible`
            : undefined}
          loading={billingSummary.loading && totals.loading}
        />
        <KpiCard
          label="CPU эффективность"
          icon={<Cpu size={16} />}
          value={cpuEff !== null ? fmtPercent(cpuEff) : '—'}
          accent={cpuEff !== null && cpuEff < 0.4 ? 'warning' : 'default'}
          trendLabel={cpuEff !== null && cpuEff < 0.4 ? 'низкая' : undefined}
          trend={cpuEff !== null && cpuEff < 0.4 ? 'down' : undefined}
          subtitle={cpuEff !== null ? `usage / requests` : undefined}
          loading={totals.loading}
        />
        <KpiCard
          label="RAM эффективность"
          icon={<MemoryStick size={16} />}
          value={ramEff !== null ? fmtPercent(ramEff) : '—'}
          accent={ramEff !== null && ramEff < 0.4 ? 'warning' : 'default'}
          trendLabel={ramEff !== null && ramEff < 0.4 ? 'низкая' : undefined}
          trend={ramEff !== null && ramEff < 0.4 ? 'down' : undefined}
          subtitle={ramEff !== null ? `usage / requests` : undefined}
          loading={totals.loading}
        />
        <KpiCard
          label="Потенциал экономии"
          icon={<TrendingDown size={16} />}
          value={totalSavings > 0 ? fmtMoney(totalSavings, currency) : '—'}
          accent="savings"
          subtitle={recsCount > 0 ? `${recsCount} рекомендаций` : undefined}
          loading={recs.loading}
        />
      </div>

      {/* Trend + Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card title="Динамика затрат" subtitle="По дням" className="lg:col-span-2">
          {billingTs.loading ? (
            <Skeleton className="h-[240px] w-full" />
          ) : billingTs.data && billingTs.data.points.length > 0 ? (
            <CostTrendChart points={billingTs.data.points} currency={billingTs.data.currency} />
          ) : (
            <div className="h-[240px] flex items-center justify-center text-sm text-[var(--color-muted)]">
              {billingTs.error ? 'Ошибка загрузки' : 'Нет данных биллинга. Запустите синхронизацию в Settings.'}
            </div>
          )}
        </Card>

        <Card title="Структура затрат" subtitle="По компонентам">
          {totals.loading ? (
            <div className="flex flex-col gap-2">
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-4 w-2/3" />
              <Skeleton className="h-4 w-1/2" />
            </div>
          ) : totals.data ? (
            <CostBreakdownChart breakdown={totals.data.breakdown} currency={currency} />
          ) : (
            <div className="text-sm text-[var(--color-muted)] py-8 text-center">Нет данных</div>
          )}
        </Card>
      </div>

      {/* Top namespaces */}
      <Card title="Топ namespace по затратам" subtitle="Top 10">
        {topNs.loading ? (
          <div className="flex flex-col gap-2">
            {[...Array(5)].map((_, i) => <Skeleton key={i} className="h-6 w-full" />)}
          </div>
        ) : topNs.data ? (
          <TopItemsBar items={topNs.data.items} currency={currency} />
        ) : (
          <div className="text-sm text-[var(--color-muted)] py-8 text-center">Нет данных</div>
        )}
      </Card>
    </div>
  )
}
