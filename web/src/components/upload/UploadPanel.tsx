import { useEffect, useCallback, useRef } from 'react'
import { X, CheckCircle, AlertCircle, Copy, Loader2 } from 'lucide-react'
import { clsx } from 'clsx'
import { useUploadStore, type UploadItem } from '@/stores/uploadStore'
import { useGalleryStore } from '@/stores/galleryStore'
import { uploadAsset } from '@/api/assets'
import { Button } from '@/components/ui'
import { UploadZone } from './UploadZone'

function UploadItemRow({ item }: { item: UploadItem }) {
  return (
    <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
      <div className="flex-shrink-0">
        {item.status === 'complete' && (
          <CheckCircle className="w-5 h-5 text-green-500" />
        )}
        {item.status === 'error' && (
          <AlertCircle className="w-5 h-5 text-red-500" />
        )}
        {item.status === 'duplicate' && (
          <Copy className="w-5 h-5 text-yellow-500" />
        )}
        {(item.status === 'pending' || item.status === 'uploading') && (
          <Loader2 className="w-5 h-5 text-primary-500 animate-spin" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{item.file.name}</p>
        <p className="text-xs text-gray-500">
          {item.status === 'uploading' && `${item.progress}%`}
          {item.status === 'complete' && 'Uploaded'}
          {item.status === 'duplicate' && 'Already exists'}
          {item.status === 'error' && (item.error || 'Failed')}
          {item.status === 'pending' && 'Waiting...'}
        </p>
      </div>
      {item.status === 'uploading' && (
        <div className="w-20 h-2 bg-gray-200 rounded-full overflow-hidden">
          <div
            className="h-full bg-primary-500 transition-all duration-300"
            style={{ width: `${item.progress}%` }}
          />
        </div>
      )}
    </div>
  )
}

export function UploadPanel() {
  const {
    uploads,
    showPanel,
    isUploading,
    setShowPanel,
    updateUpload,
    clearCompleted,
    setUploading,
  } = useUploadStore()
  const refreshGallery = useGalleryStore((s) => s.resetPagination)
  const processingRef = useRef(false)

  const processUploads = useCallback(async () => {
    if (processingRef.current) return
    processingRef.current = true
    setUploading(true)

    const pending = uploads.filter((u) => u.status === 'pending')

    for (const item of pending) {
      updateUpload(item.id, { status: 'uploading', progress: 0 })

      try {
        const result = await uploadAsset(item.file, (progress) => {
          updateUpload(item.id, { progress })
        })

        updateUpload(item.id, {
          status: result.is_duplicate ? 'duplicate' : 'complete',
          progress: 100,
          assetId: result.asset.id,
        })
      } catch (error) {
        updateUpload(item.id, {
          status: 'error',
          error: error instanceof Error ? error.message : 'Upload failed',
        })
      }
    }

    processingRef.current = false
    setUploading(false)

    // Refresh gallery if any uploads succeeded
    const hasSuccessful = uploads.some(
      (u) => u.status === 'complete' || u.status === 'duplicate'
    )
    if (hasSuccessful) {
      refreshGallery()
    }
  }, [uploads, updateUpload, setUploading, refreshGallery])

  useEffect(() => {
    const hasPending = uploads.some((u) => u.status === 'pending')
    if (hasPending && !isUploading) {
      processUploads()
    }
  }, [uploads, isUploading, processUploads])

  const completedCount = uploads.filter(
    (u) => u.status === 'complete' || u.status === 'duplicate'
  ).length
  const errorCount = uploads.filter((u) => u.status === 'error').length
  const pendingCount = uploads.filter(
    (u) => u.status === 'pending' || u.status === 'uploading'
  ).length

  if (!showPanel) return null

  return (
    <div className="fixed bottom-4 right-4 w-96 max-h-[80vh] bg-white rounded-xl shadow-2xl border border-gray-200 flex flex-col z-50">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b">
        <div>
          <h3 className="font-semibold">Upload Photos</h3>
          {uploads.length > 0 && (
            <p className="text-xs text-gray-500">
              {completedCount} complete
              {errorCount > 0 && `, ${errorCount} failed`}
              {pendingCount > 0 && `, ${pendingCount} pending`}
            </p>
          )}
        </div>
        <button
          onClick={() => setShowPanel(false)}
          className="p-1 hover:bg-gray-100 rounded"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Upload zone */}
      <div className="p-4">
        <UploadZone />
      </div>

      {/* Upload list */}
      {uploads.length > 0 && (
        <>
          <div className="flex-1 overflow-auto px-4 pb-4 space-y-2 max-h-64">
            {uploads.map((item) => (
              <UploadItemRow key={item.id} item={item} />
            ))}
          </div>

          {/* Footer */}
          {completedCount > 0 && (
            <div className="p-4 border-t">
              <Button
                variant="secondary"
                size="sm"
                onClick={clearCompleted}
                className="w-full"
              >
                Clear completed
              </Button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
