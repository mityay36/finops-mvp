import { fmtMoney, fmtPercent } from '../../lib/format'
import type { CostBreakdown } from '../../api/client'

interface Props { breakdown: CostBreakdown; currency: string }

const COMPONENTS: { key: keyof CostBreakdown; label: string; color: string }[] = [
  { key: 'cpu', label: 'CPU', color: 'var(--color-accent-info)' },
  { key: 'ram', label: 'RAM', color: 'var(--color-accent-savings)' },
  { key: 'gpu', label: 'GPU', color: 'var(--color-accent-warning)' },
  { key: 'pv', label: 'Storage (PV)', color: '#8B7355' },
  { key: 'network', label: 'Network', color: '#9B7BA8' },
  { key: 'load_balancer', label: 'Load Balancer', color: '#6B7A8F' },
  { key: 'shared', label: 'Shared', color: '#A89B8C' },
  { key: 'external', label: 'External', color: '#C68A3A' },
]

export function CostBreakdownChart({ breakdown, currency }: Props) {
  const total = parseFloat(breakdown.total) || 1
  const rows = COMPONENTS
    .map(c => ({ ...c, value: parseFloat(breakdown[c.key]) || 0 }))
    .filter(r => r.value > 0)
    .sort((a, b) => b.value - a.value)

  if (rows.length === 0) {
    return <div className="text-sm text-[var(--color-muted)] py-8 text-center">Нет данных</div>
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex h-2.5 rounded-full overflow-hidden bg-[var(--color-border)]/40">
        {rows.map(r => (
          <div
            key={r.key}
            style={{ width: `${(r.value / total) * 100}%`, background: r.color }}
            title={`${r.label}: ${fmtMoney(r.value, currency)}`}
          />
        ))}
      </div>
      <div className="flex flex-col gap-1.5">
        {rows.map(r => (
          <div key={r.key} className="flex items-center text-xs gap-2">
            <span className="w-2.5 h-2.5 rounded-sm shrink-0" style={{ background: r.color }} />
            <span className="flex-1 text-[var(--color-text)]">{r.label}</span>
            <span className="tabular text-[var(--color-muted)]">{fmtPercent(r.value / total)}</span>
            <span className="tabular font-medium w-24 text-right">{fmtMoney(r.value, currency)}</span>
          </div>
        ))}
      </div>
    </div>
  )
}
