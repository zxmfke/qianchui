import { FlaskConical, TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface ABTestVariant {
  name: string;
  traffic_ratio: number;
  sessions: number;
  acquisitions: number;
  acquisition_rate: number;
  reply_rate: number;
  avg_turns: number;
}

interface ABTestCardInlineProps {
  data: {
    name: string;
    status: string;
    variants: ABTestVariant[];
    confidence?: number;
    winner?: string;
    duration_days?: number;
  };
}

const statusLabels: Record<string, [string, string]> = {
  draft: ['待启动', 'bg-slate-500/20 text-slate-400'],
  running: ['运行中', 'bg-blue-500/20 text-blue-400'],
  completed: ['已完成', 'bg-emerald-500/20 text-emerald-400'],
  stopped: ['已停止', 'bg-red-500/20 text-red-400'],
};

export default function ABTestCardInline({ data }: ABTestCardInlineProps) {
  const [label, cls] = statusLabels[data.status] || statusLabels.draft;
  const maxRate = Math.max(...data.variants.map((v) => v.acquisition_rate));

  return (
    <div className="bg-slate-800/50 rounded-lg border border-slate-700 p-3 my-2">
      <div className="flex items-center gap-2 mb-2">
        <FlaskConical className="w-4 h-4 text-indigo-400" />
        <span className="text-xs text-white font-medium">{data.name}</span>
        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${cls}`}>{label}</span>
        {data.confidence != null && (
          <span className="text-[10px] text-slate-500 ml-auto">
            置信度 {(data.confidence * 100).toFixed(0)}%
          </span>
        )}
      </div>

      <div className="space-y-2">
        {data.variants.map((v, i) => {
          const isWinner = data.winner === v.name;
          const diff = data.variants.length > 1
            ? v.acquisition_rate - data.variants[1 - i]?.acquisition_rate
            : 0;
          return (
            <div key={i} className={`rounded p-2.5 ${isWinner ? 'bg-emerald-900/20 border border-emerald-800/50' : 'bg-slate-900/50'}`}>
              <div className="flex items-center gap-2 mb-1.5">
                <span className="text-xs font-medium text-white">{v.name}</span>
                {isWinner && (
                  <span className="px-1.5 py-0.5 bg-emerald-500/20 text-emerald-400 text-[10px] rounded">
                    胜出
                  </span>
                )}
                <span className="text-[10px] text-slate-500 ml-auto">
                  流量 {(v.traffic_ratio * 100).toFixed(0)}%
                </span>
              </div>
              <div className="grid grid-cols-4 gap-2 text-center">
                <div>
                  <p className={`text-xs font-bold ${v.acquisition_rate === maxRate ? 'text-emerald-400' : 'text-white'}`}>
                    {(v.acquisition_rate * 100).toFixed(1)}%
                  </p>
                  <p className="text-[10px] text-slate-500">留联率</p>
                </div>
                <div>
                  <p className="text-xs font-bold text-white">{(v.reply_rate * 100).toFixed(1)}%</p>
                  <p className="text-[10px] text-slate-500">回复率</p>
                </div>
                <div>
                  <p className="text-xs font-bold text-white">{v.avg_turns.toFixed(1)}</p>
                  <p className="text-[10px] text-slate-500">平均轮次</p>
                </div>
                <div>
                  <p className="text-xs font-bold text-white">{v.sessions}</p>
                  <p className="text-[10px] text-slate-500">会话数</p>
                </div>
              </div>
              {diff !== 0 && (
                <div className={`text-[10px] mt-1 flex items-center gap-1 ${diff > 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {diff > 0 ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                  留联率差异 {diff > 0 ? '+' : ''}{(diff * 100).toFixed(2)}%
                </div>
              )}
            </div>
          );
        })}
      </div>

      {data.duration_days != null && (
        <p className="text-[10px] text-slate-500 mt-2 text-right">
          已运行 {data.duration_days} 天
        </p>
      )}
    </div>
  );
}
