import { NavLink } from 'react-router-dom'
import { LayoutDashboard, Layers, Lightbulb, Settings } from 'lucide-react'
import { cn } from '../../lib/utils'

const items = [
  { to: '/', label: 'Overview', icon: LayoutDashboard, end: true },
  { to: '/allocations', label: 'Allocations', icon: Layers },
  { to: '/recommendations', label: 'Recommendations', icon: Lightbulb },
  { to: '/settings', label: 'Settings', icon: Settings },
]

export function Sidebar() {
  return (
    <aside
      className="w-56 shrink-0 border-r border-[var(--color-border)] bg-[var(--color-card)] flex flex-col"
      style={{ height: '100vh', position: 'sticky', top: 0 }}
    >
      <div className="px-5 py-5 border-b border-[var(--color-border)]">
        <div className="text-base font-semibold tracking-tight">FinOps</div>
        <div className="text-xs text-[var(--color-muted)] mt-0.5">Cost intelligence</div>
      </div>

      <nav className="flex-1 px-2 py-3 flex flex-col gap-0.5">
        {items.map(({ to, label, icon: Icon, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors',
                isActive
                  ? 'bg-[var(--color-bg)] text-[var(--color-text)] font-medium'
                  : 'text-[var(--color-muted)] hover:bg-[var(--color-bg)] hover:text-[var(--color-text)]',
              )
            }
          >
            <Icon size={16} />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="px-5 py-3 border-t border-[var(--color-border)] text-xs text-[var(--color-muted)]">
        v2.0.0
      </div>
    </aside>
  )
}
