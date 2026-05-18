import { useState } from 'react'
import { Server, Plus } from 'lucide-react'
import { Button } from './UI/Button'
import { AddClusterModal } from './AddClusterModal'

interface Props { onCreated: () => void }

export function EmptyClusterState({ onCreated }: Props) {
  const [open, setOpen] = useState(false)
  return (
    <div className="flex-1 flex items-center justify-center min-h-[60vh]">
      <div className="text-center max-w-md px-6">
        <div className="inline-flex items-center justify-center w-14 h-14 rounded-full bg-[var(--color-bg)] border border-[var(--color-border)] mb-4">
          <Server size={24} className="text-[var(--color-muted)]" />
        </div>
        <h2 className="text-xl font-semibold mb-2">Добавьте первый кластер</h2>
        <p className="text-sm text-[var(--color-muted)] mb-6">
          Чтобы начать анализ затрат, подключите Kubernetes-кластер с установленным OpenCost
          и доступом к VictoriaMetrics.
        </p>
        <Button variant="primary" leftIcon={<Plus size={16} />} onClick={() => setOpen(true)}>
          Добавить кластер
        </Button>
      </div>
      <AddClusterModal open={open} onClose={() => setOpen(false)} onCreated={() => { setOpen(false); onCreated() }} />
    </div>
  )
}
