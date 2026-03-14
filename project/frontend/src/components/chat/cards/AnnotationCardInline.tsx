import { Tag, CheckCircle2, XCircle, Minus, Lightbulb } from 'lucide-react';

interface AnnotationData {
  annotations: {
    turn_index: number;
    label: string;
    strategy_type?: string;
    note?: string;
    confidence?: number;
    extractable?: boolean;
  }[];
  mining_suggestions?: {
    type: string;
    description: string;
  }[];
  summary: {
    total: number;
    good: number;
    bad: number;
    extractable: number;
    mining_count: number;
  };
}

interface AnnotationCardInlineProps {
  data: AnnotationData;
}

const strategyLabels: Record<string, string> = {
  ice_breaking: '破冰',
  need_digging: '挖需',
  solution: '方案',
  closing: '逼单',
  objection_handling: '异议处理',
  empathy: '共情',
  other: '其他',
};

const labelIcons: Record<string, React.ElementType> = {
  good: CheckCircle2,
  bad: XCircle,
  neutral: Minus,
};

const labelColors: Record<string, string> = {
  good: 'text-emerald-400',
  bad: 'text-red-400',
  neutral: 'text-slate-400',
};

export default function AnnotationCardInline({ data }: AnnotationCardInlineProps) {
  const { summary } = data;

  return (
    <div className="bg-slate-800/50 rounded-lg border border-slate-700 p-3 my-2">
      <div className="flex items-center gap-2 mb-2">
        <Tag className="w-4 h-4 text-indigo-400" />
        <span className="text-xs text-white font-medium">对话标注结果</span>
      </div>

      <div className="grid grid-cols-4 gap-2 mb-3">
        <div className="text-center">
          <p className="text-base font-bold text-white">{summary.total}</p>
          <p className="text-[10px] text-slate-500">总标注</p>
        </div>
        <div className="text-center">
          <p className="text-base font-bold text-emerald-400">{summary.good}</p>
          <p className="text-[10px] text-slate-500">优秀</p>
        </div>
        <div className="text-center">
          <p className="text-base font-bold text-red-400">{summary.bad}</p>
          <p className="text-[10px] text-slate-500">问题</p>
        </div>
        <div className="text-center">
          <p className="text-base font-bold text-indigo-400">{summary.extractable}</p>
          <p className="text-[10px] text-slate-500">可提取</p>
        </div>
      </div>

      <div className="space-y-1.5 max-h-36 overflow-y-auto">
        {data.annotations.slice(0, 5).map((ann, i) => {
          const Icon = labelIcons[ann.label] || Minus;
          const color = labelColors[ann.label] || 'text-slate-400';
          return (
            <div key={i} className="flex items-start gap-2 text-xs">
              <Icon className={`w-3.5 h-3.5 mt-0.5 ${color}`} />
              <span className="text-slate-500 w-12">轮次{ann.turn_index}</span>
              {ann.strategy_type && (
                <span className="px-1.5 py-0.5 bg-slate-700 rounded text-slate-400 text-[10px]">
                  {strategyLabels[ann.strategy_type] || ann.strategy_type}
                </span>
              )}
              <span className="text-slate-300 flex-1 truncate">{ann.note}</span>
            </div>
          );
        })}
      </div>

      {data.mining_suggestions && data.mining_suggestions.length > 0 && (
        <div className="mt-2 pt-2 border-t border-slate-700">
          <p className="text-[10px] text-amber-400 flex items-center gap-1 mb-2">
            <Lightbulb className="w-3 h-3" /> 知识挖掘发现
          </p>
          {data.mining_suggestions.slice(0, 3).map((s, i) => (
            <p key={i} className="text-xs text-slate-400 ml-4">• {s.description}</p>
          ))}
        </div>
      )}
    </div>
  );
}
