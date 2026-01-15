import { useCallback, useEffect } from 'react'
import { getAssets, type GetAssetsParams } from '@/api/assets'
import { useGalleryStore } from '@/stores/galleryStore'

export function useAssets(params: GetAssetsParams = {}) {
  const {
    assets,
    isLoading,
    hasMore,
    page,
    total,
    setAssets,
    appendAssets,
    setLoading,
    resetPagination,
  } = useGalleryStore()

  const fetchAssets = useCallback(
    async (pageNum: number, reset = false) => {
      if (isLoading) return

      setLoading(true)
      try {
        const response = await getAssets({
          ...params,
          page: pageNum,
          page_size: 50,
        })

        if (reset || pageNum === 1) {
          setAssets(response.items, response.has_more, response.total)
        } else {
          appendAssets(response.items, response.has_more)
        }
      } catch (error) {
        console.error('Failed to fetch assets:', error)
      } finally {
        setLoading(false)
      }
    },
    [params, isLoading, setAssets, appendAssets, setLoading]
  )

  const loadMore = useCallback(() => {
    if (!isLoading && hasMore) {
      fetchAssets(page + 1)
    }
  }, [fetchAssets, isLoading, hasMore, page])

  const refresh = useCallback(() => {
    resetPagination()
    fetchAssets(1, true)
  }, [fetchAssets, resetPagination])

  useEffect(() => {
    fetchAssets(1, true)
  }, [])

  return {
    assets,
    isLoading,
    hasMore,
    total,
    loadMore,
    refresh,
  }
}
