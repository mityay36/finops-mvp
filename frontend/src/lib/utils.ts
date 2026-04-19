import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatCurrency(value: number, currency = '₽'): string {
  return `${currency} ${value.toLocaleString('ru-RU', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

export function formatCurrencyShort(value: number, currency = '₽'): string {
  if (value >= 1000) {
    return `${currency} ${(value / 1000).toFixed(1)}K`
  }
  return `${currency} ${value.toFixed(2)}`
}

export function formatPercent(value: number): string {
  return `${(value * 100).toFixed(0)}%`
}

export function getRiskColor(risk: string): string {
  switch (risk) {
    case 'low': return 'success'
    case 'medium': return 'warning'
    case 'high': return 'error'
    default: return 'muted'
  }
}

export function getRiskLabel(risk: string): string {
  switch (risk) {
    case 'low': return 'Низкий'
    case 'medium': return 'Средний'
    case 'high': return 'Высокий'
    default: return risk
  }
}

export function getActionLabel(action: string): string {
  const map: Record<string, string> = {
    reduce_cpu_requests: 'Снизить CPU requests',
    reduce_ram_requests: 'Снизить RAM requests',
    convert_to_preemptible: 'Перейти на Preemptible',
    resize_node_group: 'Изменить Node Group',
    apply_vpa_recommendation: 'Применить VPA',
  }
  return map[action] ?? action
}
