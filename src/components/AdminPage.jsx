import { lazy, Suspense } from 'react'
import { useAuth } from '../contexts/AuthContext'

const Loading = () => (
  <div className="min-h-screen bg-slate-900 flex items-center justify-center">
    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-500"></div>
  </div>
)

const AdminPanel = lazy(() => import('./AdminPanel'))

export default function AdminPage() {
  const { user, token, loading } = useAuth()

  if (loading) return <Loading />

  if (!token || !user) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="bg-slate-800 rounded-xl p-8 max-w-sm w-full text-center border border-slate-700">
          <div className="w-14 h-14 bg-gradient-to-br from-purple-500 to-pink-600 rounded-xl flex items-center justify-center mx-auto mb-4">
            <svg className="w-7 h-7 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
            </svg>
          </div>
          <h2 className="text-white text-lg font-bold mb-2">Authentication Required</h2>
          <p className="text-slate-400 text-sm mb-6">Please sign in to access the admin panel.</p>
          <button
            onClick={() => { window.location.hash = ''; window.location.reload() }}
            className="w-full px-4 py-2.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm font-medium transition"
          >
            Go to Login
          </button>
        </div>
      </div>
    )
  }

  if (user.role !== 'admin' && user.tier !== 'admin') {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center">
        <div className="bg-slate-800 rounded-xl p-8 max-w-sm w-full text-center border border-slate-700">
          <div className="w-14 h-14 bg-red-500/20 rounded-xl flex items-center justify-center mx-auto mb-4">
            <svg className="w-7 h-7 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636" />
            </svg>
          </div>
          <h2 className="text-white text-lg font-bold mb-2">Access Denied</h2>
          <p className="text-slate-400 text-sm mb-6">You don't have permission to access the admin panel.</p>
          <button
            onClick={() => { window.location.hash = ''; window.location.reload() }}
            className="w-full px-4 py-2.5 bg-slate-700 hover:bg-slate-600 text-white rounded-lg text-sm font-medium transition"
          >
            Back to App
          </button>
        </div>
      </div>
    )
  }

  return (
    <Suspense fallback={<Loading />}>
      <AdminPanel isOpen={true} onClose={() => { window.location.hash = ''; window.location.reload() }} />
    </Suspense>
  )
}
