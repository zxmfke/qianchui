import api from './api';

export const memoryService = {
  async getPainPoints() {
    const res = await api.get('/memory/pain-points');
    return res.data;
  },
  async createPainPoint(data: { name: string; description?: string }) {
    const res = await api.post('/memory/pain-points', data);
    return res.data;
  },
  async getProducts() {
    const res = await api.get('/memory/products');
    return res.data;
  },
  async createProduct(data: { name: string; description?: string }) {
    const res = await api.post('/memory/products', data);
    return res.data;
  },
  async getServices() {
    const res = await api.get('/memory/services');
    return res.data;
  },
  async createService(data: { name: string; description?: string }) {
    const res = await api.post('/memory/services', data);
    return res.data;
  },
  async getKnowledgeChain() {
    const res = await api.get('/memory/knowledge-chain');
    return res.data;
  },
};
