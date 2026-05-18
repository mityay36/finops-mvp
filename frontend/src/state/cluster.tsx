import { createContext, useContext, useState, type ReactNode } from 'react'

interface ClusterCtx {
  currentClusterId: string | null
  setCurrentClusterId: (id: string | null) => void
}

const Ctx = createContext<ClusterCtx | null>(null)

export function ClusterProvider({ children }: { children: ReactNode }) {
  const [currentClusterId, setCurrentClusterId] = useState<string | null>(() => {
    return localStorage.getItem('finops:currentClusterId')
  })

  const update = (id: string | null) => {
    setCurrentClusterId(id)
    if (id) localStorage.setItem('finops:currentClusterId', id)
    else localStorage.removeItem('finops:currentClusterId')
  }

  return (
    <Ctx.Provider value={{ currentClusterId, setCurrentClusterId: update }}>
      {children}
    </Ctx.Provider>
  )
}

export function useCluster(): ClusterCtx {
  const v = useContext(Ctx)
  if (!v) throw new Error('useCluster must be used within ClusterProvider')
  return v
}
