import api from './api';
import type { PaginatedResponse } from '@/types';

export interface SystemOverview {
  total_enterprises: number;
  active_enterprises: number;
  total_users: number;
  active_users: number;
  total_scripts: number;
  total_conversations: number;
  total_messages: number;
  total_training_records: number;
  total_simulations: number;
  total_diagnosis_reports: number;
  total_channel_materials: number;
}

export interface DailyStats {
  date: string;
  new_enterprises: number;
  new_users: number;
  new_scripts: number;
  new_conversations: number;
}

export interface SystemTrend {
  daily_stats: DailyStats[];
}

export interface AdminEnterprise {
  id: string;
  name: string;
  industry: string | null;
  is_active: boolean;
  user_count: number;
  script_count: number;
  conversation_count: number;
  created_at: string;
}

export interface EnterpriseStats {
  user_count: number;
  script_count: number;
  conversation_count: number;
  training_count: number;
  simulation_count: number;
  diagnosis_count: number;
  channel_material_count: number;
  pain_point_count: number;
  product_count: number;
  service_count: number;
}

export interface AdminUser {
  id: string;
  email: string;
  username: string;
  role: string;
  is_active: boolean;
  enterprise_id: string;
  enterprise_name: string | null;
  last_login_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface EnterpriseDetail {
  id: string;
  name: string;
  industry: string | null;
  config: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  users: AdminUser[];
  stats: EnterpriseStats;
}

export interface DataQueryResponse {
  answer: string;
  data: Record<string, unknown> | null;
}

export const adminService = {
  async getOverview(): Promise<SystemOverview> {
    const res = await api.get<SystemOverview>('/admin/overview');
    return res.data;
  },

  async getTrends(days = 30): Promise<SystemTrend> {
    const res = await api.get<SystemTrend>('/admin/trends', { params: { days } });
    return res.data;
  },

  async listEnterprises(params: {
    page?: number;
    page_size?: number;
    search?: string;
    is_active?: boolean;
  } = {}): Promise<PaginatedResponse<AdminEnterprise>> {
    const res = await api.get<PaginatedResponse<AdminEnterprise>>('/admin/enterprises', { params });
    return res.data;
  },

  async getEnterprise(id: string): Promise<EnterpriseDetail> {
    const res = await api.get<EnterpriseDetail>(`/admin/enterprises/${id}`);
    return res.data;
  },

  async createEnterprise(data: { name: string; industry?: string; is_active?: boolean }): Promise<AdminEnterprise> {
    const res = await api.post<AdminEnterprise>('/admin/enterprises', data);
    return res.data;
  },

  async updateEnterprise(id: string, data: Partial<{ name: string; industry: string; is_active: boolean; config: Record<string, unknown> }>): Promise<AdminEnterprise> {
    const res = await api.put<AdminEnterprise>(`/admin/enterprises/${id}`, data);
    return res.data;
  },

  async deleteEnterprise(id: string): Promise<void> {
    await api.delete(`/admin/enterprises/${id}`);
  },

  async listUsers(params: {
    page?: number;
    page_size?: number;
    search?: string;
    enterprise_id?: string;
    role?: string;
    is_active?: boolean;
  } = {}): Promise<PaginatedResponse<AdminUser>> {
    const res = await api.get<PaginatedResponse<AdminUser>>('/admin/users', { params });
    return res.data;
  },

  async createUser(data: {
    email: string;
    username: string;
    password: string;
    role: string;
    enterprise_id: string;
    is_active?: boolean;
  }): Promise<AdminUser> {
    const res = await api.post<AdminUser>('/admin/users', data);
    return res.data;
  },

  async updateUser(id: string, data: Partial<{
    email: string;
    username: string;
    role: string;
    is_active: boolean;
    enterprise_id: string;
    password: string;
  }>): Promise<AdminUser> {
    const res = await api.put<AdminUser>(`/admin/users/${id}`, data);
    return res.data;
  },

  async deleteUser(id: string): Promise<void> {
    await api.delete(`/admin/users/${id}`);
  },

  async queryData(question: string): Promise<DataQueryResponse> {
    const res = await api.post<DataQueryResponse>('/admin/query', { question });
    return res.data;
  },
};
