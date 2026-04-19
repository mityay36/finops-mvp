import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Layers, Lightbulb, Receipt, X } from 'lucide-react'
import { cn } from '../../lib/utils'

interface SidebarProps {
  open: boolean
  onClose: () => void
}

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'Обзор' },
  { to: '/namespaces', icon: Layers, label: 'Неймспейсы' },
  { to: '/recommendations', icon: Lightbulb, label: 'Рекомендации' },
  { to: '/billing', icon: Receipt, label: 'Биллинг YC' },
]

function FinOpsLogo() {
  return (
    <div className="flex items-center gap-2.5 px-5 py-5 border-b"
         style={{ borderColor: 'oklch(from var(--color-text) l c h / 0.07)' }}>
      <svg width="32" height="32" viewBox="0 0 32 32" fill="none" aria-label="FinOps Logo">
        <rect width="32" height="32" rx="8" fill="var(--color-primary)" />
        <path d="M8 10h10M8 16h7M8 22h10" stroke="var(--color-text-inverse)" strokeWidth="2" strokeLinecap="round"/>
        <circle cx="23" cy="22" r="4" stroke="var(--color-accent)" strokeWidth="1.5" fill="none"/>
        <path d="M23 20v2l1 1" stroke="var(--color-accent)" strokeWidth="1.5" strokeLinecap="round"/>
      </svg>
      <div>
        <p className="font-bold text-sm leading-none"
           style={{ fontFamily: 'var(--font-display)', color: 'var(--color-text)' }}>
          FinOps
        </p>
        <p className="text-xs leading-none mt-0.5"
           style={{ color: 'var(--color-text-faint)' }}>
          Yandex Cloud
        </p>
      </div>
    </div>
  )
}

export function Sidebar({ open, onClose }: SidebarProps) {
  return (
    <>
      {/* Overlay for mobile */}
      {open && (
        <div
          className="fixed inset-0 z-20 md:hidden"
          style={{ background: 'oklch(0.1 0 0 / 0.4)' }}
          onClick={onClose}
        />
      )}

      {/* Sidebar panel */}
      <aside
        className={cn(
          'fixed top-0 left-0 h-full z-30 flex flex-col transition-transform duration-300 ease-out',
          'w-56 border-r',
          'md:translate-x-0 md:static md:z-auto',
          open ? 'translate-x-0' : '-translate-x-full'
        )}
        style={{
          background: 'var(--color-surface)',
          borderColor: 'oklch(from var(--color-text) l c h / 0.07)',
          boxShadow: 'var(--shadow-lg)',
        }}
      >
        <FinOpsLogo />

        {/* Close btn mobile */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 md:hidden p-1.5 rounded-lg transition-colors"
          style={{ color: 'var(--color-text-muted)' }}
          aria-label="Закрыть меню"
        >
          <X size={16} />
        </button>

        <nav className="flex-1 p-3 space-y-0.5">
          <p className="px-3 pt-2 pb-1 text-xs font-medium uppercase tracking-widest"
             style={{ color: 'var(--color-text-faint)', letterSpacing: '0.1em', fontSize: '10px' }}>
            Навигация
          </p>
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              onClick={onClose}
              className={({ isActive }) => cn(
                'flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150',
                isActive
                  ? 'text-[var(--color-primary)]'
                  : 'text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-offset)]'
              )}
              style={({ isActive }) => isActive ? {
                background: 'var(--color-primary-subtle)',
              } : {}}
            >
              {({ isActive }) => (
                <>
                  <Icon
                    size={16}
                    strokeWidth={isActive ? 2.5 : 1.8}
                    className="flex-shrink-0"
                  />
                  {label}
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div className="p-4 border-t"
             style={{ borderColor: 'oklch(from var(--color-text) l c h / 0.07)' }}>
          <p className="text-xs" style={{ color: 'var(--color-text-faint)' }}>
            FinOps MVP v1.0
          </p>
        </div>
      </aside>
    </>
  )
}
