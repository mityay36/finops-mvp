import { useEffect, useState } from 'react'
import { Drawer } from '../UI/Drawer'
import { Button } from '../UI/Button'
import { Field } from '../UI/Field'
import { SeverityBadge } from './SeverityBadge'
import { StatusBadge } from './StatusBadge'
import { api, ApiError, type RecommendationDetail } from '../../api/client'
import { fmtMoney, fmtRelative } from '../../lib/format'

interface Props {
  open: boolean
  clusterId: string
  recId: string | null
  onClose: () => void
  onChanged: () => void
}

export function RecommendationDrawer({ open, clusterId, recId, onClose, onChanged }: Props) {
  const [detail, setDetail] = useState<RecommendationDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [acting, setActing] = useState(false)
  const [dismissReason, setDismissReason] = useState('')
  const [showDismissForm, setShowDismissForm] = useState(false)

  useEffect(() => {
    if (!open || !recId) return
    setDetail(null); setError(null); setShowDismissForm(false); setDismissReason('')
    setLoading(true)
    api.getRecommendation(clusterId, recId)
      .then(setDetail)
      .catch(e => setError(e instanceof ApiError ? `${e.status}: ${e.statusText}` : 'Ошибка'))
      .finally(() => setLoading(false))
  }, [open, recId, clusterId])

  const apply = async () => {
    if (!recId) return
    setActing(true); setError(null)
    try {
      const updated = await api.applyRecommendation(clusterId, recId)
      setDetail(updated)
      onChanged()
    } catch (e) {
      setError(e instanceof ApiError ? `Ошибка ${e.status}: ${e.statusText}` : 'Ошибка')
    } finally { setActing(false) }
  }

  const dismiss = async () => {
    if (!recId || !dismissReason.trim()) return
    setActing(true); setError(null)
    try {
      const updated = await api.dismissRecommendation(clusterId, recId, dismissReason.trim())
      setDetail(updated)
      setShowDismissForm(false)
      onChanged()
    } catch (e) {
      setError(e instanceof ApiError ? `Ошибка ${e.status}: ${e.statusText}` : 'Ошибка')
    } finally { setActing(false) }
  }

  return (
    <Drawer
      open={open}
      onClose={onClose}
      width={560}
      title={
        detail ? (
          <div className="flex items-start gap-3 min-w-0">
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 mb-1">
                <SeverityBadge severity={detail.severity} />
                <StatusBadge status={detail.status} />
                <span className="text-xs text-[var(--color-muted)]">{detail.rule_id}</span>
              </div>
              <h2 className="text-base font-semibold truncate">{detail.title}</h2>
            </div>
          </div>
        ) : (
          <span className="text-base font-semibold">Рекомендация</span>
        )
      }
      footer={
        detail && detail.status === 'open' ? (
          showDismissForm ? (
            <>
              <Button variant="ghost" onClick={() => setShowDismissForm(false)} disabled={acting}>Отмена</Button>
              <Button variant="danger" onClick={dismiss} disabled={acting || !dismissReason.trim()}>
                Подтвердить отклонение
              </Button>
            </>
          ) : (
            <>
              <Button variant="ghost" onClick={() => setShowDismissForm(true)} disabled={acting}>
                Отклонить
              </Button>
              <Button variant="primary" onClick={apply} disabled={acting}>
                {acting ? 'Применяю...' : 'Отметить применённым'}
              </Button>
            </>
          )
        ) : (
          <Button variant="ghost" onClick={onClose}>Закрыть</Button>
        )
      }
    >
      {loading && <div className="text-sm text-[var(--color-muted)]">Загрузка...</div>}
      {error && <div className="text-sm text-[var(--color-accent-critical)]">{error}</div>}

      {detail && (
        <div className="flex flex-col gap-5">
          <Section label="Цель">
            <div className="text-sm">
              <span className="text-[var(--color-muted)]">{detail.target_kind}</span>
              {detail.target_namespace && <> · <span>ns: <span className="font-medium">{detail.target_namespace}</span></span></>}
              {detail.target_name && <> · <span className="font-medium">{detail.target_name}</span></>}
            </div>
          </Section>

          <Section label={detail.impact_kind === 'saving' ? 'Потенциал экономии' : 'Стоимость безопасности'}>
            <div
              className="text-2xl font-semibold tabular"
              style={{
                color: detail.impact_kind === 'saving'
                  ? 'var(--color-accent-savings)'
                  : 'var(--color-accent-warning)',
              }}
            >
              {fmtMoney(detail.monthly_impact, detail.currency)} <span className="text-sm font-normal text-[var(--color-muted)]">/ мес</span>
            </div>
          </Section>

          <Section label="Описание">
            <p className="text-sm leading-relaxed whitespace-pre-wrap">{detail.description}</p>
          </Section>

          {detail.evidence && Object.keys(detail.evidence).length > 0 && (
            <Section label="Доказательства">
              <pre
                className="text-xs bg-[var(--color-bg)] border border-[var(--color-border)] rounded p-3 overflow-x-auto font-mono"
                style={{ fontFamily: 'var(--font-mono)' }}
              >
                {JSON.stringify(detail.evidence, null, 2)}
              </pre>
            </Section>
          )}

          {detail.remediation && Object.keys(detail.remediation).length > 0 && (
            <Section label="Как исправить">
              <pre
                className="text-xs bg-[var(--color-bg)] border border-[var(--color-border)] rounded p-3 overflow-x-auto font-mono"
                style={{ fontFamily: 'var(--font-mono)' }}
              >
                {JSON.stringify(detail.remediation, null, 2)}
              </pre>
            </Section>
          )}

          {detail.dismissed_reason && (
            <Section label="Причина отклонения">
              <p className="text-sm italic text-[var(--color-muted)]">{detail.dismissed_reason}</p>
            </Section>
          )}

          <div className="text-xs text-[var(--color-muted)] pt-2 border-t border-[var(--color-border)]">
            Создано {fmtRelative(detail.created_at)} · обновлено {fmtRelative(detail.updated_at)}
          </div>

          {showDismissForm && (
            <div className="border-t border-[var(--color-border)] pt-4">
              <Field
                label="Причина отклонения"
                placeholder="Например: ложное срабатывание, нагрузка ожидаемая"
                value={dismissReason}
                onChange={e => setDismissReason(e.target.value)}
              />
            </div>
          )}
        </div>
      )}
    </Drawer>
  )
}

function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-[11px] font-semibold uppercase tracking-wide text-[var(--color-muted)] mb-1.5">{label}</div>
      {children}
    </div>
  )
}
