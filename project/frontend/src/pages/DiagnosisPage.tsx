import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import {
  Stethoscope,
  Upload,
  FileText,
  Loader2,
  CheckCircle2,
  AlertTriangle,
  History,
  X,
  ArrowRight,
  TrendingUp,
  RefreshCw,
  Zap,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { diagnosisService } from '@/services/diagnosis';
import { optimizationService } from '@/services/optimization';
import type { DiagnosisResult } from '@/services/diagnosis';

interface DiagResult {
  overall_score: number;
  dimensions: { name: string; score: number; feedback: string; suggestions: string[] }[];
  highlights: string[];
  improvements: string[];
}

interface DiagnosisTranslations {
  layerNames: Record<string, string>;
  noIssues: string;
  noSuggestions: string;
  performsWell: (name: string, score: number) => string;
  overallOk: string;
  noHighlights: string;
  noImprovements: string;
}

function adaptBackendResult(result: DiagnosisResult, tr: DiagnosisTranslations): DiagResult {
  const dimensions: DiagResult['dimensions'] = [];
  const layerKeys = ['psychology_layer', 'strategy_layer', 'script_layer'] as const;

  for (const key of layerKeys) {
    const layer = result[key];
    if (!layer) continue;
    const issues = layer.issues || [];
    const feedback =
      issues.length > 0
        ? issues.map((i) => i.issue).filter(Boolean).join('；') || tr.noIssues
        : tr.noIssues;
    const suggestions = issues.flatMap((i) =>
      [i.suggested, i.suggested_strategy].filter(Boolean)
    ) as string[];
    if (suggestions.length === 0 && result.improvement_plan?.length) {
      suggestions.push(...result.improvement_plan.slice(0, 2));
    }
    dimensions.push({
      name: tr.layerNames[key] || key,
      score: layer.score ?? 0,
      feedback,
      suggestions: suggestions.length > 0 ? suggestions : [tr.noSuggestions],
    });
  }

  const highlights = dimensions
    .filter((d) => d.score >= 70)
    .map((d) => tr.performsWell(d.name, d.score));

  if (highlights.length === 0 && result.overall_score >= 60) {
    highlights.push(tr.overallOk);
  }

  return {
    overall_score: result.overall_score,
    dimensions,
    highlights: highlights.length > 0 ? highlights : [tr.noHighlights],
    improvements: result.improvement_plan?.length
      ? result.improvement_plan
      : [tr.noImprovements],
  };
}

interface ReportItem {
  id: string;
  conversation_text: string;
  overall_score: number;
  result: DiagnosisResult;
  created_at: string;
}

export default function DiagnosisPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [inputText, setInputText] = useState('');

  const diagnosisTr: DiagnosisTranslations = {
    layerNames: {
      psychology_layer: t('diagnosis.layers.psychology'),
      strategy_layer: t('diagnosis.layers.strategy'),
      script_layer: t('diagnosis.layers.script'),
    },
    noIssues: t('diagnosis.noIssues'),
    noSuggestions: t('diagnosis.noSuggestions'),
    performsWell: (name, score) => t('diagnosis.performsWell', { name, score }),
    overallOk: t('diagnosis.overallOk'),
    noHighlights: t('diagnosis.noHighlights'),
    noImprovements: t('diagnosis.noImprovements'),
  };
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<DiagResult | null>(null);
  const [lastReportId, setLastReportId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyList, setHistoryList] = useState<ReportItem[]>([]);
  const [creatingOptTask, setCreatingOptTask] = useState(false);

  const handleAnalyze = async () => {
    if (!inputText.trim()) return;
    setIsAnalyzing(true);
    setError(null);
    setResult(null);
    setLastReportId(null);
    try {
      const res = await diagnosisService.analyze(inputText.trim());
      setResult(adaptBackendResult(res.result, diagnosisTr));
      setLastReportId(res.report_id);
    } catch (err: unknown) {
      let msg = t('diagnosis.diagnosisFailed');
      if (err && typeof err === 'object' && 'response' in err) {
        const res = (err as { response?: { data?: { detail?: unknown } } }).response?.data;
        const d = res?.detail;
        if (typeof d === 'string') msg = d;
        else if (Array.isArray(d)) {
          msg = d.map((x: { msg?: string }) => x?.msg || '').filter(Boolean).join('; ') || msg;
        }
      }
      setError(msg);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleGoToOptimization = async () => {
    if (!lastReportId) {
      navigate('/optimization');
      return;
    }
    setCreatingOptTask(true);
    try {
      await optimizationService.createTaskFromDiagnosis(lastReportId);
      navigate('/optimization');
    } catch {
      navigate('/optimization');
    } finally {
      setCreatingOptTask(false);
    }
  };

  const handleViewHistory = async () => {
    setHistoryOpen(true);
    setHistoryLoading(true);
    setHistoryList([]);
    try {
      const res = await diagnosisService.getReports(1, 20);
      setHistoryList(res.items);
    } catch (err) {
      console.error('Failed to load history:', err);
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleSelectHistory = (item: ReportItem) => {
    setResult(adaptBackendResult(item.result, diagnosisTr));
    setHistoryOpen(false);
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-emerald-400';
    if (score >= 60) return 'text-amber-400';
    return 'text-red-400';
  };

  const getScoreBarColor = (score: number) => {
    if (score >= 80) return 'bg-emerald-500';
    if (score >= 60) return 'bg-amber-500';
    return 'bg-red-500';
  };

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-slate-100">{t('diagnosis.title')}</h1>
          <p className="text-xs text-slate-500 mt-1">{t('diagnosis.subtitle')}</p>
        </div>
        <button onClick={handleViewHistory} className="btn-secondary flex items-center gap-2">
          <History className="w-4 h-4" />
          {t('diagnosis.viewHistory')}
        </button>
      </div>

      {!result ? (
        <div className="max-w-3xl mx-auto space-y-4">
          {/* Upload area */}
          <div className="glass-card p-4">
            <div className="flex items-center gap-2 mb-3">
              <Stethoscope className="w-4 h-4 text-indigo-400" />
              <h2 className="text-sm font-semibold text-slate-200">{t('diagnosis.dialogDiagnosis')}</h2>
            </div>

            <div className="border-2 border-dashed border-slate-700 rounded-lg p-6 text-center hover:border-indigo-500/50 transition-colors mb-3">
              <Upload className="w-8 h-8 text-slate-600 mx-auto mb-2" />
              <p className="text-xs text-slate-400">{t('diagnosis.dropFile')}</p>
              <p className="text-[10px] text-slate-600 mt-1">{t('diagnosis.supportedFormats')}</p>
            </div>

            <div className="relative">
              <div className="flex items-center gap-2 mb-2">
                <FileText className="w-4 h-4 text-slate-500" />
                <span className="text-sm text-slate-400">{t('diagnosis.pasteContent')}</span>
              </div>
              <textarea
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder={t('diagnosis.placeholderText')}
                rows={10}
                className="input-field resize-none font-mono text-sm"
              />
            </div>

            {error && (
              <div className="mt-3 p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-400 text-sm">
                {error}
              </div>
            )}

            <button
              onClick={handleAnalyze}
              disabled={!inputText.trim() || isAnalyzing}
              className="btn-primary w-full mt-4 flex items-center justify-center gap-2"
            >
              {isAnalyzing ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  {t('diagnosis.analyzing')}
                </>
              ) : (
                <>
                  <Stethoscope className="w-4 h-4" />
                  {t('diagnosis.startDiagnosis')}
                </>
              )}
            </button>
          </div>
        </div>
      ) : (
        <div className="max-w-4xl mx-auto space-y-4 animate-fade-in">
          {/* Overall score */}
          <div className="glass-card p-4 text-center">
            <h2 className="text-xs font-semibold text-slate-400 mb-3">{t('diagnosis.overallScore')}</h2>
            <div className="relative inline-flex items-center justify-center">
              <svg className="w-32 h-32 -rotate-90" viewBox="0 0 120 120">
                <circle cx="60" cy="60" r="50" fill="none" stroke="#334155" strokeWidth="8" />
                <circle
                  cx="60"
                  cy="60"
                  r="50"
                  fill="none"
                  stroke={
                    result.overall_score >= 80
                      ? '#10b981'
                      : result.overall_score >= 60
                        ? '#f59e0b'
                        : '#ef4444'
                  }
                  strokeWidth="8"
                  strokeLinecap="round"
                  strokeDasharray={`${(result.overall_score / 100) * 314} 314`}
                />
              </svg>
              <span
                className={cn(
                  'absolute text-3xl font-bold',
                  getScoreColor(result.overall_score),
                )}
              >
                {result.overall_score}
              </span>
            </div>
          </div>

          {/* Dimensions */}
          <div className="grid grid-cols-2 gap-4">
            {result.dimensions.map((dim) => (
              <div key={dim.name} className="glass-card p-4">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-semibold text-slate-200">{dim.name}</h3>
                  <span className={cn('text-base font-bold', getScoreColor(dim.score))}>
                    {dim.score}
                  </span>
                </div>
                <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden mb-3">
                  <div
                    className={cn(
                      'h-full rounded-full transition-all',
                      getScoreBarColor(dim.score),
                    )}
                    style={{ width: `${dim.score}%` }}
                  />
                </div>
                <p className="text-xs text-slate-400 mb-2">{dim.feedback}</p>
                <div className="space-y-1">
                  {dim.suggestions.map((s, i) => (
                    <p key={i} className="text-xs text-slate-500 flex items-start gap-1.5">
                      <span className="text-indigo-400 mt-0.5">•</span>
                      {s}
                    </p>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* Highlights & Improvements */}
          <div className="grid grid-cols-2 gap-4">
            <div className="glass-card p-4">
              <div className="flex items-center gap-2 mb-2">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <h3 className="text-sm font-semibold text-slate-200">{t('diagnosis.highlights')}</h3>
              </div>
              <div className="space-y-2">
                {result.highlights.map((h, i) => (
                  <p key={i} className="text-xs text-emerald-300 flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                    {h}
                  </p>
                ))}
              </div>
            </div>
            <div className="glass-card p-4">
              <div className="flex items-center gap-2 mb-2">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                <h3 className="text-sm font-semibold text-slate-200">{t('diagnosis.improvements')}</h3>
              </div>
              <div className="space-y-2">
                {result.improvements.map((imp, i) => (
                  <p key={i} className="text-xs text-amber-300 flex items-center gap-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                    {imp}
                  </p>
                ))}
              </div>
            </div>
          </div>

          {/* 下一步行动引导 */}
          <div className="glass-card p-4">
            <div className="flex items-center gap-2 mb-3">
              <Zap className="w-4 h-4 text-indigo-400" />
              <h3 className="text-sm font-semibold text-slate-200">下一步行动</h3>
            </div>
            <div className="grid grid-cols-3 gap-3">
              <button
                onClick={handleGoToOptimization}
                disabled={creatingOptTask}
                className="p-3 bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-indigo-500/30 rounded-lg hover:border-indigo-400/50 transition-all text-left group"
              >
                <div className="flex items-center gap-2 mb-1">
                  <TrendingUp className="w-4 h-4 text-indigo-400" />
                  <span className="text-sm font-medium text-indigo-300">
                    {creatingOptTask ? '创建中...' : '去优化中心'}
                  </span>
                  <ArrowRight className="w-3 h-3 text-indigo-400 ml-auto group-hover:translate-x-1 transition-transform" />
                </div>
                <p className="text-xs text-slate-500">基于诊断结果生成优化策略</p>
              </button>

              <button
                onClick={() => navigate('/flywheel')}
                className="p-3 bg-gradient-to-br from-emerald-500/20 to-teal-500/20 border border-emerald-500/30 rounded-lg hover:border-emerald-400/50 transition-all text-left group"
              >
                <div className="flex items-center gap-2 mb-1">
                  <RefreshCw className="w-4 h-4 text-emerald-400" />
                  <span className="text-sm font-medium text-emerald-300">查看数据飞轮</span>
                  <ArrowRight className="w-3 h-3 text-emerald-400 ml-auto group-hover:translate-x-1 transition-transform" />
                </div>
                <p className="text-xs text-slate-500">诊断已驱动飞轮更新</p>
              </button>

              <button
                onClick={() => { setResult(null); setLastReportId(null); }}
                className="p-3 bg-slate-800/50 border border-slate-700 rounded-lg hover:border-slate-600 transition-all text-left group"
              >
                <div className="flex items-center gap-2 mb-1">
                  <Stethoscope className="w-4 h-4 text-slate-400" />
                  <span className="text-sm font-medium text-slate-300">{t('diagnosis.reDiagnose')}</span>
                </div>
                <p className="text-xs text-slate-500">诊断另一段对话</p>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* History Modal */}
      {historyOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div
            className="absolute inset-0 bg-black/60"
            onClick={() => setHistoryOpen(false)}
          />
          <div className="relative bg-slate-900 border border-slate-700 rounded-lg p-4 w-full max-w-2xl max-h-[80vh] overflow-hidden shadow-xl">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-base font-semibold text-slate-100">{t('diagnosis.historyTitle')}</h3>
              <button
                onClick={() => setHistoryOpen(false)}
                className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="overflow-y-auto max-h-[60vh] space-y-1.5">
              {historyLoading ? (
                <div className="flex justify-center py-8">
                  <Loader2 className="w-6 h-6 animate-spin text-indigo-400" />
                </div>
              ) : historyList.length === 0 ? (
                <p className="text-xs text-slate-500 py-6 text-center">{t('diagnosis.noHistory')}</p>
              ) : (
                historyList.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => handleSelectHistory(item)}
                    className="w-full text-left glass-card p-3 hover:border-indigo-500/50 transition-all"
                  >
                    <div className="flex items-center justify-between">
                      <p className="text-xs text-slate-200 line-clamp-2 flex-1 mr-2">
                        {item.conversation_text.slice(0, 80)}...
                      </p>
                      <span
                        className={cn(
                          'text-base font-bold flex-shrink-0',
                          getScoreColor(item.overall_score),
                        )}
                      >
                        {item.overall_score}
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 mt-1">
                      {new Date(item.created_at).toLocaleString()}
                    </p>
                  </button>
                ))
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
