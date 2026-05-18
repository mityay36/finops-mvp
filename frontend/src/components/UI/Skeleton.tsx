import { cn } from '../../lib/utils'

export function Skeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn('animate-pulse bg-[var(--color-border)]/60 rounded', className)}
    />
  )
}
