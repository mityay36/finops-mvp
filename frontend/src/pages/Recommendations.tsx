import { motion } from 'framer-motion'
import { Lightbulb } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import { ErrorState } from '../components/UI/ErrorState'
import { EmptyState } from '../components/UI/EmptyState'
import { Badge } from '../components/UI/Badge'
import { formatCurrency, getRiskColor, getRiskLabel, getActionLabel } from '../lib/utils'

interface RecommendationsProps { refreshKey: number }

export function Recommendations({ refreshKey }: RecommendationsProps) {
  const { data, loading, error, refetch } = useApi(
    () => api.getRecommendations(), [refreshKey]
  )

  if (error) return <div className="page-enter"><ErrorState message={error} onRetry={refetch} /></div>

  return (
    <div className="page-enter space-y-4">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="font-bold text-xl"
              style={{ fontFamily: 'var(--font-display)', color: 'var(--color-text)' }}>
            Рекомендации
          </h1>
          <p className="text-sm mt-1" style={{ color: 'var(--color-text-muted)' }}>
            Автоматические рекомендации по оптимизации расходов
          </p>
        </div>
        {data && data.estimated_monthly_saving > 0 && (
          <div className="rounded-lg px-4 py-2.5 border text-right"
               style={{
                 background: 'var(--color-success-highlight)',
                 borderColor: 'color-mix(in oklch, var(--color-success) 30%, transparent)',
               }}>
            <p className="text-xs" style={{ color: 'var(--color-success)' }}>Потенциальная экономия</p>
            <p className="font-bold tabular text-lg leading-tight"
               style={{ color: 'var(--color-success)', fontFamily: 'var(--font-display)' }}>
              {formatCurrency(data.estimated_monthly_saving)} / мес
            </p>
          </div>
        )}
      </div>

      <div className="space-y-3">
        {loading
          ? Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="rounded-xl p-5 border"
                   style={{
                     background: 'var(--color-surface)',
                     borderColor: 'oklch(from var(--color-text) l c h / 0.08)',
                     boxShadow: 'var(--shadow-sm)',
                   }}>
                <div className="space-y-2.5">
                  <div className="flex gap-2">
                    <div className="skeleton h-5 w-20 rounded-full" />
                    <div className="skeleton h-5 w-24 rounded-full" />
                  </div>
                  <div className="skeleton h-4 w-full rounded" />
                  <div className="skeleton h-3 w-2/3 rounded" />
                </div>
              </div>
            ))
          : data?.items.length === 0
            ? (
              <EmptyState
                icon={<Lightbulb size={24} />}
                title="Отличная работа!"
                description="Активных рекомендаций нет — все ресурсы используются эффективно."
              />
            )
            : data?.items.map((item, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04, duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
                className="rounded-xl p-5 border"
                style={{
                  background: 'var(--color-surface)',
                  borderColor: 'oklch(from var(--color-text) l c h / 0.08)',
                  boxShadow: 'var(--shadow-sm)',
                }}
              >
                <div className="flex items-start justify-between gap-4 flex-wrap">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap mb-2.5">
                      <span className="text-xs font-medium px-2 py-0.5 rounded-md"
                            style={{
                              background: 'var(--color-surface-offset)',
                              color: 'var(--color-text-muted)',
                              fontFamily: 'var(--font-mono)',
                            }}>
                        {item.resource}
                      </span>
                      <Badge variant={getRiskColor(item.risk) as 'success' | 'warning' | 'error'}>
                        {getRiskLabel(item.risk)} риск
                      </Badge>
                      <Badge variant="primary">{getActionLabel(item.action)}</Badge>
                    </div>
                    <p className="text-sm leading-relaxed" style={{ color: 'var(--color-text)' }}>
                      {item.description}
                    </p>
                    {item.notes && (
                      <p className="text-xs mt-2" style={{ color: 'var(--color-text-faint)' }}>
                        💡 {item.notes}
                      </p>
                    )}
                  </div>
                  {item.potential_saving != null && item.potential_saving > 0 && (
                    <div className="text-right flex-shrink-0 min-w-[100px]">
                      <p className="text-xs mb-0.5" style={{ color: 'var(--color-text-faint)' }}>Экономия</p>
                      <p className="font-bold tabular text-base"
                         style={{ color: 'var(--color-success)', fontFamily: 'var(--font-display)' }}>
                        {formatCurrency(item.potential_saving)}
                      </p>
                      <p className="text-xs" style={{ color: 'var(--color-text-faint)' }}>в месяц</p>
                    </div>
                  )}
                </div>
              </motion.div>
            ))
        }
      </div>
    </div>
  )
}
