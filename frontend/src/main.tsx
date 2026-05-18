import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { ClusterProvider } from './state/cluster.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ClusterProvider>
      <App />
    </ClusterProvider>
  </StrictMode>,
)
