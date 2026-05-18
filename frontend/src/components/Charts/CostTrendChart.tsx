import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import type { TimeseriesPoint } from '../../api/client'
import { fmtMoney } from '../../lib/format'

interface Props {
  points: TimeseriesPoint[]
  currency: string
  height?: number
}

export function CostTrendChart({ points, currency, height = 240 }: Props) {
  const data = points.map(p => ({
    date: p.date,
    total: parseFloat(p.total),
  }))

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
        <CartesianGrid stroke="var(--color-border)" strokeDasharray="3 3" vertical={false} />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 11, fill: 'var(--color-muted)' }}
          tickFormatter={d => {
            const dt = new Date(d)
            return `${dt.getDate()}.${String(dt.getMonth() + 1).padStart(2, '0')}`
          }}
          stroke="var(--color-border)"
        />
        <YAxis
          tick={{ fontSize: 11, fill: 'var(--color-muted)' }}
          tickFormatter={v => {
            if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`
            if (v >= 1_000) return `${(v / 1_000).toFixed(0)}k`
            return String(v)
          }}
          stroke="var(--color-border)"
          width={50}
        />
        <Tooltip
          contentStyle={{
            background: 'var(--color-card)',
            border: '1px solid var(--color-border)',
            borderRadius: 6,
            fontSize: 12,
          }}
          labelStyle={{ color: 'var(--color-muted)' }}
          formatter={(v: number) => [fmtMoney(v, currency), 'Стоимость']}
        />
        <Line
          type="monotone"
          dataKey="total"
          stroke="var(--color-accent-info)"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
        />
      </LineChart>
    </ResponsiveContainer>
  )
}
