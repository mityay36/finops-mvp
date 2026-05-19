import type { RecommendationItem } from '../api/client'

export function ruleLabel(ruleId: string): string {
  return ruleId
    .split('_')
    .map(s => s.charAt(0).toUpperCase() + s.slice(1))
    .join(' ')
}

export function targetLabel(item: Pick<RecommendationItem, 'target_kind' | 'target_namespace' | 'target_controller'>): string {
  const parts = [item.target_kind]
  if (item.target_namespace) parts.push(item.target_namespace)
  if (item.target_controller) parts.push(item.target_controller)
  return parts.join(' / ')
}
