import { BarChart3 } from 'lucide-react';

interface Props {
  title: string;
  data: Record<string, unknown>;
}

export default function DataCardInline({ title, data }: Props) {
  const metrics = data.metrics as { label: string; value: string | number; trend?: number }[] | undefined;

  return (
    <div className="bg-slate-900/60 border border-cyan-500/30 rounded-lg p-3 mt-2">
      <div className="flex items-center gap-2 mb-2">
        <BarChart3 className="w-4 h-4 text-cyan-400" />
        <span className="text-xs font-semibold text-cyan-300">{title}</span>
      </div>
      {metrics && (
        <div className="grid grid-cols-2 gap-2">
          {metrics.map((m) => (
            <div key={m.label} className="bg-slate-800 rounded-lg p-2">
              <p className="text-[10px] text-slate-500">{m.label}</p>
              <p className="text-xs font-bold text-slate-200">{m.value}</p>
              {m.trend != null && (
                <p className={`text-[10px] ${m.trend >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>
                  {m.trend >= 0 ? '↑' : '↓'} {Math.abs(m.trend)}%
                </p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
