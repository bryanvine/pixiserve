import { Outlet } from 'react-router-dom'
import { Header } from './Header'
import { UploadPanel } from '@/components/upload/UploadPanel'

export function MainLayout() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main className="flex-1">
        <Outlet />
      </main>
      <UploadPanel />
    </div>
  )
}
