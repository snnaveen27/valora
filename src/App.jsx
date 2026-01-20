import { lazy, Suspense } from 'react'
import './App.css'
import ErrorBoundary from './components/ErrorBoundary'

// Loading component
const Loading = () => (
  <div className="min-h-screen bg-slate-900 flex items-center justify-center">
    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
  </div>
)

// Lazy load main app
const MainApp = lazy(() => import('./components/MainApp'))

function App() {
  // Clean MVP - no authentication, load MainApp directly
  return (
    <ErrorBoundary>
      <Suspense fallback={<Loading />}>
        <MainApp />
      </Suspense>
    </ErrorBoundary>
  )
}

export default App
