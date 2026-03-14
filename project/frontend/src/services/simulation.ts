import api from './api';

export const simulationService = {
  async createSession(data: { scenario: string; customer_type?: string; difficulty?: number }) {
    const res = await api.post('/simulation/sessions', data);
    return res.data;
  },
  async sendMessage(sessionId: string, content: string) {
    const res = await api.post(`/simulation/sessions/${sessionId}/messages`, { content });
    return res.data;
  },
  async completeSession(sessionId: string) {
    const res = await api.post(`/simulation/sessions/${sessionId}/complete`);
    return res.data;
  },
  async getSessions() {
    const res = await api.get('/simulation/sessions');
    return res.data;
  },
};
