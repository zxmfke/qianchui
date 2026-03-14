import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Share2,
  Upload,
  Link,
  Video,
  Image,
  FileText,
  Search as SearchIcon,
  Eye,
  Heart,
  Sparkles,
  Loader2,
  X,
} from 'lucide-react';
import { channelMaterialService } from '@/services/channelMaterial';

type Channel = 'douyin' | 'xhs' | 'wechat' | 'baidu';

interface Material {
  id: string;
  channel: string;
  title: string;
  content: string;
  material_type: string;
  metrics: { views?: number; likes?: number };
  extracted_info?: Record<string, unknown>;
  tags?: string[];
  status: string;
}

interface Stats {
  by_channel?: Record<string, number>;
  total?: number;
}

const CHANNELS: { key: Channel; labelKey: string }[] = [
  { key: 'douyin', labelKey: 'channelMaterials.channels.douyin' },
  { key: 'xhs', labelKey: 'channelMaterials.channels.xhs' },
  { key: 'wechat', labelKey: 'channelMaterials.channels.wechat' },
  { key: 'baidu', labelKey: 'channelMaterials.channels.baidu' },
];

const channelColors: Record<string, string> = {
  douyin: 'bg-pink-500/10 text-pink-400 border-pink-500/20',
  xhs: 'bg-red-500/10 text-red-400 border-red-500/20',
  wechat: 'bg-green-500/10 text-green-400 border-green-500/20',
  baidu: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
};

const typeIcons: Record<string, React.ElementType> = {
  video: Video,
  image: Image,
  article: FileText,
  ad: SearchIcon,
};

const MATERIAL_TYPES = [
  { value: 'video', labelKey: 'channelMaterials.types.video' },
  { value: 'image', labelKey: 'channelMaterials.types.image' },
  { value: 'article', labelKey: 'channelMaterials.types.article' },
  { value: 'ad', labelKey: 'channelMaterials.types.ad' },
];

function formatMetric(value: number | undefined, tenThousandLabel: string): string {
  if (value == null || value === undefined) return '—';
  if (value >= 10000) {
    return `${(value / 10000).toFixed(1)}${tenThousandLabel}`;
  }
  return value.toLocaleString();
}

export default function ChannelMaterialsPage() {
  const { t } = useTranslation();
  const [activeChannel, setActiveChannel] = useState<Channel>('douyin');
  const [materials, setMaterials] = useState<Material[]>([]);
  const [stats, setStats] = useState<Stats>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [extractingId, setExtractingId] = useState<string | null>(null);

  const fetchMaterials = useCallback(
    async (channel?: string) => {
      setLoading(true);
      setError(null);
      try {
        const res = await channelMaterialService.getMaterials({
          channel: channel ?? activeChannel,
          page: 1,
          page_size: 50,
        });
        setMaterials(res.items ?? []);
      } catch (e) {
        setError(e instanceof Error ? e.message : t('channelMaterials.loadFailed'));
        setMaterials([]);
      } finally {
        setLoading(false);
      }
    },
    [activeChannel, t]
  );

  const fetchStats = useCallback(async () => {
    try {
      const res = await channelMaterialService.getStats();
      setStats(res);
    } catch {
      setStats({});
    }
  }, []);

  useEffect(() => {
    fetchMaterials(activeChannel);
  }, [activeChannel, fetchMaterials]);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  const handleChannelSwitch = (ch: Channel) => {
    setActiveChannel(ch);
  };

  const handleCreateSubmit = async (data: {
    channel: string;
    title: string;
    content: string;
    material_type: string;
    source_url?: string;
  }) => {
    try {
      await channelMaterialService.createMaterial(data);
      setCreateModalOpen(false);
      fetchMaterials(activeChannel);
      fetchStats();
    } catch (e) {
      throw e;
    }
  };

  const handleExtract = async (id: string) => {
    setExtractingId(id);
    try {
      const res = await channelMaterialService.extractInfo(id);
      const updated = materials.map((m) =>
        m.id === id ? { ...m, extracted_info: res.extracted_info ?? m.extracted_info } : m
      );
      setMaterials(updated);
    } catch {
      // 提取失败时保持原状
    } finally {
      setExtractingId(null);
    }
  };

  const channelCounts = stats.by_channel ?? {};
  const totalCount = stats.total ?? 0;
  const extractedCount = materials.filter((m) => m.extracted_info && Object.keys(m.extracted_info).length > 0).length;

  return (
    <div className="p-4">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <Share2 className="w-4 h-4 text-indigo-400" />
          <h1 className="text-base font-bold text-white">{t('channelMaterials.title')}</h1>
          <span className="text-xs text-slate-500">
            {t('channelMaterials.totalCount', { total: totalCount })} · {t('channelMaterials.extractedCount', { count: extractedCount })}
          </span>
        </div>
        <div className="flex gap-2">
          <button
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg border border-slate-700 text-slate-400 hover:border-indigo-500/30 hover:text-slate-200 transition-colors"
            title={t('channelMaterials.urlFetch')}
          >
            <Link className="w-3.5 h-3.5" />
            {t('channelMaterials.urlFetch')}
          </button>
          <button
            onClick={() => setCreateModalOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 transition-colors"
          >
            <Upload className="w-3.5 h-3.5" />
            {t('channelMaterials.upload')}
          </button>
        </div>
      </div>

      <div className="flex gap-2 mb-4">
        {CHANNELS.map((ch) => (
          <button
            key={ch.key}
            onClick={() => handleChannelSwitch(ch.key)}
            className={`px-4 py-2 rounded-lg text-xs font-medium transition-all ${
              activeChannel === ch.key
                ? 'bg-indigo-600 text-white'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
            }`}
          >
            {t(ch.labelKey)}
            <span className="ml-1.5 opacity-70">{channelCounts[ch.key] ?? 0}</span>
          </button>
        ))}
      </div>

      {error && (
        <div className="mb-4 px-4 py-3 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400 text-sm">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center justify-center py-16 text-slate-400">
          <Loader2 className="w-8 h-8 animate-spin mr-2" />
          <span>{t('common.loading')}</span>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
          {materials.map((m) => {
            const TypeIcon = typeIcons[m.material_type] || FileText;
            const extracted = !!(m.extracted_info && Object.keys(m.extracted_info).length > 0);
            const isExtracting = extractingId === m.id;
            const ch = CHANNELS.find((c) => c.key === m.channel);
            return (
              <div
                key={m.id}
                className="bg-slate-800/50 border border-slate-700/50 rounded-lg overflow-hidden hover:border-indigo-500/30 transition-colors"
              >
                <div className="h-24 flex items-center justify-center bg-gradient-to-br from-indigo-500/5 to-cyan-500/5 relative">
                  <span
                    className={`absolute top-2 left-2 text-[10px] font-semibold px-1.5 py-0.5 rounded border ${channelColors[m.channel] ?? 'bg-slate-500/10 text-slate-400'}`}
                  >
                    {ch ? t(ch.labelKey) : m.channel}
                  </span>
                  <TypeIcon className="w-7 h-7 text-slate-600" />
                </div>
                <div className="p-3">
                  <h3 className="text-xs font-semibold text-white mb-2 line-clamp-2">{m.title}</h3>
                  <div className="flex gap-3 text-[10px] text-slate-500 mb-3">
                    <span className="flex items-center gap-1">
                      <Eye className="w-3 h-3" />
                      {formatMetric(m.metrics?.views, t('channelMaterials.tenThousand'))}
                    </span>
                    <span className="flex items-center gap-1">
                      <Heart className="w-3 h-3" />
                      {formatMetric(m.metrics?.likes, t('channelMaterials.tenThousand'))}
                    </span>
                  </div>
                  <div className="flex gap-1.5">
                    <button
                      className="flex items-center gap-1 px-2 py-1 text-[10px] rounded bg-indigo-600/80 text-white hover:bg-indigo-500 transition-colors"
                      title={t('channelMaterials.linkScript')}
                    >
                      <Link className="w-3 h-3" />
                      {t('channelMaterials.linkScript')}
                    </button>
                    <button
                      onClick={() => handleExtract(m.id)}
                      disabled={isExtracting}
                      className={`flex items-center gap-1 px-2 py-1 text-[10px] rounded border transition-colors ${
                        extracted
                          ? 'border-emerald-500/20 text-emerald-400 bg-emerald-500/5'
                          : 'border-slate-700 text-slate-400 hover:border-indigo-500/30'
                      } ${isExtracting ? 'opacity-60 cursor-not-allowed' : ''}`}
                    >
                      {isExtracting ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : (
                        <Sparkles className="w-3 h-3" />
                      )}
                      {extracted ? t('channelMaterials.extracted') : t('channelMaterials.aiExtract')}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {!loading && materials.length === 0 && !error && (
        <div className="py-16 text-center text-slate-500 text-sm">{t('channelMaterials.noMaterials')}</div>
      )}

      {createModalOpen && (
        <CreateMaterialModal
          onClose={() => setCreateModalOpen(false)}
          onSubmit={handleCreateSubmit}
          channels={CHANNELS}
          materialTypes={MATERIAL_TYPES}
        />
      )}
    </div>
  );
}

interface CreateMaterialModalProps {
  onClose: () => void;
  onSubmit: (data: {
    channel: string;
    title: string;
    content: string;
    material_type: string;
    source_url?: string;
  }) => Promise<void>;
  channels: { key: Channel; labelKey: string }[];
  materialTypes: { value: string; labelKey: string }[];
}

function CreateMaterialModal({ onClose, onSubmit, channels, materialTypes }: CreateMaterialModalProps) {
  const { t } = useTranslation();
  const [channel, setChannel] = useState<string>('douyin');
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [materialType, setMaterialType] = useState('video');
  const [sourceUrl, setSourceUrl] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitError(null);
    setSubmitting(true);
    try {
      await onSubmit({
        channel,
        title: title.trim(),
        content: content.trim(),
        material_type: materialType,
        source_url: sourceUrl.trim() || undefined,
      });
    } catch (e) {
      setSubmitError(e instanceof Error ? e.message : t('common.createFailed'));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div
        className="bg-slate-800 border border-slate-700 rounded-lg w-full max-w-md p-4 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-bold text-white">{t('channelMaterials.upload')}</h2>
          <button
            onClick={onClose}
            className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-700 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">{t('channelMaterials.channelLabel')}</label>
            <select
              value={channel}
              onChange={(e) => setChannel(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-white text-sm focus:border-indigo-500 focus:outline-none"
            >
              {channels.map(({ key, labelKey }) => (
                <option key={key} value={key}>
                  {t(labelKey)}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">{t('channelMaterials.titleLabel')}</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              placeholder={t('channelMaterials.titlePlaceholder')}
              className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-white text-sm placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">{t('channelMaterials.contentLabel')}</label>
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              required
              rows={3}
              placeholder={t('channelMaterials.contentPlaceholder')}
              className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-white text-sm placeholder-slate-500 focus:border-indigo-500 focus:outline-none resize-none"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">{t('channelMaterials.typeLabel')}</label>
            <select
              value={materialType}
              onChange={(e) => setMaterialType(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-white text-sm focus:border-indigo-500 focus:outline-none"
            >
              {materialTypes.map(({ value, labelKey }) => (
                <option key={value} value={value}>
                  {t(labelKey)}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1.5">{t('channelMaterials.sourceUrl')}</label>
            <input
              type="url"
              value={sourceUrl}
              onChange={(e) => setSourceUrl(e.target.value)}
              placeholder="https://..."
              className="w-full px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-white text-sm placeholder-slate-500 focus:border-indigo-500 focus:outline-none"
            />
          </div>
          {submitError && (
            <div className="text-sm text-red-400">{submitError}</div>
          )}
          <div className="flex gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 px-4 py-2 rounded-lg border border-slate-600 text-slate-300 hover:bg-slate-700 transition-colors"
            >
              {t('common.cancel')}
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="flex-1 px-4 py-2 rounded-lg bg-indigo-600 text-white hover:bg-indigo-500 transition-colors disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              {submitting && <Loader2 className="w-4 h-4 animate-spin" />}
              {t('common.submit')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
