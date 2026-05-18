import { type ReactNode } from 'react'
import { cn } from '../lib/utils'

interface Props<T extends string> {
  value: T
  onChange: (v: T) => void
  options: { value: T; label: string; icon?: ReactNode }[]
}

export function Tabs<T extends string>({ value, onChange, options }: Props<T>) {
  return (
    <div className="inline-flex bg-[var(--color-card)] border border-[var(--color-border)] rounded-md p-0.5">
      {options.map(o => (
        <button
          key={o.value}
          onClick={() => onChange(o.value)}
          className={cn(
            'h-8 px-3 text-xs font-medium rounded transition-colors inline-flex items-center gap-1.5',
            value === o.value
              ? 'bg-[var(--color-text)] text-[var(--color-bg)]'
              : 'text-[var(--color-muted)] hover:text-[var(--color-text)]',
          )}
        >
          {o.icon}
          {o.label}
        </button>
      ))}
    </div>
  )
}
