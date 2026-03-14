import { GraduationCap } from 'lucide-react';

interface Props {
  title: string;
  data: Record<string, unknown>;
}

export default function TrainingCardInline({ title, data }: Props) {
  const question = data.question as string | undefined;
  const options = data.options as { key: string; text: string }[] | undefined;

  return (
    <div className="bg-slate-900/60 border border-emerald-500/30 rounded-lg p-3 mt-2">
      <div className="flex items-center gap-2 mb-2">
        <GraduationCap className="w-4 h-4 text-emerald-400" />
        <span className="text-xs font-semibold text-emerald-300">{title}</span>
      </div>
      {question && <p className="text-xs text-slate-300 mb-2">{question}</p>}
      {options && (
        <div className="space-y-1">
          {options.map((opt) => (
            <button
              key={opt.key}
              className="w-full text-left text-xs px-3 py-1.5 rounded-lg bg-slate-800 text-slate-400 hover:bg-emerald-500/20 hover:text-emerald-300 border border-slate-700 hover:border-emerald-500/30 transition-all"
            >
              <span className="font-medium mr-2">{opt.key}.</span>
              {opt.text}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
