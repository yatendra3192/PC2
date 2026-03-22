import { useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './stores/authStore'
import Layout from './components/Layout'
import Toast from './components/Toast'
import ShortcutHelp from './components/ShortcutHelp'
import LoginPage from './pages/LoginPage'
import ForgotPasswordPage from './pages/ForgotPasswordPage'
import DashboardPage from './pages/DashboardPage'
import PlaceholderPage from './pages/PlaceholderPage'
import UploadPage from './pages/UploadPage'
import PipelinePage from './pages/PipelinePage'
import ReviewPage from './pages/ReviewPage'
import PublishedPage from './pages/PublishedPage'
import BatchDetailPage from './pages/BatchDetailPage'
import ClientsPage from './pages/admin/ClientsPage'
import UsersPage from './pages/admin/UsersPage'
import ConfidencePage from './pages/admin/ConfidencePage'
import ModelsPage from './pages/admin/ModelsPage'
import TemplatesAdminPage from './pages/admin/TemplatesPage'
import PipelineConfigPage from './pages/admin/PipelinePage'
import AuditPage from './pages/admin/AuditPage'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  return <>{children}</>
}

function App() {
  const { isAuthenticated, loadUser } = useAuthStore()

  useEffect(() => {
    if (isAuthenticated) loadUser()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <>
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />

      <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route index element={<Navigate to="/dashboard" replace />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="upload" element={<UploadPage />} />
        <Route path="batch" element={<BatchDetailPage />} />
        <Route path="pipeline" element={<PipelinePage />} />
        <Route path="review" element={<ReviewPage />} />
        <Route path="published" element={<PublishedPage />} />
        <Route path="admin/clients" element={<ClientsPage />} />
        <Route path="admin/users" element={<UsersPage />} />
        <Route path="admin/confidence" element={<ConfidencePage />} />
        <Route path="admin/models" element={<ModelsPage />} />
        <Route path="admin/templates" element={<TemplatesAdminPage />} />
        <Route path="admin/pipeline" element={<PipelineConfigPage />} />
        <Route path="admin/audit" element={<AuditPage />} />
      </Route>

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
    <Toast />
    <ShortcutHelp />
    </>
  )
}

export default App
