import { Badge } from '../UI/Badge'
import type { RecSeverity } from '../../api/client'

const map: Record<RecSeverity, { tone: 'critical' | 'high' | 'medium' | 'low'; label: string }> = {
  critical: { tone: 'critical', label: 'Critical' },
  high: { tone: 'high', label: 'High' },
  medium: { tone: 'medium', label: 'Medium' },
  low: { tone: 'low', label: 'Low' },
}

export function SeverityBadge({ severity }: { severity: RecSeverity }) {
  const { tone, label } = map[severity]
  return <Badge tone={tone} dot>{label}</Badge>
}
