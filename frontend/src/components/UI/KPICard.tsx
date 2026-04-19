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

function AnimatedNumber({ value, prefix = '', suffix = '' }: { value: number; prefix?: string; suffix?: string }) {
  const motionValue = useMotionValue(0)
  const rounded = useTransform(motionValue, (v) =>
    `${prefix}${v.toLocaleString('ru-RU', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}${suffix}`
  )

  useEffect(() => {
    const controls = animate(motionValue, value, {
      duration: 1.2,
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
      <div className="rounded-xl p-5 border" style={{
        background: 'var(--color-surface)',
        borderColor: 'oklch(from var(--color-text) l c h / 0.08)',
        boxShadow: 'var(--shadow-sm)',
      }}>
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 space-y-3">
            <div className="skeleton h-3 w-28 rounded" />
            <div className="skeleton h-7 w-36 rounded" />
            <div className="skeleton h-3 w-20 rounded" />
          </div>
          <div className="skeleton w-10 h-10 rounded-lg flex-shrink-0" />
        </div>
      </div>
    )
  }

  const isPositiveTrend = trend && trend.value > 0

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
      className="rounded-xl p-5 border group hover:shadow-md transition-shadow duration-200"
      style={{
        background: 'var(--color-surface)',
        borderColor: 'oklch(from var(--color-text) l c h / 0.08)',
        boxShadow: 'var(--shadow-sm)',
      }}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium uppercase tracking-wider mb-2"
             style={{ color: 'var(--color-text-faint)', letterSpacing: '0.08em' }}>
            {label}
          </p>
          <p className="font-display font-bold tabular text-2xl leading-none mb-2"
             style={{ color: 'var(--color-text)', fontFamily: 'var(--font-display)' }}>
            {animateValue && numericValue !== undefined ? (
              <AnimatedNumber value={numericValue} prefix={prefix} suffix={suffix} />
            ) : (
              value
            )}
          </p>
          {subtitle && (
            <p className="text-xs" style={{ color: 'var(--color-text-faint)' }}>{subtitle}</p>
          )}
          {trend && (
            <div className={cn(
              'inline-flex items-center gap-1 text-xs font-medium mt-1',
              isPositiveTrend ? 'text-[var(--color-success)]' : 'text-[var(--color-error)]'
            )}>
              <span>{isPositiveTrend ? '↑' : '↓'} {Math.abs(trend.value)}%</span>
              <span style={{ color: 'var(--color-text-faint)' }}>{trend.label}</span>
            </div>
          )}
        </div>
        <div
          className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 transition-transform duration-200 group-hover:scale-105"
          style={{ background: iconBg }}
        >
          {icon}
        </div>
      </div>
    </motion.div>
  )
}
