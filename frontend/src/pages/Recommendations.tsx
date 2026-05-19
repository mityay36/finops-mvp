import { useState, useMemo } from 'react'
import { useApi } from '../hooks/useApi'
import { api, ApiError, type RecSeverity, type RecStatus } from '../api/client'
import { useCluster } from '../state/cluster'
import { useCurrency } from '../state/currency'
import { Card } from '../components/UI/Card'
import { Button } from '../components/UI/Button'
import { Select } from '../components/UI/Select'
import { Skeleton } from '../components/UI/Skeleton'
import { SeverityBadge, severityOrder } from '../components/recommendations/SeverityBadge'
import { StatusBadge } from '../components/recommendations/StatusBadge'
import { RecommendationDrawer } from '../components/recommendations/RecommendationDrawer'
import { ruleLabel } from '../lib/recommendations'
import { fmtMoney, fmtRelative } from '../lib/format'
import { RefreshCw, Lightbulb, ChevronRight } from 'lucide-react'

const SEVERITIES: RecSeverity[] = ['critical', 'warning', 'info']
const STATUSES: RecStatus[] = ['open', 'applied', 'dismissed', 'closed_resolved']

export default function Recommendations() {
  const { currentClusterId } = useCluster()
  const { currency } = useCurrency()
  const [severity, setSeverity] = useState<'all' | RecSeverity>('all')
  const [status, setStatus] = useState<'all' | RecStatus>('open')
  const [refreshKey, setRefreshKey] = useState(0)
  const [drawerId, setDrawerId] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState(false)
  const [refreshError, setRefreshError] = useState<string | null>(null)
  const [refreshNotice, setRefreshNotice] = useState<string | null>(null)

  const list = useApi(
    () => api.listRecommendations(currentClusterId!, {
      limit: 200,
      status: status === 'all' ? undefined : [status],
      severity: severity === 'all' ? undefined : [severity],
    }),
    [currentClusterId, severity, status, refreshKey],
  )

  const items = list.data?.items ?? []

  const aggregateSavings = useMemo(() => items
    .filter(i => i.impact_kind === 'saving' && i.status === 'open')
    .reduce((sum, i) => sum + (parseFloat(i.monthly_impact_usd) || 0), 0), [items])

  const openCount = useMemo(() => items.filter(i => i.status === 'open').length, [items])

  const sorted = useMemo(() => {
    return [...items].sort((a, b) => {
      const s = severityOrder[a.severity] - severityOrder[b.severity]
      if (s !== 0) return s
      return (parseFloat(b.monthly_impact_usd) || 0) - (parseFloat(a.monthly_impact_usd) || 0)
    })
  }, [items])

  const triggerRefresh = async () => {
    if (!currentClusterId) return
    setRefreshing(true); setRefreshError(null); setRefreshNotice(null)
    try {
      const r = await api.refreshRecommendations(currentClusterId)
      setRefreshNotice(r.message)
      // Подождём, пока движок успеет обновить — list endpoint потом перезапросим.
      setTimeout(() => {
        setRefreshKey(k => k + 1)
        setRefreshing(false)
        setTimeout(() => setRefreshNotice(null), 4000)
      }, 2500)
    } catch (e) {
      setRefreshError(e instanceof ApiError ? `Ошибка ${e.status}: ${e.statusText}` : 'Ошибка')
      setRefreshing(false)
    }
  }

  if (!currentClusterId) {
    return <div className="p-6 text-sm text-[var(--color-muted)]">Выберите кластер</div>
  }

  return (
    <div className="p-6 flex flex-col gap-6 max-w-[1400px]">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-xl font-semibold">Рекомендации</h1>
          <p className="text-xs text-[var(--color-muted)] mt-0.5">
            Открытых: {openCount} · Потенциал экономии:{' '}
            <span className="font-medium text-[var(--color-accent-savings)]">
              {fmtMoney(aggregateSavings, currency)} / мес
            </span>
          </p>
        </div>
        <Button
          variant="secondary"
          leftIcon={<RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />}
          onClick={triggerRefresh}
          disabled={refreshing}
        >
          {refreshing ? 'Пересчёт...' : 'Пересчитать'}
        </Button>
      </div>

      {refreshError && (
        <div className="text-xs text-[var(--color-accent-critical)] border border-[var(--color-accent-critical)]/30 bg-[var(--color-accent-critical)]/10 rounded px-3 py-2">
          {refreshError}
        </div>
      )}
      {refreshNotice && !refreshError && (
        <div className="text-xs text-[var(--color-accent-savings)] border border-[var(--color-accent-savings)]/30 bg-[var(--color-accent-savings)]/10 rounded px-3 py-2">
          {refreshNotice}
        </div>
      )}

      <div className="flex items-end gap-3">
        <Select label="Severity" value={severity} onChange={e => setSeverity(e.target.value as 'all' | RecSeverity)}>
          <option value="all">Все</option>
          {SEVERITIES.map(s => <option key={s} value={s}>{s}</option>)}
        </Select>
        <Select label="Status" value={status} onChange={e => setStatus(e.target.value as 'all' | RecStatus)}>
          <option value="all">Все</option>
          {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
        </Select>
      </div>

      <Card padding={false}>
        {list.loading ? (
          <div className="flex flex-col gap-2 p-5">
            {[...Array(6)].map((_, i) => <Skeleton key={i} className="h-12 w-full" />)}
          </div>
        ) : list.error ? (
          <div className="p-10 text-center text-sm text-[var(--color-accent-critical)]">Ошибка: {list.error}</div>
        ) : sorted.length === 0 ? (
          <div className="py-16 text-center">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-[var(--color-bg)] mb-3">
              <Lightbulb size={20} className="text-[var(--color-muted)]" />
            </div>
            <p className="text-sm font-medium mb-1">Рекомендаций нет</p>
            <p className="text-xs text-[var(--color-muted)]">Попробуйте изменить фильтры или нажмите «Пересчитать».</p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-[var(--color-muted)] uppercase tracking-wide">
                  <th className="text-left font-medium px-5 py-2.5">Severity</th>
                  <th className="text-left font-medium px-2 py-2.5">Status</th>
                  <th className="text-left font-medium px-2 py-2.5">Rule</th>
                  <th className="text-left font-medium px-2 py-2.5">Target</th>
                  <th className="text-right font-medium px-2 py-2.5">Impact / mo</th>
                  <th className="text-left font-medium px-2 py-2.5">Last seen</th>
                  <th className="px-3 py-2.5"></th>
                </tr>
              </thead>
              <tbody>
                {sorted.map(item => (
                  <tr
                    key={item.id}
                    className="border-t border-[var(--color-border)] hover:bg-[var(--color-bg)]/60 cursor-pointer transition-colors"
                    onClick={() => setDrawerId(item.id)}
                  >
                    <td className="px-5 py-3"><SeverityBadge severity={item.severity} /></td>
                    <td className="px-2 py-3"><StatusBadge status={item.status} /></td>
                    <td className="px-2 py-3 max-w-md">
                      <div className="font-medium truncate">{ruleLabel(item.rule_id)}</div>
                      <div className="text-xs text-[var(--color-muted)] font-mono">{item.rule_id}</div>
                    </td>
                    <td className="px-2 py-3 text-xs">
                      <span className="text-[var(--color-muted)]">{item.target_kind}</span>
                      {item.target_namespace && <> · {item.target_namespace}</>}
                      {item.target_controller && <> / <span className="font-medium">{item.target_controller}</span></>}
                    </td>
                    <td
                      className="px-2 py-3 text-right tabular font-medium"
                      style={{
                        color: item.impact_kind === 'saving'
                          ? 'var(--color-accent-savings)'
                          : 'var(--color-accent-warning)',
                      }}
                    >
                      {item.impact_kind === 'saving' ? '−' : '+'}{fmtMoney(Math.abs(parseFloat(item.monthly_impact_usd) || 0), currency)}
                    </td>
                    <td className="px-2 py-3 text-xs text-[var(--color-muted)]">{fmtRelative(item.last_seen_at)}</td>
                    <td className="px-3 py-3"><ChevronRight size={14} className="text-[var(--color-muted)]" /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <RecommendationDrawer
        open={drawerId !== null}
        clusterId={currentClusterId}
        recId={drawerId}
        onClose={() => setDrawerId(null)}
        onChanged={() => setRefreshKey(k => k + 1)}
      />
    </div>
  )
}