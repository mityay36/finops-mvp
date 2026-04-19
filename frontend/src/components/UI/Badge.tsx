import { cn } from '../../lib/utils'

interface BadgeProps {
  variant?: 'default' | 'success' | 'warning' | 'error' | 'primary' | 'accent'
  size?: 'sm' | 'md'
  children: React.ReactNode
  className?: string
}

const variantStyles = {
  default: 'bg-[var(--color-surface-offset)] text-[var(--color-text-muted)]',
  success: 'bg-[var(--color-success-highlight)] text-[var(--color-success)]',
  warning: 'bg-[var(--color-warning-highlight)] text-[var(--color-warning)]',
  error: 'bg-[var(--color-error-highlight)] text-[var(--color-error)]',
  primary: 'bg-[var(--color-primary-highlight)] text-[var(--color-primary)]',
  accent: 'bg-[var(--color-accent-highlight)] text-[var(--color-accent)]',
}

export function Badge({ variant = 'default', size = 'sm', children, className }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center font-medium rounded-full tabular',
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm',
        variantStyles[variant],
        className
      )}
    >
      {children}
    </span>
  )
}
