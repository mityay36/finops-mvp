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
  { label: '7д', value: '7d' },
  { label: '30д', value: '30d' },
  { label: '90д', value: '90d' },
]

export function TopBar({
  theme,
  onThemeToggle,
  onMenuToggle,
  window: selectedWindow,
  onWindowChange,
  onRefresh,
  title,
}: TopBarProps) {
  return (
    <header
      className="sticky top-0 z-10 flex items-center justify-between px-4 md:px-6 h-14 border-b"
      style={{
        background: 'var(--color-surface)',
        borderColor: 'oklch(from var(--color-text) l c h / 0.07)',
        backdropFilter: 'blur(8px)',
      }}
    >
      {/* Left: hamburger + title */}
      <div className="flex items-center gap-3">
        <button
          onClick={onMenuToggle}
          className="md:hidden p-2 rounded-lg transition-colors hover:bg-[var(--color-surface-offset)]"
          style={{ color: 'var(--color-text-muted)' }}
          aria-label="Открыть меню"
        >
          <Menu size={18} />
        </button>
        {title && (
          <h1 className="font-semibold text-base hidden md:block"
              style={{ fontFamily: 'var(--font-display)', color: 'var(--color-text)' }}>
            {title}
          </h1>
        )}
      </div>

      {/* Right: window selector + actions */}
      <div className="flex items-center gap-2">
        {/* Window selector */}
        <div className="flex items-center rounded-lg p-0.5 gap-0.5"
             style={{ background: 'var(--color-surface-offset)' }}>
          {WINDOWS.map(({ label, value }) => (
            <button
              key={value}
              onClick={() => onWindowChange(value)}
              className="px-3 py-1 rounded-md text-sm font-medium transition-all duration-150"
              style={{
                background: selectedWindow === value ? 'var(--color-surface-2)' : 'transparent',
                color: selectedWindow === value ? 'var(--color-text)' : 'var(--color-text-muted)',
                boxShadow: selectedWindow === value ? 'var(--shadow-sm)' : 'none',
                fontFamily: 'var(--font-body)',
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
            className="p-2 rounded-lg transition-all duration-150 hover:bg-[var(--color-surface-offset)] active:scale-95"
            style={{ color: 'var(--color-text-muted)' }}
            aria-label="Обновить данные"
          >
            <RefreshCw size={15} />
          </button>
        )}

        {/* Theme toggle */}
        <button
          onClick={onThemeToggle}
          className="p-2 rounded-lg transition-all duration-150 hover:bg-[var(--color-surface-offset)] active:scale-95"
          style={{ color: 'var(--color-text-muted)' }}
          aria-label={theme === 'dark' ? 'Светлая тема' : 'Тёмная тема'}
        >
          {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
        </button>
      </div>
    </header>
  )
}
