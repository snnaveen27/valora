import { useState, useEffect, lazy, Suspense } from 'react'
import './App.css'

// Loading component
const Loading = () => (
  <div className="min-h-screen bg-slate-900 flex items-center justify-center">
    <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
  </div>
)

// Lazy load components
const MainApp = lazy(() => import('./components/MainApp'))
const AdminDashboard = lazy(() => import('./components/admin/AdminDashboard'))

// Supported languages
const SUPPORTED_LANGUAGES = [
  { code: 'en', name: 'English' },
  { code: 'hi', name: 'Hindi' },
  { code: 'kn', name: 'Kannada' },
  { code: 'ta', name: 'Tamil' },
  { code: 'te', name: 'Telugu' },
  { code: 'mr', name: 'Marathi' },
  { code: 'bn', name: 'Bengali' },
  { code: 'gu', name: 'Gujarati' },
  { code: 'ml', name: 'Malayalam' },
  { code: 'pa', name: 'Punjabi' }
]

function App() {
  const [user, setUser] = useState(null)
  const [checking, setChecking] = useState(true)
  const [isLogin, setIsLogin] = useState(true)
  const [loginEmail, setLoginEmail] = useState('')
  const [loginPassword, setLoginPassword] = useState('')
  const [loginName, setLoginName] = useState('')
  const [textLanguage, setTextLanguage] = useState('en')
  const [voiceLanguage, setVoiceLanguage] = useState('en')
  const [loginError, setLoginError] = useState('')
  const [loginLoading, setLoginLoading] = useState(false)

  useEffect(() => {
    const stored = localStorage.getItem('user')
    if (stored) {
      try {
        setUser(JSON.parse(stored))
      } catch (e) {
        localStorage.removeItem('user')
      }
    }
    setChecking(false)
  }, [])

  const handleLogin = async (e) => {
    e.preventDefault()
    setLoginLoading(true)
    setLoginError('')
    
    try {
      const endpoint = isLogin ? '/api/auth/login' : '/api/auth/register'
      const body = isLogin 
        ? { email: loginEmail, password: loginPassword }
        : { 
            email: loginEmail, 
            password: loginPassword, 
            name: loginName,
            text_language: textLanguage,
            voice_language: voiceLanguage
          }
      
      const res = await fetch(`http://localhost:8000${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      })
      const data = await res.json()
      
      if (res.ok) {
        localStorage.setItem('token', data.access_token)
        localStorage.setItem('user', JSON.stringify(data.user))
        setUser(data.user)
      } else {
        setLoginError(data.detail || (isLogin ? 'Login failed' : 'Registration failed'))
      }
    } catch (err) {
      setLoginError('Connection error - is backend running?')
    }
    setLoginLoading(false)
  }

  const handleLogout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setUser(null)
  }

  // Show loading while checking stored user
  if (checking) {
    return <Loading />
  }

  // Show login/register if no user
  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-blue-900 to-slate-900 flex items-center justify-center p-4">
        <div className="w-full max-w-md bg-white/10 backdrop-blur rounded-2xl p-8 border border-white/20">
          <h1 className="text-2xl font-bold text-white text-center mb-6">
            {isLogin ? 'Valora AI Login' : 'Create Account'}
          </h1>
          
          {loginError && (
            <div className="mb-4 p-3 bg-red-500/20 border border-red-500 rounded text-red-200 text-sm">
              {loginError}
            </div>
          )}
          
          <form onSubmit={handleLogin} className="space-y-4">
            {/* Name field - only for registration */}
            {!isLogin && (
              <input
                type="text"
                placeholder="Full Name"
                value={loginName}
                onChange={(e) => setLoginName(e.target.value)}
                className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                required
                minLength={2}
              />
            )}
            
            <input
              type="email"
              placeholder="Email"
              value={loginEmail}
              onChange={(e) => setLoginEmail(e.target.value)}
              className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
            />
            <input
              type="password"
              placeholder="Password"
              value={loginPassword}
              onChange={(e) => setLoginPassword(e.target.value)}
              className="w-full px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
              required
              minLength={6}
            />
            
            {/* Language selection - only for registration */}
            {!isLogin && (
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Text Language</label>
                  <select
                    value={textLanguage}
                    onChange={(e) => setTextLanguage(e.target.value)}
                    className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {SUPPORTED_LANGUAGES.map((lang) => (
                      <option key={lang.code} value={lang.code} className="bg-slate-800">
                        {lang.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-xs text-gray-400 mb-1">Voice Language</label>
                  <select
                    value={voiceLanguage}
                    onChange={(e) => setVoiceLanguage(e.target.value)}
                    className="w-full px-3 py-2 bg-white/10 border border-white/20 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {SUPPORTED_LANGUAGES.map((lang) => (
                      <option key={lang.code} value={lang.code} className="bg-slate-800">
                        {lang.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            )}
            
            <button
              type="submit"
              disabled={loginLoading}
              className="w-full py-3 bg-blue-500 text-white rounded-xl hover:bg-blue-600 disabled:opacity-50 font-medium"
            >
              {loginLoading ? (isLogin ? 'Signing in...' : 'Creating account...') : (isLogin ? 'Sign In' : 'Create Account')}
            </button>
          </form>
          
          {/* Toggle between login and register */}
          <div className="mt-6 text-center">
            <p className="text-gray-400 text-sm">
              {isLogin ? "Don't have an account?" : "Already have an account?"}
              <button
                type="button"
                onClick={() => {
                  setIsLogin(!isLogin)
                  setLoginError('')
                }}
                className="ml-2 text-blue-400 hover:text-blue-300 font-medium"
              >
                {isLogin ? 'Sign Up' : 'Sign In'}
              </button>
            </p>
          </div>
          
          {isLogin && (
            <div className="mt-4 text-center text-gray-500 text-xs space-y-1">
              <p><span className="text-blue-400">Admin:</span> naveen.sandcube@gmail.com / admin123</p>
              <p><span className="text-green-400">Demo:</span> demo@valora.ai / demo123</p>
            </div>
          )}
        </div>
      </div>
    )
  }

  // Admin gets admin dashboard
  if (user.role === 'admin') {
    return (
      <Suspense fallback={<Loading />}>
        <AdminDashboard user={user} onLogout={handleLogout} />
      </Suspense>
    )
  }

  // Regular users get main app
  return (
    <Suspense fallback={<Loading />}>
      <MainApp user={user} onLogout={handleLogout} />
    </Suspense>
  )
}

export default App
