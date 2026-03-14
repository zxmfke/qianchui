import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Plus,
  Search,
  AlertCircle,
  Package,
  Headphones,
  ArrowRight,
  BookOpen,
  Loader2,
  X,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import type { PainPoint, Product, Service } from '@/types';
import { memoryService } from '@/services/memory';

type TabType = 'painpoints' | 'products' | 'services';

// API response types
interface ApiPainPoint {
  id: string;
  name: string;
  description?: string | null;
  created_at: string;
}

interface ApiProduct {
  id: string;
  name: string;
  description?: string | null;
  pain_points?: ApiPainPoint[];
  created_at: string;
}

interface ApiService {
  id: string;
  name: string;
  description?: string | null;
  products?: ApiProduct[];
  created_at: string;
}

function toPainPoint(p: ApiPainPoint): PainPoint {
  return {
    id: p.id,
    title: p.name,
    description: p.description || '',
    severity: 'medium',
    frequency: 0,
    related_products: [],
    source: '未知',
    created_at: p.created_at,
  };
}

function toProduct(p: ApiProduct): Product {
  return {
    id: p.id,
    name: p.name,
    description: p.description || '',
    features: [],
    price_range: '-',
    target_audience: '-',
    pain_points_solved: (p.pain_points || []).map((pp) => pp.id),
    created_at: p.created_at,
  };
}

function toService(s: ApiService): Service {
  return {
    id: s.id,
    name: s.name,
    description: s.description || '',
    service_type: '通用服务',
    sla: '-',
    related_products: (s.products || []).map((p) => p.id),
    created_at: s.created_at,
  };
}

const severityConfig = {
  critical: { labelKey: 'memory.severity.critical', color: 'bg-red-500/20 text-red-400 border-red-500/30' },
  high: { labelKey: 'memory.severity.high', color: 'bg-amber-500/20 text-amber-400 border-amber-500/30' },
  medium: { labelKey: 'memory.severity.medium', color: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
  low: { labelKey: 'memory.severity.low', color: 'bg-slate-500/20 text-slate-400 border-slate-500/30' },
};

const tabs: { key: TabType; labelKey: string; icon: React.ComponentType<{ className?: string }> }[] = [
  { key: 'painpoints', labelKey: 'memory.tabs.painpoints', icon: AlertCircle },
  { key: 'products', labelKey: 'memory.tabs.products', icon: Package },
  { key: 'services', labelKey: 'memory.tabs.services', icon: Headphones },
];

function filterBySearch<T extends { title?: string; name?: string; description?: string }>(
  items: T[],
  search: string
): T[] {
  if (!search.trim()) return items;
  const q = search.trim().toLowerCase();
  return items.filter(
    (item) =>
      (item.title || item.name || '').toLowerCase().includes(q) ||
      (item.description || '').toLowerCase().includes(q)
  );
}

export default function MemoryPage() {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState<TabType>('painpoints');
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [painPoints, setPainPoints] = useState<PainPoint[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [services, setServices] = useState<Service[]>([]);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [createName, setCreateName] = useState('');
  const [createDesc, setCreateDesc] = useState('');
  const [createSubmitting, setCreateSubmitting] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [ppRes, prodRes, svcRes] = await Promise.all([
        memoryService.getPainPoints(),
        memoryService.getProducts(),
        memoryService.getServices(),
      ]);
      setPainPoints((ppRes as ApiPainPoint[]).map(toPainPoint));
      setProducts((prodRes as ApiProduct[]).map(toProduct));
      setServices((svcRes as ApiService[]).map(toService));
    } catch (err) {
      console.error('Failed to load memory data:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleCreate = async () => {
    const name = createName.trim();
    if (!name) return;
    setCreateSubmitting(true);
    setCreateError(null);
    try {
      if (activeTab === 'painpoints') {
        await memoryService.createPainPoint({ name, description: createDesc.trim() || undefined });
      } else if (activeTab === 'products') {
        await memoryService.createProduct({ name, description: createDesc.trim() || undefined });
      } else {
        await memoryService.createService({ name, description: createDesc.trim() || undefined });
      }
      setCreateModalOpen(false);
      setCreateName('');
      setCreateDesc('');
      await loadData();
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : t('common.createFailed');
      setCreateError(msg);
    } finally {
      setCreateSubmitting(false);
    }
  };

  const openCreateModal = () => {
    setCreateName('');
    setCreateDesc('');
    setCreateError(null);
    setCreateModalOpen(true);
  };

  const filteredPainPoints = filterBySearch(painPoints, search);
  const filteredProducts = filterBySearch(products, search);
  const filteredServices = filterBySearch(services, search);

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-lg font-bold text-slate-100">{t('memory.title')}</h1>
          <p className="text-xs text-slate-500 mt-1">{t('memory.subtitle')}</p>
        </div>
        <button onClick={openCreateModal} className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" />
          {t('common.add')}
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-slate-900 p-1 rounded-lg w-fit">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={cn(
              'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all',
              activeTab === tab.key
                ? 'bg-indigo-600 text-white'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800',
            )}
          >
            <tab.icon className="w-4 h-4" />
            {t(tab.labelKey)}
          </button>
        ))}
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder={t('memory.searchPlaceholder')}
          className="input-field pl-9"
        />
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-16">
          <Loader2 className="w-8 h-8 animate-spin text-indigo-400" />
        </div>
      ) : (
        <>
          {activeTab === 'painpoints' && (
            <div className="space-y-3">
              {filteredPainPoints.map((item) => (
                <div
                  key={item.id}
                  className="glass-card p-4 hover:border-indigo-500/50 transition-all cursor-pointer"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="text-sm font-semibold text-slate-200">{item.title}</h3>
                        <span
                          className={cn('badge border', severityConfig[item.severity].color)}
                        >
                          {t(severityConfig[item.severity].labelKey)}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 mb-2">{item.description}</p>
                      <div className="flex items-center gap-3 text-xs text-slate-500">
                        <span>{t('memory.frequency')}：{item.frequency}</span>
                        <span>{t('memory.sourceLabel')}：{item.source === '未知' ? t('memory.unknown') : item.source}</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
              {filteredPainPoints.length === 0 && (
                <p className="text-sm text-slate-500 py-8 text-center">{t('common.noData')}</p>
              )}
            </div>
          )}

          {activeTab === 'products' && (
            <div className="grid grid-cols-3 gap-4">
              {filteredProducts.map((item) => (
                <div
                  key={item.id}
                  className="glass-card p-4 hover:border-indigo-500/50 transition-all cursor-pointer"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <Package className="w-4 h-4 text-indigo-400" />
                    <h3 className="text-sm font-semibold text-slate-200">{item.name}</h3>
                  </div>
                  <p className="text-xs text-slate-400 mb-2">{item.description}</p>
                  <div className="flex flex-wrap gap-1 mb-2">
                    {item.features.length > 0 ? (
                      item.features.map((f) => (
                        <span
                          key={f}
                          className="badge bg-indigo-500/20 text-indigo-300 border border-indigo-500/30"
                        >
                          {f}
                        </span>
                      ))
                    ) : (
                      <span className="text-xs text-slate-500">-</span>
                    )}
                  </div>
                  <div className="text-xs text-slate-500 space-y-1">
                    <p>💰 {item.price_range}</p>
                    <p>🎯 {item.target_audience}</p>
                  </div>
                </div>
              ))}
              {filteredProducts.length === 0 && (
                <p className="col-span-3 text-sm text-slate-500 py-8 text-center">{t('common.noData')}</p>
              )}
            </div>
          )}

          {activeTab === 'services' && (
            <div className="space-y-3">
              {filteredServices.map((item) => (
                <div
                  key={item.id}
                  className="glass-card p-4 hover:border-indigo-500/50 transition-all cursor-pointer"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <Headphones className="w-4 h-4 text-emerald-400" />
                    <h3 className="text-sm font-semibold text-slate-200">{item.name}</h3>
                    <span className="badge bg-slate-700 text-slate-400">{item.service_type === '通用服务' ? t('memory.generalService') : item.service_type}</span>
                  </div>
                  <p className="text-xs text-slate-400 mb-2">{item.description}</p>
                  {item.sla && <p className="text-xs text-slate-500">SLA：{item.sla}</p>}
                </div>
              ))}
              {filteredServices.length === 0 && (
                <p className="text-sm text-slate-500 py-8 text-center">{t('common.noData')}</p>
              )}
            </div>
          )}
        </>
      )}

      {/* Knowledge chain visualization */}
      <div className="glass-card p-4">
        <div className="flex items-center gap-2 mb-3">
          <BookOpen className="w-4 h-4 text-indigo-400" />
          <h2 className="text-sm font-semibold text-slate-200">{t('memory.knowledgeChain')}</h2>
          <span className="text-xs text-slate-500">{t('memory.knowledgeChainDesc')}</span>
        </div>
        <div className="flex items-center gap-3 overflow-x-auto pb-2">
          <div className="flex-shrink-0 bg-red-500/10 border border-red-500/30 rounded-lg p-3 w-40">
            <p className="text-xs text-red-400 font-medium mb-1">{t('memory.painPoint')}</p>
            <p className="text-sm text-slate-200">
              {painPoints[0]?.title || t('memory.none')}
            </p>
            <p className="text-xs text-slate-500 mt-1">{t('memory.frequency')} {painPoints[0]?.frequency ?? '-'}</p>
          </div>
          <ArrowRight className="w-4 h-4 text-slate-600 flex-shrink-0" />
          <div className="flex-shrink-0 bg-indigo-500/10 border border-indigo-500/30 rounded-lg p-3 w-40">
            <p className="text-xs text-indigo-400 font-medium mb-1">{t('memory.product')}</p>
            <p className="text-sm text-slate-200">{products[0]?.name || t('memory.none')}</p>
            <p className="text-xs text-slate-500 mt-1">{products[0]?.price_range ?? '-'}</p>
          </div>
          <ArrowRight className="w-4 h-4 text-slate-600 flex-shrink-0" />
          <div className="flex-shrink-0 bg-emerald-500/10 border border-emerald-500/30 rounded-lg p-3 w-40">
            <p className="text-xs text-emerald-400 font-medium mb-1">{t('memory.service')}</p>
            <p className="text-sm text-slate-200">{services[0]?.name || t('memory.none')}</p>
            <p className="text-xs text-slate-500 mt-1">{t('memory.monthlyDelivery')}</p>
          </div>
          <ArrowRight className="w-4 h-4 text-slate-600 flex-shrink-0" />
          <div className="flex-shrink-0 bg-purple-500/10 border border-purple-500/30 rounded-lg p-3 w-40">
            <p className="text-xs text-purple-400 font-medium mb-1">{t('memory.script')}</p>
            <p className="text-sm text-slate-200">{t('memory.roiAnchor')}</p>
            <p className="text-xs text-slate-500 mt-1">{t('memory.conversionRate')} 89%</p>
          </div>
        </div>
      </div>

      {/* Create Modal */}
      {createModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
          <div
            className="absolute inset-0 bg-black/60"
            onClick={() => !createSubmitting && setCreateModalOpen(false)}
          />
          <div className="relative bg-slate-900 border border-slate-700 rounded-lg p-4 w-full max-w-md shadow-xl">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-base font-semibold text-slate-100">
                {t(activeTab === 'painpoints' ? 'memory.createPainPoint' : activeTab === 'products' ? 'memory.createProduct' : 'memory.createService')}
              </h3>
              <button
                onClick={() => !createSubmitting && setCreateModalOpen(false)}
                className="p-1 rounded hover:bg-slate-800 text-slate-400 hover:text-slate-200"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="space-y-3">
              <div>
                <label className="block text-sm text-slate-400 mb-1">{t('memory.nameLabel')} *</label>
                <input
                  type="text"
                  value={createName}
                  onChange={(e) => setCreateName(e.target.value)}
                  placeholder={t('memory.namePlaceholder')}
                  className="input-field w-full"
                />
              </div>
              <div>
                <label className="block text-sm text-slate-400 mb-1">{t('memory.descLabel')}</label>
                <textarea
                  value={createDesc}
                  onChange={(e) => setCreateDesc(e.target.value)}
                  placeholder={t('memory.descPlaceholder')}
                  rows={3}
                  className="input-field w-full resize-none"
                />
              </div>
              {createError && (
                <p className="text-sm text-red-400">{createError}</p>
              )}
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <button
                onClick={() => !createSubmitting && setCreateModalOpen(false)}
                className="btn-secondary"
              >
                {t('common.cancel')}
              </button>
              <button
                onClick={handleCreate}
                disabled={!createName.trim() || createSubmitting}
                className="btn-primary flex items-center gap-2"
              >
                {createSubmitting && <Loader2 className="w-4 h-4 animate-spin" />}
                {t('common.create')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
