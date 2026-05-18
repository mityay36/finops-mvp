import { Outlet } from 'react-router-dom'
import { Sidebar } from './Sidebar'
import { TopBar } from './TopBar'
import { useClusters } from '../../hooks/useClusters'
import { EmptyClusterState } from '../EmptyClusterState'
import { Loader2 } from 'lucide-react'

export function AppShell() {
  const { data, loading, error, refetch } = useClusters()

  return (
    <div className="min-h-screen flex bg-[var(--color-bg)] text-[var(--color-text)]">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <TopBar
          clusters={data?.items ?? []}
          onClustersChanged={refetch}
        />

        <main className="flex-1 flex flex-col">
          {loading && (
            <div className="flex-1 flex items-center justify-center">
              <Loader2 size={20} className="animate-spin text-[var(--color-muted)]" />
            </div>
          )}
          {!loading && error && (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <p className="text-sm text-[var(--color-accent-critical)] mb-2">
                  Не удалось загрузить кластеры
                </p>
                <p className="text-xs text-[var(--color-muted)]">{error}</p>
              </div>
            </div>
          )}
          {!loading && !error && data && data.items.length === 0 && (
            <EmptyClusterState onCreated={refetch} />
          )}
          {!loading && !error && data && data.items.length > 0 && <Outlet />}
        </main>
      </div>
    </div>
  )
}
