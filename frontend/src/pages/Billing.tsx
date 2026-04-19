import { useState } from 'react'
import { motion } from 'framer-motion'
import { Receipt, Zap, BarChart2, List } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import { ErrorState } from '../components/UI/ErrorState'
import { EmptyState } from '../components/UI/EmptyState'
import { ServiceCostChart } from '../components/Charts/ServiceCostChart'
import { KPICard } from '../components/UI/KPICard'
import { formatCurrency } from '../lib/utils'

interface BillingProps { window: string; refreshKey: number }
type BillingTab = 'chart' | 'list'

interface ResourceItem {
  resource_name: string
  service_name: string
  cost: number
  is_preemptible?: boolean
}

function ResourceRow({ r, max, index }: { r: ResourceItem; max: number; index: number }) {
  const pct = max > 0 ? (r.cost / max) * 100 : 0

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: index * 0.02 }}
      className="px-5 py-3.5 border-b last:border-0 hover:bg-[var(--color-surface-offset)] transition-colors"
      style={{ borderColor: 'rgba(28,20,10,0.06)' }}
    >
      {/* Имя ресурса + цена */}
      <div className="flex items-start justify-between gap-4 mb-2">
        <p
          className="font-medium leading-snug"
          style={{ fontSize: '14px', color: 'var(--color-text)' }}
        >
          {r.resource_name}
        </p>
        <span
          className="font-semibold tabular flex-shrink-0"
          style={{ fontSize: '14px', color: 'var(--color-text)' }}
        >
          {formatCurrency(r.cost)}
        </span>
      </div>

      {/* Сервис + spot badge — с явным gap */}
      <div className="flex items-center gap-3 mb-2">
        <span style={{ fontSize: '12px', color: 'var(--color-text-faint)' }}>
          {r.service_name}
        </span>
        {r.is_preemptible && (
          <span
            className="px-2 py-0.5 rounded font-medium"
            style={{
              background: 'var(--color-success-highlight)',
              color: 'var(--color-success)',
              fontSize: '11px',
            }}
          >
            spot
          </span>
        )}
      </div>

      {/* Progress bar */}
      <div
        className="h-1 rounded-full overflow-hidden"
        style={{ background: 'var(--color-surface-offset)' }}
      >
        <motion.div
          className="h-full rounded-full"
          style={{ background: 'var(--color-primary)' }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ delay: index * 0.02 + 0.1, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        />
      </div>
    </motion.div>
  )
}

export function Billing({ window: w, refreshKey }: BillingProps) {
  const [activeTab, setActiveTab] = useState<BillingTab>('list')
  const days = w === '7d' ? 7 : w === '90d' ? 90 : 30

  const { data, loading, error, refetch } = useApi(
    () => api.getBilling(days), [days, refreshKey]
  )

  const serviceData = data
    ? Object.entries(data.by_service).map(([name, cost]) => ({ name, cost }))
    : []

  const maxCost = data?.top_resources?.length
    ? Math.max(...data.top_resources.map((r: ResourceItem) => r.cost))
    : 0

  if (error) return <div className="page-enter"><ErrorState message={error} onRetry={refetch} /></div>

  return (
    <div className="page-enter space-y-5">
      {/* Header */}
      <div>
        <h1 className="page-title" style={{ color: 'var(--color-text)' }}>Биллинг YC</h1>
        <p className="mt-1" style={{ fontSize: '13px', color: 'var(--color-text-muted)' }}>
          Фактические расходы из Yandex Cloud Billing за последние {days} дней
        </p>
      </div>

      {/* KPI cards */}
      <div className="grid grid-cols-2 gap-3">
        <KPICard
          label="Итого по YC"
          value={data ? formatCurrency(data.total) : '—'}
          numericValue={data?.total}
          prefix="₽ "
          animateValue={!!data}
          subtitle={`за ${days} дней`}
          icon={<Receipt size={20} strokeWidth={1.8} style={{ color: 'var(--color-accent)' }} />}
          iconBg="var(--color-accent-highlight)"
          loading={loading}
        />
        <KPICard
          label="Режим нод"
          value={data ? (data.has_preemptible_nodes ? 'Preemptible' : 'On-Demand') : '—'}
          subtitle={data?.has_preemptible_nodes ? 'скидка до 80%' : 'рекомендуем перейти'}
          icon={
            <Zap
              size={20}
              strokeWidth={1.8}
              style={{ color: data?.has_preemptible_nodes ? 'var(--color-success)' : 'var(--color-warning)' }}
            />
          }
          iconBg={
            data?.has_preemptible_nodes
              ? 'var(--color-success-highlight)'
              : 'var(--color-warning-highlight)'
          }
          loading={loading}
        />
      </div>

      {/* По сервисам */}
      <div
        className="rounded-lg border"
        style={{
          background: 'var(--color-surface)',
          borderColor: 'rgba(28,20,10,0.09)',
          boxShadow: 'var(--shadow-sm)',
        }}
      >
        <div className="px-5 py-3.5 border-b" style={{ borderColor: 'rgba(28,20,10,0.07)' }}>
          <h2 className="font-semibold" style={{ fontSize: '15px', color: 'var(--color-text)' }}>
            По сервисам
          </h2>
        </div>
        <div className="p-4">
          <ServiceCostChart data={serviceData} loading={loading} />
        </div>
      </div>

      {/* Топ ресурсов — без maxHeight, растягивается на всю страницу */}
      <div
        className="rounded-lg border"
        style={{
          background: 'var(--color-surface)',
          borderColor: 'rgba(28,20,10,0.09)',
          boxShadow: 'var(--shadow-sm)',
        }}
      >
        {/* Заголовок + переключатель */}
        <div
          className="px-5 py-3.5 border-b flex items-center justify-between gap-3"
          style={{ borderColor: 'rgba(28,20,10,0.07)' }}
        >
          <h2 className="font-semibold" style={{ fontSize: '15px', color: 'var(--color-text)' }}>
            Топ ресурсов
            {data && (
              <span className="ml-2 font-normal" style={{ fontSize: '13px', color: 'var(--color-text-faint)' }}>
                ({data.top_resources.length})
              </span>
            )}
          </h2>

          {/* Tab toggle */}
          <div
            className="flex items-center rounded-md p-0.5 gap-0.5"
            style={{ background: 'var(--color-surface-offset)' }}
          >
            {([
              { key: 'list' as BillingTab, icon: <List size={14} /> },
              { key: 'chart' as BillingTab, icon: <BarChart2 size={14} /> },
            ] as { key: BillingTab; icon: React.ReactNode }[]).map(({ key, icon }) => (
              <button
                key={key}
                onClick={() => setActiveTab(key)}
                className="px-2.5 py-1.5 rounded-sm transition-all"
                style={{
                  background: activeTab === key ? 'var(--color-surface-2)' : 'transparent',
                  color: activeTab === key ? 'var(--color-text)' : 'var(--color-text-faint)',
                  boxShadow: activeTab === key ? 'var(--shadow-sm)' : 'none',
                }}
                aria-label={key}
              >
                {icon}
              </button>
            ))}
          </div>
        </div>

        {/* Контент — полная высота, НЕТ maxHeight */}
        {loading ? (
          <div>
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="px-5 py-4 border-b last:border-0 space-y-2"
                   style={{ borderColor: 'rgba(28,20,10,0.06)' }}>
                <div className="flex justify-between gap-3">
                  <div className="skeleton h-4 rounded" style={{ width: '55%' }} />
                  <div className="skeleton h-4 rounded" style={{ width: '15%' }} />
                </div>
                <div className="flex items-center gap-3">
                  <div className="skeleton h-3 rounded" style={{ width: '30%' }} />
                  <div className="skeleton h-4 rounded-full" style={{ width: '32px' }} />
                </div>
                <div className="skeleton h-1 rounded-full" style={{ width: '65%' }} />
              </div>
            ))}
          </div>
        ) : data?.top_resources.length === 0 ? (
          <EmptyState
            icon={<Receipt size={24} />}
            title="Нет данных"
            description="Billing данные пока не поступали."
          />
        ) : activeTab === 'list' ? (
          <>
            {data?.top_resources.map((r: ResourceItem, i: number) => (
              <ResourceRow key={i} r={r} max={maxCost} index={i} />
            ))}
          </>
        ) : (
          <div className="p-4">
            <ServiceCostChart
              data={data?.top_resources.slice(0, 12).map((r: ResourceItem) => ({
                name: r.resource_name.split('/').pop() ?? r.resource_name,
                cost: r.cost,
              })) ?? []}
              loading={false}
            />
          </div>
        )}
      </div>
    </div>
  )
}
