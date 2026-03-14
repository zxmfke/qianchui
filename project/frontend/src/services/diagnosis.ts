import api from './api';

export interface DiagnosisLayerResult {
  score: number;
  issues: Array<{
    turn?: number;
    issue?: string;
    original?: string;
    suggested?: string;
    current_strategy?: string;
    suggested_strategy?: string;
  }>;
}

export interface DiagnosisResult {
  overall_score: number;
  psychology_layer: DiagnosisLayerResult;
  strategy_layer: DiagnosisLayerResult;
  script_layer: DiagnosisLayerResult;
  improvement_plan: string[];
}

export interface DiagnosisAnalyzeResponse {
  report_id: string;
  result: DiagnosisResult;
}

export interface DiagnosisReportItem {
  id: string;
  conversation_text: string;
  overall_score: number;
  result: DiagnosisResult;
  created_at: string;
}

export interface DiagnosisReportListResponse {
  items: DiagnosisReportItem[];
  total: number;
}

export const diagnosisService = {
  async analyze(conversationText: string): Promise<DiagnosisAnalyzeResponse> {
    const res = await api.post<DiagnosisAnalyzeResponse>('/diagnosis/analyze', {
      conversation_text: conversationText,
    });
    return res.data;
  },

  async getReports(page = 1, pageSize = 20): Promise<DiagnosisReportListResponse> {
    const res = await api.get<DiagnosisReportListResponse>('/diagnosis/reports', {
      params: { page, page_size: pageSize },
    });
    return res.data;
  },

  async getReport(reportId: string): Promise<DiagnosisReportItem> {
    const res = await api.get<DiagnosisReportItem>(`/diagnosis/reports/${reportId}`);
    return res.data;
  },
};
