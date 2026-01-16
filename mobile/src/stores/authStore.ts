/**
 * Authentication store for mobile app.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import * as SecureStore from 'expo-secure-store';
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

interface User {
  id: string;
  username: string;
  email: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  serverUrl: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;

  setServerUrl: (url: string) => void;
  login: (token: string, user: User) => Promise<void>;
  logout: () => Promise<void>;
  loadToken: () => Promise<void>;
}

const TOKEN_KEY = 'pixiserve_token';

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,
      serverUrl: null,
      isAuthenticated: false,
      isLoading: true,

      setServerUrl: (url: string) => {
        // Normalize URL (remove trailing slash)
        const normalized = url.replace(/\/$/, '');
        set({ serverUrl: normalized });
      },

      login: async (token: string, user: User) => {
        // Store token securely
        await SecureStore.setItemAsync(TOKEN_KEY, token);

        set({
          token,
          user,
          isAuthenticated: true,
          isLoading: false,
        });
      },

      logout: async () => {
        // Remove token
        await SecureStore.deleteItemAsync(TOKEN_KEY);

        set({
          token: null,
          user: null,
          isAuthenticated: false,
        });
      },

      loadToken: async () => {
        try {
          const token = await SecureStore.getItemAsync(TOKEN_KEY);

          if (token) {
            set({ token, isAuthenticated: true, isLoading: false });
          } else {
            set({ isLoading: false });
          }
        } catch (error) {
          console.error('Failed to load token:', error);
          set({ isLoading: false });
        }
      },
    }),
    {
      name: 'pixiserve-auth',
      storage: createJSONStorage(() => AsyncStorage),
      partialize: (state) => ({
        serverUrl: state.serverUrl,
        user: state.user,
      }),
    }
  )
);
