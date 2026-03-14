import { BookOpen, Copy } from 'lucide-react';

interface Props {
  title: string;
  data: Record<string, unknown>;
}

export default function ScriptCardInline({ title, data }: Props) {
  const psychology = data.psychology as { customer_type?: string } | undefined;
  const strategy = data.strategy as { approach?: string } | undefined;
  const content = data.content as { opening?: string } | undefined;

  return (
    <div className="bg-slate-900/60 border border-indigo-500/30 rounded-lg p-3 mt-2">
      <div className="flex items-center gap-2 mb-2">
        <BookOpen className="w-4 h-4 text-indigo-400" />
        <span className="text-xs font-semibold text-indigo-300">{title}</span>
      </div>
      <div className="flex flex-wrap gap-1 mb-2">
        {psychology?.customer_type && (
          <span className="badge bg-purple-500/20 text-purple-300 text-[10px]">
            🧠 {psychology.customer_type}
          </span>
        )}
        {strategy?.approach && (
          <span className="badge bg-blue-500/20 text-blue-300 text-[10px]">
            🎯 {strategy.approach}
          </span>
        )}
      </div>
      {content?.opening && (
        <p className="text-xs text-slate-400 line-clamp-2">{content.opening}</p>
      )}
      <button className="mt-2 flex items-center gap-1 text-[10px] text-indigo-400 hover:text-indigo-300">
        <Copy className="w-3 h-3" /> 复制话术
      </button>
    </div>
  );
}
