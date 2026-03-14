import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  BookOpen,
  Copy,
  TrendingUp,
  GraduationCap,
  Trophy,
  Users,
  Loader2,
  AlertCircle,
} from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart,
  Bar,
} from 'recharts';
import StatCard from '@/components/dashboard/StatCard';
import { dashboardService } from '@/services/dashboard';
import type { DashboardOverview, ScriptRanking, TeamStats } from '@/types';

interface TrendItem {
  date: string;
  usage: number;
  conversion: number;
}

function formatDate(d: string) {
  const m = d.match(/(\d{4})-(\d{2})-(\d{2})/);
  return m ? `${m[2]}/${m[3]}` : d;
}

export default function DashboardPage() {
  const { t } = useTranslation();
  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [rankings, setRankings] = useState<ScriptRanking[]>([]);
  const [teamStats, setTeamStats] = useState<TeamStats[]>([]);
  const [usageTrendData, setUsageTrendData] = useState<TrendItem[]>([]);
  const [trainingTrendData, setTrainingTrendData] = useState<TrendItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string>('');

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      setError(null);
      try {
        const [overviewRes, rankingRes, teamRes, trendsRes] = await Promise.all([
          dashboardService.getOverview(),
          dashboardService.getScriptRanking(10),
          dashboardService.getTeamStats(),
          dashboardService.getTrends(7),
        ]);

        // 映射后端 Overview（today_usage_count 等）
        const ov = overviewRes as Record<string, unknown>;
        setOverview({
          total_scripts: (ov?.total_scripts as number) ?? 0,
          today_usage: (ov?.today_usage_count as number) ?? 0,
          avg_conversion_rate: (ov?.avg_conversion_rate as number) ?? 0,
          training_completion_rate: (ov?.training_completion_rate as number) ?? 0,
          scripts_trend: 0,
          usage_trend: 0,
          conversion_trend: 0,
          training_trend: 0,
        });

        // 后端返回 by_usage，映射为 rankings（conversion_rate 作 success_rate）
        const rank = rankingRes as { by_usage?: Array<{ script_id: string; title: string; category?: string; usage_count: number; conversion_rate: number }> };
        const list = rank?.by_usage ?? [];
        setRankings(
          list.map((r) => ({
            script_id: r.script_id,
            title: r.title,
            usage_count: r.usage_count,
            success_rate: r.conversion_rate ?? 0,
            category: r.category ?? '',
          }))
        );

        // 后端 members: username, training_accuracy
        const team = teamRes as { members?: Array<{ user_id: string; username: string; scripts_used: number; training_accuracy: number }> };
        const members = team?.members ?? [];
        const sorted = members
          .map((m) => ({
            user_id: m.user_id,
            name: m.username,
            scripts_used: m.scripts_used,
            training_score: Math.round((m.training_accuracy ?? 0) * 100),
            conversion_rate: 0,
            rank: 0,
          }))
          .sort((a, b) => b.scripts_used - a.scripts_used);
        sorted.forEach((m, i) => {
          m.rank = i + 1;
        });
        setTeamStats(sorted);

        // 后端 trends: usage_trend, training_trend 为 [{date, value}]
        const trends = trendsRes as {
          usage_trend?: Array<{ date: string; value: number }>;
          training_trend?: Array<{ date: string; value: number }>;
        };
        const usageList = trends?.usage_trend ?? [];
        const trainingList = trends?.training_trend ?? [];
        setUsageTrendData(
          usageList.map((t) => ({ date: formatDate(t.date), usage: t.value, conversion: 0 }))
        );
        setTrainingTrendData(
          trainingList.map((t) => ({ date: formatDate(t.date), usage: 0, conversion: t.value }))
        );

        setLastUpdated(new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }));
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : t('common.loadDataFailed');
        setError(msg);
      } finally {
        setLoading(false);
      }
    }

    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="p-4 flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-3 text-slate-400">
          <Loader2 className="w-8 h-8 animate-spin text-indigo-400" />
          <p className="text-xs">{t('dashboard.loadingData')}</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 flex items-center justify-center min-h-[400px]">
        <div className="flex flex-col items-center gap-4 text-slate-400 max-w-md text-center">
          <AlertCircle className="w-10 h-10 text-amber-400" />
          <p className="text-slate-200 font-medium text-sm">{t('dashboard.loadFailed')}</p>
          <p className="text-xs">{error}</p>
        </div>
      </div>
    );
  }

  const defaultOverview: DashboardOverview = {
    total_scripts: 0,
    today_usage: 0,
    avg_conversion_rate: 0,
    training_completion_rate: 0,
    scripts_trend: 0,
    usage_trend: 0,
    conversion_trend: 0,
    training_trend: 0,
  };

  const ov = overview ?? defaultOverview;

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-lg font-bold text-slate-100">{t('dashboard.title')}</h1>
        <span className="text-xs text-slate-500">
          {t('dashboard.lastUpdated')}：{lastUpdated || t('dashboard.justNow')}
        </span>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-4 gap-4" data-tour="page-dashboard-stats">
        <StatCard
          title={t('dashboard.totalScripts')}
          value={ov.total_scripts}
          trend={ov.scripts_trend}
          icon={BookOpen}
          color="indigo"
        />
        <StatCard
          title={t('dashboard.todayUsage')}
          value={ov.today_usage}
          trend={ov.usage_trend}
          icon={Copy}
          color="cyan"
        />
        <StatCard
          title={t('dashboard.avgConversion')}
          value={`${(ov.avg_conversion_rate * 100).toFixed(1)}%`}
          trend={ov.conversion_trend}
          icon={TrendingUp}
          color="emerald"
        />
        <StatCard
          title={t('dashboard.trainingCompletion')}
          value={`${(ov.training_completion_rate * 100).toFixed(0)}%`}
          trend={ov.training_trend}
          icon={GraduationCap}
          color="amber"
        />
      </div>

      {/* Middle section */}
      <div className="grid grid-cols-2 gap-4">
        {/* Rankings */}
        <div className="glass-card p-4">
          <div className="flex items-center gap-2 mb-3">
            <Trophy className="w-4 h-4 text-amber-400" />
            <h2 className="text-sm font-semibold text-slate-200">{t('dashboard.scriptRanking')}</h2>
          </div>
          <div className="space-y-2">
            {rankings.length === 0 ? (
              <p className="text-xs text-slate-500 py-6 text-center">{t('dashboard.noScriptData')}</p>
            ) : (
              rankings.map((item, index) => (
                <div key={item.script_id} className="flex items-center gap-2">
                  <span
                    className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                      index === 0
                        ? 'bg-amber-500/20 text-amber-400'
                        : index === 1
                          ? 'bg-slate-400/20 text-slate-400'
                          : index === 2
                            ? 'bg-orange-500/20 text-orange-400'
                            : 'bg-slate-800 text-slate-500'
                    }`}
                  >
                    {index + 1}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-slate-200 truncate">{item.title}</p>
                    <p className="text-xs text-slate-500">{item.category}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-xs font-medium text-slate-300">{item.usage_count}</p>
                    <p className="text-xs text-emerald-400">{(item.success_rate * 100).toFixed(0)}%</p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Team stats */}
        <div className="glass-card p-4">
          <div className="flex items-center gap-2 mb-3">
            <Users className="w-4 h-4 text-indigo-400" />
            <h2 className="text-sm font-semibold text-slate-200">{t('dashboard.teamPerformance')}</h2>
          </div>
          <div className="space-y-2">
            {teamStats.length === 0 ? (
              <p className="text-xs text-slate-500 py-6 text-center">{t('dashboard.noTeamData')}</p>
            ) : (
              teamStats.map((member) => (
                <div key={member.user_id} className="flex items-center gap-2">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-xs font-bold">
                    {member.name.charAt(0)}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs text-slate-200">{member.name}</p>
                    <div className="flex gap-2 text-xs text-slate-500">
                      <span>{t('dashboard.scripts')} {member.scripts_used}</span>
                      <span>{t('dashboard.trainingLabel')} {member.training_score}{t('dashboard.points')}</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-xs font-medium text-emerald-400">
                      {(member.conversion_rate * 100).toFixed(0)}%
                    </p>
                    <p className="text-xs text-slate-500">{t('dashboard.conversionRate')}</p>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>

      {/* Trend chart */}
      <div className="grid grid-cols-2 gap-4">
        <div className="glass-card p-4">
          <h2 className="text-xs font-semibold text-slate-200 mb-3">{t('dashboard.usageTrend')}</h2>
          <ResponsiveContainer width="100%" height={240}>
            {usageTrendData.length === 0 ? (
              <div className="flex items-center justify-center h-full text-slate-500 text-xs">
                {t('dashboard.noTrendData')}
              </div>
            ) : (
              <AreaChart data={usageTrendData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: '8px',
                    color: '#e2e8f0',
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="usage"
                  stroke="#6366f1"
                  fill="url(#colorUsage)"
                  name={t('dashboard.usageCount')}
                />
                <defs>
                  <linearGradient id="colorUsage" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#6366f1" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
                  </linearGradient>
                </defs>
              </AreaChart>
            )}
          </ResponsiveContainer>
        </div>

        <div className="glass-card p-4">
          <h2 className="text-xs font-semibold text-slate-200 mb-3">{t('dashboard.conversionTrend')}</h2>
          <ResponsiveContainer width="100%" height={240}>
            {trainingTrendData.length === 0 ? (
              <div className="flex items-center justify-center h-full text-slate-500 text-xs">
                {t('dashboard.noTrendData')}
              </div>
            ) : (
              <BarChart data={trainingTrendData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                <XAxis dataKey="date" tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <YAxis tick={{ fill: '#94a3b8', fontSize: 12 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#1e293b',
                    border: '1px solid #334155',
                    borderRadius: '8px',
                    color: '#e2e8f0',
                  }}
                />
                <Bar dataKey="conversion" fill="#10b981" radius={[4, 4, 0, 0]} name={t('dashboard.conversionCount')} />
              </BarChart>
            )}
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
