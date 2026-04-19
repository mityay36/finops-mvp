import { useState, useCallback } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { TopBar } from './TopBar'
import { useTheme } from '../../hooks/useTheme'

interface AppShellProps {
  window: string
  onWindowChange: (w: string) => void
  onRefresh: () => void
}

const PAGE_TITLES: Record<string, string> = {
  '/': 'Обзор',
  '/namespaces': 'Неймспейсы',
  '/recommendations': 'Рекомендации',
  '/billing': 'Биллинг YC',
}

export function AppShell({ window: w, onWindowChange, onRefresh }: AppShellProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { theme, toggle: toggleTheme } = useTheme()
  const location = useLocation()

  const handleMenuToggle = useCallback(() => setSidebarOpen(o => !o), [])
  const handleClose = useCallback(() => setSidebarOpen(false), [])

  return (
    <div className="flex h-screen overflow-hidden" style={{ background: 'var(--color-bg)' }}>
      <Sidebar open={sidebarOpen} onClose={handleClose} />

      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <TopBar
          theme={theme}
          onThemeToggle={toggleTheme}
          onMenuToggle={handleMenuToggle}
          window={w}
          onWindowChange={onWindowChange}
          onRefresh={onRefresh}
          title={PAGE_TITLES[location.pathname] ?? 'FinOps'}
        />
        <main className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
