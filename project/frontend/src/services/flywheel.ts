import api from './api';

export interface PainPointTrendView {
  id: string;
  name: string;
  mention_count_current: number;
  mention_count_previous: number;
  change_rate: number;
  trend_label: 'rising' | 'falling' | 'stable' | 'new' | 'extinct';
  evidence_keywords: string[];
  related_product_count: number;
  related_script_count: number;
}

export interface ProductStrategyView {
  id: string;
  name: string;
  dynamic_priority: string;
  recommendation_count: number;
  recommendation_hit_rate: number;
  priority_reason: string | null;
  related_pain_point_trends: string[];
}

export interface ServiceStrategyView {
  id: string;
  name: string;
  usage_count: number;
  effectiveness: number;
  has_scenario_gap: boolean;
  gap_description: string | null;
}

export interface ScriptLifecycleView {
  id: string;
  title: string;
  lifecycle_stage: 'draft' | 'review' | 'active' | 'declining' | 'archived';
  effectiveness_score: number;
  effectiveness_trend: 'rising' | 'stable' | 'declining';
  usage_contact_rate: number;
  source_type: 'manual' | 'flywheel_generated' | 'diagnosis_suggested';
}

export interface StrategyCascade {
  id: string;
  flywheel_event_id: string | null;
  trigger_signal: Record<string, unknown>;
  pain_point_actions?: Record<string, unknown>;
  product_actions?: Record<string, unknown>;
  service_actions?: Record<string, unknown>;
  script_actions?: Record<string, unknown>;
  status: string;
  reviewed_at?: string | null;
  created_at: string;
}

export interface FlywheelEvent {
  id: string;
  event_type: string;
  trigger_type: string;
  trigger_data: Record<string, unknown>;
  result_summary: Record<string, unknown>;
  status: string;
  completed_at?: string | null;
  created_at: string;
}

export interface FlywheelHealth {
  overall_score: number;
  status: 'healthy' | 'warming' | 'cold' | 'inactive';
  label: string;
  gear_scores: {
    pain_points: number;
    products: number;
    services: number;
    scripts: number;
  };
  data_flow_score: number;
  bottleneck: {
    gear: string;
    score: number;
    suggestion: string;
  } | null;
  stats: {
    pain_points: number;
    products: number;
    services: number;
    scripts: number;
    events: number;
    diagnoses: number;
  };
}

export interface FlywheelDashboard {
  pain_point_trends: PainPointTrendView[];
  product_strategies: ProductStrategyView[];
  service_strategies: ServiceStrategyView[];
  script_lifecycles: ScriptLifecycleView[];
  pending_cascades: StrategyCascade[];
  new_pain_points_pending: number;
  scenario_gaps: number;
  scripts_declining: number;
  scripts_added_this_week: number;
  flywheel_health: FlywheelHealth;
  recent_events: FlywheelEvent[];
  total_events: number;
  total_diagnosis: number;
}

export const flywheelApi = {
  getDashboard: () => api.get<FlywheelDashboard>('/v1/flywheel/dashboard'),
  getPainPointTrends: (days = 30) =>
    api.get('/v1/flywheel/pain-points/trends', { params: { days } }),
  getProductPriorities: () => api.get('/v1/flywheel/products/priorities'),
  getCoverageMatrix: () => api.get('/v1/flywheel/products/coverage-matrix'),
  getServiceEffectiveness: () => api.get('/v1/flywheel/services/effectiveness'),
  getScriptLifecycle: () => api.get('/v1/flywheel/scripts/lifecycle'),
  getCascades: (status?: string) =>
    api.get('/v1/flywheel/cascades', { params: { status } }),
  reviewCascade: (cascadeId: string, status: string) =>
    api.post(`/v1/flywheel/cascades/${cascadeId}/review`, null, {
      params: { status },
    }),
  triggerSense: (days = 30) =>
    api.post('/v1/flywheel/sense', null, { params: { time_window_days: days } }),
  getEvents: (page = 1, pageSize = 20) =>
    api.get<{ items: FlywheelEvent[]; total: number }>('/v1/flywheel/events', {
      params: { page, page_size: pageSize },
    }),
  getHealth: () => api.get<FlywheelHealth>('/v1/flywheel/health'),
};
