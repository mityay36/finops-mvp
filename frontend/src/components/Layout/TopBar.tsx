import { useState } from 'react'
import { RefreshCw } from 'lucide-react'
import { ClusterPicker } from '../ClusterPicker'
import { PeriodPicker } from '../PeriodPicker'
import { AddClusterModal } from '../AddClusterModal'
import { Button } from '../UI/Button'
import type { ClusterRead } from '../../api/client'

interface Props {
  clusters: ClusterRead[]
  onClustersChanged: () => void
}

export function TopBar({ clusters, onClustersChanged }: Props) {
  const [addOpen, setAddOpen] = useState(false)
  const [refreshing, setRefreshing] = useState(false)

  const handleRefresh = () => {
    setRefreshing(true)
    onClustersChanged()
    setTimeout(() => setRefreshing(false), 500)
  }

  return (
    <header
      className="h-14 border-b border-[var(--color-border)] bg-[var(--color-card)] flex items-center px-6 gap-3 sticky top-0 z-20"
    >
      <ClusterPicker clusters={clusters} onAddNew={() => setAddOpen(true)} />
      <div className="flex-1" />
      <PeriodPicker />
      <Button
        size="sm"
        variant="ghost"
        onClick={handleRefresh}
        leftIcon={<RefreshCw size={14} className={refreshing ? 'animate-spin' : ''} />}
      >
        Обновить
      </Button>

      <AddClusterModal
        open={addOpen}
        onClose={() => setAddOpen(false)}
        onCreated={() => { setAddOpen(false); onClustersChanged() }}
      />
    </header>
  )
}
