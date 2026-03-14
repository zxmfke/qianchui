import { create } from 'zustand';
import type { User } from '@/types';
import { authService } from '@/services/auth';
import axios from 'axios';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
  loadUser: () => Promise<void>;
  setToken: (token: string) => void;
}

function extractErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error) && error.response?.data) {
    const data = error.response.data;
    if (data.message) return data.message;
    if (data.detail) return typeof data.detail === 'string' ? data.detail : '请求失败';
  }
  return '网络异常，请稍后重试';
}

export const useAuthStore = create<AuthState>((set, get) => ({
  user: null,
  token: localStorage.getItem('token'),
  isAuthenticated: !!localStorage.getItem('token'),
  isLoading: false,

  login: async (username, password) => {
    set({ isLoading: true });
    try {
      const res = await authService.login(username, password);
      localStorage.setItem('token', res.access_token);
      set({
        token: res.access_token,
        isAuthenticated: true,
        isLoading: false,
      });
      try {
        const user = await authService.getMe();
        set({ user });
      } catch { /* user info will load on next navigation */ }
    } catch (error) {
      set({ isLoading: false });
      throw new Error(extractErrorMessage(error));
    }
  },

  logout: () => {
    localStorage.removeItem('token');
    set({ user: null, token: null, isAuthenticated: false });
  },

  loadUser: async () => {
    const { token } = get();
    if (!token) return;
    try {
      const user = await authService.getMe();
      set({ user, isAuthenticated: true });
    } catch {
      get().logout();
    }
  },

  setToken: (token) => {
    localStorage.setItem('token', token);
    set({ token, isAuthenticated: true });
  },
}));
