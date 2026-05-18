import { type InputHTMLAttributes, type ReactNode } from 'react'
import { cn } from '../../lib/utils'

interface Props extends InputHTMLAttributes<HTMLInputElement> {
  label: string
  hint?: string
  error?: string | null
  rightSlot?: ReactNode
}

export function Field({ label, hint, error, rightSlot, className, ...rest }: Props) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-xs font-medium text-[var(--color-muted)]">{label}</span>
      <div className="relative">
        <input
          {...rest}
          className={cn(
            'w-full h-10 px-3 rounded-md text-sm',
            'bg-[var(--color-card)] border border-[var(--color-border)]',
            'focus:outline-none focus:border-[var(--color-text)]/40',
            'placeholder:text-[var(--color-muted)]',
            error && 'border-[var(--color-accent-critical)]',
            rightSlot && 'pr-10',
            className,
          )}
        />
        {rightSlot && (
          <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center">
            {rightSlot}
          </div>
        )}
      </div>
      {error && <span className="text-xs text-[var(--color-accent-critical)]">{error}</span>}
      {!error && hint && <span className="text-xs text-[var(--color-muted)]">{hint}</span>}
    </label>
  )
}
