import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Lightbulb, ChevronDown, TrendingDown } from 'lucide-react'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import { ErrorState } from '../components/UI/ErrorState'
import { EmptyState } from '../components/UI/EmptyState'
import { Badge } from '../components/UI/Badge'
import { formatCurrency, getRiskColor, getRiskLabel, getActionLabel } from '../lib/utils'

interface RecommendationsProps { refreshKey: number }

// Цвет левой полоски по риску
const RISK_ACCENT: Record<string, string> = {
  low:    'var(--color-success)',
  medium: 'var(--color-warning)',
  high:   'var(--color-error)',
}

interface RecItem {
  resource: string
  risk: string
  action: string
  description: string
  notes?: string
  potential_saving?: number | null
}

function RecCard({ item, index }: { item: RecItem; index: number }) {
  const [open, setOpen] = useState(false)
  const accent = RISK_ACCENT[item.risk] ?? 'var(--color-text-faint)'

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.04, duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
      className="rounded-lg border overflow-hidden"
      style={{
        background: 'var(--color-surface)',
        borderColor: 'rgba(28,20,10,0.09)',
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      {/* Кликабельный заголовок карточки */}
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full text-left flex items-center gap-0 focus:outline-none"
        aria-expanded={open}
      >
        {/* Цветная полоска слева по риску */}
        <div className="w-1 self-stretch flex-shrink-0 rounded-l-lg" style={{ background: accent }} />

        <div className="flex-1 flex items-center justify-between gap-3 px-4 py-3.5 hover:bg-[var(--color-surface-offset)] transition-colors">
          {/* Левая часть: ресурс + бейджи */}
          <div className="flex items-center gap-2.5 flex-wrap min-w-0">
            <span
              className="text-sm font-semibold tracking-tight truncate max-w-[220px]"
              style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-text)' }}
            >
              {item.resource}
            </span>
            <div className="flex items-center gap-1.5 flex-shrink-0">
              <Badge variant={getRiskColor(item.risk) as 'success' | 'warning' | 'error'}>
                {getRiskLabel(item.risk)}
              </Badge>
              <Badge variant="primary">{getActionLabel(item.action)}</Badge>
            </div>
          </div>

          {/* Правая часть: экономия + chevron */}
          <div className="flex items-center gap-3 flex-shrink-0">
            {item.potential_saving != null && item.potential_saving > 0 && (
              <div className="text-right hidden sm:block">
                <p className="text-xs" style={{ color: 'var(--color-text-faint)' }}>экономия</p>
                <p
                  className="text-sm font-bold tabular leading-tight"
                  style={{ color: 'var(--color-success)' }}
                >
                  {formatCurrency(item.potential_saving)}<span className="text-xs font-normal">/мес</span>
                </p>
              </div>
            )}
            <ChevronDown
              size={15}
              className="transition-transform duration-200 flex-shrink-0"
              style={{
                color: 'var(--color-text-faint)',
                transform: open ? 'rotate(180deg)' : 'rotate(0deg)',
              }}
            />
          </div>
        </div>
      </button>

      {/* Разворачиваемое тело */}
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
            style={{ overflow: 'hidden' }}
          >
            <div
              className="px-5 py-4 border-t space-y-3"
              style={{ borderColor: 'rgba(28,20,10,0.07)' }}
            >
              {/* Описание */}
              <p className="text-sm leading-relaxed" style={{ color: 'var(--color-text)' }}>
                {item.description}
              </p>

              {/* Заметка */}
              {item.notes && (
                <div
                  className="flex items-start gap-2 px-3 py-2.5 rounded-md text-xs leading-relaxed"
                  style={{
                    background: 'var(--color-surface-offset)',
                    color: 'var(--color-text-muted)',
                  }}
                >
                  <Lightbulb size={13} className="flex-shrink-0 mt-0.5" style={{ color: 'var(--color-warning)' }} />
                  <span>{item.notes}</span>
                </div>
              )}

              {/* Мобильная экономия */}
              {item.potential_saving != null && item.potential_saving > 0 && (
                <div className="flex items-center gap-1.5 sm:hidden">
                  <TrendingDown size={13} style={{ color: 'var(--color-success)' }} />
                  <span className="text-sm font-bold tabular" style={{ color: 'var(--color-success)' }}>
                    {formatCurrency(item.potential_saving)} / мес
                  </span>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export function Recommendations({ refreshKey }: RecommendationsProps) {
  const { data, loading, error, refetch } = useApi(
    () => api.getRecommendations(), [refreshKey]
  )

  if (error) return <div className="page-enter"><ErrorState message={error} onRetry={refetch} /></div>

  return (
    <div className="page-enter space-y-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h1 className="page-title" style={{ color: 'var(--color-text)' }}>Рекомендации</h1>
          <p className="mt-1 text-xs" style={{ color: 'var(--color-text-muted)' }}>
            Нажмите на карточку, чтобы увидеть детали
          </p>
        </div>

        {data && data.estimated_monthly_saving > 0 && (
          <div
            className="flex items-center gap-2.5 px-4 py-2.5 rounded-lg border"
            style={{
              background: 'var(--color-success-highlight)',
              borderColor: 'rgba(58,107,42,0.25)',
            }}
          >
            <TrendingDown size={16} style={{ color: 'var(--color-success)', flexShrink: 0 }} />
            <div>
              <p className="text-xs" style={{ color: 'var(--color-success)' }}>Потенциальная экономия</p>
              <p className="text-base font-bold tabular leading-tight" style={{ color: 'var(--color-success)' }}>
                {formatCurrency(data.estimated_monthly_saving)} / мес
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 text-xs" style={{ color: 'var(--color-text-faint)' }}>
        {[
          { color: 'var(--color-success)', label: 'Низкий риск' },
          { color: 'var(--color-warning)', label: 'Средний риск' },
          { color: 'var(--color-error)',   label: 'Высокий риск' },
        ].map(({ color, label }) => (
          <div key={label} className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 rounded-sm flex-shrink-0" style={{ background: color }} />
            <span>{label}</span>
          </div>
        ))}
      </div>

      {/* Cards */}
      <div className="space-y-2">
        {loading
          ? Array.from({ length: 5 }).map((_, i) => (
              <div
                key={i}
                className="rounded-lg border p-4"
                style={{
                  background: 'var(--color-surface)',
                  borderColor: 'rgba(28,20,10,0.09)',
                }}
              >
                <div className="flex items-center justify-between gap-3">
                  <div className="flex items-center gap-2.5">
                    <div className="skeleton h-4 rounded" style={{ width: 120 }} />
                    <div className="skeleton h-4 rounded-full" style={{ width: 64 }} />
                    <div className="skeleton h-4 rounded-full" style={{ width: 80 }} />
                  </div>
                  <div className="skeleton h-4 rounded" style={{ width: 80 }} />
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
              <RecCard key={i} item={item} index={i} />
            ))
        }
      </div>
    </div>
  )
}
