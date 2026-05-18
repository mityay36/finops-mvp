import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AppShell } from './components/Layout/AppShell'
import Overview from './pages/Overview'
import Namespaces from './pages/Namespaces'
import Recommendations from './pages/Recommendations'
import Billing from './pages/Billing'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<Overview />} />
          <Route path="/namespaces" element={<Namespaces />} />
          <Route path="/recommendations" element={<Recommendations />} />
          <Route path="/billing" element={<Billing />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}