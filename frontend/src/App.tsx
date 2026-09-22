import { Route, Routes } from 'react-router-dom'
import { AppShell } from '@/components/layout/AppShell'
import { useSession } from '@/lib/auth/SessionContext'
import { LoginPage } from '@/pages/LoginPage'
import { DashboardPage } from '@/pages/DashboardPage'
import { CopilotPage } from '@/pages/CopilotPage'
import { OpportunitiesPage } from '@/pages/OpportunitiesPage'
import { TransactionsPage } from '@/pages/TransactionsPage'
import { ActivityPage } from '@/pages/ActivityPage'
import { SettingsPage } from '@/pages/SettingsPage'

export function App() {
  const session = useSession()

  if (session.status !== 'ready') {
    return <LoginPage />
  }

  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<DashboardPage />} />
        <Route path="copilot" element={<CopilotPage />} />
        <Route path="opportunities" element={<OpportunitiesPage />} />
        <Route path="transactions" element={<TransactionsPage />} />
        <Route path="activity" element={<ActivityPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  )
}
