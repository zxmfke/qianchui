import { create } from 'zustand';
import type { Script } from '@/types';
import { scriptService } from '@/services/scripts';

interface ScriptFilters {
  category: string;
  search: string;
  tags: string[];
}

interface ScriptState {
  scripts: Script[];
  total: number;
  page: number;
  isLoading: boolean;
  filters: ScriptFilters;

  loadScripts: () => Promise<void>;
  setFilters: (filters: Partial<ScriptFilters>) => void;
  setPage: (page: number) => void;
  createScript: (data: Partial<Script>) => Promise<Script>;
  updateScript: (id: string, data: Partial<Script>) => Promise<void>;
  deleteScript: (id: string) => Promise<void>;
}

export const useScriptStore = create<ScriptState>((set, get) => ({
  scripts: [],
  total: 0,
  page: 1,
  isLoading: false,
  filters: { category: '', search: '', tags: [] },

  loadScripts: async () => {
    set({ isLoading: true });
    try {
      const { filters, page } = get();
      const res = await scriptService.getScripts({
        category: filters.category || undefined,
        search: filters.search || undefined,
        tags: filters.tags.length > 0 ? filters.tags : undefined,
        page,
        page_size: 12,
      });
      set({ scripts: res.items, total: res.total, isLoading: false });
    } catch (error) {
      console.error('Failed to load scripts:', error);
      set({ isLoading: false });
    }
  },

  setFilters: (newFilters) => {
    set((state) => ({
      filters: { ...state.filters, ...newFilters },
      page: 1,
    }));
    get().loadScripts();
  },

  setPage: (page) => {
    set({ page });
    get().loadScripts();
  },

  createScript: async (data) => {
    const script = await scriptService.createScript(data);
    await get().loadScripts();
    return script;
  },

  updateScript: async (id, data) => {
    await scriptService.updateScript(id, data);
    await get().loadScripts();
  },

  deleteScript: async (id) => {
    await scriptService.deleteScript(id);
    await get().loadScripts();
  },
}));
