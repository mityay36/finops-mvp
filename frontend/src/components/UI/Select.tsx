import { type SelectHTMLAttributes } from 'react'
import { cn } from '../../lib/utils'

interface Props extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
}

export function Select({ label, className, children, ...rest }: Props) {
  return (
    <label className="flex flex-col gap-1">
      {label && <span className="text-[11px] font-medium text-[var(--color-muted)] uppercase tracking-wide">{label}</span>}
      <select
        {...rest}
        className={cn(
          'h-9 px-3 pr-8 rounded-md text-sm bg-[var(--color-card)] border border-[var(--color-border)]',
          'focus:outline-none focus:border-[var(--color-text)]/40 cursor-pointer',
          className,
        )}
      >
        {children}
      </select>
    </label>
  )
}
