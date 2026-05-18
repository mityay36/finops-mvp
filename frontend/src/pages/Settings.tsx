import { useState, useEffect } from 'react'
import { useApi } from '../hooks/useApi'
import { api, ApiError, type CredentialMaskedRead, type ProviderRead } from '../api/client'
import { useCluster } from '../state/cluster'
import { Card } from '../components/UI/Card'
import { Button } from '../components/UI/Button'
import { Field } from '../components/UI/Field'
import { Skeleton } from '../components/UI/Skeleton'
import { Badge } from '../components/UI/Badge'
import { fmtRelative, fmtDate } from '../lib/format'
import { Play, Database, Activity, AlertCircle, CheckCircle2 } from 'lucide-react'

export default function Settings() {
  const { currentClusterId } = useCluster()

  if (!currentClusterId) {
    return <div className="p-6 text-sm text-[var(--color-muted)]">Выберите кластер</div>
  }

  return <SettingsContent clusterId={currentClusterId} />
}

function SettingsContent({ clusterId }: { clusterId: string }) {
  const cluster = useApi(() => api.getCluster(clusterId), [clusterId])
  const providers = useApi(() => api.listProviders(), [])
  const credentials = useApi(() => api.listCredentials(clusterId), [clusterId])
  const [refreshKey, setRefreshKey] = useState(0)

  const billingRun = useApi(() => api.getLatestBillingSync(clusterId).catch(() => null), [clusterId, refreshKey])
  const allocRun = useApi(() => api.getLatestAllocationsSync(clusterId).catch(() => null), [clusterId, refreshKey])

  return (
    <div className="p-6 flex flex-col gap-6 max-w-[1100px]">
      <div>
        <h1 className="text-xl font-semibold">Настройки кластера</h1>
        {cluster.data && (
          <p className="text-xs text-[var(--color-muted)] mt-0.5">
            {cluster.data.name} · {cluster.data.provider_type === 'yc' ? 'Yandex Cloud' : 'On-prem'}
          </p>
        )}
      </div>

      <Card title="Параметры подключения">
        {cluster.loading ? (
          <Skeleton className="h-32 w-full" />
        ) : cluster.data ? (
          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3 text-sm">
            <Row label="Имя" value={cluster.data.name} />
            <Row label="Тип" value={cluster.data.provider_type === 'yc' ? 'Yandex Cloud' : 'On-prem'} />
            <Row label="OpenCost URL" value={<code className="font-mono text-xs">{cluster.data.opencost_url}</code>} />
            <Row label="VictoriaMetrics URL" value={<code className="font-mono text-xs">{cluster.data.vm_url}</code>} />
            <Row label="Активен" value={cluster.data.is_active ? <Badge tone="success">Да</Badge> : <Badge tone="neutral">Нет</Badge>} />
            <Row label="Создан" value={fmtDate(cluster.data.created_at)} />
          </dl>
        ) : null}
      </Card>

      <CredentialsCard
        clusterId={clusterId}
        credentials={credentials.data ?? []}
        loading={credentials.loading}
        provider={providers.data?.find(p => p.type === cluster.data?.provider_type)}
        onSaved={() => credentials.refetch()}
      />

      <Card title="Синхронизация">
        <div className="flex flex-col gap-4">
          <SyncBlock
            kind="billing"
            label="Биллинг"
            icon={<Database size={16} />}
            run={billingRun.data}
            loading={billingRun.loading}
            onTrigger={async (force) => {
              await api.triggerBillingSync(clusterId, force)
              setRefreshKey(k => k + 1)
            }}
          />
          <div className="border-t border-[var(--color-border)]" />
          <SyncBlock
            kind="allocations"
            label="Allocations"
            icon={<Activity size={16} />}
            run={allocRun.data}
            loading={allocRun.loading}
            onTrigger={async () => {
              await api.triggerAllocationsSync(clusterId, 30)
              setRefreshKey(k => k + 1)
            }}
          />
        </div>
      </Card>

      <DiagnosticsCard clusterId={clusterId} />
    </div>
  )
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div>
      <dt className="text-[11px] uppercase tracking-wide text-[var(--color-muted)] font-medium">{label}</dt>
      <dd className="mt-0.5 break-all">{value}</dd>
    </div>
  )
}

function CredentialsCard({
  clusterId, credentials, loading, provider, onSaved,
}: {
  clusterId: string
  credentials: CredentialMaskedRead[]
  loading: boolean
  provider: ProviderRead | undefined
  onSaved: () => void
}) {
  const [editing, setEditing] = useState(false)
  const [values, setValues] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fields = provider?.credentials ?? []

  useEffect(() => {
    if (!editing) setValues({})
  }, [editing])

  const save = async () => {
    setSaving(true); setError(null)
    try {
      const filled = Object.fromEntries(Object.entries(values).filter(([, v]) => v && v.trim()))
      if (Object.keys(filled).length === 0) {
        setEditing(false); setSaving(false); return
      }
      await api.upsertCredentials(clusterId, { values: filled })
      setEditing(false)
      onSaved()
    } catch (e) {
      setError(e instanceof ApiError ? `${e.status}: ${e.statusText}` : 'Ошибка')
    } finally { setSaving(false) }
  }

  return (
    <Card
      title="Учётные данные"
      action={
        !editing ? (
          <Button size="sm" variant="secondary" onClick={() => setEditing(true)}>Редактировать</Button>
        ) : (
          <div className="flex gap-2">
            <Button size="sm" variant="ghost" onClick={() => setEditing(false)} disabled={saving}>Отмена</Button>
            <Button size="sm" variant="primary" onClick={save} disabled={saving}>{saving ? 'Сохраняю...' : 'Сохранить'}</Button>
          </div>
        )
      }
    >
      {loading ? (
        <Skeleton className="h-20 w-full" />
      ) : !editing ? (
        credentials.length === 0 ? (
          <div className="text-sm text-[var(--color-muted)]">Учётные данные не заданы</div>
        ) : (
          <div className="flex flex-col gap-2">
            {credentials.map(c => (
              <div key={c.key_name} className="flex items-center justify-between text-sm py-1.5 border-b border-[var(--color-border)] last:border-0">
                <span className="font-medium">{c.key_name}</span>
                <span className="font-mono text-xs text-[var(--color-muted)]">
                  {c.has_value ? c.masked_preview : <span className="italic">не задано</span>}
                </span>
              </div>
            ))}
          </div>
        )
      ) : (
        <div className="flex flex-col gap-3">
          <p className="text-xs text-[var(--color-muted)]">Заполните только те поля, которые хотите изменить. Остальные останутся как есть.</p>
          {fields.map(f => (
            <Field
                key={f.name}
                label={f.label}
                hint={f.help_text ?? undefined}
                placeholder={credentials.find(c => c.key_name === f.name)?.masked_preview ?? f.placeholder ?? ''}
                type={f.is_secret ? 'password' : 'text'}
                value={values[f.name] ?? ''}
                onChange={e => setValues(v => ({ ...v, [f.name]: e.target.value }))}
            />
          ))}
          {error && <div className="text-xs text-[var(--color-accent-critical)]">{error}</div>}
        </div>
      )}
    </Card>
  )
}

function SyncBlock({
  label, icon, run, loading, onTrigger,
}: {
  kind: 'billing' | 'allocations'
  label: string
  icon: React.ReactNode
  run: { status: string; started_at: string; finished_at: string | null; error_message?: string | null; error?: string | null; window_start: string; window_end: string } | null | undefined
  loading: boolean
  onTrigger: (force?: boolean) => Promise<void>
}) {
  const [running, setRunning] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const trigger = async (force = false) => {
    setRunning(true); setError(null)
    try {
      await onTrigger(force)
    } catch (e) {
      setError(e instanceof ApiError ? `${e.status}: ${e.statusText}` : 'Ошибка')
    } finally { setRunning(false) }
  }

  const errMsg = run?.error_message ?? run?.error ?? null
  const isSuccess = run?.status === 'success' || run?.status === 'completed'

  return (
    <div className="flex items-start justify-between gap-4">
      <div className="flex items-start gap-3 min-w-0">
        <div className="text-[var(--color-muted)] mt-0.5">{icon}</div>
        <div className="min-w-0">
          <div className="font-medium text-sm">{label}</div>
          {loading ? (
            <Skeleton className="h-3 w-40 mt-1" />
          ) : run ? (
            <div className="text-xs text-[var(--color-muted)] mt-0.5 flex items-center gap-2 flex-wrap">
              {isSuccess ? (
                <Badge tone="success"><CheckCircle2 size={11} /> {run.status}</Badge>
              ) : errMsg ? (
                <Badge tone="critical"><AlertCircle size={11} /> {run.status}</Badge>
              ) : (
                <Badge tone="medium">{run.status}</Badge>
              )}
              <span>Окно: {fmtDate(run.window_start)} → {fmtDate(run.window_end)}</span>
              <span>·</span>
              <span>{run.finished_at ? `завершён ${fmtRelative(run.finished_at)}` : `запущен ${fmtRelative(run.started_at)}`}</span>
            </div>
          ) : (
            <div className="text-xs text-[var(--color-muted)] mt-0.5">Запусков ещё не было</div>
          )}
          {errMsg && <div className="text-xs text-[var(--color-accent-critical)] mt-1 break-all">{errMsg}</div>}
          {error && <div className="text-xs text-[var(--color-accent-critical)] mt-1">{error}</div>}
        </div>
      </div>
      <Button
        size="sm"
        variant="primary"
        leftIcon={<Play size={12} />}
        onClick={() => trigger()}
        disabled={running}
      >
        {running ? 'Запускаю...' : 'Запустить'}
      </Button>
    </div>
  )
}

function DiagnosticsCard({ clusterId }: { clusterId: string }) {
  const [data, setData] = useState<unknown>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const run = async () => {
    setLoading(true); setError(null); setData(null)
    try {
      const r = await api.getDiagnostics(clusterId)
      setData(r)
    } catch (e) {
      setError(e instanceof ApiError ? `${e.status}: ${e.statusText}` : 'Ошибка')
    } finally { setLoading(false) }
  }

  return (
    <Card
      title="Диагностика подключения"
      subtitle="Проверка доступности OpenCost, VictoriaMetrics и провайдера"
      action={
        <Button size="sm" variant="secondary" onClick={run} disabled={loading}>
          {loading ? 'Проверка...' : 'Запустить'}
        </Button>
      }
    >
      {!data && !error && !loading && (
        <div className="text-sm text-[var(--color-muted)]">Нажмите «Запустить» для проверки подключений</div>
      )}
      {error && <div className="text-sm text-[var(--color-accent-critical)]">{error}</div>}
      {data ? (
        <pre
          className="text-xs bg-[var(--color-bg)] border border-[var(--color-border)] rounded p-3 overflow-x-auto"
          style={{ fontFamily: 'var(--font-mono)' }}
        >
          {JSON.stringify(data, null, 2)}
        </pre>
      ) : null}
    </Card>
  )
}