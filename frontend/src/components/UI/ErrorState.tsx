import { AlertCircle, RefreshCw } from 'lucide-react'

interface ErrorStateProps {
  message?: string
  onRetry?: () => void
}

export function ErrorState({ message = 'Ошибка загрузки данных', onRetry }: ErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-12 px-8">
      <div className="w-12 h-12 mb-4 flex items-center justify-center rounded-xl"
           style={{ background: 'var(--color-error-highlight)', color: 'var(--color-error)' }}>
        <AlertCircle size={24} />
      </div>
      <h3 className="font-semibold mb-1" style={{ color: 'var(--color-text)', fontFamily: 'var(--font-display)' }}>
        Что-то пошло не так
      </h3>
      <p className="text-sm max-w-sm mb-6" style={{ color: 'var(--color-text-muted)' }}>
        {message}
      </p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-150 hover:opacity-90 active:scale-95"
          style={{ background: 'var(--color-primary)', color: 'var(--color-text-inverse)' }}
        >
          <RefreshCw size={14} />
          Повторить
        </button>
      )}
    </div>
  )
}
