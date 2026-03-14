import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Building2,
  Users,
  BookOpen,
  MessageSquare,
  GraduationCap,
  Theater,
  Stethoscope,
  Share2,
  TrendingUp,
  TrendingDown,
  Activity,
  Loader2,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import { adminService, type SystemOverview, type DailyStats } from '@/services/admin';

interface StatCardProps {
  icon: React.ElementType;
  label: string;
  value: number;
  subLabel?: string;
  subValue?: number;
  color: string;
  bgColor: string;
}

function StatCard({ icon: Icon, label, value, subLabel, subValue, color, bgColor }: StatCardProps) {
  return (
    <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-4 hover:border-slate-600/60 transition-colors">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-slate-400 mb-1">{label}</p>
          <p className="text-2xl font-bold text-slate-100 tabular-nums">{value.toLocaleString()}</p>
          {subLabel && (
            <p className="text-xs text-slate-500 mt-1">
              {subLabel}: <span className={color}>{subValue?.toLocaleString()}</span>
            </p>
          )}
        </div>
        <div className={cn('w-10 h-10 rounded-xl flex items-center justify-center', bgColor)}>
          <Icon className={cn('w-5 h-5', color)} />
        </div>
      </div>
    </div>
  );
}

export default function AdminDashboardPage() {
  const { t } = useTranslation();
  const [overview, setOverview] = useState<SystemOverview | null>(null);
  const [trends, setTrends] = useState<DailyStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [trendDays, setTrendDays] = useState(30);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      adminService.getOverview(),
      adminService.getTrends(trendDays),
    ])
      .then(([ov, tr]) => {
        setOverview(ov);
        setTrends(tr.daily_stats);
      })
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [trendDays]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="w-8 h-8 text-amber-400 animate-spin" />
      </div>
    );
  }

  if (!overview) return null;

  const statCards: StatCardProps[] = [
    {
      icon: Building2, label: t('admin.overview.totalEnterprises'), value: overview.total_enterprises,
      subLabel: t('admin.overview.active'), subValue: overview.active_enterprises,
      color: 'text-amber-400', bgColor: 'bg-amber-500/10',
    },
    {
      icon: Users, label: t('admin.overview.totalUsers'), value: overview.total_users,
      subLabel: t('admin.overview.active'), subValue: overview.active_users,
      color: 'text-blue-400', bgColor: 'bg-blue-500/10',
    },
    {
      icon: BookOpen, label: t('admin.overview.totalScripts'), value: overview.total_scripts,
      color: 'text-emerald-400', bgColor: 'bg-emerald-500/10',
    },
    {
      icon: MessageSquare, label: t('admin.overview.totalConversations'), value: overview.total_conversations,
      subLabel: t('admin.overview.messages'), subValue: overview.total_messages,
      color: 'text-purple-400', bgColor: 'bg-purple-500/10',
    },
    {
      icon: GraduationCap, label: t('admin.overview.totalTraining'), value: overview.total_training_records,
      color: 'text-cyan-400', bgColor: 'bg-cyan-500/10',
    },
    {
      icon: Theater, label: t('admin.overview.totalSimulations'), value: overview.total_simulations,
      color: 'text-pink-400', bgColor: 'bg-pink-500/10',
    },
    {
      icon: Stethoscope, label: t('admin.overview.totalDiagnosis'), value: overview.total_diagnosis_reports,
      color: 'text-orange-400', bgColor: 'bg-orange-500/10',
    },
    {
      icon: Share2, label: t('admin.overview.totalMaterials'), value: overview.total_channel_materials,
      color: 'text-indigo-400', bgColor: 'bg-indigo-500/10',
    },
  ];

  const chartData = trends.map((d) => ({
    date: d.date.slice(5),
    [t('admin.overview.newEnterprises')]: d.new_enterprises,
    [t('admin.overview.newUsers')]: d.new_users,
    [t('admin.overview.newScripts')]: d.new_scripts,
    [t('admin.overview.newConversations')]: d.new_conversations,
  }));

  return (
    <div className="p-4 sm:p-6 space-y-4 sm:space-y-6 max-w-[1400px] w-full pt-14 lg:pt-4 sm:pt-6">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-slate-100">{t('admin.overview.title')}</h1>
        <p className="text-sm text-slate-400 mt-1">{t('admin.overview.subtitle')}</p>
      </div>

      {/* Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        {statCards.map((card) => (
          <StatCard key={card.label} {...card} />
        ))}
      </div>

      {/* Trend Chart */}
      <div className="bg-slate-800/60 border border-slate-700/50 rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-amber-400" />
            <h2 className="text-sm font-semibold text-slate-200">{t('admin.overview.growthTrend')}</h2>
          </div>
          <div className="flex items-center gap-1">
            {[7, 14, 30].map((d) => (
              <button
                key={d}
                onClick={() => setTrendDays(d)}
                className={cn(
                  'px-2.5 py-1 rounded-md text-xs transition-colors',
                  trendDays === d
                    ? 'bg-amber-600/20 text-amber-400'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/50',
                )}
              >
                {d}{t('admin.overview.days')}
              </button>
            ))}
          </div>
        </div>
        <div className="h-[200px] sm:h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="gradEnterprise" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gradUser" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gradScript" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gradConv" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#a855f7" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#a855f7" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
              <XAxis dataKey="date" stroke="#64748b" fontSize={11} />
              <YAxis stroke="#64748b" fontSize={11} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #334155',
                  borderRadius: '8px',
                  fontSize: '12px',
                }}
              />
              <Legend wrapperStyle={{ fontSize: '12px' }} />
              <Area
                type="monotone"
                dataKey={t('admin.overview.newEnterprises')}
                stroke="#f59e0b"
                fill="url(#gradEnterprise)"
                strokeWidth={2}
              />
              <Area
                type="monotone"
                dataKey={t('admin.overview.newUsers')}
                stroke="#3b82f6"
                fill="url(#gradUser)"
                strokeWidth={2}
              />
              <Area
                type="monotone"
                dataKey={t('admin.overview.newScripts')}
                stroke="#10b981"
                fill="url(#gradScript)"
                strokeWidth={2}
              />
              <Area
                type="monotone"
                dataKey={t('admin.overview.newConversations')}
                stroke="#a855f7"
                fill="url(#gradConv)"
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
