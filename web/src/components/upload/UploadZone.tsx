import { useCallback, useState } from 'react'
import { Upload, Image } from 'lucide-react'
import { clsx } from 'clsx'
import { useUploadStore } from '@/stores/uploadStore'

const ACCEPTED_TYPES = [
  'image/jpeg',
  'image/png',
  'image/gif',
  'image/webp',
  'image/heic',
  'image/heif',
  'video/mp4',
  'video/quicktime',
  'video/webm',
]

export function UploadZone() {
  const [isDragging, setIsDragging] = useState(false)
  const addFiles = useUploadStore((s) => s.addFiles)

  const handleFiles = useCallback(
    (files: FileList | File[]) => {
      const validFiles = Array.from(files).filter(
        (file) => ACCEPTED_TYPES.includes(file.type) || file.type.startsWith('image/') || file.type.startsWith('video/')
      )
      if (validFiles.length > 0) {
        addFiles(validFiles)
      }
    },
    [addFiles]
  )

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setIsDragging(false)
  }, [])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setIsDragging(false)
      handleFiles(e.dataTransfer.files)
    },
    [handleFiles]
  )

  const handleInputChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files) {
        handleFiles(e.target.files)
      }
    },
    [handleFiles]
  )

  return (
    <div
      className={clsx(
        'relative border-2 border-dashed rounded-xl p-8 text-center transition-colors',
        isDragging
          ? 'border-primary-500 bg-primary-50'
          : 'border-gray-300 hover:border-gray-400'
      )}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      <input
        type="file"
        multiple
        accept={ACCEPTED_TYPES.join(',')}
        onChange={handleInputChange}
        className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
      />
      <div className="flex flex-col items-center gap-3">
        <div className="p-4 bg-gray-100 rounded-full">
          {isDragging ? (
            <Image className="w-8 h-8 text-primary-500" />
          ) : (
            <Upload className="w-8 h-8 text-gray-400" />
          )}
        </div>
        <div>
          <p className="text-lg font-medium text-gray-700">
            {isDragging ? 'Drop files here' : 'Drag and drop photos here'}
          </p>
          <p className="text-sm text-gray-500 mt-1">or click to select files</p>
        </div>
        <p className="text-xs text-gray-400">
          Supports JPEG, PNG, GIF, WebP, HEIC, MP4, MOV, WebM
        </p>
      </div>
    </div>
  )
}
