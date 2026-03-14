import { TrendingUp, CheckCircle2, XCircle, AlertTriangle } from 'lucide-react';

interface Strategy {
  priority: string;
  problem: string;
  root_cause_type: string;
  current_script: string;
  suggested_script: string;
  expected_impact: string;
  risk_level: string;
}

interface OptimizeCardInlineProps {
  data: {
    priority: string;
    problem: string;
    root_cause_type: string;
    current_script: string;
    suggested_script: string;
    expected_impact: string;
    risk_level: string;
  };
}

const rootCauseLabels: Record<string, string> = {
  config: '配置问题',
  script: '话术问题',
  traffic: '流量问题',
  product: '产品问题',
};

export default function OptimizeCardInline({ data }: OptimizeCardInlineProps) {
  return (
    <div className="bg-slate-800/50 rounded-lg border border-slate-700 p-3 my-2">
      <div className="flex items-center gap-2 mb-2">
        <TrendingUp className="w-4 h-4 text-indigo-400" />
        <span className={`px-2 py-0.5 rounded text-xs font-bold ${
          data.priority === 'P0' ? 'bg-red-500/20 text-red-400' : 'bg-amber-500/20 text-amber-400'
        }`}>
          {data.priority}
        </span>
        <span className="text-xs text-white font-medium">{data.problem}</span>
      </div>
      <div className="grid grid-cols-2 gap-2 mb-2">
        <div>
          <p className="text-xs text-red-400 mb-1 flex items-center gap-1">
            <XCircle className="w-3 h-3" /> 当前
          </p>
          <p className="text-xs text-slate-400 bg-slate-900/50 p-2 rounded">{data.current_script}</p>
        </div>
        <div>
          <p className="text-xs text-emerald-400 mb-1 flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" /> 建议
          </p>
          <p className="text-xs text-slate-300 bg-slate-900/50 p-2 rounded">{data.suggested_script}</p>
        </div>
      </div>
      <div className="flex items-center gap-2 text-[10px] text-slate-500">
        <span>{rootCauseLabels[data.root_cause_type] || data.root_cause_type}</span>
        <span>{data.expected_impact}</span>
        <span className="flex items-center gap-1">
          <AlertTriangle className="w-3 h-3" />
          {data.risk_level === 'low' ? '低风险' : data.risk_level === 'medium' ? '中风险' : '高风险'}
        </span>
      </div>
    </div>
  );
}
