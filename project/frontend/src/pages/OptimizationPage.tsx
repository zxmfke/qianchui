import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  RefreshCw,
  Stethoscope,
  TrendingUp,
  History,
  ChevronRight,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Loader2,
  ArrowRight,
  Zap,
  Target,
  BarChart3,
} from 'lucide-react';
import { optimizationService } from '@/services/optimization';
import type { OptimizationTask, OptimizationStrategy, OptimizationStats } from '@/services/optimization';

type Tab = 'overview' | 'new_task' | 'strategies' | 'history';

const rootCauseColors: Record<string, string> = {
  config: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  script: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
  traffic: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
  product: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
};

export default function OptimizationPage() {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  const [stats, setStats] = useState<OptimizationStats | null>(null);
  const [tasks, setTasks] = useState<OptimizationTask[]>([]);
  const [totalTasks, setTotalTasks] = useState(0);
  const [selectedTaskId, setSelectedTaskId] = useState<string | null>(null);
  const [strategies, setStrategies] = useState<OptimizationStrategy[]>([]);
  const [loading, setLoading] = useState(false);
  const [strategiesLoading, setStrategiesLoading] = useState(false);

  const [conversationInput, setConversationInput] = useState('');
  const [creating, setCreating] = useState(false);
  const [createResult, setCreateResult] = useState<{
    task_id: string;
    overall_score: number;
    priority: string;
    root_causes: Array<{ layer: string; issue: string }>;
  } | null>(null);

  const tabs: { id: Tab; label: string; icon: React.ElementType }[] = [
    { id: 'overview', label: '优化总览', icon: BarChart3 },
    { id: 'new_task', label: '新建优化', icon: Stethoscope },
    { id: 'strategies', label: '优化策略', icon: TrendingUp },
    { id: 'history', label: '优化历史', icon: History },
  ];

  useEffect(() => {
    loadStats();
    loadTasks();
  }, []);

  const loadStats = async () => {
    try {
      const data = await optimizationService.getStats();
      setStats(data);
    } catch {
      // stats are optional
    }
  };

  const loadTasks = async () => {
    setLoading(true);
    try {
      const data = await optimizationService.getTasks(1, 50);
      setTasks(data.items);
      setTotalTasks(data.total);
    } catch {
      // handle silently
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTask = async () => {
    if (!conversationInput.trim() || conversationInput.trim().length < 10) return;
    setCreating(true);
    setCreateResult(null);
    try {
      const result = await optimizationService.createTask({
        conversation_text: conversationInput.trim(),
      });
      setCreateResult(result);
      await loadTasks();
      await loadStats();
    } catch (err) {
      console.error('Create task failed:', err);
    } finally {
      setCreating(false);
    }
  };

  const handleGenerateStrategies = async (taskId: string) => {
    setSelectedTaskId(taskId);
    setStrategiesLoading(true);
    setActiveTab('strategies');
    try {
      const result = await optimizationService.generateStrategies(taskId);
      setStrategies(result.strategies);
      await loadTasks();
    } catch {
      const existing = await optimizationService.getStrategies(taskId);
      setStrategies(existing.strategies);
    } finally {
      setStrategiesLoading(false);
    }
  };

  const handleLoadStrategies = async (taskId: string) => {
    setSelectedTaskId(taskId);
    setStrategiesLoading(true);
    setActiveTab('strategies');
    try {
      const result = await optimizationService.getStrategies(taskId);
      setStrategies(result.strategies);
    } catch {
      setStrategies([]);
    } finally {
      setStrategiesLoading(false);
    }
  };

  const handleStrategyAction = async (strategyId: string, action: string) => {
    try {
      await optimizationService.updateStrategy(strategyId, { status: action });
      setStrategies(prev =>
        prev.map(s => s.id === strategyId ? { ...s, status: action } : s)
      );
      await loadStats();
    } catch {
      // handle silently
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-emerald-400';
    if (score >= 60) return 'text-amber-400';
    return 'text-red-400';
  };

  return (
    <div className="flex-1 h-screen overflow-hidden flex flex-col bg-slate-950">
      <header className="px-4 py-3 border-b border-slate-800 flex items-center gap-2">
        <RefreshCw className="w-4 h-4 text-indigo-400" />
        <h1 className="text-base font-semibold text-white">{t('optimization.title')}</h1>
        <span className="text-xs px-2 py-0.5 rounded bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">v2.0</span>
      </header>

      <div className="flex border-b border-slate-800 px-4">
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-3 py-2 text-xs font-medium border-b-2 transition-colors ${
              activeTab === tab.id
                ? 'border-indigo-500 text-indigo-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <tab.icon className="w-4 h-4" />
            {tab.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'overview' && (
          <OverviewTab stats={stats} tasks={tasks} loading={loading}
            onCreateNew={() => setActiveTab('new_task')}
            onViewStrategies={handleLoadStrategies}
            onGenerateStrategies={handleGenerateStrategies}
          />
        )}

        {activeTab === 'new_task' && (
          <NewTaskTab
            conversationInput={conversationInput}
            setConversationInput={setConversationInput}
            creating={creating}
            createResult={createResult}
            onSubmit={handleCreateTask}
            onGenerateStrategies={handleGenerateStrategies}
            getScoreColor={getScoreColor}
          />
        )}

        {activeTab === 'strategies' && (
          <StrategiesTab
            strategies={strategies}
            loading={strategiesLoading}
            taskId={selectedTaskId}
            onAction={handleStrategyAction}
          />
        )}

        {activeTab === 'history' && (
          <HistoryTab tasks={tasks} loading={loading} totalTasks={totalTasks}
            onViewStrategies={handleLoadStrategies}
            getScoreColor={getScoreColor}
          />
        )}
      </div>
    </div>
  );
}

function OverviewTab({ stats, tasks, loading, onCreateNew, onViewStrategies, onGenerateStrategies }: {
  stats: OptimizationStats | null;
  tasks: OptimizationTask[];
  loading: boolean;
  onCreateNew: () => void;
  onViewStrategies: (taskId: string) => void;
  onGenerateStrategies: (taskId: string) => void;
}) {
  const recentTasks = tasks.slice(0, 5);

  return (
    <div className="max-w-4xl mx-auto space-y-4">
      {/* 数据流说明 */}
      <div className="bg-gradient-to-r from-indigo-500/10 via-purple-500/10 to-pink-500/10 border border-indigo-500/20 rounded-lg p-4">
        <h3 className="text-sm font-semibold text-white mb-2 flex items-center gap-2">
          <Zap className="w-4 h-4 text-indigo-400" />
          优化闭环流程
        </h3>
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <span className="px-2 py-1 bg-indigo-500/20 text-indigo-300 rounded">① 诊断对话</span>
          <ArrowRight className="w-3 h-3" />
          <span className="px-2 py-1 bg-purple-500/20 text-purple-300 rounded">② 创建任务</span>
          <ArrowRight className="w-3 h-3" />
          <span className="px-2 py-1 bg-pink-500/20 text-pink-300 rounded">③ 生成策略</span>
          <ArrowRight className="w-3 h-3" />
          <span className="px-2 py-1 bg-emerald-500/20 text-emerald-300 rounded">④ 采纳落地</span>
          <ArrowRight className="w-3 h-3" />
          <span className="px-2 py-1 bg-amber-500/20 text-amber-300 rounded">⑤ 飞轮更新</span>
        </div>
      </div>

      {/* 统计卡片 */}
      <div className="grid grid-cols-4 gap-3">
        <StatCard label="优化任务" value={stats?.total_tasks ?? 0} icon={<Target className="w-4 h-4 text-indigo-400" />} />
        <StatCard label="优化策略" value={stats?.total_strategies ?? 0} icon={<TrendingUp className="w-4 h-4 text-purple-400" />} />
        <StatCard label="已采纳策略" value={stats?.adopted_strategies ?? 0} icon={<CheckCircle2 className="w-4 h-4 text-emerald-400" />} />
        <StatCard label="平均诊断分" value={stats?.avg_diagnosis_score ?? 0} icon={<BarChart3 className="w-4 h-4 text-amber-400" />}
          suffix="分" />
      </div>

      {/* 最近任务 */}
      <div className="bg-slate-900 rounded-lg border border-slate-800 p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-white">最近优化任务</h3>
          <button onClick={onCreateNew}
            className="px-3 py-1.5 bg-indigo-600 text-white text-xs rounded-lg hover:bg-indigo-500 flex items-center gap-1">
            <Stethoscope className="w-3 h-3" /> 新建优化
          </button>
        </div>

        {loading ? (
          <div className="flex justify-center py-8"><Loader2 className="w-6 h-6 animate-spin text-slate-500" /></div>
        ) : recentTasks.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-sm text-slate-500 mb-3">暂无优化任务，从诊断一段对话开始</p>
            <button onClick={onCreateNew}
              className="px-4 py-2 bg-indigo-600 text-white text-sm rounded-lg hover:bg-indigo-500">
              立即开始
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            {recentTasks.map(task => (
              <div key={task.id} className="flex items-center gap-3 p-3 bg-slate-800/50 rounded-lg hover:bg-slate-800 transition">
                <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                  task.priority === 'P0' ? 'bg-red-500/20 text-red-400' :
                  task.priority === 'P1' ? 'bg-amber-500/20 text-amber-400' :
                  'bg-green-500/20 text-green-400'
                }`}>{task.priority}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-slate-200 truncate">{task.title}</p>
                  <p className="text-xs text-slate-500">
                    {task.root_causes_count}个问题 · {task.strategies_count}个策略 · {task.strategies_adopted}个已采纳
                  </p>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded ${
                  task.status === 'strategies_generated' ? 'bg-green-500/20 text-green-400' :
                  task.status === 'diagnosed' ? 'bg-amber-500/20 text-amber-400' :
                  'bg-slate-500/20 text-slate-400'
                }`}>
                  {task.status === 'strategies_generated' ? '已生成策略' :
                   task.status === 'diagnosed' ? '待生成策略' : task.status}
                </span>
                <button
                  onClick={() => task.strategies_count > 0 ? onViewStrategies(task.id) : onGenerateStrategies(task.id)}
                  className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
                >
                  {task.strategies_count > 0 ? '查看策略' : '生成策略'}
                  <ChevronRight className="w-3 h-3" />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function NewTaskTab({ conversationInput, setConversationInput, creating, createResult, onSubmit, onGenerateStrategies, getScoreColor }: {
  conversationInput: string;
  setConversationInput: (v: string) => void;
  creating: boolean;
  createResult: { task_id: string; overall_score: number; priority: string; root_causes: Array<{ layer: string; issue: string }> } | null;
  onSubmit: () => void;
  onGenerateStrategies: (taskId: string) => void;
  getScoreColor: (score: number) => string;
}) {
  return (
    <div className="max-w-4xl mx-auto space-y-4">
      <div className="bg-slate-900 rounded-lg border border-slate-800 p-4">
        <h2 className="text-sm font-semibold text-white mb-3 flex items-center gap-2">
          <Stethoscope className="w-4 h-4 text-indigo-400" />
          粘贴对话记录 → 自动诊断 → 创建优化任务
        </h2>
        <textarea
          className="w-full h-40 bg-slate-800 border border-slate-700 rounded-lg p-4 text-sm text-slate-200 placeholder-slate-500 resize-none focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
          placeholder="粘贴对话记录...&#10;格式示例：&#10;客户：种植牙多少钱？&#10;客服：您好，欢迎咨询..."
          value={conversationInput}
          onChange={(e) => setConversationInput(e.target.value)}
        />
        <button
          onClick={onSubmit}
          disabled={!conversationInput.trim() || conversationInput.trim().length < 10 || creating}
          className="w-full mt-3 px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
        >
          {creating ? (
            <><Loader2 className="w-4 h-4 animate-spin" /> 正在诊断并创建任务...</>
          ) : (
            <><Stethoscope className="w-4 h-4" /> 诊断 + 创建优化任务</>
          )}
        </button>
      </div>

      {createResult && (
        <div className="bg-slate-900 rounded-lg border border-slate-800 p-4 animate-fade-in">
          <div className="flex items-center gap-3 mb-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            <h3 className="text-sm font-semibold text-white">优化任务已创建</h3>
          </div>

          <div className="grid grid-cols-3 gap-3 mb-3">
            <div className="p-3 bg-slate-800/50 rounded-lg text-center">
              <div className="text-xs text-slate-500 mb-1">诊断评分</div>
              <div className={`text-2xl font-bold ${getScoreColor(createResult.overall_score)}`}>
                {createResult.overall_score}
              </div>
            </div>
            <div className="p-3 bg-slate-800/50 rounded-lg text-center">
              <div className="text-xs text-slate-500 mb-1">优先级</div>
              <div className={`text-2xl font-bold ${
                createResult.priority === 'P0' ? 'text-red-400' :
                createResult.priority === 'P1' ? 'text-amber-400' : 'text-green-400'
              }`}>{createResult.priority}</div>
            </div>
            <div className="p-3 bg-slate-800/50 rounded-lg text-center">
              <div className="text-xs text-slate-500 mb-1">发现问题</div>
              <div className="text-2xl font-bold text-slate-100">{createResult.root_causes.length}</div>
            </div>
          </div>

          {createResult.root_causes.length > 0 && (
            <div className="space-y-1.5 mb-3">
              {createResult.root_causes.slice(0, 5).map((rc, i) => (
                <div key={i} className="flex items-start gap-2 text-xs text-slate-400">
                  <AlertTriangle className="w-3 h-3 text-amber-400 mt-0.5 flex-shrink-0" />
                  <span>{rc.issue}</span>
                </div>
              ))}
            </div>
          )}

          <button
            onClick={() => onGenerateStrategies(createResult.task_id)}
            className="w-full px-4 py-2.5 bg-gradient-to-r from-indigo-600 to-purple-600 text-white text-sm font-medium rounded-lg hover:from-indigo-500 hover:to-purple-500 transition flex items-center justify-center gap-2"
          >
            <TrendingUp className="w-4 h-4" />
            下一步：AI 生成优化策略
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
      )}
    </div>
  );
}

function StrategiesTab({ strategies, loading, taskId, onAction }: {
  strategies: OptimizationStrategy[];
  loading: boolean;
  taskId: string | null;
  onAction: (strategyId: string, action: string) => void;
}) {
  const { t } = useTranslation();

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <Loader2 className="w-8 h-8 animate-spin text-indigo-400 mb-3" />
        <p className="text-sm text-slate-400">AI 正在生成优化策略...</p>
      </div>
    );
  }

  if (!taskId || strategies.length === 0) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="bg-slate-900 rounded-lg border border-slate-800 p-4 text-center py-16">
          <TrendingUp className="w-10 h-10 text-slate-600 mx-auto mb-3" />
          <p className="text-sm text-slate-400">请先在「优化总览」或「新建优化」中选择一个任务</p>
        </div>
      </div>
    );
  }

  const pendingCount = strategies.filter(s => s.status === 'pending').length;
  const adoptedCount = strategies.filter(s => s.status === 'adopted').length;

  return (
    <div className="max-w-4xl mx-auto space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-white">
            优化策略 <span className="text-slate-500 font-normal">({strategies.length}个策略)</span>
          </h2>
          <p className="text-xs text-slate-500 mt-0.5">
            {pendingCount}个待处理 · {adoptedCount}个已采纳
          </p>
        </div>
      </div>

      <div className="space-y-3">
        {strategies.map(s => (
          <div key={s.id} className={`p-4 rounded-lg border transition ${
            s.status === 'adopted' ? 'bg-emerald-500/5 border-emerald-500/30' :
            s.status === 'rejected' ? 'bg-slate-800/30 border-slate-700 opacity-60' :
            'bg-slate-900 border-slate-800'
          }`}>
            <div className="flex items-center gap-2 mb-2">
              <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                s.priority === 'P0' ? 'bg-red-500/20 text-red-400' : 'bg-amber-500/20 text-amber-400'
              }`}>{s.priority}</span>
              <span className={`px-2 py-0.5 rounded text-xs border ${rootCauseColors[s.root_cause_type] || rootCauseColors.script}`}>
                {t(`optimization.rootCauseType.${s.root_cause_type}`) || s.root_cause_type}
              </span>
              <span className="text-sm text-white font-medium flex-1">{s.problem}</span>
              {s.status === 'adopted' && (
                <span className="text-xs bg-emerald-500/20 text-emerald-400 px-2 py-0.5 rounded flex items-center gap-1">
                  <CheckCircle2 className="w-3 h-3" /> 已采纳
                </span>
              )}
              {s.status === 'rejected' && (
                <span className="text-xs bg-slate-500/20 text-slate-400 px-2 py-0.5 rounded">已忽略</span>
              )}
            </div>

            {(s.current_script || s.suggested_script) && (
              <div className="grid grid-cols-2 gap-3 mb-2">
                <div>
                  <p className="text-xs text-red-400 mb-1 flex items-center gap-1">
                    <XCircle className="w-3 h-3" /> {t('optimization.currentScript')}
                  </p>
                  <p className="text-sm text-slate-400 bg-slate-800/50 p-3 rounded">
                    {s.current_script || '—'}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-emerald-400 mb-1 flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3" /> {t('optimization.suggestedScript')}
                  </p>
                  <p className="text-sm text-slate-300 bg-slate-800/50 p-3 rounded">
                    {s.suggested_script || s.solution}
                  </p>
                </div>
              </div>
            )}

            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4 text-xs text-slate-500">
                {s.expected_impact && <span>{t('optimization.expectedEffect')}: {s.expected_impact}</span>}
                <span className="flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3" />
                  {t('optimization.risk')}: {s.risk_level === 'low' ? t('optimization.riskLow') : s.risk_level === 'medium' ? t('optimization.riskMedium') : t('optimization.riskHigh')}
                </span>
              </div>
              {s.status === 'pending' && (
                <div className="flex gap-2">
                  <button onClick={() => onAction(s.id, 'adopted')}
                    className="px-3 py-1.5 bg-emerald-600/20 text-emerald-400 text-xs rounded-lg hover:bg-emerald-600/30 border border-emerald-500/30">
                    {t('optimization.adopt')}
                  </button>
                  <button onClick={() => onAction(s.id, 'modified')}
                    className="px-3 py-1.5 bg-slate-700 text-slate-300 text-xs rounded-lg hover:bg-slate-600">
                    {t('optimization.adoptModified')}
                  </button>
                  <button onClick={() => onAction(s.id, 'rejected')}
                    className="px-3 py-1.5 bg-slate-700 text-slate-400 text-xs rounded-lg hover:bg-slate-600">
                    {t('optimization.ignore')}
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function HistoryTab({ tasks, loading, totalTasks, onViewStrategies, getScoreColor }: {
  tasks: OptimizationTask[];
  loading: boolean;
  totalTasks: number;
  onViewStrategies: (taskId: string) => void;
  getScoreColor: (score: number) => string;
}) {
  if (loading) {
    return (
      <div className="flex justify-center py-16"><Loader2 className="w-8 h-8 animate-spin text-slate-500" /></div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      <div className="bg-slate-900 rounded-lg border border-slate-800 p-4">
        <h2 className="text-sm font-semibold text-white mb-1">优化历史</h2>
        <p className="text-xs text-slate-500 mb-4">共 {totalTasks} 个优化任务</p>

        {tasks.length === 0 ? (
          <div className="text-center py-16 text-slate-500">
            <History className="w-10 h-10 mx-auto mb-3 text-slate-600" />
            <p className="text-sm">暂无优化记录</p>
          </div>
        ) : (
          <div className="space-y-2">
            {tasks.map(task => (
              <div key={task.id}
                className="flex items-center gap-3 p-3 bg-slate-800/50 rounded-lg hover:bg-slate-800 transition cursor-pointer"
                onClick={() => onViewStrategies(task.id)}
              >
                <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                  task.priority === 'P0' ? 'bg-red-500/20 text-red-400' :
                  task.priority === 'P1' ? 'bg-amber-500/20 text-amber-400' :
                  'bg-green-500/20 text-green-400'
                }`}>{task.priority}</span>

                <div className="flex-1 min-w-0">
                  <p className="text-sm text-slate-200 truncate">{task.title}</p>
                  <div className="flex items-center gap-3 text-xs text-slate-500 mt-0.5">
                    <span>诊断分: <span className={getScoreColor(task.classification?.overall_score ?? 0)}>
                      {task.classification?.overall_score ?? '—'}
                    </span></span>
                    <span>{task.strategies_count}个策略</span>
                    <span className="text-emerald-400">{task.strategies_adopted}个已采纳</span>
                    {task.created_at && <span>{new Date(task.created_at).toLocaleDateString()}</span>}
                  </div>
                </div>

                <ChevronRight className="w-4 h-4 text-slate-600" />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function StatCard({ label, value, icon, suffix }: {
  label: string; value: number; icon: React.ReactNode; suffix?: string;
}) {
  return (
    <div className="bg-slate-900 rounded-lg border border-slate-800 p-3">
      <div className="flex items-center gap-2 mb-1">
        {icon}
        <span className="text-xs text-slate-500">{label}</span>
      </div>
      <div className="text-xl font-bold text-slate-100">
        {value}{suffix}
      </div>
    </div>
  );
}
