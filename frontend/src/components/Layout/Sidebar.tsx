import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Layers, Lightbulb, Receipt, X } from 'lucide-react'
import { cn } from '../../lib/utils'

interface SidebarProps {
  open: boolean
  onClose: () => void
}

const navItems = [
  { to: '/',                icon: LayoutDashboard, label: 'Обзор' },
  { to: '/namespaces',      icon: Layers,          label: 'Неймспейсы' },
  { to: '/recommendations', icon: Lightbulb,       label: 'Рекомендации' },
  { to: '/billing',         icon: Receipt,         label: 'Биллинг YC' },
]

function FinOpsLogo() {
  return (
    <div
      className="flex items-center gap-3 px-4 py-5 border-b flex-shrink-0"
      style={{ borderColor: 'rgba(28,20,10,0.08)' }}
    >
      <svg width="34" height="34" viewBox="0 0 32 32" fill="none" aria-label="FinOps">
        <rect width="32" height="32" rx="7" fill="var(--color-primary)" />
        <path d="M8 10h10M8 16h7M8 22h10"
          stroke="var(--color-text-inverse)" strokeWidth="2" strokeLinecap="round" />
        <circle cx="23" cy="22" r="4"
          stroke="var(--color-accent)" strokeWidth="1.5" fill="none" />
        <path d="M23 20v2l1 1"
          stroke="var(--color-accent)" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
      <div className="min-w-0">
        <p className="font-bold leading-none truncate"
           style={{ fontSize: '15px', color: 'var(--color-text)' }}>
          FinOps
        </p>
        <p className="leading-none mt-1.5 truncate"
           style={{ fontSize: '12px', color: 'var(--color-text-faint)' }}>
          Yandex Cloud
        </p>
      </div>
    </div>
  )
}

export function Sidebar({ open, onClose }: SidebarProps) {
  return (
    <>
      {/* Mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 z-20 md:hidden"
          style={{ background: 'rgba(10,8,5,0.45)' }}
          onClick={onClose}
        />
      )}

      <aside
        className={cn(
          'fixed top-0 left-0 h-full z-30 flex flex-col transition-transform duration-300 ease-out',
          'w-56 border-r',
          'md:translate-x-0 md:static md:z-auto'
        , open ? 'translate-x-0' : '-translate-x-full')}
        style={{
          background: 'var(--color-surface)',
          borderColor: 'rgba(28,20,10,0.08)',
          boxShadow: 'var(--shadow-lg)',
        }}
      >
        <FinOpsLogo />

        {/* Close btn (mobile) */}
        <button
          onClick={onClose}
          className="absolute top-4 right-3 md:hidden p-1.5 rounded-md transition-colors hover:bg-[var(--color-surface-offset)]"
          style={{ color: 'var(--color-text-muted)' }}
          aria-label="Закрыть меню"
        >
          <X size={16} />
        </button>

        {/* Nav */}
        <nav className="flex-1 px-3 py-3 space-y-0.5 overflow-y-auto">
          <p
            className="px-3 pt-1 pb-2 font-medium uppercase"
            style={{ color: 'var(--color-text-faint)', fontSize: '11px', letterSpacing: '0.09em' }}
          >
            Навигация
          </p>

          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              onClick={onClose}
              /* no-underline обязательно */
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 px-3 py-2.5 rounded-lg font-medium transition-all duration-150',
                  'no-underline',   /* убираем подчёркивание */
                  isActive
                    ? 'text-[var(--color-primary)]'
                    : 'text-[var(--color-text-muted)] hover:text-[var(--color-text)] hover:bg-[var(--color-surface-offset)]'
                )
              }
              style={({ isActive }) =>
                isActive
                  ? { background: 'var(--color-primary-subtle)', textDecoration: 'none', fontSize: '15px' }
                  : { textDecoration: 'none', fontSize: '15px' }
              }
            >
              {({ isActive }) => (
                <>
                  <Icon size={18} strokeWidth={isActive ? 2.5 : 1.8} className="flex-shrink-0" />
                  <span className="truncate">{label}</span>
                </>
              )}
            </NavLink>
          ))}
        </nav>

        <div
          className="px-4 py-3.5 border-t flex-shrink-0"
          style={{ borderColor: 'rgba(28,20,10,0.07)', fontSize: '12px', color: 'var(--color-text-faint)' }}
        >
          FinOps MVP v1.0
        </div>
      </aside>
    </>
  )
}
