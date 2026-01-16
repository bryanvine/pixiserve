/**
 * API client for mobile app.
 */

import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';
import * as SecureStore from 'expo-secure-store';
import { useAuthStore } from '../stores/authStore';

const TOKEN_KEY = 'pixiserve_token';

// Create axios instance
export const api = axios.create({
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token and base URL
api.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    const { serverUrl } = useAuthStore.getState();

    if (serverUrl) {
      config.baseURL = `${serverUrl}/api/v1`;
    }

    const token = await SecureStore.getItemAsync(TOKEN_KEY);
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      const { logout } = useAuthStore.getState();
      await logout();
    }

    return Promise.reject(error);
  }
);

// Auth API
export const authApi = {
  login: async (username: string, password: string) => {
    const response = await api.post<{ access_token: string; token_type: string }>(
      '/auth/login',
      new URLSearchParams({ username, password }),
      { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }
    );
    return response.data;
  },

  register: async (username: string, email: string, password: string) => {
    const response = await api.post<{ id: string; username: string; email: string }>(
      '/auth/register',
      { username, email, password }
    );
    return response.data;
  },

  getMe: async () => {
    const response = await api.get<{ id: string; username: string; email: string }>(
      '/auth/me'
    );
    return response.data;
  },
};

// Assets API
export const assetsApi = {
  list: async (page = 1, pageSize = 50) => {
    const response = await api.get('/assets', {
      params: { page, page_size: pageSize },
    });
    return response.data;
  },

  get: async (id: string) => {
    const response = await api.get(`/assets/${id}`);
    return response.data;
  },

  upload: async (file: FormData) => {
    const response = await api.post('/assets', file, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return response.data;
  },

  delete: async (id: string) => {
    await api.delete(`/assets/${id}`);
  },

  toggleFavorite: async (id: string) => {
    const response = await api.post(`/assets/${id}/favorite`);
    return response.data;
  },
};

// Sync API
export const syncApi = {
  registerDevice: async (device: {
    device_name: string;
    device_type: string;
    device_id: string;
    app_version?: string;
  }) => {
    const response = await api.post('/sync/devices', device);
    return response.data;
  },

  checkHashes: async (hashes: string[]) => {
    const response = await api.post<{ existing: string[]; missing: string[] }>(
      '/sync/check',
      { hashes }
    );
    return response.data;
  },

  getStatus: async (deviceId: string) => {
    const response = await api.get(`/sync/status/${deviceId}`);
    return response.data;
  },

  updateCursor: async (deviceId: string, cursor: string) => {
    const response = await api.put(`/sync/cursor/${deviceId}`, { cursor });
    return response.data;
  },

  getChanges: async (deviceId: string, limit = 100) => {
    const response = await api.get(`/sync/changes/${deviceId}`, {
      params: { limit },
    });
    return response.data;
  },
};

// People API
export const peopleApi = {
  list: async (page = 1, pageSize = 50) => {
    const response = await api.get('/people', {
      params: { page, page_size: pageSize },
    });
    return response.data;
  },

  get: async (id: string) => {
    const response = await api.get(`/people/${id}`);
    return response.data;
  },

  update: async (id: string, data: { name?: string; is_hidden?: boolean; is_favorite?: boolean }) => {
    const response = await api.patch(`/people/${id}`, data);
    return response.data;
  },

  getAssets: async (id: string, page = 1, pageSize = 50) => {
    const response = await api.get(`/people/${id}/assets`, {
      params: { page, page_size: pageSize },
    });
    return response.data;
  },
};

// Albums API
export const albumsApi = {
  list: async (page = 1, pageSize = 50) => {
    const response = await api.get('/albums', {
      params: { page, page_size: pageSize },
    });
    return response.data;
  },

  create: async (data: { title: string; description?: string }) => {
    const response = await api.post('/albums', data);
    return response.data;
  },

  get: async (id: string) => {
    const response = await api.get(`/albums/${id}`);
    return response.data;
  },

  getAssets: async (id: string, page = 1, pageSize = 50) => {
    const response = await api.get(`/albums/${id}/assets`, {
      params: { page, page_size: pageSize },
    });
    return response.data;
  },

  addAssets: async (id: string, assetIds: string[]) => {
    const response = await api.post(`/albums/${id}/assets`, { asset_ids: assetIds });
    return response.data;
  },

  removeAsset: async (albumId: string, assetId: string) => {
    await api.delete(`/albums/${albumId}/assets/${assetId}`);
  },

  delete: async (id: string) => {
    await api.delete(`/albums/${id}`);
  },
};

// Search API
export const searchApi = {
  search: async (params: {
    query?: string;
    asset_type?: string;
    date_from?: string;
    date_to?: string;
    people_ids?: string[];
    city?: string;
    country?: string;
    is_favorite?: boolean;
  }) => {
    const response = await api.post('/search', params);
    return response.data;
  },

  suggestions: async (q: string) => {
    const response = await api.get('/search/suggestions', { params: { q } });
    return response.data;
  },

  facets: async () => {
    const response = await api.get('/search/facets');
    return response.data;
  },
};
