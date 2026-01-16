/**
 * Sync store for managing photo backup state.
 */

import AsyncStorage from '@react-native-async-storage/async-storage';
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

export type SyncStatus = 'idle' | 'scanning' | 'syncing' | 'paused' | 'error';

interface SyncProgress {
  totalAssets: number;
  syncedAssets: number;
  pendingAssets: number;
  currentAsset: string | null;
  bytesUploaded: number;
  bytesTotal: number;
}

interface SyncSettings {
  autoSync: boolean;
  syncOnWifiOnly: boolean;
  syncVideos: boolean;
  syncScreenshots: boolean;
}

interface SyncState {
  deviceId: string | null;
  status: SyncStatus;
  progress: SyncProgress;
  settings: SyncSettings;
  lastSyncAt: string | null;
  syncCursor: string | null;
  error: string | null;

  // Queue of assets to upload (hashes)
  uploadQueue: string[];

  setDeviceId: (id: string) => void;
  setStatus: (status: SyncStatus) => void;
  setProgress: (progress: Partial<SyncProgress>) => void;
  updateSettings: (settings: Partial<SyncSettings>) => void;
  addToQueue: (hashes: string[]) => void;
  removeFromQueue: (hash: string) => void;
  clearQueue: () => void;
  setSyncCursor: (cursor: string) => void;
  setError: (error: string | null) => void;
  resetSync: () => void;
}

const initialProgress: SyncProgress = {
  totalAssets: 0,
  syncedAssets: 0,
  pendingAssets: 0,
  currentAsset: null,
  bytesUploaded: 0,
  bytesTotal: 0,
};

const defaultSettings: SyncSettings = {
  autoSync: true,
  syncOnWifiOnly: true,
  syncVideos: true,
  syncScreenshots: false,
};

export const useSyncStore = create<SyncState>()(
  persist(
    (set, get) => ({
      deviceId: null,
      status: 'idle',
      progress: initialProgress,
      settings: defaultSettings,
      lastSyncAt: null,
      syncCursor: null,
      error: null,
      uploadQueue: [],

      setDeviceId: (id: string) => set({ deviceId: id }),

      setStatus: (status: SyncStatus) => set({ status }),

      setProgress: (progress: Partial<SyncProgress>) =>
        set((state) => ({
          progress: { ...state.progress, ...progress },
        })),

      updateSettings: (settings: Partial<SyncSettings>) =>
        set((state) => ({
          settings: { ...state.settings, ...settings },
        })),

      addToQueue: (hashes: string[]) =>
        set((state) => ({
          uploadQueue: [...new Set([...state.uploadQueue, ...hashes])],
          progress: {
            ...state.progress,
            pendingAssets: state.progress.pendingAssets + hashes.length,
          },
        })),

      removeFromQueue: (hash: string) =>
        set((state) => ({
          uploadQueue: state.uploadQueue.filter((h) => h !== hash),
          progress: {
            ...state.progress,
            syncedAssets: state.progress.syncedAssets + 1,
            pendingAssets: Math.max(0, state.progress.pendingAssets - 1),
          },
        })),

      clearQueue: () =>
        set({
          uploadQueue: [],
          progress: initialProgress,
        }),

      setSyncCursor: (cursor: string) =>
        set({
          syncCursor: cursor,
          lastSyncAt: new Date().toISOString(),
        }),

      setError: (error: string | null) =>
        set({
          error,
          status: error ? 'error' : 'idle',
        }),

      resetSync: () =>
        set({
          status: 'idle',
          progress: initialProgress,
          uploadQueue: [],
          error: null,
        }),
    }),
    {
      name: 'pixiserve-sync',
      storage: createJSONStorage(() => AsyncStorage),
      partialize: (state) => ({
        deviceId: state.deviceId,
        settings: state.settings,
        syncCursor: state.syncCursor,
        lastSyncAt: state.lastSyncAt,
      }),
    }
  )
);
