import { Activity, AlertTriangle } from 'lucide-react';

interface DimensionScore {
  dimension: string;
  score: number;
  weight: number;
  details: string;
}

interface RootCause {
  type: string;
  description: string;
  severity: string;
}

interface DiagnosisRadarInlineProps {
  data: {
    overall_score: number;
    grade: string;
    layers: {
      name: string;
      score: number;
      dimensions: DimensionScore[];
    }[];
    classification: {
      traffic_quality: string;
      dialogue_depth: string;
      service_mode: string;
    };
    root_causes: RootCause[];
  };
}

const layerColors: Record<string, string> = {
  策略层: 'bg-blue-500',
  内容层: 'bg-indigo-500',
  体验层: 'bg-violet-500',
};

const gradeColors: Record<string, string> = {
  A: 'text-emerald-400',
  B: 'text-blue-400',
  C: 'text-amber-400',
  D: 'text-red-400',
};

const severityColors: Record<string, string> = {
  high: 'text-red-400',
  medium: 'text-amber-400',
  low: 'text-slate-400',
};

export default function DiagnosisRadarInline({ data }: DiagnosisRadarInlineProps) {
  return (
    <div className="bg-slate-800/50 rounded-lg border border-slate-700 p-3 my-2">
      <div className="flex items-center gap-2 mb-2">
        <Activity className="w-4 h-4 text-indigo-400" />
        <span className="text-sm text-white font-medium">话术诊断报告（3层7维）</span>
      </div>

      <div className="flex items-center gap-4 mb-3">
        <div className="text-center">
          <p className={`text-2xl font-bold ${gradeColors[data.grade] || 'text-white'}`}>
            {data.overall_score}
          </p>
          <p className={`text-xs font-bold ${gradeColors[data.grade] || 'text-white'}`}>
            {data.grade}级
          </p>
        </div>
        <div className="flex-1 space-y-2">
          {data.layers.map((layer) => (
            <div key={layer.name}>
              <div className="flex justify-between text-xs mb-0.5">
                <span className="text-slate-400">{layer.name}</span>
                <span className="text-white">{layer.score.toFixed(1)}</span>
              </div>
              <div className="h-1.5 bg-slate-700 rounded overflow-hidden">
                <div
                  className={`h-full rounded ${layerColors[layer.name] || 'bg-indigo-500'}`}
                  style={{ width: `${layer.score}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-7 gap-1 mb-3">
        {data.layers.flatMap((layer) =>
          layer.dimensions.map((d) => (
            <div key={d.dimension} className="text-center">
              <p className="text-xs font-bold text-white">{d.score.toFixed(0)}</p>
              <p className="text-[9px] text-slate-500 truncate">{d.dimension}</p>
            </div>
          ))
        )}
      </div>

      <div className="flex gap-2 text-[10px] text-slate-500 mb-3">
        <span>流量: {data.classification.traffic_quality}</span>
        <span>深度: {data.classification.dialogue_depth}</span>
        <span>模式: {data.classification.service_mode}</span>
      </div>

      {data.root_causes.length > 0 && (
        <div className="border-t border-slate-700 pt-2">
          <p className="text-[10px] text-amber-400 flex items-center gap-1 mb-1">
            <AlertTriangle className="w-3 h-3" /> 根因分析
          </p>
          {data.root_causes.slice(0, 3).map((rc, i) => (
            <p key={i} className={`text-xs ml-4 ${severityColors[rc.severity]}`}>
              • [{rc.type}] {rc.description}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}
