import { PackageOpen } from 'lucide-react'

interface EmptyStateProps {
  title?: string
  description?: string
  action?: React.ReactNode
  icon?: React.ReactNode
}

export function EmptyState({
  title = 'Нет данных',
  description = 'Данные ещё не загружены или отсутствуют.',
  action,
  icon,
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-16 px-8">
      <div className="w-12 h-12 mb-4 flex items-center justify-center rounded-xl"
           style={{ background: 'var(--color-surface-offset)', color: 'var(--color-text-faint)' }}>
        {icon ?? <PackageOpen size={24} />}
      </div>
      <h3 className="font-semibold mb-1" style={{ color: 'var(--color-text)', fontFamily: 'var(--font-display)' }}>
        {title}
      </h3>
      <p className="text-sm max-w-xs mb-6" style={{ color: 'var(--color-text-muted)' }}>
        {description}
      </p>
      {action}
    </div>
  )
}
