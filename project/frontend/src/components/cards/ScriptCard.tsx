import { Copy, TrendingUp, BarChart2, MoreHorizontal } from 'lucide-react';
import type { Script } from '@/types';
import { cn, formatPercent, truncate } from '@/lib/utils';

interface ScriptCardProps {
  script: Script;
  onUse?: (script: Script) => void;
  onClick?: (script: Script) => void;
  compact?: boolean;
}

export default function ScriptCard({ script, onUse, onClick, compact }: ScriptCardProps) {
  return (
    <div
      onClick={() => onClick?.(script)}
      className={cn(
        'glass-card p-3 hover:border-indigo-500/50 transition-all duration-200 cursor-pointer group',
        compact && 'p-2.5',
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-2">
        <h3 className={cn('font-semibold text-slate-100', compact ? 'text-xs' : 'text-sm')}>
          {truncate(script.title, 24)}
        </h3>
        <button
          className="p-1 rounded opacity-0 group-hover:opacity-100 text-slate-500 hover:text-slate-300 hover:bg-slate-700 transition-all"
          onClick={(e) => {
            e.stopPropagation();
          }}
        >
          <MoreHorizontal className="w-4 h-4" />
        </button>
      </div>

      {/* Three-layer badges */}
      <div className="flex flex-wrap gap-1 mb-2">
        <span className="badge bg-purple-500/20 text-purple-300 border border-purple-500/30">
          🧠 {script.psychology.customer_type}
        </span>
        <span className="badge bg-blue-500/20 text-blue-300 border border-blue-500/30">
          🎯 {script.strategy.approach}
        </span>
        <span className="badge bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
          💬 {script.category}
        </span>
      </div>

      {/* Preview */}
      {!compact && (
        <p className="text-xs text-slate-400 mb-2 line-clamp-2">
          {script.content.opening}
        </p>
      )}

      {/* Tags */}
      <div className="flex flex-wrap gap-1 mb-2">
        {script.tags.slice(0, 3).map((tag) => (
          <span key={tag} className="text-xs text-slate-500 bg-slate-800 px-1.5 py-0.5 rounded">
            #{tag}
          </span>
        ))}
      </div>

      {/* Stats */}
      <div className="flex items-center justify-between pt-2 border-t border-slate-700/50">
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <span className="flex items-center gap-1">
            <Copy className="w-3 h-3" />
            {script.usage_count}
          </span>
          <span className="flex items-center gap-1">
            <TrendingUp className="w-3 h-3" />
            {formatPercent(script.success_rate)}
          </span>
        </div>
        {onUse && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onUse(script);
            }}
            className="flex items-center gap-1 text-xs text-indigo-400 hover:text-indigo-300 font-medium transition-colors"
          >
            <BarChart2 className="w-3 h-3" />
            使用
          </button>
        )}
      </div>
    </div>
  );
}
