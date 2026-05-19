import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AppShell } from './components/Layout/AppShell'
import { CurrencyProvider } from './state/currency'
import Overview from './pages/Overview'
import Allocations from './pages/Allocations'
import Recommendations from './pages/Recommendations'
import Settings from './pages/Settings'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<CurrencyProvider><AppShell /></CurrencyProvider>}>
          <Route path="/" element={<Overview />} />
          <Route path="/allocations" element={<Allocations />} />
          <Route path="/recommendations" element={<Recommendations />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}