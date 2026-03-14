import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from '@/stores/authStore';
import Layout from '@/components/layout/Layout';
import AdminLayout from '@/components/layout/AdminLayout';
import LoginPage from '@/pages/LoginPage';
import ChatPage from '@/pages/ChatPage';
import DashboardPage from '@/pages/DashboardPage';
import ScriptsPage from '@/pages/ScriptsPage';
import TrainingPage from '@/pages/TrainingPage';
import SimulationPage from '@/pages/SimulationPage';
import DiagnosisPage from '@/pages/DiagnosisPage';
import OptimizationPage from '@/pages/OptimizationPage';
import FlywheelPage from '@/pages/FlywheelPage';
import ChannelMaterialsPage from '@/pages/ChannelMaterialsPage';
import MemoryPage from '@/pages/MemoryPage';
import SettingsPage from '@/pages/SettingsPage';
import AdminDashboardPage from '@/pages/admin/AdminDashboardPage';
import AdminEnterprisesPage from '@/pages/admin/AdminEnterprisesPage';
import AdminAccountsPage from '@/pages/admin/AdminAccountsPage';
import AdminQueryPage from '@/pages/admin/AdminQueryPage';

function AuthGuard({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
}

function AdminGuard({ children }: { children: React.ReactNode }) {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const user = useAuthStore((s) => s.user);
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  if (user && user.role !== 'super_admin') {
    return <Navigate to="/" replace />;
  }
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      {/* Super Admin */}
      <Route
        path="/admin"
        element={
          <AdminGuard>
            <AdminLayout />
          </AdminGuard>
        }
      >
        <Route index element={<AdminDashboardPage />} />
        <Route path="enterprises" element={<AdminEnterprisesPage />} />
        <Route path="accounts" element={<AdminAccountsPage />} />
        <Route path="query" element={<AdminQueryPage />} />
      </Route>

      {/* Main App */}
      <Route
        path="/"
        element={
          <AuthGuard>
            <Layout />
          </AuthGuard>
        }
      >
        <Route index element={<Navigate to="/chat" replace />} />
        <Route path="chat" element={<ChatPage />} />
        <Route path="dashboard" element={<DashboardPage />} />
        <Route path="scripts" element={<ScriptsPage />} />
        <Route path="channel-materials" element={<ChannelMaterialsPage />} />
        <Route path="training" element={<TrainingPage />} />
        <Route path="simulation" element={<SimulationPage />} />
        <Route path="diagnosis" element={<DiagnosisPage />} />
        <Route path="optimization" element={<OptimizationPage />} />
        <Route path="flywheel" element={<FlywheelPage />} />
        <Route path="memory" element={<MemoryPage />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
