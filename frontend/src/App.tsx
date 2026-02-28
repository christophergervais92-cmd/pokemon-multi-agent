import { lazy, Suspense } from 'react'
import { Routes, Route } from 'react-router-dom'
import AppShell from './components/layout/AppShell'
import LoadingScreen from './components/shared/LoadingScreen'

// Lazy-loaded pages for code splitting
const Dashboard = lazy(() => import('./pages/Dashboard'))
const Stock = lazy(() => import('./pages/Stock'))
const Cards = lazy(() => import('./pages/Cards'))
const CardDetail = lazy(() => import('./pages/CardDetail'))
const Database = lazy(() => import('./pages/Database'))
const Drops = lazy(() => import('./pages/Drops'))
const Monitors = lazy(() => import('./pages/Monitors'))
const Flip = lazy(() => import('./pages/Flip'))
const PackEV = lazy(() => import('./pages/PackEV'))
const Sealed = lazy(() => import('./pages/Sealed'))
const Grading = lazy(() => import('./pages/Grading'))
const Assistant = lazy(() => import('./pages/Assistant'))
const Portfolio = lazy(() => import('./pages/Portfolio'))
const Analytics = lazy(() => import('./pages/Analytics'))
const Vending = lazy(() => import('./pages/Vending'))
const Settings = lazy(() => import('./pages/Settings'))

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<Suspense fallback={<LoadingScreen />}><Dashboard /></Suspense>} />
        <Route path="/stock" element={<Suspense fallback={<LoadingScreen />}><Stock /></Suspense>} />
        <Route path="/cards" element={<Suspense fallback={<LoadingScreen />}><Cards /></Suspense>} />
        <Route path="/cards/:cardId" element={<Suspense fallback={<LoadingScreen />}><CardDetail /></Suspense>} />
        <Route path="/database" element={<Suspense fallback={<LoadingScreen />}><Database /></Suspense>} />
        <Route path="/drops" element={<Suspense fallback={<LoadingScreen />}><Drops /></Suspense>} />
        <Route path="/monitors" element={<Suspense fallback={<LoadingScreen />}><Monitors /></Suspense>} />
        <Route path="/flip" element={<Suspense fallback={<LoadingScreen />}><Flip /></Suspense>} />
        <Route path="/pack-ev" element={<Suspense fallback={<LoadingScreen />}><PackEV /></Suspense>} />
        <Route path="/sealed" element={<Suspense fallback={<LoadingScreen />}><Sealed /></Suspense>} />
        <Route path="/grading" element={<Suspense fallback={<LoadingScreen />}><Grading /></Suspense>} />
        <Route path="/assistant" element={<Suspense fallback={<LoadingScreen />}><Assistant /></Suspense>} />
        <Route path="/portfolio" element={<Suspense fallback={<LoadingScreen />}><Portfolio /></Suspense>} />
        <Route path="/analytics" element={<Suspense fallback={<LoadingScreen />}><Analytics /></Suspense>} />
        <Route path="/vending" element={<Suspense fallback={<LoadingScreen />}><Vending /></Suspense>} />
        <Route path="/settings" element={<Suspense fallback={<LoadingScreen />}><Settings /></Suspense>} />
      </Route>
    </Routes>
  )
}
