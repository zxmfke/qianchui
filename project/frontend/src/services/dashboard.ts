import api from './api';

export const dashboardService = {
  async getOverview() {
    const res = await api.get('/dashboard/overview');
    return res.data;
  },
  async getScriptRanking(limit = 10) {
    const res = await api.get('/dashboard/script-ranking', { params: { limit } });
    return res.data;
  },
  async getTeamStats() {
    const res = await api.get('/dashboard/team-stats');
    return res.data;
  },
  async getTrends(days = 7) {
    const res = await api.get('/dashboard/trends', { params: { days } });
    return res.data;
  },
};
