import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import { ErrorState } from '../components/UI/ErrorState'
import { EmptyState } from '../components/UI/EmptyState'
import { formatCurrency } from '../lib/utils'
import { Layers } from 'lucide-react'

interface NamespacesProps { window: string; refreshKey: number }

const COL_HEADERS = ['Неймспейс', 'CPU', 'RAM', 'PV', 'Сеть', 'Итого']

export function Namespaces({ window: w, refreshKey }: NamespacesProps) {
  const { data, loading, error, refetch } = useApi(
    () => api.getAllocations(w), [w, refreshKey]
  )

  if (error) return <div className="page-enter"><ErrorState message={error} onRetry={refetch} /></div>

  return (
    <div className="page-enter space-y-4">
      <div>
        <h1 className="font-bold text-xl"
            style={{ fontFamily: 'var(--font-display)', color: 'var(--color-text)' }}>
          Неймспейсы
        </h1>
        <p className="text-sm mt-1" style={{ color: 'var(--color-text-muted)' }}>
          Детализация расходов Kubernetes за период {w}
        </p>
      </div>

      <div className="rounded-xl border overflow-hidden"
           style={{
             background: 'var(--color-surface)',
             borderColor: 'oklch(from var(--color-text) l c h / 0.08)',
             boxShadow: 'var(--shadow-sm)',
           }}>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b"
                  style={{ borderColor: 'oklch(from var(--color-text) l c h / 0.07)' }}>
                {COL_HEADERS.map(h => (
                  <th key={h}
                      className="px-4 py-3 text-left font-medium"
                      style={{
                        color: 'var(--color-text-faint)',
                        fontSize: '10px',
                        letterSpacing: '0.08em',
                        textTransform: 'uppercase',
                      }}>
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {loading
                ? Array.from({ length: 6 }).map((_, i) => (
                    <tr key={i} className="border-b"
                        style={{ borderColor: 'oklch(from var(--color-text) l c h / 0.05)' }}>
                      {Array.from({ length: 6 }).map((_, j) => (
                        <td key={j} className="px-4 py-3.5">
                          <div className={`skeleton h-3 rounded ${j === 0 ? 'w-24' : 'w-14'}`} />
                        </td>
                      ))}
                    </tr>
                  ))
                : data?.items.length === 0
                  ? (
                    <tr>
                      <td colSpan={6}>
                        <EmptyState
                          icon={<Layers size={24} />}
                          title="Нет неймспейсов"
                          description="Данные OpenCost ещё не поступили."
                        />
                      </td>
                    </tr>
                  )
                  : data?.items.map((item) => (
                    <tr key={item.name}
                        className="transition-colors hover:bg-[var(--color-surface-offset)] border-b last:border-0"
                        style={{ borderColor: 'oklch(from var(--color-text) l c h / 0.05)' }}>
                      <td className="px-4 py-3">
                        <span
                          className="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium"
                          style={{
                            background: 'var(--color-surface-offset)',
                            color: 'var(--color-text)',
                            fontFamily: 'var(--font-mono)',
                          }}>
                          {item.name}
                        </span>
                      </td>
                      {[item.cpu_cost, item.ram_cost, item.pv_cost, item.network_cost, item.total_cost].map((v, idx) => (
                        <td key={idx}
                            className="px-4 py-3 tabular"
                            style={{
                              color: idx === 4 ? 'var(--color-text)' : 'var(--color-text-muted)',
                              fontWeight: idx === 4 ? 600 : 400,
                              textAlign: 'right',
                            }}>
                          {formatCurrency(v)}
                        </td>
                      ))}
                    </tr>
                  ))
              }
            </tbody>
          </table>
        </div>
        {data && (
          <div className="px-4 py-3 border-t flex items-center justify-between"
               style={{ borderColor: 'oklch(from var(--color-text) l c h / 0.07)', background: 'var(--color-surface-offset)' }}>
            <p className="text-xs" style={{ color: 'var(--color-text-faint)' }}>
              Всего неймспейсов: {data.count}
            </p>
            <p className="text-xs" style={{ color: 'var(--color-text-faint)' }}>
              Агрегация: {data.aggregate} · Период: {data.window}
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
