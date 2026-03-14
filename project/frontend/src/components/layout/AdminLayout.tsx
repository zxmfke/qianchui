import { useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import AdminSidebar from './AdminSidebar';
import PageAgentButton from '@/components/page-agent/PageAgentButton';
import { useAuthStore } from '@/stores/authStore';

export default function AdminLayout() {
  const loadUser = useAuthStore((s) => s.loadUser);
  const user = useAuthStore((s) => s.user);

  useEffect(() => {
    if (!user) loadUser();
  }, [user, loadUser]);

  return (
    <div className="flex h-screen overflow-hidden bg-slate-950">
      <AdminSidebar />
      <main className="flex-1 overflow-y-auto min-w-0">
        <Outlet />
      </main>
      <PageAgentButton />
    </div>
  );
}
