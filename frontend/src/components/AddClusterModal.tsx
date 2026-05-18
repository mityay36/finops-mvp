import { useEffect, useState } from 'react'
import { Modal } from './UI/Modal'
import { Field } from './UI/Field'
import { Button } from './UI/Button'
import { api, ApiError, type ProviderRead, type ProviderType } from '../api/client'
import { useCluster } from '../state/cluster'

interface Props {
  open: boolean
  onClose: () => void
  onCreated: () => void
}

export function AddClusterModal({ open, onClose, onCreated }: Props) {
  const { setCurrentClusterId } = useCluster()
  const [providers, setProviders] = useState<ProviderRead[]>([])
  const [providerType, setProviderType] = useState<ProviderType>('yc')
  const [name, setName] = useState('')
  const [opencostUrl, setOpencostUrl] = useState('http://opencost.opencost.svc.cluster.local:9003')
  const [vmUrl, setVmUrl] = useState('http://vmsingle.monitoring.svc.cluster.local:8429')
  const [creds, setCreds] = useState<Record<string, string>>({})
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    api.listProviders().then(setProviders).catch(() => setProviders([]))
  }, [open])

  useEffect(() => {
    if (!open) {
      setName(''); setCreds({}); setError(null); setProviderType('yc')
    }
  }, [open])

  const provider = providers.find(p => p.type === providerType)

  const setCred = (k: string, v: string) => setCreds(prev => ({ ...prev, [k]: v }))

  const submit = async () => {
    setError(null)
    if (!name.trim()) { setError('Укажите имя кластера'); return }
    if (!opencostUrl.trim()) { setError('Укажите OpenCost URL'); return }
    if (!vmUrl.trim()) { setError('Укажите VictoriaMetrics URL'); return }

    setSubmitting(true)
    try {
      const created = await api.createCluster({
        name: name.trim(),
        provider_type: providerType,
        opencost_url: opencostUrl.trim(),
        vm_url: vmUrl.trim(),
        is_active: true,
      })

      const filledCreds = Object.fromEntries(
        Object.entries(creds).filter(([, v]) => v && v.trim() !== '')
      )
      if (Object.keys(filledCreds).length > 0) {
        await api.upsertCredentials(created.id, { values: filledCreds })
      }

      setCurrentClusterId(created.id)
      onCreated()
    } catch (e) {
      if (e instanceof ApiError) {
        const body = e.body as { detail?: string } | undefined
        setError(body?.detail ?? `Ошибка ${e.status}: ${e.statusText}`)
      } else {
        setError('Неизвестная ошибка')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Добавить кластер"
      footer={
        <>
          <Button variant="ghost" onClick={onClose} disabled={submitting}>Отмена</Button>
          <Button variant="primary" onClick={submit} disabled={submitting}>
            {submitting ? 'Создаю...' : 'Создать'}
          </Button>
        </>
      }
    >
      <div className="flex flex-col gap-4">
        <div>
          <span className="text-xs font-medium text-[var(--color-muted)] block mb-1.5">Тип провайдера</span>
          <div className="inline-flex bg-[var(--color-bg)] border border-[var(--color-border)] rounded-md p-0.5">
            {(['yc', 'onprem'] as ProviderType[]).map(t => (
              <button
                key={t}
                onClick={() => setProviderType(t)}
                className={`h-8 px-3 text-xs font-medium rounded transition-colors ${
                  providerType === t
                    ? 'bg-[var(--color-text)] text-[var(--color-bg)]'
                    : 'text-[var(--color-muted)] hover:text-[var(--color-text)]'
                }`}
              >
                {t === 'yc' ? 'Yandex Cloud' : 'On-prem'}
              </button>
            ))}
          </div>
        </div>

        <Field
          label="Имя кластера"
          placeholder="prod-k8s"
          value={name}
          onChange={e => setName(e.target.value)}
        />

        <Field
          label="OpenCost URL"
          placeholder="http://opencost.opencost.svc.cluster.local:9003"
          value={opencostUrl}
          onChange={e => setOpencostUrl(e.target.value)}
        />

        <Field
          label="VictoriaMetrics URL"
          placeholder="http://vmsingle.monitoring.svc.cluster.local:8429"
          value={vmUrl}
          onChange={e => setVmUrl(e.target.value)}
        />

        {provider && provider.credential_fields.length > 0 && (
          <div className="border-t border-[var(--color-border)] pt-4 flex flex-col gap-3">
            <div className="text-xs font-semibold uppercase tracking-wide text-[var(--color-muted)]">
              Учётные данные
            </div>
            {provider.credential_fields.map(f => (
              <Field
                key={f.name}
                label={f.label + (f.required ? ' *' : '')}
                hint={f.help_text ?? undefined}
                type={f.is_secret ? 'password' : 'text'}
                value={creds[f.name] ?? ''}
                onChange={e => setCred(f.name, e.target.value)}
              />
            ))}
          </div>
        )}

        {error && (
          <div className="text-xs text-[var(--color-accent-critical)] border border-[var(--color-accent-critical)]/30 bg-[var(--color-accent-critical)]/10 rounded px-3 py-2">
            {error}
          </div>
        )}
      </div>
    </Modal>
  )
}
