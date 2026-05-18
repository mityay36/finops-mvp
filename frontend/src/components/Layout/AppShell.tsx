import { Outlet, NavLink } from 'react-router-dom'

export function AppShell() {
  return (
    <div className="min-h-screen flex">
      <aside className="w-56 border-r border-[var(--color-border)] p-4">
        <h2 className="font-semibold mb-4">FinOps</h2>
        <nav className="flex flex-col gap-1 text-sm">
          <NavLink to="/" end className={({isActive}) => isActive ? 'font-semibold' : ''}>Overview</NavLink>
          <NavLink to="/namespaces" className={({isActive}) => isActive ? 'font-semibold' : ''}>Namespaces</NavLink>
          <NavLink to="/recommendations" className={({isActive}) => isActive ? 'font-semibold' : ''}>Recommendations</NavLink>
          <NavLink to="/billing" className={({isActive}) => isActive ? 'font-semibold' : ''}>Billing</NavLink>
        </nav>
      </aside>
      <main className="flex-1">
        <Outlet />
      </main>
    </div>
  )
}