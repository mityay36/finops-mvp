import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Cell
} from 'recharts'
import { formatCurrencyShort } from '../../lib/utils'

interface NamespaceCostChartProps {
  data: { name: string; total_cost: number }[]
  loading?: boolean
}

const COLORS = [
  'var(--chart-1)',
  'var(--chart-2)',
  'var(--chart-3)',
  'var(--chart-4)',
  'var(--chart-5)',
  'var(--chart-6)',
]

interface TooltipProps {
  active?: boolean
  payload?: { value: number }[]
  label?: string
}

function CustomTooltip({ active, payload, label }: TooltipProps) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-lg px-3 py-2 text-sm border"
         style={{
           background: 'var(--color-surface-2)',
           borderColor: 'oklch(from var(--color-text) l c h / 0.1)',
           boxShadow: 'var(--shadow-md)',
           color: 'var(--color-text)',
         }}>
      <p className="font-medium mb-1"
         style={{ fontFamily: 'var(--font-mono)', fontSize: '0.75rem', color: 'var(--color-text-muted)' }}>
        {label}
      </p>
      <p className="tabular font-semibold" style={{ color: 'var(--color-primary)' }}>
        {formatCurrencyShort(payload[0].value)}
      </p>
    </div>
  )
}

export function NamespaceCostChart({ data, loading }: NamespaceCostChartProps) {
  if (loading) {
    return (
      <div className="h-60 flex items-end gap-2 px-2 pb-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i}
               className="skeleton flex-1 rounded-t"
               style={{ height: `${40 + Math.random() * 60}%` }} />
        ))}
      </div>
    )
  }

  const top = data.slice(0, 8)
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={top} margin={{ top: 4, right: 8, left: 8, bottom: 4 }} barSize={28}>
        <XAxis
          dataKey="name"
          tick={{ fontSize: 11, fill: 'var(--color-text-faint)', fontFamily: 'var(--font-body)' }}
          axisLine={false}
          tickLine={false}
          interval={0}
          tickFormatter={(v: string) => v.length > 12 ? v.slice(0, 11) + '…' : v}
        />
        <YAxis
          tick={{ fontSize: 11, fill: 'var(--color-text-faint)', fontFamily: 'var(--font-body)' }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v: number) => formatCurrencyShort(v).replace('₽ ', '')}
          width={48}
        />
        <Tooltip content={<CustomTooltip />}
                 cursor={{ fill: 'oklch(from var(--color-text) l c h / 0.04)' }} />
        <Bar dataKey="total_cost" radius={[4, 4, 0, 0]}>
          {top.map((_, index) => (
            <Cell key={index} fill={COLORS[index % COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
