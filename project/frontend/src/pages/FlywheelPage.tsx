import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  TrendingUp, TrendingDown, Minus, AlertTriangle, Package,
  Users, FileText, ArrowRight, Sparkles, BarChart3, Loader2,
  Activity, Clock, CheckCircle2, Zap, RefreshCw, Settings,
} from 'lucide-react';
import { flywheelApi } from '@/services/flywheel';
import type {
  PainPointTrendView,
  ProductStrategyView,
  ServiceStrategyView,
  ScriptLifecycleView,
  FlywheelDashboard,
  FlywheelEvent,
  FlywheelHealth,
} from '@/services/flywheel';

type Tab = 'overview' | 'pain_points' | 'products' | 'services' | 'scripts' | 'events';

const TREND_ICON: Record<string, React.ReactNode> = {
  rising: <TrendingUp className="w-4 h-4 text-red-500" />,
  falling: <TrendingDown className="w-4 h-4 text-blue-500" />,
  stable: <Minus className="w-4 h-4 text-slate-500" />,
  new: <Sparkles className="w-4 h-4 text-orange-500" />,
};

const LIFECYCLE_COLOR: Record<string, string> = {
  draft: 'bg-slate-500/20 text-slate-400',
  review: 'bg-yellow-500/20 text-yellow-400',
  active: 'bg-green-500/20 text-green-400',
  declining: 'bg-red-500/20 text-red-400',
  archived: 'bg-slate-600/20 text-slate-500',
};

const EVENT_TYPE_LABELS: Record<string, { label: string; color: string; icon: React.ReactNode }> = {
  diagnosis_completed: { label: '完成诊断', color: 'text-blue-400', icon: <Stethoscope className="w-3.5 h-3.5" /> },
  pain_point_sense: { label: '痛点感知', color: 'text-orange-400', icon: <Activity className="w-3.5 h-3.5" /> },
  optimization_strategies_generated: { label: '生成策略', color: 'text-purple-400', icon: <Zap className="w-3.5 h-3.5" /> },
  strategy_status_changed: { label: '策略变更', color: 'text-emerald-400', icon: <CheckCircle2 className="w-3.5 h-3.5" /> },
  cascade_reviewed: { label: '联动审核', color: 'text-pink-400', icon: <Settings className="w-3.5 h-3.5" /> },
};

function Stethoscope(props: React.SVGProps<SVGSVGElement> & { className?: string }) {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}>
      <path d="M4.8 2.3A.3.3 0 1 0 5 2H4a2 2 0 0 0-2 2v5a6 6 0 0 0 6 6v0a6 6 0 0 0 6-6V4a2 2 0 0 0-2-2h-1a.2.2 0 1 0 .3.3" />
      <path d="M8 15v1a6 6 0 0 0 6 6v0a6 6 0 0 0 6-6v-4" />
      <circle cx="20" cy="10" r="2" />
    </svg>
  );
}

export default function FlywheelPage() {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [dashboard, setDashboard] = useState<FlywheelDashboard | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [senseLoading, setSenseLoading] = useState(false);
  const [senseResult, setSenseResult] = useState<string | null>(null);

  const tabs: { key: Tab; label: string }[] = [
    { key: 'overview', label: t('flywheel.tabs.overview') },
    { key: 'pain_points', label: t('flywheel.tabs.painPoints') },
    { key: 'products', label: t('flywheel.tabs.products') },
    { key: 'services', label: t('flywheel.tabs.services') },
    { key: 'scripts', label: t('flywheel.tabs.scripts') },
    { key: 'events', label: '事件日志' },
  ];

  const fetchDashboard = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await flywheelApi.getDashboard();
      setDashboard(res.data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t('common.loadFailed'));
      setDashboard(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboard();
  }, []);

  const handleTriggerSense = async () => {
    setSenseLoading(true);
    setSenseResult(null);
    try {
      const res = await flywheelApi.triggerSense(30);
      const data = res.data as Record<string, unknown>;
      const msg = `扫描完成：分析了${data.reports_analyzed ?? 0}份报告，` +
        `更新${data.updates_applied ?? 0}个痛点，` +
        `新发现${data.new_pain_points_created ?? 0}个痛点` +
        (data.should_cascade ? '，已触发策略联动' : '');
      setSenseResult(msg);
      await fetchDashboard();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : t('flywheel.scanFailed'));
    } finally {
      setSenseLoading(false);
    }
  };

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-slate-100">{t('flywheel.title')}</h1>
          <p className="text-xs text-slate-500 mt-1">{t('flywheel.subtitle')}</p>
        </div>
        <button
          onClick={handleTriggerSense}
          disabled={senseLoading}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm hover:bg-indigo-700 disabled:opacity-50 flex items-center gap-2"
        >
          {senseLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <RefreshCw className="w-4 h-4" />}
          {t('flywheel.scanNow')}
        </button>
      </div>

      {senseResult && (
        <div className="p-3 bg-emerald-500/10 border border-emerald-500/30 rounded-lg text-emerald-400 text-sm flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
          {senseResult}
        </div>
      )}

      {error && (
        <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      <div className="border-b border-slate-700">
        <nav className="flex gap-4">
          {tabs.map(tab => (
            <button key={tab.key} onClick={() => setActiveTab(tab.key)}
              className={`pb-3 text-sm font-medium border-b-2 transition ${
                activeTab === tab.key
                  ? 'border-indigo-500 text-indigo-400'
                  : 'border-transparent text-slate-500 hover:text-slate-200'
              }`}>
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-8 h-8 text-slate-500 animate-spin" />
        </div>
      ) : (
        <>
          {activeTab === 'overview' && dashboard && <OverviewSection dashboard={dashboard} />}
          {activeTab === 'pain_points' && dashboard && <PainPointSection painPoints={dashboard.pain_point_trends} />}
          {activeTab === 'products' && dashboard && <ProductSection products={dashboard.product_strategies} painPoints={dashboard.pain_point_trends} />}
          {activeTab === 'services' && dashboard && <ServiceSection services={dashboard.service_strategies} />}
          {activeTab === 'scripts' && dashboard && <ScriptSection scripts={dashboard.script_lifecycles} />}
          {activeTab === 'events' && dashboard && <EventsSection events={dashboard.recent_events} totalEvents={dashboard.total_events} />}
        </>
      )}
    </div>
  );
}

function OverviewSection({ dashboard }: { dashboard: FlywheelDashboard }) {
  const { t } = useTranslation();
  const {
    pain_point_trends = [], product_strategies = [], service_strategies = [],
    new_pain_points_pending = 0, scenario_gaps = 0, scripts_declining = 0,
    scripts_added_this_week = 0, flywheel_health, recent_events = [],
    total_events = 0, total_diagnosis = 0, script_lifecycles = [],
    pending_cascades = [],
  } = dashboard;
  const gapServices = service_strategies.filter(s => s.has_scenario_gap);

  return (
    <div className="space-y-4">
      {/* 飞轮健康度 */}
      <FlywheelHealthCard health={flywheel_health} totalEvents={total_events} totalDiagnosis={total_diagnosis} />

      {/* 齿轮一 */}
      <GearSection icon={<BarChart3 className="w-4 h-4" />} title={t('flywheel.gear1')}
        gearScore={flywheel_health?.gear_scores?.pain_points}
        badge={new_pain_points_pending > 0 ? (
          <span className="text-xs bg-orange-500/20 text-orange-400 px-2 py-0.5 rounded-full">{t('flywheel.newPainPoints', { count: new_pain_points_pending })}</span>
        ) : undefined}>
        {pain_point_trends.length > 0 ? (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {pain_point_trends.map(p => (
              <div key={p.id} className="p-3 bg-slate-800/50 rounded-lg border border-slate-700">
                <div className="flex items-center gap-1.5">
                  {TREND_ICON[p.trend_label]}
                  <span className="font-medium text-sm text-slate-200">{p.name}</span>
                </div>
                <div className="mt-1 text-xs text-slate-500">
                  {p.mention_count_current}{t('flywheel.perWeek')}
                  <span className={p.change_rate > 0 ? 'text-red-400 ml-1' : p.change_rate < 0 ? 'text-blue-400 ml-1' : 'ml-1 text-slate-400'}>
                    {p.change_rate > 0 ? '+' : ''}{(p.change_rate * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyGear hint="诊断对话后，系统将自动感知客户痛点趋势变化" />
        )}
      </GearSection>

      <ArrowDown />

      {/* 齿轮二 */}
      <GearSection icon={<Package className="w-4 h-4" />} title={t('flywheel.gear2')}
        gearScore={flywheel_health?.gear_scores?.products}>
        {product_strategies.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {product_strategies.map(p => (
              <div key={p.id} className="p-3 bg-slate-800/50 rounded-lg border border-slate-700 flex justify-between items-start">
                <div>
                  <div className="font-medium text-sm text-slate-200">{p.name}</div>
                  <div className="text-xs text-slate-500 mt-0.5">{p.priority_reason || '-'}</div>
                </div>
                <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                  p.dynamic_priority === 'P0' ? 'bg-red-500/20 text-red-400' : 'bg-yellow-500/20 text-yellow-400'
                }`}>{p.dynamic_priority}</span>
              </div>
            ))}
          </div>
        ) : (
          <EmptyGear hint="在「企业记忆」中添加产品，系统将根据痛点动态调整优先级" />
        )}
      </GearSection>

      <ArrowDown />

      {/* 齿轮三 */}
      <GearSection icon={<Users className="w-4 h-4" />} title={t('flywheel.gear3')}
        gearScore={flywheel_health?.gear_scores?.services}
        badge={scenario_gaps > 0 ? (
          <span className="text-xs bg-orange-500/20 text-orange-400 px-2 py-0.5 rounded-full">{t('flywheel.scenarioGaps', { count: scenario_gaps })}</span>
        ) : undefined}>
        {service_strategies.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {service_strategies.filter(s => !s.has_scenario_gap).map(s => (
              <div key={s.id} className="p-3 bg-slate-800/50 rounded-lg border border-slate-700">
                <div className="font-medium text-sm text-slate-200">{s.name}</div>
                <div className="text-xs text-slate-500 mt-0.5">{t('flywheel.usage')} {s.usage_count} · {t('flywheel.effectiveness')} {(s.effectiveness * 100).toFixed(0)}%</div>
              </div>
            ))}
            {gapServices.map(s => (
              <div key={s.id} className="p-3 bg-orange-500/10 border border-orange-500/30 rounded-lg">
                <div className="flex items-center gap-1">
                  <AlertTriangle className="w-4 h-4 text-orange-400" />
                  <span className="font-medium text-sm text-orange-400">{t('flywheel.missingScenario', { name: s.name })}</span>
                </div>
                <div className="text-xs text-orange-500/80 mt-0.5">{s.gap_description || t('flywheel.painRisingNoService')}</div>
              </div>
            ))}
          </div>
        ) : (
          <EmptyGear hint="在「企业记忆」中添加服务，系统将识别场景缺口" />
        )}
      </GearSection>

      <ArrowDown />

      {/* 齿轮四 */}
      <GearSection icon={<FileText className="w-4 h-4" />} title={t('flywheel.gear4')}
        gearScore={flywheel_health?.gear_scores?.scripts}>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <StatCard label={t('flywheel.addedThisWeek')} value={`${scripts_added_this_week}${t('flywheel.count')}`} sub={t('flywheel.flywheelDriven')} />
          <StatCard label={t('flywheel.decliningWarning')} value={`${scripts_declining}${t('flywheel.count')}`} sub={t('flywheel.relatedPainDecline')} alert={scripts_declining > 0} />
          <StatCard label={t('flywheel.totalScripts')} value={`${script_lifecycles.length}${t('flywheel.count')}`} sub={t('flywheel.fullLifecycle')} />
          <StatCard label={t('flywheel.pendingCascade')} value={`${pending_cascades.length}${t('flywheel.items')}`} sub={t('flywheel.cascadePlan')} positive={pending_cascades.length > 0} />
        </div>
      </GearSection>

      {/* 最近事件时间线 */}
      {recent_events.length > 0 && (
        <div className="bg-slate-800/30 rounded-lg border border-slate-700 p-4">
          <div className="flex items-center gap-2 mb-3">
            <Clock className="w-4 h-4 text-indigo-400" />
            <h3 className="font-semibold text-slate-200">飞轮事件时间线</h3>
            <span className="text-xs text-slate-500">最近{recent_events.length}条 / 共{total_events}条</span>
          </div>
          <EventTimeline events={recent_events.slice(0, 6)} />
        </div>
      )}
    </div>
  );
}

function FlywheelHealthCard({ health, totalEvents, totalDiagnosis }: {
  health: FlywheelHealth;
  totalEvents: number;
  totalDiagnosis: number;
}) {
  if (!health) return null;

  const statusColors: Record<string, string> = {
    healthy: 'from-emerald-500/20 to-emerald-500/5 border-emerald-500/30',
    warming: 'from-amber-500/20 to-amber-500/5 border-amber-500/30',
    cold: 'from-blue-500/20 to-blue-500/5 border-blue-500/30',
    inactive: 'from-slate-500/20 to-slate-500/5 border-slate-500/30',
  };
  const scoreColors: Record<string, string> = {
    healthy: 'text-emerald-400',
    warming: 'text-amber-400',
    cold: 'text-blue-400',
    inactive: 'text-slate-400',
  };

  return (
    <div className={`bg-gradient-to-r ${statusColors[health.status]} border rounded-lg p-4`}>
      <div className="flex items-center gap-4">
        {/* 健康分 */}
        <div className="flex flex-col items-center">
          <div className="relative w-20 h-20 flex items-center justify-center">
            <svg className="w-full h-full -rotate-90" viewBox="0 0 80 80">
              <circle cx="40" cy="40" r="34" fill="none" stroke="currentColor" strokeWidth="6" className="text-slate-700" />
              <circle cx="40" cy="40" r="34" fill="none" strokeWidth="6" strokeLinecap="round"
                className={health.status === 'healthy' ? 'stroke-emerald-400' :
                  health.status === 'warming' ? 'stroke-amber-400' :
                  health.status === 'cold' ? 'stroke-blue-400' : 'stroke-slate-400'}
                strokeDasharray={`${(health.overall_score / 100) * 213.6} 213.6`}
              />
            </svg>
            <span className={`absolute text-xl font-bold ${scoreColors[health.status]}`}>
              {health.overall_score}
            </span>
          </div>
          <span className={`text-xs font-medium mt-1 ${scoreColors[health.status]}`}>{health.label}</span>
        </div>

        {/* 四个齿轮分数 */}
        <div className="flex-1 grid grid-cols-4 gap-2">
          {[
            { key: 'pain_points', label: '痛点感知', icon: <BarChart3 className="w-3 h-3" /> },
            { key: 'products', label: '产品策略', icon: <Package className="w-3 h-3" /> },
            { key: 'services', label: '服务策略', icon: <Users className="w-3 h-3" /> },
            { key: 'scripts', label: '话术策略', icon: <FileText className="w-3 h-3" /> },
          ].map(gear => {
            const score = health.gear_scores[gear.key as keyof typeof health.gear_scores] ?? 0;
            return (
              <div key={gear.key} className="text-center">
                <div className="flex items-center justify-center gap-1 text-xs text-slate-400 mb-1">
                  {gear.icon} {gear.label}
                </div>
                <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${
                      score >= 80 ? 'bg-emerald-500' : score >= 50 ? 'bg-amber-500' : score > 0 ? 'bg-blue-500' : 'bg-slate-600'
                    }`}
                    style={{ width: `${score}%` }}
                  />
                </div>
                <div className="text-xs text-slate-300 mt-0.5">{score}分</div>
              </div>
            );
          })}
        </div>

        {/* 数据流 */}
        <div className="text-center px-4 border-l border-slate-700">
          <div className="text-xs text-slate-400 mb-1">数据流</div>
          <div className="text-lg font-bold text-slate-100">{health.data_flow_score}</div>
          <div className="text-xs text-slate-500">{totalDiagnosis}次诊断 · {totalEvents}个事件</div>
        </div>
      </div>

      {health.bottleneck && (
        <div className="mt-3 p-2 bg-amber-500/10 border border-amber-500/20 rounded text-xs text-amber-400 flex items-center gap-2">
          <AlertTriangle className="w-3 h-3 flex-shrink-0" />
          <span>瓶颈：{health.bottleneck.gear}（{health.bottleneck.score}分）— {health.bottleneck.suggestion}</span>
        </div>
      )}
    </div>
  );
}

function EventTimeline({ events }: { events: FlywheelEvent[] }) {
  return (
    <div className="space-y-0">
      {events.map((event, idx) => {
        const meta = EVENT_TYPE_LABELS[event.event_type] || {
          label: event.event_type,
          color: 'text-slate-400',
          icon: <Activity className="w-3.5 h-3.5" />,
        };

        const summaryParts: string[] = [];
        const rs = event.result_summary || {};
        if (rs.overall_score != null) summaryParts.push(`评分${rs.overall_score}`);
        if (rs.strategies_count != null) summaryParts.push(`${rs.strategies_count}个策略`);
        if (rs.updates_applied != null) summaryParts.push(`更新${rs.updates_applied}个痛点`);
        if (rs.new_pain_points != null && Number(rs.new_pain_points) > 0)
          summaryParts.push(`新发现${rs.new_pain_points}个`);
        if (rs.status != null) summaryParts.push(`状态→${rs.status}`);

        return (
          <div key={event.id} className="flex items-start gap-3">
            <div className="flex flex-col items-center">
              <div className={`w-7 h-7 rounded-full flex items-center justify-center bg-slate-800 border border-slate-600 ${meta.color}`}>
                {meta.icon}
              </div>
              {idx < events.length - 1 && <div className="w-px h-6 bg-slate-700" />}
            </div>
            <div className="flex-1 pb-2">
              <div className="flex items-center gap-2">
                <span className={`text-xs font-medium ${meta.color}`}>{meta.label}</span>
                {summaryParts.length > 0 && (
                  <span className="text-xs text-slate-500">{summaryParts.join(' · ')}</span>
                )}
              </div>
              <div className="text-xs text-slate-600 mt-0.5">
                {event.created_at ? new Date(event.created_at).toLocaleString() : ''}
                {event.trigger_type === 'user_action' && ' · 用户操作'}
                {event.trigger_type === 'manual' && ' · 手动触发'}
                {event.trigger_type === 'automatic' && ' · 自动触发'}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function EventsSection({ events, totalEvents }: { events: FlywheelEvent[]; totalEvents: number }) {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-base font-semibold text-slate-200">飞轮事件日志</h2>
        <span className="text-xs text-slate-500">共 {totalEvents} 条事件</span>
      </div>

      {events.length === 0 ? (
        <div className="bg-slate-900 rounded-lg border border-slate-800 p-8 text-center">
          <Clock className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <p className="text-sm text-slate-400">暂无飞轮事件</p>
          <p className="text-xs text-slate-500 mt-1">诊断对话、触发感知扫描、采纳优化策略都会产生飞轮事件</p>
        </div>
      ) : (
        <div className="bg-slate-900 rounded-lg border border-slate-800 p-4">
          <EventTimeline events={events} />
        </div>
      )}
    </div>
  );
}

function PainPointSection({ painPoints }: { painPoints: PainPointTrendView[] }) {
  const { t } = useTranslation();
  return (
    <div className="space-y-4">
      <h2 className="text-base font-semibold text-slate-200">{t('flywheel.painPointData')}</h2>
      {painPoints.length === 0 ? (
        <EmptyState hint="暂无痛点数据。在「企业记忆」中添加痛点，或通过诊断对话自动发现。" />
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-700 text-left text-slate-500">
                <th className="pb-2">{t('flywheel.painPointName')}</th>
                <th className="pb-2">{t('flywheel.trend')}</th>
                <th className="pb-2">{t('flywheel.thisWeekMention')}</th>
                <th className="pb-2">{t('flywheel.lastWeekMention')}</th>
                <th className="pb-2">{t('flywheel.changeRate')}</th>
                <th className="pb-2">{t('flywheel.relatedProducts')}</th>
                <th className="pb-2">{t('flywheel.relatedScripts')}</th>
                <th className="pb-2">{t('flywheel.evidenceKeywords')}</th>
              </tr>
            </thead>
            <tbody>
              {painPoints.map(p => (
                <tr key={p.id} className="border-b border-slate-700 hover:bg-slate-800/50">
                  <td className="py-3 font-medium text-slate-200">{p.name}</td>
                  <td className="py-3">
                    <span className="flex items-center gap-1 text-slate-300">
                      {TREND_ICON[p.trend_label]}
                      {t(`flywheel.trends.${p.trend_label}`) || p.trend_label}
                    </span>
                  </td>
                  <td className="py-3 text-slate-300">{p.mention_count_current}</td>
                  <td className="py-3 text-slate-300">{p.mention_count_previous}</td>
                  <td className={`py-3 font-medium ${
                    p.change_rate > 0 ? 'text-red-400' : p.change_rate < 0 ? 'text-blue-400' : 'text-slate-400'
                  }`}>
                    {p.change_rate > 0 ? '+' : ''}{(p.change_rate * 100).toFixed(0)}%
                  </td>
                  <td className="py-3 text-slate-300">{p.related_product_count}{t('flywheel.items')}</td>
                  <td className="py-3 text-slate-300">{p.related_script_count}{t('flywheel.count')}</td>
                  <td className="py-3">
                    <div className="flex gap-1 flex-wrap">
                      {(p.evidence_keywords || []).map(k => (
                        <span key={k} className="text-xs bg-slate-700 text-slate-400 px-1.5 py-0.5 rounded">{k}</span>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function ProductSection({ products, painPoints }: { products: ProductStrategyView[]; painPoints: PainPointTrendView[] }) {
  const { t } = useTranslation();
  if (products.length === 0 && painPoints.length === 0) {
    return <EmptyState hint="暂无产品数据。在「企业记忆」中添加产品并关联痛点。" />;
  }
  return (
    <div className="space-y-4">
      <h2 className="text-base font-semibold text-slate-200">{t('flywheel.productCoverage')}</h2>
      <p className="text-sm text-slate-500">{t('flywheel.productCoverageDesc')}</p>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700 text-left text-slate-500">
              <th className="pb-2">{t('flywheel.painVsProduct')}</th>
              {products.map(p => (
                <th key={p.id} className="pb-2 text-center">
                  <span className="text-slate-300">{p.name}</span>
                  <div className="text-xs font-normal text-slate-500">{p.dynamic_priority}</div>
                </th>
              ))}
              <th className="pb-2 text-center text-red-400">{t('flywheel.coverageStatus')}</th>
            </tr>
          </thead>
          <tbody>
            {painPoints.map(pp => {
              const hasCoverage = pp.related_product_count > 0;
              return (
                <tr key={pp.id} className={`border-b border-slate-700 ${!hasCoverage ? 'bg-red-500/10' : 'hover:bg-slate-800/50'}`}>
                  <td className="py-3 font-medium flex items-center gap-1 text-slate-200">
                    {TREND_ICON[pp.trend_label]} {pp.name}
                  </td>
                  {products.map(pr => {
                    const related = (pr.related_pain_point_trends || []).includes(pp.name);
                    return (
                      <td key={pr.id} className="py-3 text-center">
                        {related
                          ? <span className="inline-block w-6 h-6 bg-indigo-500 rounded" title={t('flywheel.strongRelated')} />
                          : <span className="inline-block w-6 h-6 bg-slate-700 rounded" title={t('flywheel.noRelated')} />}
                      </td>
                    );
                  })}
                  <td className="py-3 text-center">
                    {hasCoverage
                      ? <span className="text-green-400 text-xs">{t('flywheel.covered')}</span>
                      : <span className="text-red-400 text-xs font-medium flex items-center justify-center gap-1">
                          <AlertTriangle className="w-3 h-3" />{t('flywheel.blank')}
                        </span>}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ServiceSection({ services }: { services: ServiceStrategyView[] }) {
  const { t } = useTranslation();
  if (services.length === 0) {
    return <EmptyState hint="暂无服务数据。在「企业记忆」中添加服务项目。" />;
  }
  return (
    <div className="space-y-4">
      <h2 className="text-base font-semibold text-slate-200">{t('flywheel.serviceEffect')}</h2>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700 text-left text-slate-500">
              <th className="pb-2">{t('flywheel.serviceName')}</th>
              <th className="pb-2">{t('flywheel.usageCount')}</th>
              <th className="pb-2">{t('flywheel.effectLabel')}</th>
              <th className="pb-2">{t('flywheel.scenarioGap')}</th>
              <th className="pb-2">{t('flywheel.gapDesc')}</th>
            </tr>
          </thead>
          <tbody>
            {services.map(s => (
              <tr key={s.id} className={`border-b border-slate-700 hover:bg-slate-800/50 ${s.has_scenario_gap ? 'bg-orange-500/5' : ''}`}>
                <td className="py-3 font-medium text-slate-200">{s.name}</td>
                <td className="py-3 text-slate-300">{s.usage_count}</td>
                <td className="py-3 text-slate-300">{(s.effectiveness * 100).toFixed(0)}%</td>
                <td className="py-3">
                  {s.has_scenario_gap ? (
                    <span className="text-orange-400 text-xs flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3" /> {t('flywheel.hasGap')}
                    </span>
                  ) : (
                    <span className="text-green-400 text-xs">{t('flywheel.normal')}</span>
                  )}
                </td>
                <td className="py-3 text-slate-500 text-xs">{s.gap_description || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ScriptSection({ scripts }: { scripts: ScriptLifecycleView[] }) {
  const { t } = useTranslation();
  if (scripts.length === 0) {
    return <EmptyState hint="暂无话术数据。在「话术库」中创建话术，或通过优化中心采纳策略自动生成。" />;
  }
  return (
    <div className="space-y-4">
      <h2 className="text-base font-semibold text-slate-200">{t('flywheel.scriptLifecycle')}</h2>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-700 text-left text-slate-500">
              <th className="pb-2">{t('flywheel.scriptTitle')}</th>
              <th className="pb-2">{t('flywheel.lifecycleStage')}</th>
              <th className="pb-2">{t('flywheel.effectTrend')}</th>
              <th className="pb-2">{t('flywheel.contactRate')}</th>
              <th className="pb-2">{t('flywheel.source')}</th>
            </tr>
          </thead>
          <tbody>
            {scripts.map(s => (
              <tr key={s.id} className="border-b border-slate-700 hover:bg-slate-800/50">
                <td className="py-3 font-medium text-slate-200">{s.title}</td>
                <td className="py-3">
                  <span className={`text-xs px-2 py-0.5 rounded-full ${LIFECYCLE_COLOR[s.lifecycle_stage] ?? 'bg-slate-600/20 text-slate-400'}`}>
                    {s.lifecycle_stage === 'draft' && t('flywheel.stages.draft')}
                    {s.lifecycle_stage === 'review' && t('flywheel.stages.review')}
                    {s.lifecycle_stage === 'active' && t('flywheel.stages.active')}
                    {s.lifecycle_stage === 'declining' && t('flywheel.stages.declining')}
                    {s.lifecycle_stage === 'archived' && t('flywheel.stages.archived')}
                    {!['draft', 'review', 'active', 'declining', 'archived'].includes(s.lifecycle_stage) && s.lifecycle_stage}
                  </span>
                </td>
                <td className="py-3">{TREND_ICON[s.effectiveness_trend]}</td>
                <td className="py-3 text-slate-300">{s.usage_contact_rate > 0 ? `${(s.usage_contact_rate * 100).toFixed(0)}%` : '-'}</td>
                <td className="py-3">
                  <span className={`text-xs px-2 py-0.5 rounded ${
                    s.source_type === 'flywheel_generated' ? 'bg-indigo-500/20 text-indigo-400' : 'bg-slate-700 text-slate-400'
                  }`}>
                    {s.source_type === 'flywheel_generated' ? t('flywheel.sources.flywheelGenerated') : t('flywheel.sources.manual')}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}


function GearSection({ icon, title, badge, gearScore, children }: {
  icon: React.ReactNode;
  title: string;
  badge?: React.ReactNode;
  gearScore?: number;
  children: React.ReactNode;
}) {
  return (
    <div className="bg-slate-800/30 rounded-lg border border-slate-700 p-4">
      <div className="flex items-center gap-2 mb-2">
        <div className="text-indigo-400">{icon}</div>
        <h3 className="font-semibold text-slate-200">{title}</h3>
        {gearScore != null && (
          <span className={`text-xs px-2 py-0.5 rounded ${
            gearScore >= 80 ? 'bg-emerald-500/20 text-emerald-400' :
            gearScore >= 50 ? 'bg-amber-500/20 text-amber-400' :
            gearScore > 0 ? 'bg-blue-500/20 text-blue-400' :
            'bg-slate-500/20 text-slate-400'
          }`}>{gearScore}分</span>
        )}
        {badge}
      </div>
      {children}
    </div>
  );
}

function EmptyGear({ hint }: { hint: string }) {
  return (
    <div className="text-center py-6 text-slate-500">
      <p className="text-xs">{hint}</p>
    </div>
  );
}

function EmptyState({ hint }: { hint: string }) {
  return (
    <div className="bg-slate-900 rounded-lg border border-slate-800 p-8 text-center">
      <p className="text-sm text-slate-400">{hint}</p>
    </div>
  );
}

function ArrowDown() {
  const { t } = useTranslation();
  return (
    <div className="flex items-center justify-center text-slate-600">
      <ArrowRight className="w-4 h-4 rotate-90" />
      <span className="text-xs text-slate-500 ml-2">{t('flywheel.driveNextLayer')}</span>
    </div>
  );
}

function StatCard({ label, value, sub, alert, positive }: {
  label: string; value: string; sub: string; alert?: boolean; positive?: boolean;
}) {
  return (
    <div className={`p-3 rounded-lg border ${alert ? 'bg-red-500/10 border-red-500/30' : 'bg-slate-800/50 border-slate-700'}`}>
      <div className="text-xs text-slate-500">{label}</div>
      <div className={`text-lg font-bold mt-1 ${
        alert ? 'text-red-400' : positive ? 'text-green-400' : 'text-slate-100'
      }`}>{value}</div>
      <div className="text-xs text-slate-500 mt-0.5">{sub}</div>
    </div>
  );
}
