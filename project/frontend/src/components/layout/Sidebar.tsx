import { NavLink, useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import {
  MessageSquare,
  BarChart3,
  BookOpen,
  GraduationCap,
  Theater,
  Stethoscope,
  Brain,
  Settings,
  LogOut,
  Zap,
  RefreshCw,
  Share2,
  RotateCw,
  Shield,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/stores/authStore';

const navItems = [
  { to: '/chat', icon: MessageSquare, labelKey: 'nav.chat', tourId: 'nav-chat' },
  { to: '/dashboard', icon: BarChart3, labelKey: 'nav.dashboard', tourId: 'nav-dashboard' },
  { to: '/scripts', icon: BookOpen, labelKey: 'nav.scripts', tourId: 'nav-scripts' },
  { to: '/channel-materials', icon: Share2, labelKey: 'nav.channelMaterials', tourId: 'nav-channel-materials' },
  { to: '/training', icon: GraduationCap, labelKey: 'nav.training', tourId: 'nav-training' },
  { to: '/simulation', icon: Theater, labelKey: 'nav.simulation', tourId: 'nav-simulation' },
  { to: '/diagnosis', icon: Stethoscope, labelKey: 'nav.diagnosis', tourId: 'nav-diagnosis' },
  { to: '/optimization', icon: RefreshCw, labelKey: 'nav.optimization', tourId: 'nav-optimization' },
  { to: '/flywheel', icon: RotateCw, labelKey: 'nav.flywheel', tourId: 'nav-flywheel' },
  { to: '/memory', icon: Brain, labelKey: 'nav.memory', tourId: 'nav-memory' },
  { to: '/settings', icon: Settings, labelKey: 'nav.settings', tourId: 'nav-settings' },
];

export default function Sidebar() {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <aside className="w-56 h-screen flex flex-col bg-slate-900 border-r border-slate-800" data-tour="sidebar">
      {/* Logo */}
      <div className="p-4 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center">
            <Zap className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-base font-bold text-white leading-tight">{t('brand.name')}</h1>
            <p className="text-xs text-slate-400 leading-tight">{t('brand.subtitle')}</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-2 py-3 space-y-0.5 overflow-y-auto">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            data-tour={item.tourId}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200',
                isActive
                  ? 'bg-indigo-600/20 text-indigo-400 border border-indigo-500/30'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60',
              )
            }
          >
            <item.icon className="w-[18px] h-[18px] flex-shrink-0" />
            <span>{t(item.labelKey)}</span>
          </NavLink>
        ))}
      </nav>

      {/* Admin Entry */}
      {user?.role === 'super_admin' && (
        <div className="px-2 pb-2">
          <NavLink
            to="/admin"
            className={({ isActive }) =>
              cn(
                'flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-200',
                isActive
                  ? 'bg-amber-600/20 text-amber-400 border border-amber-500/30'
                  : 'text-amber-400/70 hover:text-amber-400 hover:bg-amber-500/10 border border-transparent',
              )
            }
          >
            <Shield className="w-[18px] h-[18px] flex-shrink-0" />
            <span>{t('nav.adminPanel')}</span>
          </NavLink>
        </div>
      )}

      {/* User */}
      <div className="p-3 border-t border-slate-800">
        <div className="flex items-center gap-2.5 px-2 py-1.5">
          <div className="w-8 h-8 rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center text-white text-sm font-bold">
            {user?.name?.charAt(0) || 'U'}
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm text-slate-200 truncate">{user?.name || '用户'}</p>
            <p className="text-xs text-slate-500 truncate">{user?.role || 'agent'}</p>
          </div>
          <button
            onClick={handleLogout}
            className="p-1.5 rounded-lg text-slate-500 hover:text-red-400 hover:bg-slate-800 transition-colors"
            title={t('auth.logout')}
          >
            <LogOut className="w-4 h-4" />
          </button>
        </div>
      </div>
    </aside>
  );
}
