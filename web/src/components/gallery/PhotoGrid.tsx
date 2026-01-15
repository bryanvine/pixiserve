import { useRef, useCallback } from 'react'
import { useVirtualizer } from '@tanstack/react-virtual'
import { Loader2 } from 'lucide-react'
import type { Asset } from '@/types'
import { PhotoCard } from './PhotoCard'
import { useGalleryStore } from '@/stores/galleryStore'

interface PhotoGridProps {
  assets: Asset[]
  isLoading: boolean
  hasMore: boolean
  onLoadMore: () => void
}

export function PhotoGrid({ assets, isLoading, hasMore, onLoadMore }: PhotoGridProps) {
  const parentRef = useRef<HTMLDivElement>(null)
  const { openViewer, selectedIds, toggleSelect } = useGalleryStore()

  // Calculate number of columns based on container width
  const getColumnCount = () => {
    if (typeof window === 'undefined') return 4
    const width = window.innerWidth
    if (width < 640) return 2
    if (width < 768) return 3
    if (width < 1024) return 4
    if (width < 1280) return 5
    return 6
  }

  const columnCount = getColumnCount()
  const rowCount = Math.ceil(assets.length / columnCount)

  const rowVirtualizer = useVirtualizer({
    count: hasMore ? rowCount + 1 : rowCount, // +1 for loading row
    getScrollElement: () => parentRef.current,
    estimateSize: () => 200,
    overscan: 3,
  })

  const handleScroll = useCallback(() => {
    if (!parentRef.current || isLoading || !hasMore) return

    const { scrollTop, scrollHeight, clientHeight } = parentRef.current
    if (scrollHeight - scrollTop - clientHeight < 500) {
      onLoadMore()
    }
  }, [isLoading, hasMore, onLoadMore])

  if (assets.length === 0 && !isLoading) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-gray-500">
        <p className="text-lg">No photos yet</p>
        <p className="text-sm mt-1">Upload some photos to get started</p>
      </div>
    )
  }

  return (
    <div
      ref={parentRef}
      className="h-[calc(100vh-4rem)] overflow-auto px-4 py-4"
      onScroll={handleScroll}
    >
      <div
        className="relative w-full"
        style={{ height: `${rowVirtualizer.getTotalSize()}px` }}
      >
        {rowVirtualizer.getVirtualItems().map((virtualRow) => {
          const isLoadingRow = virtualRow.index === rowCount

          if (isLoadingRow) {
            return (
              <div
                key="loading"
                className="absolute top-0 left-0 w-full flex justify-center py-8"
                style={{ transform: `translateY(${virtualRow.start}px)` }}
              >
                {isLoading && (
                  <Loader2 className="w-8 h-8 animate-spin text-primary-600" />
                )}
              </div>
            )
          }

          const startIndex = virtualRow.index * columnCount
          const rowAssets = assets.slice(startIndex, startIndex + columnCount)

          return (
            <div
              key={virtualRow.index}
              className="absolute top-0 left-0 w-full grid gap-2"
              style={{
                transform: `translateY(${virtualRow.start}px)`,
                gridTemplateColumns: `repeat(${columnCount}, 1fr)`,
              }}
            >
              {rowAssets.map((asset) => (
                <PhotoCard
                  key={asset.id}
                  asset={asset}
                  onClick={() => openViewer(asset)}
                  isSelected={selectedIds.has(asset.id)}
                  onSelect={() => toggleSelect(asset.id)}
                />
              ))}
            </div>
          )
        })}
      </div>
    </div>
  )
}
