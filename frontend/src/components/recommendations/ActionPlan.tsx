import { useState } from 'react'
import { Copy, Check, ChevronDown, ChevronRight } from 'lucide-react'
import type { RecommendedAction } from '../../lib/recommendations'

export function ActionPlan({ action }: { action: RecommendedAction }) {
  const [copied, setCopied] = useState(false)
  const [showRaw, setShowRaw] = useState(false)

  const copy = (text: string) => {
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    })
  }

  return (
    <div className="flex flex-col gap-5">
      {/* Headline */}
      <div>
        <SectionLabel>что сделать</SectionLabel>
        <p className="text-sm leading-relaxed">{action.headline}</p>
      </div>

      {/* Changes */}
      {action.changes.length > 0 && (
        <div>
          <SectionLabel>изменения в манифесте</SectionLabel>
          <div className="border border-[var(--color-border)] rounded-md overflow-hidden">
            {action.changes.map((c, i) => (
              <div key={i} className={`p-3 ${i > 0 ? 'border-t border-[var(--color-border)]' : ''}`}>
                <div className="text-xs font-mono text-[var(--color-muted)] mb-1.5 break-all">{c.field}</div>
                <div className="flex items-center gap-2 flex-wrap">
                  <code className="text-xs px-2 py-0.5 rounded bg-[var(--color-bg)] line-through text-[var(--color-muted)]">
                    {c.from}
                  </code>
                  <span className="text-[var(--color-muted)]">→</span>
                  <code className="text-xs px-2 py-0.5 rounded font-medium" style={{ backgroundColor: 'color-mix(in srgb, var(--color-accent-savings) 15%, transparent)', color: 'var(--color-accent-savings)' }}>
                    {c.to}
                  </code>
                  {c.note && <span className="text-xs text-[var(--color-muted)]">· {c.note}</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* kubectl quick-apply */}
      {action.kubectl && (
        <div>
          <SectionLabel>команда kubectl (быстрое применение)</SectionLabel>
          <div className="relative group">
            <pre className="text-xs bg-[var(--color-bg)] border border-[var(--color-border)] rounded-md p-3 pr-12 overflow-x-auto" style={{ fontFamily: 'var(--font-mono)' }}>
              {action.kubectl}
            </pre>
            <button
              onClick={() => copy(action.kubectl!)}
              className="absolute top-2 right-2 p-1.5 rounded hover:bg-[var(--color-border)] transition-colors"
              title="Копировать"
            >
              {copied ? <Check size={14} className="text-[var(--color-accent-savings)]" /> : <Copy size={14} className="text-[var(--color-muted)]" />}
            </button>
          </div>
          <p className="text-xs text-[var(--color-muted)] mt-1.5">
            Это патчит ресурс напрямую. Для GitOps-flow зафиксируйте изменение в Helm/Kustomize/манифесте репозитория.
          </p>
        </div>
      )}

      {/* Why */}
      <div>
        <SectionLabel>почему</SectionLabel>
        <ul className="flex flex-col gap-1 text-sm">
          {action.why.map((line, i) => (
            <li key={i} className="flex gap-2">
              <span className="text-[var(--color-muted)] mt-0.5">•</span>
              <span>{line}</span>
            </li>
          ))}
        </ul>
      </div>

      {/* Formula */}
      {action.formula && (
        <div>
          <SectionLabel>как считается</SectionLabel>
          <div className="text-xs font-mono bg-[var(--color-bg)] border border-[var(--color-border)] rounded-md p-3 leading-relaxed" style={{ fontFamily: 'var(--font-mono)' }}>
            {action.formula}
          </div>
        </div>
      )}

      {/* Raw evidence — collapsed by default */}
      <div>
        <button
          onClick={() => setShowRaw(s => !s)}
          className="flex items-center gap-1.5 text-xs text-[var(--color-muted)] hover:text-[var(--color-text)] transition-colors"
        >
          {showRaw ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
          Показать сырые данные (evidence)
        </button>
      </div>
    </div>
  )
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <div className="text-[11px] font-semibold uppercase tracking-wide text-[var(--color-muted)] mb-1.5">
      {children}
    </div>
  )
}
