import { Badge } from '../UI/Badge'
import type { RecStatus } from '../../api/client'

const map: Record<RecStatus, { tone: 'medium' | 'success' | 'neutral'; label: string }> = {
  open:            { tone: 'medium',  label: 'Open' },
  applied:         { tone: 'success', label: 'Applied' },
  dismissed:       { tone: 'neutral', label: 'Dismissed' },
  closed_resolved: { tone: 'success', label: 'Resolved' },
}

export function StatusBadge({ status }: { status: RecStatus | string }) {
  const entry = map[status as RecStatus]
  if (!entry) return <Badge tone="neutral">{String(status)}</Badge>
  return <Badge tone={entry.tone}>{entry.label}</Badge>
}
