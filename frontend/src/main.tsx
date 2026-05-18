import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { ClusterProvider } from './state/cluster.tsx'
import { PeriodProvider } from './state/period.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ClusterProvider>
      <PeriodProvider>
        <App />
      </PeriodProvider>
    </ClusterProvider>
  </StrictMode>,
)
