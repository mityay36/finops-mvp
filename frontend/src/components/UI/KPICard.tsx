import { useEffect } from 'react'
import { motion, useMotionValue, useTransform, animate } from 'framer-motion'
import { cn } from '../../lib/utils'

interface KPICardProps {
  label: string
  value: string | number
  subtitle?: string
  icon: React.ReactNode
  iconBg?: string
  animateValue?: boolean
  numericValue?: number
  prefix?: string
  suffix?: string
  trend?: { value: number; label: string }
  loading?: boolean
}

function AnimatedNumber({ value, prefix = '', suffix = '' }: {
  value: number; prefix?: string; suffix?: string
}) {
  const motionValue = useMotionValue(0)
  const rounded = useTransform(motionValue, (v) =>
    `${prefix}${v.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}${suffix}`
  )

  useEffect(() => {
    const controls = animate(motionValue, value, {
      duration: 1.0,
      ease: [0.16, 1, 0.3, 1],
    })
    return controls.stop
  }, [value, motionValue])

  return <motion.span>{rounded}</motion.span>
}

export function KPICard({
  label,
  value,
  subtitle,
  icon,
  iconBg = 'var(--color-primary-subtle)',
  animateValue,
  numericValue,
  prefix,
  suffix,
  trend,
  loading,
}: KPICardProps) {
  if (loading) {
    return (
      <div
        className="rounded-lg p-4 border"
        style={{
          background: 'var(--color-surface)',
          borderColor: 'rgba(28,20,10,0.09)',
          boxShadow: 'var(--shadow-sm)',
        }}
      >
        <div className="flex items-start gap-3">
          <div className="skeleton rounded-md flex-shrink-0" style={{ width: 36, height: 36 }} />
          <div className="flex-1 space-y-2 pt-0.5">
            <div className="skeleton h-2.5 rounded" style={{ width: '60%' }} />
            <div className="skeleton h-5 rounded" style={{ width: '80%' }} />
            <div className="skeleton h-2.5 rounded" style={{ width: '40%' }} />
          </div>
        </div>
      </div>
    )
  }

  const isPositiveTrend = trend && trend.value > 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
      className="rounded-lg p-4 border"
      style={{
        background: 'var(--color-surface)',
        borderColor: 'rgba(28,20,10,0.09)',
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      {/* Top row: icon + label */}
      <div className="flex items-center gap-2.5 mb-3">
        <div
          className="rounded-md flex-shrink-0 flex items-center justify-center"
          style={{ width: 32, height: 32, background: iconBg }}
        >
          {icon}
        </div>
        <p
          className="text-xs font-medium uppercase tracking-wider truncate"
          style={{ color: 'var(--color-text-faint)', letterSpacing: '0.07em' }}
        >
          {label}
        </p>
      </div>

      {/* Value — большой */}
      <p
        className="kpi-value tabular"
        style={{ color: 'var(--color-text)' }}
      >
        {animateValue && numericValue !== undefined ? (
          <AnimatedNumber value={numericValue} prefix={prefix} suffix={suffix} />
        ) : (
          value
        )}
      </p>

      {/* Subtitle */}
      {subtitle && (
        <p
          className="mt-1.5 text-xs"
          style={{ color: 'var(--color-text-faint)' }}
        >
          {subtitle}
        </p>
      )}

      {/* Trend */}
      {trend && (
        <div
          className={cn(
            'inline-flex items-center gap-1 mt-1.5 text-xs font-medium',
            isPositiveTrend ? 'text-[var(--color-success)]' : 'text-[var(--color-error)]'
          )}
        >
          <span>{isPositiveTrend ? '↑' : '↓'} {Math.abs(trend.value)}%</span>
          <span style={{ color: 'var(--color-text-faint)' }}>{trend.label}</span>
        </div>
      )}
    </motion.div>
  )
}
