import { useState, useCallback } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AppShell } from './components/Layout/AppShell'
import { Overview } from './pages/Overview'
import { Namespaces } from './pages/Namespaces'
import { Recommendations } from './pages/Recommendations'
import { Billing } from './pages/Billing'

export default function App() {
  const [window, setWindow] = useState('30d')
  const [refreshKey, setRefreshKey] = useState(0)

  const handleRefresh = useCallback(() => setRefreshKey(k => k + 1), [])

  return (
    <BrowserRouter>
      <Routes>
        <Route
          element={
            <AppShell
              window={window}
              onWindowChange={setWindow}
              onRefresh={handleRefresh}
            />
          }
        >
          <Route path="/" element={<Overview window={window} refreshKey={refreshKey} />} />
          <Route path="/namespaces" element={<Namespaces window={window} refreshKey={refreshKey} />} />
          <Route path="/recommendations" element={<Recommendations refreshKey={refreshKey} />} />
          <Route path="/billing" element={<Billing window={window} refreshKey={refreshKey} />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
