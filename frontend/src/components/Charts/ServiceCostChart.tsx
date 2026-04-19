import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Cell
} from 'recharts'
import { formatCurrencyShort } from '../../lib/utils'

interface ServiceCostChartProps {
  data: { name: string; cost: number }[]
  loading?: boolean
}

const COLORS = [
  'var(--chart-1)',
  'var(--chart-3)',
  'var(--chart-2)',
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
      <p className="text-xs mb-1 max-w-48" style={{ color: 'var(--color-text-muted)' }}>
        {label}
      </p>
      <p className="tabular font-semibold" style={{ color: 'var(--color-accent)' }}>
        {formatCurrencyShort(payload[0].value)}
      </p>
    </div>
  )
}

export function ServiceCostChart({ data, loading }: ServiceCostChartProps) {
  if (loading) {
    return (
      <div className="h-60 flex flex-col justify-around px-2 py-2 gap-2">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="flex items-center gap-2">
            <div className="skeleton h-3 w-20 rounded flex-shrink-0" />
            <div className="skeleton h-4 rounded" style={{ width: `${30 + i * 10}%` }} />
          </div>
        ))}
      </div>
    )
  }

  const top = data.slice(0, 8)
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart
        data={top}
        layout="vertical"
        margin={{ top: 4, right: 16, left: 8, bottom: 4 }}
        barSize={18}
      >
        <XAxis
          type="number"
          tick={{ fontSize: 11, fill: 'var(--color-text-faint)', fontFamily: 'var(--font-body)' }}
          axisLine={false}
          tickLine={false}
          tickFormatter={(v: number) => formatCurrencyShort(v).replace('₽ ', '')}
        />
        <YAxis
          type="category"
          dataKey="name"
          tick={{ fontSize: 11, fill: 'var(--color-text-faint)', fontFamily: 'var(--font-body)' }}
          axisLine={false}
          tickLine={false}
          width={120}
          tickFormatter={(v: string) => v.length > 18 ? v.slice(0, 17) + '…' : v}
        />
        <Tooltip content={<CustomTooltip />}
                 cursor={{ fill: 'oklch(from var(--color-text) l c h / 0.04)' }} />
        <Bar dataKey="cost" radius={[0, 4, 4, 0]}>
          {top.map((_, index) => (
            <Cell key={index} fill={COLORS[index % COLORS.length]} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}
