import { Badge } from '../UI/Badge'
import type { RecSeverity } from '../../api/client'

const map: Record<RecSeverity, { tone: 'critical' | 'high' | 'medium'; label: string }> = {
  critical: { tone: 'critical', label: 'Critical' },
  warning:  { tone: 'high',     label: 'Warning' },
  info:     { tone: 'medium',   label: 'Info' },
}

export const severityOrder: Record<RecSeverity, number> = {
  critical: 0,
  warning: 1,
  info: 2,
}

export function SeverityBadge({ severity }: { severity: RecSeverity | string }) {
  const entry = map[severity as RecSeverity]
  if (!entry) return <Badge tone="neutral">{String(severity)}</Badge>
  return <Badge tone={entry.tone} dot>{entry.label}</Badge>
}
