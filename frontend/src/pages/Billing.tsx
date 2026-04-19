import { motion } from 'framer-motion'
import { Receipt, Zap } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import { ErrorState } from '../components/UI/ErrorState'
import { EmptyState } from '../components/UI/EmptyState'
import { ServiceCostChart } from '../components/Charts/ServiceCostChart'
import { KPICard } from '../components/UI/KPICard'
import { formatCurrency } from '../lib/utils'

interface BillingProps { window: string; refreshKey: number }

export function Billing({ window: w, refreshKey }: BillingProps) {
  const days = w === '7d' ? 7 : w === '90d' ? 90 : 30
  const { data, loading, error, refetch } = useApi(
    () => api.getBilling(days), [days, refreshKey]
  )

  const serviceData = data
    ? Object.entries(data.by_service).map(([name, cost]) => ({ name, cost }))
    : []

  if (error) return <div className="page-enter"><ErrorState message={error} onRetry={refetch} /></div>

  return (
    <div className="page-enter space-y-5">
      <div>
        <h1 className="font-bold text-xl"
            style={{ fontFamily: 'var(--font-display)', color: 'var(--color-text)' }}>
          Биллинг YC
        </h1>
        <p className="text-sm mt-1" style={{ color: 'var(--color-text-muted)' }}>
          Фактические расходы из Yandex Cloud Billing за последние {days} дней
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <KPICard
          label="Итого по YC"
          value={data ? formatCurrency(data.total) : '—'}
          numericValue={data?.total}
          prefix="₽ "
          animateValue={!!data}
          subtitle={`за ${days} дней`}
          icon={<Receipt size={18} strokeWidth={1.8} style={{ color: 'var(--color-accent)' }} />}
          iconBg="var(--color-accent-highlight)"
          loading={loading}
        />
        <KPICard
          label="Режим нод"
          value={data ? (data.has_preemptible_nodes ? 'Preemptible' : 'On-Demand') : '—'}
          subtitle={data?.has_preemptible_nodes ? 'скидка до 80%' : 'рекомендуем перейти'}
          icon={
            <Zap
              size={18}
              strokeWidth={1.8}
              style={{ color: data?.has_preemptible_nodes ? 'var(--color-success)' : 'var(--color-warning)' }}
            />
          }
          iconBg={data?.has_preemptible_nodes ? 'var(--color-success-highlight)' : 'var(--color-warning-highlight)'}
          loading={loading}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="rounded-xl p-5 border"
             style={{
               background: 'var(--color-surface)',
               borderColor: 'oklch(from var(--color-text) l c h / 0.08)',
               boxShadow: 'var(--shadow-sm)',
             }}>
          <h2 className="font-semibold text-sm mb-4"
              style={{ fontFamily: 'var(--font-display)', color: 'var(--color-text)' }}>
            По сервисам
          </h2>
          <ServiceCostChart data={serviceData} loading={loading} />
        </div>

        <div className="rounded-xl border overflow-hidden"
             style={{
               background: 'var(--color-surface)',
               borderColor: 'oklch(from var(--color-text) l c h / 0.08)',
               boxShadow: 'var(--shadow-sm)',
             }}>
          <div className="px-5 py-4 border-b"
               style={{ borderColor: 'oklch(from var(--color-text) l c h / 0.07)' }}>
            <h2 className="font-semibold text-sm"
                style={{ fontFamily: 'var(--font-display)', color: 'var(--color-text)' }}>
              Топ ресурсов
            </h2>
          </div>
          <div>
            {loading
              ? Array.from({ length: 6 }).map((_, i) => (
                  <div key={i}
                       className="px-5 py-3 flex items-center justify-between gap-3 border-b last:border-0"
                       style={{ borderColor: 'oklch(from var(--color-text) l c h / 0.05)' }}>
                    <div className="flex-1 space-y-1.5">
                      <div className="skeleton h-3 w-40 rounded" />
                      <div className="skeleton h-2.5 w-24 rounded" />
                    </div>
                    <div className="skeleton h-3 w-16 rounded" />
                  </div>
                ))
              : data?.top_resources.length === 0
                ? (
                  <EmptyState
                    icon={<Receipt size={24} />}
                    title="Нет данных"
                    description="Billing данные пока не поступали."
                  />
                )
                : data?.top_resources.map((r, i) => (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      transition={{ delay: i * 0.03 }}
                      className="px-5 py-3 flex items-center justify-between gap-3 border-b last:border-0 transition-colors hover:bg-[var(--color-surface-offset)]"
                      style={{ borderColor: 'oklch(from var(--color-text) l c h / 0.05)' }}
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-sm truncate" style={{ color: 'var(--color-text)' }}>
                          {r.resource_name}
                        </p>
                        <div className="flex items-center gap-1.5 mt-0.5">
                          <span className="text-xs" style={{ color: 'var(--color-text-faint)' }}>
                            {r.service_name}
                          </span>
                          {r.is_preemptible && (
                            <span className="text-xs px-1.5 py-0.5 rounded-full"
                                  style={{
                                    background: 'var(--color-success-highlight)',
                                    color: 'var(--color-success)',
                                    fontSize: '10px',
                                  }}>
                              spot
                            </span>
                          )}
                        </div>
                      </div>
                      <span className="font-semibold tabular text-sm flex-shrink-0"
                            style={{ color: 'var(--color-text)' }}>
                        {formatCurrency(r.cost)}
                      </span>
                    </motion.div>
                  ))
            }
          </div>
        </div>
      </div>
    </div>
  )
}
