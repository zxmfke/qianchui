import api from './api';
import type { Script, ScriptUsage, PaginatedResponse } from '@/types';

interface ScriptFilters {
  category?: string;
  tags?: string[];
  search?: string;
  page?: number;
  page_size?: number;
}

export const scriptService = {
  async getScripts(filters?: ScriptFilters): Promise<PaginatedResponse<Script>> {
    const res = await api.get<PaginatedResponse<Script>>('/scripts', { params: filters });
    return res.data;
  },

  async getScript(id: string): Promise<Script> {
    const res = await api.get<Script>(`/scripts/${id}`);
    return res.data;
  },

  async createScript(data: Partial<Script>): Promise<Script> {
    const res = await api.post<Script>('/scripts', data);
    return res.data;
  },

  async updateScript(id: string, data: Partial<Script>): Promise<Script> {
    const res = await api.put<Script>(`/scripts/${id}`, data);
    return res.data;
  },

  async deleteScript(id: string): Promise<void> {
    await api.delete(`/scripts/${id}`);
  },

  async recordUsage(data: Omit<ScriptUsage, 'id' | 'used_at'>): Promise<ScriptUsage> {
    const res = await api.post<ScriptUsage>('/scripts/usage', data);
    return res.data;
  },
};
