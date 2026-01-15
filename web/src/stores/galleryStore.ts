import { create } from 'zustand'
import type { Asset } from '@/types'

interface GalleryState {
  assets: Asset[]
  selectedAsset: Asset | null
  selectedIds: Set<string>
  isLoading: boolean
  hasMore: boolean
  page: number
  total: number
  viewerOpen: boolean
  setAssets: (assets: Asset[], hasMore: boolean, total: number) => void
  appendAssets: (assets: Asset[], hasMore: boolean) => void
  setSelectedAsset: (asset: Asset | null) => void
  openViewer: (asset: Asset) => void
  closeViewer: () => void
  toggleSelect: (id: string) => void
  clearSelection: () => void
  selectAll: () => void
  updateAsset: (id: string, updates: Partial<Asset>) => void
  removeAsset: (id: string) => void
  setLoading: (loading: boolean) => void
  incrementPage: () => void
  resetPagination: () => void
}

export const useGalleryStore = create<GalleryState>((set, get) => ({
  assets: [],
  selectedAsset: null,
  selectedIds: new Set(),
  isLoading: false,
  hasMore: true,
  page: 1,
  total: 0,
  viewerOpen: false,

  setAssets: (assets, hasMore, total) => set({ assets, hasMore, total, page: 1 }),

  appendAssets: (newAssets, hasMore) =>
    set((state) => ({
      assets: [...state.assets, ...newAssets],
      hasMore,
      page: state.page + 1,
    })),

  setSelectedAsset: (asset) => set({ selectedAsset: asset }),

  openViewer: (asset) => set({ selectedAsset: asset, viewerOpen: true }),

  closeViewer: () => set({ viewerOpen: false }),

  toggleSelect: (id) =>
    set((state) => {
      const newSet = new Set(state.selectedIds)
      if (newSet.has(id)) {
        newSet.delete(id)
      } else {
        newSet.add(id)
      }
      return { selectedIds: newSet }
    }),

  clearSelection: () => set({ selectedIds: new Set() }),

  selectAll: () =>
    set((state) => ({
      selectedIds: new Set(state.assets.map((a) => a.id)),
    })),

  updateAsset: (id, updates) =>
    set((state) => ({
      assets: state.assets.map((a) => (a.id === id ? { ...a, ...updates } : a)),
      selectedAsset:
        state.selectedAsset?.id === id
          ? { ...state.selectedAsset, ...updates }
          : state.selectedAsset,
    })),

  removeAsset: (id) =>
    set((state) => ({
      assets: state.assets.filter((a) => a.id !== id),
      selectedIds: new Set([...state.selectedIds].filter((i) => i !== id)),
      selectedAsset: state.selectedAsset?.id === id ? null : state.selectedAsset,
      viewerOpen: state.selectedAsset?.id === id ? false : state.viewerOpen,
    })),

  setLoading: (loading) => set({ isLoading: loading }),

  incrementPage: () => set((state) => ({ page: state.page + 1 })),

  resetPagination: () => set({ page: 1, hasMore: true, assets: [] }),
}))
