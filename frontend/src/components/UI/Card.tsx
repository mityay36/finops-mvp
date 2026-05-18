import { type ReactNode } from 'react'
import { cn } from '../../lib/utils'

interface Props {
  children: ReactNode
  className?: string
  title?: string
  subtitle?: string
  action?: ReactNode
  padding?: boolean
}

export function Card({ children, className, title, subtitle, action, padding = true }: Props) {
  return (
    <div
      className={cn(
        'bg-[var(--color-card)] border border-[var(--color-border)] rounded-lg',
        className,
      )}
    >
      {(title || action) && (
        <div className="flex items-start justify-between px-5 pt-4 pb-3">
          <div>
            {title && <h3 className="text-sm font-semibold">{title}</h3>}
            {subtitle && <p className="text-xs text-[var(--color-muted)] mt-0.5">{subtitle}</p>}
          </div>
          {action && <div>{action}</div>}
        </div>
      )}
      <div className={cn(padding && !title && 'p-5', padding && title && 'px-5 pb-5')}>
        {children}
      </div>
    </div>
  )
}
