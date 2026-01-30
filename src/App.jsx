import { lazy, Suspense, useState } from 'react'
import './App.css'
import ErrorBoundary from './components/ErrorBoundary'
import { AuthProvider, useAuth } from './contexts/AuthContext'

// Loading component
const Loading = () => (
  <div className="min-h-screen bg-slate-900 flex items-center justify-center">
    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
  </div>
)

// Lazy load components
const MainApp = lazy(() => import('./components/MainApp'))
const LoginPage = lazy(() => import('./components/LoginPage'))
const SignupPage = lazy(() => import('./components/SignupPage'))

function AuthenticatedApp() {
  const { isAuthenticated, loading } = useAuth();
  const [showSignup, setShowSignup] = useState(false);

  if (loading) {
    return <Loading />;
  }

  if (!isAuthenticated) {
    return (
      <Suspense fallback={<Loading />}>
        {showSignup ? (
          <SignupPage onSwitchToLogin={() => setShowSignup(false)} />
        ) : (
          <LoginPage onSwitchToSignup={() => setShowSignup(true)} />
        )}
      </Suspense>
    );
  }

  return (
    <Suspense fallback={<Loading />}>
      <MainApp />
    </Suspense>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <AuthenticatedApp />
      </AuthProvider>
    </ErrorBoundary>
  )
}

export default App
