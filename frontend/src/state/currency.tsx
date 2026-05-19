import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { api } from '../api/client'
import { useCluster } from './cluster'

interface Ctx {
  currency: string
  loading: boolean
}

const CurrencyContext = createContext<Ctx>({ currency: 'RUB', loading: false })

export function CurrencyProvider({ children }: { children: ReactNode }) {
  const { currentClusterId } = useCluster()
  const [currency, setCurrency] = useState<string>('RUB')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (!currentClusterId) return
    setLoading(true)
    api.getBillingSummary(currentClusterId)
      .then(r => setCurrency(r.currency || 'RUB'))
      .catch(() => setCurrency('RUB'))
      .finally(() => setLoading(false))
  }, [currentClusterId])

  return <CurrencyContext.Provider value={{ currency, loading }}>{children}</CurrencyContext.Provider>
}

export const useCurrency = () => useContext(CurrencyContext)
