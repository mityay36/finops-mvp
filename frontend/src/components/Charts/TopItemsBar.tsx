import type { AggregatedItem } from '../../api/client'
import { fmtMoney, fmtPercent } from '../../lib/format'

interface Props { items: AggregatedItem[]; currency: string; emptyLabel?: string }

export function TopItemsBar({ items, currency, emptyLabel = 'Нет данных' }: Props) {
  if (!items.length) {
    return <div className="text-sm text-[var(--color-muted)] py-8 text-center">{emptyLabel}</div>
  }
  const max = Math.max(...items.map(i => parseFloat(i.breakdown.total) || 0)) || 1

  return (
    <div className="flex flex-col gap-2">
      {items.map(item => {
        const total = parseFloat(item.breakdown.total) || 0
        const widthPct = (total / max) * 100
        return (
          <div key={item.key} className="grid grid-cols-[1fr_auto] gap-3 items-center text-xs">
            <div className="min-w-0">
              <div className="flex items-center justify-between mb-1">
                <span className="font-medium truncate" title={item.key}>{item.key}</span>
                <span className="tabular text-[var(--color-muted)] ml-2">{fmtPercent(item.share_of_total)}</span>
              </div>
              <div className="h-1.5 bg-[var(--color-border)]/50 rounded-full overflow-hidden">
                <div
                  className="h-full rounded-full transition-all"
                  style={{ width: `${widthPct}%`, background: 'var(--color-accent-info)' }}
                />
              </div>
            </div>
            <span className="tabular font-medium w-24 text-right">{fmtMoney(total, currency)}</span>
          </div>
        )
      })}
    </div>
  )
}
