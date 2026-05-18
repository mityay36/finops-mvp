import { useState, useRef, useEffect } from 'react'
import { ChevronDown, Plus, Check, Server } from 'lucide-react'
import { useCluster } from '../state/cluster'
import type { ClusterRead } from '../api/client'
import { cn } from '../lib/utils'

interface Props {
  clusters: ClusterRead[]
  onAddNew: () => void
}

export function ClusterPicker({ clusters, onAddNew }: Props) {
  const { currentClusterId, setCurrentClusterId } = useCluster()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    if (open) document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [open])

  const current = clusters.find(c => c.id === currentClusterId) ?? null

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(o => !o)}
        className={cn(
          'flex items-center gap-2 h-9 px-3 rounded-md text-sm',
          'bg-[var(--color-card)] border border-[var(--color-border)]',
          'hover:border-[var(--color-text)]/30 transition-colors',
        )}
      >
        <Server size={14} className="text-[var(--color-muted)]" />
        <span className="font-medium">{current ? current.name : 'Кластер не выбран'}</span>
        {current && (
          <span className="text-xs text-[var(--color-muted)]">
            {current.provider_type === 'yc' ? 'Yandex Cloud' : 'On-prem'}
          </span>
        )}
        <ChevronDown size={14} className="text-[var(--color-muted)]" />
      </button>

      {open && (
        <div
          className={cn(
            'absolute top-full left-0 mt-1 w-72 z-30',
            'bg-[var(--color-card)] border border-[var(--color-border)] rounded-md shadow-lg',
            'py-1',
          )}
        >
          <div className="max-h-64 overflow-y-auto">
            {clusters.length === 0 ? (
              <div className="px-3 py-3 text-sm text-[var(--color-muted)]">Нет кластеров</div>
            ) : (
              clusters.map(c => (
                <button
                  key={c.id}
                  onClick={() => { setCurrentClusterId(c.id); setOpen(false) }}
                  className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-[var(--color-bg)] text-left"
                >
                  <span className="flex-1">
                    <span className="font-medium block">{c.name}</span>
                    <span className="text-xs text-[var(--color-muted)]">
                      {c.provider_type === 'yc' ? 'Yandex Cloud' : 'On-prem'}
                      {!c.is_active && ' · неактивен'}
                    </span>
                  </span>
                  {c.id === currentClusterId && <Check size={14} />}
                </button>
              ))
            )}
          </div>
          <div className="border-t border-[var(--color-border)] mt-1 pt-1">
            <button
              onClick={() => { setOpen(false); onAddNew() }}
              className="w-full flex items-center gap-2 px-3 py-2 text-sm hover:bg-[var(--color-bg)] text-[var(--color-text)]"
            >
              <Plus size={14} />
              Добавить кластер
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
