import { create } from 'zustand'

export interface UploadItem {
  id: string
  file: File
  progress: number
  status: 'pending' | 'uploading' | 'complete' | 'error' | 'duplicate'
  error?: string
  assetId?: string
}

interface UploadState {
  uploads: UploadItem[]
  isUploading: boolean
  showPanel: boolean
  addFiles: (files: File[]) => void
  updateUpload: (id: string, updates: Partial<UploadItem>) => void
  removeUpload: (id: string) => void
  clearCompleted: () => void
  setShowPanel: (show: boolean) => void
  setUploading: (uploading: boolean) => void
}

let uploadIdCounter = 0

export const useUploadStore = create<UploadState>((set) => ({
  uploads: [],
  isUploading: false,
  showPanel: false,

  addFiles: (files) =>
    set((state) => ({
      uploads: [
        ...state.uploads,
        ...files.map((file) => ({
          id: `upload-${++uploadIdCounter}`,
          file,
          progress: 0,
          status: 'pending' as const,
        })),
      ],
      showPanel: true,
    })),

  updateUpload: (id, updates) =>
    set((state) => ({
      uploads: state.uploads.map((u) => (u.id === id ? { ...u, ...updates } : u)),
    })),

  removeUpload: (id) =>
    set((state) => ({
      uploads: state.uploads.filter((u) => u.id !== id),
    })),

  clearCompleted: () =>
    set((state) => ({
      uploads: state.uploads.filter(
        (u) => u.status !== 'complete' && u.status !== 'duplicate'
      ),
    })),

  setShowPanel: (show) => set({ showPanel: show }),

  setUploading: (uploading) => set({ isUploading: uploading }),
}))
