import { createContext, useContext, useState, type ReactNode } from 'react'

export type Period = '7d' | '30d' | '90d'

interface PeriodCtx {
  period: Period
  setPeriod: (p: Period) => void
}

const Ctx = createContext<PeriodCtx | null>(null)

export function PeriodProvider({ children }: { children: ReactNode }) {
  const [period, setPeriodState] = useState<Period>(() => {
    const saved = localStorage.getItem('finops:period')
    return (saved === '7d' || saved === '30d' || saved === '90d') ? saved : '30d'
  })

  const setPeriod = (p: Period) => {
    setPeriodState(p)
    localStorage.setItem('finops:period', p)
  }

  return <Ctx.Provider value={{ period, setPeriod }}>{children}</Ctx.Provider>
}

export function usePeriod(): PeriodCtx {
  const v = useContext(Ctx)
  if (!v) throw new Error('usePeriod must be used within PeriodProvider')
  return v
}
