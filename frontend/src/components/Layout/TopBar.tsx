import { Menu, Sun, Moon, RefreshCw } from 'lucide-react'

interface TopBarProps {
  theme: 'light' | 'dark'
  onThemeToggle: () => void
  onMenuToggle: () => void
  window: string
  onWindowChange: (w: string) => void
  onRefresh?: () => void
  title?: string
}

const WINDOWS = [
  { label: '7д',  value: '7d'  },
  { label: '30д', value: '30d' },
  { label: '90д', value: '90d' },
]

export function TopBar({
  theme, onThemeToggle, onMenuToggle,
  window: selectedWindow, onWindowChange, onRefresh, title,
}: TopBarProps) {
  return (
    <header
      className="sticky top-0 z-10 flex items-center justify-between px-4 md:px-5 h-12 border-b flex-shrink-0"
      style={{
        background: 'var(--color-surface)',
        borderColor: 'rgba(28,20,10,0.08)',
      }}
    >
      {/* Left */}
      <div className="flex items-center gap-2.5">
        <button
          onClick={onMenuToggle}
          className="md:hidden p-2 rounded-md transition-colors hover:bg-[var(--color-surface-offset)]"
          style={{ color: 'var(--color-text-muted)' }}
          aria-label="Открыть меню"
        >
          <Menu size={16} />
        </button>
        {title && (
          <span
            className="font-semibold text-sm hidden md:block"
            style={{ color: 'var(--color-text-muted)' }}
          >
            {title}
          </span>
        )}
      </div>

      {/* Right */}
      <div className="flex items-center gap-1.5">
        {/* Window selector */}
        <div
          className="flex items-center rounded-md p-0.5 gap-0.5"
          style={{ background: 'var(--color-surface-offset)' }}
        >
          {WINDOWS.map(({ label, value }) => (
            <button
              key={value}
              onClick={() => onWindowChange(value)}
              className="px-2.5 py-1 rounded-sm text-xs font-medium transition-all duration-150"
              style={{
                background: selectedWindow === value ? 'var(--color-surface-2)' : 'transparent',
                color: selectedWindow === value ? 'var(--color-text)' : 'var(--color-text-muted)',
                boxShadow: selectedWindow === value ? 'var(--shadow-sm)' : 'none',
              }}
            >
              {label}
            </button>
          ))}
        </div>

        {/* Refresh */}
        {onRefresh && (
          <button
            onClick={onRefresh}
            className="p-1.5 rounded-md transition-all hover:bg-[var(--color-surface-offset)] active:scale-95"
            style={{ color: 'var(--color-text-muted)' }}
            aria-label="Обновить"
          >
            <RefreshCw size={14} />
          </button>
        )}

        {/* Theme */}
        <button
          onClick={onThemeToggle}
          className="p-1.5 rounded-md transition-all hover:bg-[var(--color-surface-offset)] active:scale-95"
          style={{ color: 'var(--color-text-muted)' }}
          aria-label={theme === 'dark' ? 'Светлая тема' : 'Тёмная тема'}
        >
          {theme === 'dark' ? <Sun size={14} /> : <Moon size={14} />}
        </button>
      </div>
    </header>
  )
}
