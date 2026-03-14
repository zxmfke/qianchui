import api from './api';

export interface OptimizationTask {
  id: string;
  title: string;
  status: string;
  priority: string;
  classification: Record<string, number>;
  root_causes_count: number;
  strategies_count: number;
  strategies_adopted: number;
  diagnosis_report_id: string | null;
  created_at: string | null;
}

export interface OptimizationStrategy {
  id: string;
  priority: string;
  problem: string;
  root_cause_type: string;
  solution: string;
  current_script: string;
  suggested_script: string;
  expected_impact: string;
  risk_level: string;
  status: string;
  created_at?: string;
}

export interface OptimizationTaskDetail {
  id: string;
  title: string;
  status: string;
  priority: string;
  classification: Record<string, number>;
  score_result: Record<string, unknown>;
  root_causes: Array<{ layer: string; issue: string; turn?: number }>;
  diagnosis_report_id: string | null;
  strategies: OptimizationStrategy[];
  created_at: string | null;
}

export interface OptimizationStats {
  total_tasks: number;
  total_strategies: number;
  adopted_strategies: number;
  adoption_rate: number;
  avg_diagnosis_score: number;
}

export const optimizationService = {
  async createTask(data: { conversation_text: string; title?: string }) {
    const res = await api.post('/v1/optimization/tasks', data);
    return res.data;
  },
  async createTaskFromDiagnosis(diagnosisReportId: string, title?: string) {
    const res = await api.post('/v1/optimization/tasks/from-diagnosis', {
      diagnosis_report_id: diagnosisReportId,
      title,
    });
    return res.data;
  },
  async getTasks(page = 1, pageSize = 20, status?: string) {
    const res = await api.get<{ items: OptimizationTask[]; total: number }>('/v1/optimization/tasks', {
      params: { page, page_size: pageSize, status },
    });
    return res.data;
  },
  async getTask(id: string) {
    const res = await api.get<OptimizationTaskDetail>(`/v1/optimization/tasks/${id}`);
    return res.data;
  },
  async getStrategies(taskId: string) {
    const res = await api.get<{ strategies: OptimizationStrategy[] }>(`/v1/optimization/tasks/${taskId}/strategies`);
    return res.data;
  },
  async generateStrategies(taskId: string) {
    const res = await api.post<{ strategies: OptimizationStrategy[]; count: number }>(`/v1/optimization/tasks/${taskId}/generate-strategies`);
    return res.data;
  },
  async updateStrategy(strategyId: string, data: { status: string }) {
    const res = await api.put(`/v1/optimization/strategies/${strategyId}`, data);
    return res.data;
  },
  async getStats() {
    const res = await api.get<OptimizationStats>('/v1/optimization/stats');
    return res.data;
  },
};
