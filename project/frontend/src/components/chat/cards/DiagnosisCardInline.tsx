import { Stethoscope } from 'lucide-react';

interface Props {
  title: string;
  data: Record<string, unknown>;
}

export default function DiagnosisCardInline({ title, data }: Props) {
  const score = data.overall_score as number | undefined;
  const dimensions = data.dimensions as { name: string; score: number }[] | undefined;

  return (
    <div className="bg-slate-900/60 border border-amber-500/30 rounded-lg p-3 mt-2">
      <div className="flex items-center gap-2 mb-2">
        <Stethoscope className="w-4 h-4 text-amber-400" />
        <span className="text-xs font-semibold text-amber-300">{title}</span>
        {score != null && (
          <span className="ml-auto text-base font-bold text-amber-400">{score}分</span>
        )}
      </div>
      {dimensions && (
        <div className="space-y-1">
          {dimensions.slice(0, 4).map((d) => (
            <div key={d.name} className="flex items-center gap-2">
              <span className="text-[10px] text-slate-400 w-16 truncate">{d.name}</span>
              <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-amber-500 rounded-full transition-all"
                  style={{ width: `${d.score}%` }}
                />
              </div>
              <span className="text-[10px] text-slate-500 w-8 text-right">{d.score}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
