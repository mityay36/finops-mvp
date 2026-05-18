import { Badge } from '../UI/Badge'
import type { RecStatus } from '../../api/client'

const map: Record<RecStatus, { tone: 'medium' | 'success' | 'neutral' | 'low'; label: string }> = {
  open: { tone: 'medium', label: 'Open' },
  applied: { tone: 'success', label: 'Applied' },
  dismissed: { tone: 'neutral', label: 'Dismissed' },
  stale: { tone: 'low', label: 'Stale' },
}

export function StatusBadge({ status }: { status: RecStatus }) {
  const { tone, label } = map[status]
  return <Badge tone={tone}>{label}</Badge>
}