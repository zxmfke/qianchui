import api from './api';
import type { User } from '@/types';

interface LoginResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

interface RegisterRequest {
  email: string;
  username: string;
  password: string;
  enterprise_name: string;
  industry?: string;
}

let _cachedPublicKey: CryptoKey | null = null;

async function fetchPublicKey(): Promise<CryptoKey> {
  if (_cachedPublicKey) return _cachedPublicKey;

  const res = await api.get<{ public_key: string }>('/auth/public-key');
  const pem = res.data.public_key
    .replace('-----BEGIN PUBLIC KEY-----', '')
    .replace('-----END PUBLIC KEY-----', '')
    .replace(/\s/g, '');

  const binaryStr = atob(pem);
  const bytes = new Uint8Array(binaryStr.length);
  for (let i = 0; i < binaryStr.length; i++) {
    bytes[i] = binaryStr.charCodeAt(i);
  }

  _cachedPublicKey = await crypto.subtle.importKey(
    'spki',
    bytes.buffer,
    { name: 'RSA-OAEP', hash: 'SHA-256' },
    false,
    ['encrypt'],
  );
  return _cachedPublicKey;
}

async function encryptPassword(password: string): Promise<string> {
  try {
    const key = await fetchPublicKey();
    const encoded = new TextEncoder().encode(password);
    const encrypted = await crypto.subtle.encrypt({ name: 'RSA-OAEP' }, key, encoded);
    return btoa(String.fromCharCode(...new Uint8Array(encrypted)));
  } catch {
    return password;
  }
}

export const authService = {
  async login(username: string, password: string): Promise<LoginResponse> {
    const encPwd = await encryptPassword(password);
    const res = await api.post<LoginResponse>('/auth/login', {
      username,
      password: encPwd,
    });
    return res.data;
  },

  async register(data: RegisterRequest): Promise<LoginResponse> {
    const encPwd = await encryptPassword(data.password);
    const res = await api.post<LoginResponse>('/auth/register', {
      ...data,
      password: encPwd,
    });
    return res.data;
  },

  async getMe(): Promise<User> {
    const res = await api.get<User>('/auth/me');
    return res.data;
  },

  async refreshToken(refreshToken: string): Promise<LoginResponse> {
    const res = await api.post<LoginResponse>('/auth/refresh', {
      refresh_token: refreshToken,
    });
    return res.data;
  },
};
