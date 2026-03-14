import api from './api';

export const channelMaterialService = {
  async getMaterials(params?: { channel?: string; status?: string; page?: number; page_size?: number }) {
    const res = await api.get('/v1/channel-materials', { params });
    return res.data;
  },
  async getMaterial(id: string) {
    const res = await api.get(`/v1/channel-materials/${id}`);
    return res.data;
  },
  async createMaterial(data: Record<string, unknown>) {
    const res = await api.post('/v1/channel-materials', data);
    return res.data;
  },
  async updateMaterial(id: string, data: Record<string, unknown>) {
    const res = await api.put(`/v1/channel-materials/${id}`, data);
    return res.data;
  },
  async deleteMaterial(id: string) {
    await api.delete(`/v1/channel-materials/${id}`);
  },
  async getStats() {
    const res = await api.get('/v1/channel-materials/stats');
    return res.data;
  },
  async extractInfo(id: string) {
    const res = await api.post(`/v1/channel-materials/${id}/extract`);
    return res.data;
  },
};
