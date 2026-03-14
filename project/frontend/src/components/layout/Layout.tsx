import { useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import OnboardingProvider from '@/components/onboarding/OnboardingProvider';
import PageAgentButton from '@/components/page-agent/PageAgentButton';
import { useAuthStore } from '@/stores/authStore';

export default function Layout() {
  const loadUser = useAuthStore((s) => s.loadUser);
  const user = useAuthStore((s) => s.user);

  useEffect(() => {
    if (!user) loadUser();
  }, [user, loadUser]);

  return (
    <div className="flex h-screen overflow-hidden bg-slate-950">
      <Sidebar />
      <main className="flex-1 overflow-y-auto">
        <Outlet />
      </main>
      <OnboardingProvider />
      <PageAgentButton />
    </div>
  );
}
