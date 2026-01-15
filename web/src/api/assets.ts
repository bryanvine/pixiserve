import { apiClient } from './client'
import type { Asset, AssetListResponse, UploadResponse } from '@/types'

export interface GetAssetsParams {
  page?: number
  page_size?: number
  asset_type?: 'image' | 'video'
  is_favorite?: boolean
}

export async function getAssets(params: GetAssetsParams = {}): Promise<AssetListResponse> {
  const response = await apiClient.get<AssetListResponse>('/assets', { params })
  return response.data
}

export async function getAsset(id: string): Promise<Asset> {
  const response = await apiClient.get<Asset>(`/assets/${id}`)
  return response.data
}

export async function uploadAsset(
  file: File,
  onProgress?: (progress: number) => void
): Promise<UploadResponse> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await apiClient.post<UploadResponse>('/assets', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: (progressEvent) => {
      if (progressEvent.total && onProgress) {
        const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
        onProgress(progress)
      }
    },
  })

  return response.data
}

export async function deleteAsset(id: string): Promise<void> {
  await apiClient.delete(`/assets/${id}`)
}

export async function toggleFavorite(id: string): Promise<Asset> {
  const response = await apiClient.post<Asset>(`/assets/${id}/favorite`)
  return response.data
}

export function getAssetFileUrl(id: string): string {
  const baseUrl = import.meta.env.VITE_API_URL || '/api/v1'
  return `${baseUrl}/assets/${id}/file`
}

export function getAssetThumbUrl(id: string): string {
  // For now, use the full file - thumbnails will be added in Phase 3
  return getAssetFileUrl(id)
}
