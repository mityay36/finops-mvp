import { CheckCircle2, AlertTriangle, XCircle } from 'lucide-react'
import type { CoverageInfo } from '../api/client'

interface Props { coverage: CoverageInfo }

export function CoverageBadge({ coverage }: Props) {
  const ratio = coverage.completeness_ratio
  let icon, color, label
  if (ratio >= 0.95) {
    icon = <CheckCircle2 size={14} />
    color = 'var(--color-accent-savings)'
    label = 'Полные данные'
  } else if (ratio >= 0.7) {
    icon = <AlertTriangle size={14} />
    color = 'var(--color-accent-warning)'
    label = 'Неполные данные'
  } else {
    icon = <XCircle size={14} />
    color = 'var(--color-accent-critical)'
    label = 'Мало данных'
  }

  return (
    <div
      className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full border"
      style={{ color, borderColor: color, backgroundColor: `color-mix(in srgb, ${color} 8%, transparent)` }}
      title={`${coverage.days_with_data} из ${coverage.days_requested} дней`}
    >
      {icon}
      {label} · {coverage.days_with_data}/{coverage.days_requested} дн
    </div>
  )
}
