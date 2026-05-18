import { useState } from 'react'
import { useApi } from '../hooks/useApi'
import { api } from '../api/client'
import { useCluster } from '../state/cluster'
import { usePeriod } from '../state/period'
import { periodFromWindow, fmtMoney, fmtPercent } from '../lib/format'
import { Card } from '../components/UI/Card'
import { Skeleton } from '../components/UI/Skeleton'
import { Tabs } from '../components/Tabs'
import { CoverageBadge } from '../components/CoverageBadge'

type GroupBy = 'namespace' | 'controller' | 'node'

export default function Allocations() {
  const { currentClusterId } = useCluster()
  const { period } = usePeriod()
  const [groupBy, setGroupBy] = useState<GroupBy>('namespace')

  const allocPeriod = periodFromWindow(period)

  const result = useApi(
    () => api.getAllocationsAggregated(currentClusterId!, { ...allocPeriod, group_by: groupBy, top: 50 }),
    [currentClusterId, period, groupBy],
  )

  if (!currentClusterId) {
    return <div className="p-6 text-sm text-[var(--color-muted)]">Выберите кластер</div>
  }

  const items = result.data?.items ?? []
  const other = result.data?.other ?? null
  const clusterTotal = parseFloat(result.data?.cluster_total ?? '0') || 0

  return (
    <div className="p-6 flex flex-col gap-6 max-w-[1400px]">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Распределение затрат</h1>
          <p className="text-xs text-[var(--color-muted)] mt-0.5">
            Группировка по {groupBy === 'namespace' ? 'неймспейсам' : groupBy === 'controller' ? 'контроллерам' : 'нодам'}
          </p>
        </div>
        {result.data && <CoverageBadge coverage={result.data.period} />}
      </div>

      <div className="flex items-center gap-3">
        <Tabs<GroupBy>
          value={groupBy}
          onChange={setGroupBy}
          options={[
            { value: 'namespace', label: 'Namespace' },
            { value: 'controller', label: 'Controller' },
            { value: 'node', label: 'Node' },
          ]}
        />
        <div className="text-xs text-[var(--color-muted)]">
          Всего по кластеру: <span className="tabular font-medium text-[var(--color-text)]">{fmtMoney(clusterTotal, 'RUB')}</span>
        </div>
      </div>

      <Card padding={false}>
        {result.loading ? (
          <div className="flex flex-col gap-2 p-5">
            {[...Array(8)].map((_, i) => <Skeleton key={i} className="h-10 w-full" />)}
          </div>
        ) : result.error ? (
          <div className="p-10 text-center text-sm text-[var(--color-accent-critical)]">{result.error}</div>
        ) : items.length === 0 ? (
          <div className="p-10 text-center text-sm text-[var(--color-muted)]">Нет данных. Запустите allocations sync в Settings.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-[var(--color-muted)] uppercase tracking-wide">
                  <th className="text-left font-medium px-5 py-2.5">Имя</th>
                  <th className="text-right font-medium px-2 py-2.5">CPU</th>
                  <th className="text-right font-medium px-2 py-2.5">RAM</th>
                  <th className="text-right font-medium px-2 py-2.5">PV</th>
                  <th className="text-right font-medium px-2 py-2.5">Network</th>
                  <th className="text-right font-medium px-2 py-2.5">CPU eff</th>
                  <th className="text-right font-medium px-2 py-2.5">RAM eff</th>
                  <th className="text-right font-medium px-2 py-2.5">Доля</th>
                  <th className="text-right font-medium px-5 py-2.5">Всего</th>
                </tr>
              </thead>
              <tbody>
                {items.map(item => (
                  <Row key={item.key} item={item} clusterTotal={clusterTotal} />
                ))}
                {other && (
                  <tr className="border-t border-[var(--color-border)] bg-[var(--color-bg)]/40">
                    <td className="px-5 py-3 italic text-[var(--color-muted)]">Прочее</td>
                    <td className="px-2 py-3 text-right tabular text-[var(--color-muted)]">{fmtMoney(other.breakdown.cpu, 'RUB')}</td>
                    <td className="px-2 py-3 text-right tabular text-[var(--color-muted)]">{fmtMoney(other.breakdown.ram, 'RUB')}</td>
                    <td className="px-2 py-3 text-right tabular text-[var(--color-muted)]">{fmtMoney(other.breakdown.pv, 'RUB')}</td>
                    <td className="px-2 py-3 text-right tabular text-[var(--color-muted)]">{fmtMoney(other.breakdown.network, 'RUB')}</td>
                    <td className="px-2 py-3 text-right">—</td>
                    <td className="px-2 py-3 text-right">—</td>
                    <td className="px-2 py-3 text-right tabular text-[var(--color-muted)]">{fmtPercent(other.share_of_total)}</td>
                    <td className="px-5 py-3 text-right tabular font-medium">{fmtMoney(other.breakdown.total, 'RUB')}</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}

function Row({ item, clusterTotal: _clusterTotal }: { item: import('../api/client').AggregatedItem; clusterTotal: number }) {
  return (
    <tr className="border-t border-[var(--color-border)] hover:bg-[var(--color-bg)]/60">
      <td className="px-5 py-3 font-medium">{item.key}</td>
      <td className="px-2 py-3 text-right tabular">{fmtMoney(item.breakdown.cpu, 'RUB')}</td>
      <td className="px-2 py-3 text-right tabular">{fmtMoney(item.breakdown.ram, 'RUB')}</td>
      <td className="px-2 py-3 text-right tabular">{fmtMoney(item.breakdown.pv, 'RUB')}</td>
      <td className="px-2 py-3 text-right tabular">{fmtMoney(item.breakdown.network, 'RUB')}</td>
      <td className="px-2 py-3 text-right tabular">
        {item.cpu_efficiency !== null ? (
          <span style={{ color: item.cpu_efficiency < 0.4 ? 'var(--color-accent-warning)' : 'inherit' }}>
            {fmtPercent(item.cpu_efficiency)}
          </span>
        ) : '—'}
      </td>
      <td className="px-2 py-3 text-right tabular">
        {item.ram_efficiency !== null ? (
          <span style={{ color: item.ram_efficiency < 0.4 ? 'var(--color-accent-warning)' : 'inherit' }}>
            {fmtPercent(item.ram_efficiency)}
          </span>
        ) : '—'}
      </td>
      <td className="px-2 py-3 text-right tabular text-[var(--color-muted)]">{fmtPercent(item.share_of_total)}</td>
      <td className="px-5 py-3 text-right tabular font-semibold">{fmtMoney(item.breakdown.total, 'RUB')}</td>
    </tr>
  )
}
