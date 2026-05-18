import { usePeriod, type Period } from '../state/period'
import { cn } from '../lib/utils'

const options: { value: Period; label: string }[] = [
  { value: '7d', label: '7 дней' },
  { value: '30d', label: '30 дней' },
  { value: '90d', label: '90 дней' },
]

export function PeriodPicker() {
  const { period, setPeriod } = usePeriod()
  return (
    <div className="inline-flex bg-[var(--color-card)] border border-[var(--color-border)] rounded-md p-0.5">
      {options.map(o => (
        <button
          key={o.value}
          onClick={() => setPeriod(o.value)}
          className={cn(
            'h-8 px-3 text-xs font-medium rounded transition-colors',
            period === o.value
              ? 'bg-[var(--color-text)] text-[var(--color-bg)]'
              : 'text-[var(--color-muted)] hover:text-[var(--color-text)]',
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}
