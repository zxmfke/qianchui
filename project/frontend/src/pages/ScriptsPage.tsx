import { useEffect, useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { Search, Filter, Plus, BookOpen, ChevronDown, X } from 'lucide-react';
import { useScriptStore } from '@/stores/scriptStore';
import ScriptCard from '@/components/cards/ScriptCard';
import { cn } from '@/lib/utils';
import type { Script, ScriptPsychology, ScriptStrategy, ScriptContent } from '@/types';

const CATEGORIES = ['全部', '开场白', '异议处理', '竞品应对', '促成', '售后', '复购'];

/** 后端 API 返回的 Script 结构（扁平字段） */
interface BackendScriptResponse {
  id: string;
  title: string;
  category: string | null;
  tags: string[];
  psychology_layer: string | null;
  strategy_layer: string | null;
  content: string;
  usage_count: number;
  conversion_rate: number;
  user_rating?: number;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

/** 将后端数据适配为前端 Script 类型 */
function adaptScript(raw: BackendScriptResponse): Script {
  let psychology: ScriptPsychology = {
    customer_type: '',
    emotion_state: '中性',
    resistance_level: 3,
    decision_stage: '考虑阶段',
    core_need: '',
  };
  if (raw.psychology_layer) {
    try {
      const parsed = JSON.parse(raw.psychology_layer) as Partial<ScriptPsychology>;
      psychology = { ...psychology, ...parsed };
    } catch {
      psychology.customer_type = raw.psychology_layer;
    }
  }

  let strategy: ScriptStrategy = {
    approach: '',
    techniques: [],
    timing: '',
    risk_level: 'low',
  };
  if (raw.strategy_layer) {
    try {
      const parsed = JSON.parse(raw.strategy_layer) as Partial<ScriptStrategy>;
      strategy = { ...strategy, ...parsed };
    } catch {
      strategy.approach = raw.strategy_layer;
    }
  }

  let content: ScriptContent = { opening: '', body: '', closing: '' };
  if (raw.content) {
    try {
      const parsed = JSON.parse(raw.content) as Partial<ScriptContent>;
      content = { ...content, ...parsed };
    } catch {
      content.body = raw.content;
    }
  }

  return {
    id: String(raw.id),
    title: raw.title,
    category: raw.category ?? '',
    tags: Array.isArray(raw.tags) ? raw.tags : [],
    psychology,
    strategy,
    content,
    usage_count: raw.usage_count ?? 0,
    success_rate: raw.conversion_rate ?? 0,
    created_by: raw.created_by ?? '',
    created_at: raw.created_at,
    updated_at: raw.updated_at,
  };
}

/** 创建话术的 API 请求体 */
interface CreateScriptPayload {
  title: string;
  category?: string;
  tags?: string[];
  psychology_layer?: string;
  strategy_layer?: string;
  content: string;
  difficulty?: number;
  target_role?: string;
}

export default function ScriptsPage() {
  const { t } = useTranslation();
  const {
    scripts: rawScripts,
    total,
    isLoading,
    filters,
    setFilters,
    loadScripts,
    createScript,
  } = useScriptStore();

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showFilter, setShowFilter] = useState(false);
  const [createSubmitting, setCreateSubmitting] = useState(false);
  const [createForm, setCreateForm] = useState({
    title: '',
    category: '',
    tagsInput: '',
    psychology_layer: '',
    strategy_layer: '',
    opening: '',
    body: '',
    closing: '',
  });

  const adaptedScripts = rawScripts.map((s) => adaptScript(s as unknown as BackendScriptResponse));

  const handleCopyToClipboard = useCallback((script: Script) => {
    const text = [script.content.opening, script.content.body, script.content.closing]
      .filter(Boolean)
      .join('\n\n');
    if (text) {
      navigator.clipboard.writeText(text).then(
        () => {
          // 可选：toast 提示
        },
        () => {},
      );
    }
  }, []);

  useEffect(() => {
    loadScripts();
  }, [loadScripts]);

  const handleCategoryChange = (cat: string) => {
    setFilters({ category: cat === '全部' ? '' : cat });
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!createForm.title.trim()) return;
    setCreateSubmitting(true);
    try {
      const tags = createForm.tagsInput
        .split(/[,，、\s]+/)
        .map((t) => t.trim())
        .filter(Boolean);
      const content = JSON.stringify({
        opening: createForm.opening,
        body: createForm.body,
        closing: createForm.closing,
      });
      const payload: CreateScriptPayload = {
        title: createForm.title.trim(),
        category: createForm.category || undefined,
        tags,
        psychology_layer: createForm.psychology_layer || undefined,
        strategy_layer: createForm.strategy_layer || undefined,
        content,
        difficulty: 1,
        target_role: 'all',
      };
      await createScript(payload as unknown as Partial<Script>);
      setShowCreateModal(false);
      setCreateForm({
        title: '',
        category: '',
        tagsInput: '',
        psychology_layer: '',
        strategy_layer: '',
        opening: '',
        body: '',
        closing: '',
      });
    } catch (err) {
      console.error('Create script failed:', err);
    } finally {
      setCreateSubmitting(false);
    }
  };

  const selectedCategory = filters.category || '全部';

  const categoryDisplay = (cat: string) => {
    const map: Record<string, string> = {
      '全部': t('scripts.categories.all'),
      '开场白': t('scripts.categories.opening'),
      '异议处理': t('scripts.categories.objection'),
      '竞品应对': t('scripts.categories.competitor'),
      '促成': t('scripts.categories.closing'),
      '售后': t('scripts.categories.afterSales'),
      '复购': t('scripts.categories.repurchase'),
    };
    return map[cat] ?? cat;
  };

  return (
    <div className="p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-slate-100">{t('scripts.title')}</h1>
          <p className="text-xs text-slate-500 mt-1">
            {isLoading ? t('common.loading') : t('scripts.count', { count: total })}
          </p>
        </div>
        <button
          type="button"
          onClick={() => setShowCreateModal(true)}
          className="btn-primary flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          {t('scripts.addScript')}
        </button>
      </div>

      {/* Search & filters */}
      <div className="flex items-center gap-2">
        <div className="relative flex-1 max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
          <input
            type="text"
            value={filters.search}
            onChange={(e) => setFilters({ search: e.target.value })}
            placeholder={t('scripts.searchPlaceholder')}
            className="input-field pl-9"
          />
        </div>
        <button
          type="button"
          onClick={() => setShowFilter(!showFilter)}
          className={cn('btn-secondary flex items-center gap-2', showFilter && 'bg-slate-600')}
        >
          <Filter className="w-4 h-4" />
          {t('common.filter')}
          <ChevronDown className={cn('w-3 h-3 transition-transform', showFilter && 'rotate-180')} />
        </button>
      </div>

      {/* Category tabs */}
      <div className="flex gap-2 overflow-x-auto pb-1">
        {CATEGORIES.map((cat) => (
          <button
            key={cat}
            type="button"
            onClick={() => handleCategoryChange(cat)}
            className={cn(
              'px-4 py-1.5 rounded-full text-sm font-medium whitespace-nowrap transition-all',
              selectedCategory === cat
                ? 'bg-indigo-600 text-white'
                : 'bg-slate-800 text-slate-400 hover:bg-slate-700',
            )}
          >
            {categoryDisplay(cat)}
          </button>
        ))}
      </div>

      {/* Script grid */}
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-20">
          <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          <p className="text-slate-500 mt-3">{t('common.loading')}</p>
        </div>
      ) : adaptedScripts.length > 0 ? (
        <div className="grid grid-cols-3 gap-4">
          {adaptedScripts.map((script) => (
            <ScriptCard
              key={script.id}
              script={script}
              onUse={handleCopyToClipboard}
            />
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-20">
          <BookOpen className="w-10 h-10 text-slate-700 mb-2" />
          <p className="text-slate-500">{t('scripts.noScripts')}</p>
        </div>
      )}

      {/* 新增话术弹窗 */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div
            className="absolute inset-0 bg-black/60"
            onClick={() => !createSubmitting && setShowCreateModal(false)}
            aria-hidden
          />
          <div className="relative w-full max-w-lg max-h-[90vh] overflow-y-auto bg-slate-900 border border-slate-700 rounded-lg shadow-xl">
            <div className="sticky top-0 flex items-center justify-between p-3 border-b border-slate-700 bg-slate-900/95">
              <h2 className="text-base font-semibold text-slate-100">{t('scripts.createTitle')}</h2>
              <button
                type="button"
                onClick={() => !createSubmitting && setShowCreateModal(false)}
                className="p-1 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-700 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <form onSubmit={handleCreateSubmit} className="p-3 space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">{t('scripts.titleLabel')} *</label>
                <input
                  type="text"
                  value={createForm.title}
                  onChange={(e) => setCreateForm((f) => ({ ...f, title: e.target.value }))}
                  placeholder={t('scripts.titlePlaceholder')}
                  required
                  className="input-field w-full"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">{t('scripts.categoryLabel')}</label>
                <select
                  value={createForm.category}
                  onChange={(e) => setCreateForm((f) => ({ ...f, category: e.target.value }))}
                  className="input-field w-full bg-slate-800 border-slate-600 text-slate-100"
                >
                  <option value="">{t('scripts.categoryPlaceholder')}</option>
                  {CATEGORIES.filter((c) => c !== '全部').map((c) => (
                    <option key={c} value={c}>
                      {categoryDisplay(c)}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">{t('scripts.tagsLabel')}</label>
                <input
                  type="text"
                  value={createForm.tagsInput}
                  onChange={(e) => setCreateForm((f) => ({ ...f, tagsInput: e.target.value }))}
                  placeholder={t('scripts.tagsPlaceholder')}
                  className="input-field w-full"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">{t('scripts.psychologyLabel')}</label>
                <textarea
                  value={createForm.psychology_layer}
                  onChange={(e) =>
                    setCreateForm((f) => ({ ...f, psychology_layer: e.target.value }))
                  }
                  placeholder={t('scripts.psychologyPlaceholder')}
                  rows={2}
                  className="input-field w-full resize-none"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">{t('scripts.strategyLabel')}</label>
                <textarea
                  value={createForm.strategy_layer}
                  onChange={(e) =>
                    setCreateForm((f) => ({ ...f, strategy_layer: e.target.value }))
                  }
                  placeholder={t('scripts.strategyPlaceholder')}
                  rows={2}
                  className="input-field w-full resize-none"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">{t('scripts.contentLabel')}</label>
                <div className="space-y-1.5">
                  <input
                    type="text"
                    value={createForm.opening}
                    onChange={(e) => setCreateForm((f) => ({ ...f, opening: e.target.value }))}
                    placeholder={t('scripts.openingPlaceholder')}
                    className="input-field w-full"
                  />
                  <textarea
                    value={createForm.body}
                    onChange={(e) => setCreateForm((f) => ({ ...f, body: e.target.value }))}
                    placeholder={t('scripts.bodyPlaceholder')}
                    rows={3}
                    className="input-field w-full resize-none"
                  />
                  <input
                    type="text"
                    value={createForm.closing}
                    onChange={(e) => setCreateForm((f) => ({ ...f, closing: e.target.value }))}
                    placeholder={t('scripts.closingPlaceholder')}
                    className="input-field w-full"
                  />
                </div>
              </div>
              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  disabled={createSubmitting}
                  className="btn-secondary"
                >
                  {t('common.cancel')}
                </button>
                <button
                  type="submit"
                  disabled={createSubmitting}
                  className="btn-primary disabled:opacity-50"
                >
                  {createSubmitting ? t('common.creating') : t('common.create')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
