import { type ReactNode } from 'react'
import { cn } from '../../lib/utils'

type Tone = 'critical' | 'high' | 'medium' | 'low' | 'neutral' | 'savings' | 'success'

const tones: Record<Tone, string> = {
  critical: 'text-[var(--color-accent-critical)] border-[var(--color-accent-critical)]/30 bg-[var(--color-accent-critical)]/10',
  high: 'text-[var(--color-accent-warning)] border-[var(--color-accent-warning)]/30 bg-[var(--color-accent-warning)]/10',
  medium: 'text-[var(--color-accent-info)] border-[var(--color-accent-info)]/30 bg-[var(--color-accent-info)]/10',
  low: 'text-[var(--color-muted)] border-[var(--color-border)] bg-[var(--color-bg)]',
  neutral: 'text-[var(--color-muted)] border-[var(--color-border)] bg-[var(--color-bg)]',
  savings: 'text-[var(--color-accent-savings)] border-[var(--color-accent-savings)]/30 bg-[var(--color-accent-savings)]/10',
  success: 'text-[var(--color-accent-savings)] border-[var(--color-accent-savings)]/30 bg-[var(--color-accent-savings)]/10',
}

interface Props {
  tone?: Tone
  children: ReactNode
  className?: string
  dot?: boolean
}

export function Badge({ tone = 'neutral', children, className, dot }: Props) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[11px] font-medium border',
        tones[tone],
        className,
      )}
    >
      {dot && <span className="w-1.5 h-1.5 rounded-full bg-current" />}
      {children}
    </span>
  )
}