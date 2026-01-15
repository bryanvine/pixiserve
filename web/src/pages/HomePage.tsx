import { useAssets } from '@/hooks/useAssets'
import { PhotoGrid } from '@/components/gallery/PhotoGrid'
import { PhotoViewer } from '@/components/gallery/PhotoViewer'

export function HomePage() {
  const { assets, isLoading, hasMore, total, loadMore } = useAssets()

  return (
    <div>
      <div className="px-4 py-3 border-b bg-white">
        <h1 className="text-lg font-semibold">
          Photos {total > 0 && <span className="text-gray-500 font-normal">({total})</span>}
        </h1>
      </div>

      <PhotoGrid
        assets={assets}
        isLoading={isLoading}
        hasMore={hasMore}
        onLoadMore={loadMore}
      />

      <PhotoViewer />
    </div>
  )
}
