// Money/percent/date formatting helpers — centralized so we don't sprinkle
// Intl.NumberFormat all over.

export function fmtMoney(value: string | number | null | undefined, currency = 'RUB'): string {
  if (value === null || value === undefined || value === '') return '—'
  const n = typeof value === 'string' ? parseFloat(value) : value
  if (!Number.isFinite(n)) return '—'
  return new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency,
    maximumFractionDigits: n >= 1000 ? 0 : 2,
  }).format(n)
}

export function fmtNumber(value: number | null | undefined, opts: Intl.NumberFormatOptions = {}): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—'
  return new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 1, ...opts }).format(value)
}

export function fmtPercent(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—'
  return `${(value * 100).toFixed(digits)}%`
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleDateString('ru-RU', { day: '2-digit', month: 'short', year: 'numeric' })
}

export function fmtRelative(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  const diffMs = Date.now() - d.getTime()
  const min = Math.round(diffMs / 60000)
  if (min < 1) return 'только что'
  if (min < 60) return `${min} мин назад`
  const h = Math.round(min / 60)
  if (h < 24) return `${h} ч назад`
  const days = Math.round(h / 24)
  if (days < 30) return `${days} д назад`
  return fmtDate(iso)
}

export function periodFromWindow(p: { days: number }): { period_start: string; period_end: string } {
  const to = new Date()
  const from = new Date()
  from.setDate(to.getDate() - p.days + 1)
  return {
    period_start: from.toISOString(),
    period_end: to.toISOString(),
  }
}

export function allocPeriodFromWindow(p: { days: number }): { from: string; to: string } {
  const to = new Date()
  const from = new Date()
  from.setDate(to.getDate() - p.days + 1)
  const fmt = (d: Date) => d.toISOString().slice(0, 10)
  return { from: fmt(from), to: fmt(to) }
}

export function periodFromWindowISO(window: '7d' | '30d' | '90d'): { period_start: string; period_end: string } {
  const days = parseInt(window)
  const period_end = new Date().toISOString()
  const start = new Date()
  start.setDate(start.getDate() - days)
  const period_start = start.toISOString()
  return { period_start, period_end }
}
