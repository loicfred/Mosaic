import { lazy } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from '@/auth/AuthProvider'
import { AppShell } from '@/components/layout/AppShell'
import { PageSkeleton } from '@/components/ui/states'
import { LoginPage } from '@/pages/Login'
import { RegisterPage } from '@/pages/Register'

const DataHealthPage = lazy(() => import('@/pages/DataHealth').then((mod) => ({ default: mod.DataHealthPage })))
const InsightsPage = lazy(() => import('@/pages/Insights').then((mod) => ({ default: mod.InsightsPage })))
const OpportunitiesPage = lazy(() => import('@/pages/Opportunities').then((mod) => ({ default: mod.OpportunitiesPage })))
const OverviewPage = lazy(() => import('@/pages/Overview').then((mod) => ({ default: mod.OverviewPage })))
const ReportsPage = lazy(() => import('@/pages/Reports').then((mod) => ({ default: mod.ReportsPage })))
const ScenarioLabPage = lazy(() => import('@/pages/ScenarioLab').then((mod) => ({ default: mod.ScenarioLabPage })))
const SecurityPage = lazy(() => import('@/pages/Security').then((mod) => ({ default: mod.SecurityPage })))
const SettingsPage = lazy(() => import('@/pages/Settings').then((mod) => ({ default: mod.SettingsPage })))
const TransactionsPage = lazy(() => import('@/pages/Transactions').then((mod) => ({ default: mod.TransactionsPage })))

function Protected() {
  const { me, loading } = useAuth()
  if (loading)
    return (
      <div className="p-8">
        <PageSkeleton />
      </div>
    )
  if (!me) return <Navigate to="/login" replace />
  return <AppShell />
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<Protected />}>
        <Route index element={<OverviewPage />} />
        <Route path="transactions" element={<TransactionsPage />} />
        <Route path="data-health" element={<DataHealthPage />} />
        <Route path="insights" element={<InsightsPage />} />
        <Route path="opportunities" element={<OpportunitiesPage />} />
        <Route path="scenarios" element={<ScenarioLabPage />} />
        <Route path="reports" element={<ReportsPage />} />
        <Route path="security" element={<SecurityPage />} />
        <Route path="settings" element={<SettingsPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}
