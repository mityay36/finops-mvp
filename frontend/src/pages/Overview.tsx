import { DollarSign, Layers, TrendingDown, Lightbulb } from 'lucide-react'
import { KPICard } from '../components/UI/KPICard'
import { NamespaceCostChart } from '../components/Charts/NamespaceCostChart'
import { ServiceCostChart } from '../components/Charts/ServiceCostChart'
import { ErrorState } from '../components/UI/ErrorState'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import { formatCurrency } from '../lib/utils'

interface OverviewProps { window: string; refreshKey: number }

export function Overview({ window: w, refreshKey }: OverviewProps) {
  const summary = useApi(() => api.getSummary(w), [w, refreshKey])
  const billing = useApi(() => api.getBilling(w === '7d' ? 7 : w === '90d' ? 90 : 30), [w, refreshKey])
  const recs    = useApi(() => api.getRecommendations(), [refreshKey])

  const serviceData = billing.data
    ? Object.entries(billing.data.by_service).map(([name, cost]) => ({ name, cost }))
    : []

  // Показываем данные только когда ОБА источника загружены.
  // Приоритет: summary (OpenCost). Если его нет — billing.total
  const bothLoaded   = !summary.loading && !billing.loading
  const totalCost    = bothLoaded
    ? (summary.data?.total_cost ?? billing.data?.total ?? null)
    : null
  const totalLoading = summary.loading || billing.loading

  return (
    <div className="page-enter space-y-5">
      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <KPICard
          label="Всего расходов"
          value={totalCost !== null ? formatCurrency(totalCost) : '—'}
          numericValue={totalCost ?? undefined}
          prefix="₽ "
          animateValue={totalCost !== null}
          subtitle="фактически за период"
          icon={<DollarSign size={20} strokeWidth={1.8} style={{ color: 'var(--color-primary)' }} />}
          iconBg="var(--color-primary-subtle)"
          loading={totalLoading}
        />
        <KPICard
          label="Неймспейсов"
          value={summary.data?.namespace_count ?? '—'}
          subtitle="активных"
          icon={<Layers size={20} strokeWidth={1.8} style={{ color: 'var(--color-accent)' }} />}
          iconBg="var(--color-accent-highlight)"
          loading={summary.loading}
        />
        <KPICard
          label="Потенциал экономии"
          value={recs.data ? formatCurrency(recs.data.estimated_monthly_saving) : '—'}
          numericValue={recs.data?.estimated_monthly_saving}
          prefix="₽ "
          animateValue={!!recs.data}
          subtitle="в месяц"
          icon={<TrendingDown size={20} strokeWidth={1.8} style={{ color: 'var(--color-success)' }} />}
          iconBg="var(--color-success-highlight)"
          loading={recs.loading}
        />
        <KPICard
          label="Рекомендации"
          value={recs.data?.count ?? '—'}
          subtitle="активных"
          icon={<Lightbulb size={20} strokeWidth={1.8} style={{ color: 'var(--color-warning)' }} />}
          iconBg="var(--color-warning-highlight)"
          loading={recs.loading}
        />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div
          className="rounded-lg border"
          style={{
            background: 'var(--color-surface)',
            borderColor: 'rgba(28,20,10,0.09)',
            boxShadow: 'var(--shadow-sm)',
          }}
        >
          <div className="px-5 pt-4 pb-2">
            <h2 className="font-semibold" style={{ fontSize: '15px', color: 'var(--color-text)' }}>
              Топ неймспейсов по затратам
            </h2>
            <p className="mt-0.5" style={{ fontSize: '12px', color: 'var(--color-text-faint)' }}>
              Распределение расходов OpenCost
            </p>
          </div>
          <div className="px-3 pb-4">
            {summary.error
              ? <ErrorState message={summary.error} onRetry={summary.refetch} />
              : (
                <NamespaceCostChart
                  data={summary.data?.top_namespaces.map(n => ({ name: n.namespace, total_cost: n.cost })) ?? []}
                  loading={summary.loading}
                />
              )
            }
          </div>
        </div>

        <div
          className="rounded-lg border"
          style={{
            background: 'var(--color-surface)',
            borderColor: 'rgba(28,20,10,0.09)',
            boxShadow: 'var(--shadow-sm)',
          }}
        >
          <div className="px-5 pt-4 pb-2">
            <h2 className="font-semibold" style={{ fontSize: '15px', color: 'var(--color-text)' }}>
              Фактические расходы YC
            </h2>
            <p className="mt-0.5" style={{ fontSize: '12px', color: 'var(--color-text-faint)' }}>
              Топ сервисов из Billing API
            </p>
          </div>
          <div className="px-3 pb-4">
            {billing.error
              ? <ErrorState message={billing.error} onRetry={billing.refetch} />
              : <ServiceCostChart data={serviceData} loading={billing.loading} />
            }
          </div>
        </div>
      </div>

      {/* Preemptible banner */}
      {billing.data?.has_preemptible_nodes && (
        <div
          className="flex items-center gap-2.5 px-4 py-3 rounded-lg border"
          style={{
            background: 'var(--color-success-highlight)',
            borderColor: 'rgba(58,107,42,0.25)',
            color: 'var(--color-success)',
            fontSize: '14px',
          }}
        >
          <span className="font-semibold">✓ Preemptible ноды активны</span>
          <span style={{ color: 'var(--color-text-muted)' }}>
            — стоимость вычислений снижена до 80%
          </span>
        </div>
      )}
    </div>
  )
}
