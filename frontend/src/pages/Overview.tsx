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
  const recs = useApi(() => api.getRecommendations(), [refreshKey])

  const serviceData = billing.data
    ? Object.entries(billing.data.by_service).map(([name, cost]) => ({ name, cost }))
    : []

  return (
    <div className="page-enter space-y-6">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <KPICard
          label="Всего расходов"
          value={summary.data ? formatCurrency(summary.data.total_cost) : '—'}
          numericValue={summary.data?.total_cost}
          prefix="₽ "
          animateValue={!!summary.data}
          subtitle="фактически за период"
          icon={<DollarSign size={18} strokeWidth={1.8} style={{ color: 'var(--color-primary)' }} />}
          iconBg="var(--color-primary-subtle)"
          loading={summary.loading}
        />
        <KPICard
          label="Неймспейсов"
          value={summary.data?.namespace_count ?? '—'}
          subtitle="активных"
          icon={<Layers size={18} strokeWidth={1.8} style={{ color: 'var(--color-accent)' }} />}
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
          icon={<TrendingDown size={18} strokeWidth={1.8} style={{ color: 'var(--color-success)' }} />}
          iconBg="var(--color-success-highlight)"
          loading={recs.loading}
        />
        <KPICard
          label="Рекомендации"
          value={recs.data?.count ?? '—'}
          subtitle="активных"
          icon={<Lightbulb size={18} strokeWidth={1.8} style={{ color: 'var(--color-warning)' }} />}
          iconBg="var(--color-warning-highlight)"
          loading={recs.loading}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="rounded-xl p-5 border"
             style={{ background: 'var(--color-surface)', borderColor: 'oklch(from var(--color-text) l c h / 0.08)', boxShadow: 'var(--shadow-sm)' }}>
          <div className="mb-4">
            <h2 className="font-semibold text-sm"
                style={{ fontFamily: 'var(--font-display)', color: 'var(--color-text)' }}>
              Топ неймспейсов по затратам
            </h2>
            <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-faint)' }}>
              Распределение расходов OpenCost
            </p>
          </div>
          {summary.error
            ? <ErrorState message={summary.error} onRetry={summary.refetch} />
            : <NamespaceCostChart
                data={summary.data?.top_namespaces.map(n => ({ name: n.namespace, total_cost: n.cost })) ?? []}
                loading={summary.loading}
              />
          }
        </div>

        <div className="rounded-xl p-5 border"
             style={{ background: 'var(--color-surface)', borderColor: 'oklch(from var(--color-text) l c h / 0.08)', boxShadow: 'var(--shadow-sm)' }}>
          <div className="mb-4">
            <h2 className="font-semibold text-sm"
                style={{ fontFamily: 'var(--font-display)', color: 'var(--color-text)' }}>
              Фактические расходы YC
            </h2>
            <p className="text-xs mt-0.5" style={{ color: 'var(--color-text-faint)' }}>
              Топ сервисов из Billing API
            </p>
          </div>
          {billing.error
            ? <ErrorState message={billing.error} onRetry={billing.refetch} />
            : <ServiceCostChart data={serviceData} loading={billing.loading} />
          }
        </div>
      </div>

      {billing.data?.has_preemptible_nodes && (
        <div className="flex items-center gap-2 px-4 py-3 rounded-lg border text-sm"
             style={{
               background: 'var(--color-success-highlight)',
               borderColor: 'color-mix(in oklch, var(--color-success) 30%, transparent)',
               color: 'var(--color-success)',
             }}>
          <span className="font-medium">✓ Preemptible ноды активны</span>
          <span style={{ color: 'var(--color-text-muted)' }}>— стоимость вычислений снижена до 80%</span>
        </div>
      )}
    </div>
  )
}
