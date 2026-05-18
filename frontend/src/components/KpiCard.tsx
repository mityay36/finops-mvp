import { type ReactNode } from 'react'
import { Card } from './UI/Card'
import { Skeleton } from './UI/Skeleton'
import { cn } from '../lib/utils'

interface Props {
  label: string
  value: string
  subtitle?: string
  icon?: ReactNode
  loading?: boolean
  trend?: 'up' | 'down' | 'neutral'
  trendLabel?: string
  accent?: 'default' | 'savings' | 'warning' | 'critical'
}

const accentColor: Record<NonNullable<Props['accent']>, string> = {
  default: 'var(--color-text)',
  savings: 'var(--color-accent-savings)',
  warning: 'var(--color-accent-warning)',
  critical: 'var(--color-accent-critical)',
}

export function KpiCard({ label, value, subtitle, icon, loading, trend, trendLabel, accent = 'default' }: Props) {
  return (
    <Card padding>
      <div className="flex items-start justify-between mb-3">
        <span className="text-xs font-medium text-[var(--color-muted)] uppercase tracking-wide">
          {label}
        </span>
        {icon && <span className="text-[var(--color-muted)]">{icon}</span>}
      </div>
      {loading ? (
        <Skeleton className="h-8 w-32 mb-2" />
      ) : (
        <div
          className="text-2xl font-semibold tabular leading-tight"
          style={{ color: accentColor[accent] }}
        >
          {value}
        </div>
      )}
      {(subtitle || trendLabel) && (
        <div className="mt-1.5 flex items-center gap-1.5 text-xs">
          {trendLabel && (
            <span
              className={cn(
                'font-medium',
                trend === 'up' && 'text-[var(--color-accent-warning)]',
                trend === 'down' && 'text-[var(--color-accent-savings)]',
                trend === 'neutral' && 'text-[var(--color-muted)]',
              )}
            >
              {trendLabel}
            </span>
          )}
          {subtitle && <span className="text-[var(--color-muted)]">{subtitle}</span>}
        </div>
      )}
    </Card>
  )
}
