import { Link } from 'react-router-dom'
import { Upload, LogOut, User, Image } from 'lucide-react'
import { useAuthStore } from '@/stores/authStore'
import { useUploadStore } from '@/stores/uploadStore'
import { Button } from '@/components/ui'

export function Header() {
  const { user, logout } = useAuthStore()
  const { setShowPanel, uploads } = useUploadStore()

  const pendingUploads = uploads.filter(
    (u) => u.status === 'pending' || u.status === 'uploading'
  ).length

  const handleLogout = () => {
    logout()
  }

  return (
    <header className="sticky top-0 z-40 bg-white border-b border-gray-200">
      <div className="flex items-center justify-between h-16 px-4 md:px-6">
        <Link to="/" className="flex items-center gap-2 text-xl font-semibold text-gray-900">
          <Image className="w-7 h-7 text-primary-600" />
          <span>Pixiserve</span>
        </Link>

        <div className="flex items-center gap-2">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setShowPanel(true)}
            className="relative"
          >
            <Upload className="w-4 h-4 mr-2" />
            Upload
            {pendingUploads > 0 && (
              <span className="absolute -top-1 -right-1 w-5 h-5 flex items-center justify-center text-xs bg-primary-600 text-white rounded-full">
                {pendingUploads}
              </span>
            )}
          </Button>

          <div className="flex items-center gap-3 ml-4 pl-4 border-l border-gray-200">
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <User className="w-4 h-4" />
              <span className="hidden md:inline">{user?.username}</span>
            </div>
            <Button variant="ghost" size="sm" onClick={handleLogout}>
              <LogOut className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </div>
    </header>
  )
}
