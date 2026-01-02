import { useState, useEffect, lazy, Suspense } from 'react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

// Lazy load MainApp for user mode
const MainApp = lazy(() => import('../MainApp'))

export default function AdminDashboard({ user, onLogout }) {
  const [activeTab, setActiveTab] = useState('overview')
  const [users, setUsers] = useState([])
  const [apiKeys, setApiKeys] = useState([])
  const [credits, setCredits] = useState({})
  const [systemStats, setSystemStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [isUserMode, setIsUserMode] = useState(false)
  const [showApiKeyModal, setShowApiKeyModal] = useState(false)
  const [newApiKeyName, setNewApiKeyName] = useState('')

  const getToken = () => localStorage.getItem('token')

  useEffect(() => {
    fetchData()
  }, [])

  const fetchData = async () => {
    setLoading(true)
    try {
      const usersRes = await fetch(`${API_URL}/api/auth/admin/users`, {
        headers: { 'Authorization': `Bearer ${getToken()}` }
      })
      if (usersRes.ok) setUsers(await usersRes.json())

      const healthRes = await fetch(`${API_URL}/health`)
      if (healthRes.ok) setSystemStats(await healthRes.json())

      // Mock API keys and credits data
      setApiKeys([
        { id: 'key_1', name: 'Production API', key: 'vla_prod_xxx...xxx', created: '2024-12-01', requests: 15420, status: 'active' },
        { id: 'key_2', name: 'Development API', key: 'vla_dev_xxx...xxx', created: '2024-12-10', requests: 3250, status: 'active' },
        { id: 'key_3', name: 'Partner - Housing.com', key: 'vla_b2b_xxx...xxx', created: '2024-12-15', requests: 8900, status: 'active' }
      ])
      setCredits({
        total: 100000,
        used: 27570,
        remaining: 72430,
        planName: 'Enterprise',
        pricePerCredit: 0.001,
        billingCycle: 'monthly'
      })
    } catch (err) {
      console.error('Error fetching data:', err)
    } finally {
      setLoading(false)
    }
  }

  const generateApiKey = () => {
    const newKey = {
      id: `key_${Date.now()}`,
      name: newApiKeyName || 'New API Key',
      key: `vla_${Math.random().toString(36).substr(2, 9)}_${Math.random().toString(36).substr(2, 9)}`,
      created: new Date().toISOString().split('T')[0],
      requests: 0,
      status: 'active'
    }
    setApiKeys([...apiKeys, newKey])
    setShowApiKeyModal(false)
    setNewApiKeyName('')
  }

  // Tabs organized by architecture layers
  const tabs = [
    { id: 'overview', name: 'Overview', icon: '📊' },
    // Architecture Layers
    { id: 'data', name: 'Data Layer', icon: '🗄️' },
    { id: 'knowledge', name: 'Knowledge Layer', icon: '🧠' },
    { id: 'intelligence', name: 'Intelligence Layer', icon: '🤖' },
    { id: 'llm', name: 'LLM & Learning', icon: '🧬' },
    { id: 'orchestration', name: 'Orchestration', icon: '🎯' },
    { id: 'digitaltwin', name: 'Digital Twin', icon: '🏗️' },
    // Business
    { id: 'cities', name: 'Cities', icon: '🏙️' },
    { id: 'users', name: 'Users', icon: '👥' },
    { id: 'api', name: 'API & B2B', icon: '🔑' },
    { id: 'analytics', name: 'Analytics', icon: '📈' },
    { id: 'platformtests', name: 'Platform Tests', icon: '🧪' },
    { id: 'cloudservices', name: 'Cloud Services', icon: '☁️' },
    { id: 'errors', name: 'Error Logs', icon: '🚨' },
    { id: 'settings', name: 'Settings', icon: '⚙️' }
  ]

  // If admin is in user mode, show the actual MainApp (3-panel UI)
  if (isUserMode) {
    return (
      <div className="relative">
        {/* Floating Admin Toggle Button */}
        <div className="fixed top-4 right-4 z-[9999] flex items-center gap-2 bg-purple-600 text-white px-4 py-2 rounded-full shadow-lg backdrop-blur">
          <span className="text-sm font-medium">👁️ Admin Preview Mode</span>
          <button
            onClick={() => setIsUserMode(false)}
            className="ml-2 px-3 py-1.5 bg-white text-purple-600 rounded-full text-sm font-medium hover:bg-gray-100 transition"
          >
            Back to Admin
          </button>
        </div>
        
        {/* Render actual MainApp with 3-panel UI */}
        <Suspense fallback={
          <div className="min-h-screen bg-slate-900 flex items-center justify-center">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
          </div>
        }>
          <MainApp user={user} onLogout={onLogout} />
        </Suspense>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Top Navigation */}
      <nav className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-600 rounded-xl flex items-center justify-center text-xl">
              🏢
            </div>
            <div>
              <h1 className="text-xl font-bold">Valora Admin</h1>
              <p className="text-xs text-gray-400">City Intelligence Platform</p>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <button
              onClick={() => setIsUserMode(true)}
              className="px-4 py-2 bg-purple-500/20 text-purple-400 rounded-lg hover:bg-purple-500/30 transition flex items-center gap-2"
            >
              <span>👁️</span> View as User
            </button>
            <span className="text-sm text-gray-400">
              <span className="text-white font-medium">{user?.name || user?.email}</span>
            </span>
            <button
              onClick={onLogout}
              className="px-4 py-2 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 transition"
            >
              Logout
            </button>
          </div>
        </div>
      </nav>

      <div className="flex">
        {/* Sidebar */}
        <aside className="w-64 bg-gray-800 min-h-[calc(100vh-73px)] p-4">
          <nav className="space-y-1">
            {tabs.map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition ${
                  activeTab === tab.id
                    ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30'
                    : 'text-gray-400 hover:bg-gray-700 hover:text-white'
                }`}
              >
                <span className="text-lg">{tab.icon}</span>
                <span className="font-medium text-sm">{tab.name}</span>
              </button>
            ))}
          </nav>

          {/* Credits Summary in Sidebar */}
          <div className="mt-6 p-4 bg-gradient-to-br from-blue-500/20 to-purple-500/20 rounded-xl border border-blue-500/30">
            <p className="text-xs text-gray-400 mb-1">API Credits</p>
            <p className="text-2xl font-bold text-white">{credits.remaining?.toLocaleString()}</p>
            <div className="mt-2 h-2 bg-gray-700 rounded-full overflow-hidden">
              <div 
                className="h-full bg-gradient-to-r from-blue-500 to-purple-500"
                style={{ width: `${((credits.remaining || 0) / (credits.total || 1)) * 100}%` }}
              />
            </div>
            <p className="text-xs text-gray-400 mt-1">of {credits.total?.toLocaleString()} total</p>
          </div>
        </aside>

        {/* Main Content */}
        <main className="flex-1 p-6 overflow-auto max-h-[calc(100vh-73px)]">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
            </div>
          ) : (
            <>
              {activeTab === 'overview' && <OverviewTab stats={systemStats} users={users} credits={credits} apiKeys={apiKeys} />}
              {activeTab === 'data' && <DataLayerTab />}
              {activeTab === 'knowledge' && <KnowledgeLayerTab />}
              {activeTab === 'intelligence' && <IntelligenceLayerTab />}
              {activeTab === 'llm' && <LLMTab />}
              {activeTab === 'orchestration' && <OrchestrationTab />}
              {activeTab === 'digitaltwin' && <DigitalTwinTab />}
              {activeTab === 'cities' && <CitiesTab />}
              {activeTab === 'users' && <UsersTab users={users} currentUserEmail={user?.email} />}
              {activeTab === 'api' && <ApiTab apiKeys={apiKeys} onGenerateKey={() => setShowApiKeyModal(true)} />}
              {activeTab === 'analytics' && <AnalyticsTab />}
              {activeTab === 'platformtests' && <PlatformTestsTab />}
              {activeTab === 'cloudservices' && <CloudServicesTab />}
              {activeTab === 'errors' && <ErrorLogsTab />}
              {activeTab === 'settings' && <SettingsTab />}
            </>
          )}
        </main>
      </div>

      {/* API Key Generation Modal */}
      {showApiKeyModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-2xl p-6 w-full max-w-md border border-gray-700">
            <h3 className="text-xl font-bold mb-4">Generate New API Key</h3>
            <input
              type="text"
              placeholder="API Key Name (e.g., Production, Development)"
              value={newApiKeyName}
              onChange={(e) => setNewApiKeyName(e.target.value)}
              className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl text-white mb-4"
            />
            <div className="flex gap-3">
              <button
                onClick={() => setShowApiKeyModal(false)}
                className="flex-1 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600"
              >
                Cancel
              </button>
              <button
                onClick={generateApiKey}
                className="flex-1 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
              >
                Generate Key
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// Overview Tab
function OverviewTab({ stats, users, credits, apiKeys }) {
  const cards = [
    { title: 'Total Users', value: users?.length || 0, icon: '👥', color: 'blue', change: '+12%' },
    { title: 'API Requests Today', value: '15,420', icon: '📡', color: 'green', change: '+8%' },
    { title: 'Credits Used', value: credits?.used?.toLocaleString() || 0, icon: '💳', color: 'purple', change: '+15%' },
    { title: 'Active API Keys', value: apiKeys?.filter(k => k.status === 'active').length || 0, icon: '🔑', color: 'yellow', change: '0%' },
    { title: 'Revenue (MTD)', value: '₹2.4L', icon: '💰', color: 'emerald', change: '+22%' },
    { title: 'B2B Partners', value: '3', icon: '🤝', color: 'pink', change: '+1' }
  ]

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold">Dashboard Overview</h2>
        <p className="text-gray-400 text-sm">Last updated: {new Date().toLocaleTimeString()}</p>
      </div>
      
      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 mb-6">
        {cards.map((card, i) => (
          <div key={i} className="bg-gray-800 rounded-2xl p-5 border border-gray-700 hover:border-gray-600 transition">
            <div className="flex items-center justify-between mb-3">
              <span className="text-3xl">{card.icon}</span>
              <span className={`px-2 py-1 rounded-full text-xs ${
                card.change.startsWith('+') ? 'bg-green-500/20 text-green-400' : 'bg-gray-600 text-gray-400'
              }`}>
                {card.change}
              </span>
            </div>
            <h3 className="text-gray-400 text-sm">{card.title}</h3>
            <p className="text-2xl font-bold mt-1">{card.value}</p>
          </div>
        ))}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div className="bg-gray-800 rounded-2xl p-6 border border-gray-700">
          <h3 className="text-lg font-semibold mb-4">API Usage (Last 7 Days)</h3>
          <div className="h-48 flex items-end justify-between gap-2">
            {[65, 45, 80, 55, 90, 70, 85].map((h, i) => (
              <div key={i} className="flex-1 flex flex-col items-center">
                <div 
                  className="w-full bg-gradient-to-t from-blue-500 to-purple-500 rounded-t"
                  style={{ height: `${h}%` }}
                />
                <span className="text-xs text-gray-400 mt-2">{['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][i]}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-gray-800 rounded-2xl p-6 border border-gray-700">
          <h3 className="text-lg font-semibold mb-4">Revenue Breakdown</h3>
          <div className="space-y-4">
            {[
              { name: 'API Credits', value: '₹1.8L', percent: 75, color: 'blue' },
              { name: 'B2B Subscriptions', value: '₹45K', percent: 19, color: 'purple' },
              { name: 'Premium Features', value: '₹15K', percent: 6, color: 'green' }
            ].map((item, i) => (
              <div key={i}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-gray-400">{item.name}</span>
                  <span className="font-medium">{item.value}</span>
                </div>
                <div className="h-2 bg-gray-700 rounded-full overflow-hidden">
                  <div 
                    className={`h-full bg-${item.color}-500`}
                    style={{ width: `${item.percent}%`, background: item.color === 'blue' ? '#3b82f6' : item.color === 'purple' ? '#8b5cf6' : '#22c55e' }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* System Status */}
      <div className="bg-gray-800 rounded-2xl p-6 border border-gray-700">
        <h3 className="text-lg font-semibold mb-4">System Status</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { name: 'Backend API', status: 'online' },
            { name: 'ML Models', status: 'online' },
            { name: 'Database', status: 'online' },
            { name: 'Mappls API', status: 'online' }
          ].map((service, i) => (
            <div key={i} className="flex items-center gap-3 p-3 bg-gray-700/50 rounded-xl">
              <span className={`w-3 h-3 rounded-full ${service.status === 'online' ? 'bg-green-500' : 'bg-red-500'}`} />
              <span className="text-sm">{service.name}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// Users Tab
function UsersTab({ users, currentUserEmail }) {
  const [filter, setFilter] = useState('all')
  
  const filteredUsers = users.filter(u => {
    if (filter === 'all') return true
    return u.role === filter
  })

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold">User Management</h2>
        <div className="flex gap-2">
          {['all', 'admin', 'user', 'analyst'].map(f => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-4 py-2 rounded-lg text-sm ${
                filter === f ? 'bg-blue-500 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
              }`}
            >
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-gray-800 rounded-2xl border border-gray-700 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-700/50">
            <tr>
              <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">User</th>
              <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Role</th>
              <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Credits</th>
              <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">API Requests</th>
              <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Status</th>
              <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredUsers.map((u, i) => (
              <tr key={i} className="border-t border-gray-700 hover:bg-gray-700/30">
                <td className="px-6 py-4">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-500 rounded-full flex items-center justify-center text-white font-medium">
                      {u.name?.charAt(0) || u.email?.charAt(0)}
                    </div>
                    <div>
                      <p className="font-medium">{u.name || 'User'}</p>
                      <p className="text-sm text-gray-400">{u.email}</p>
                    </div>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <span className={`px-3 py-1 rounded-full text-xs ${
                    u.role === 'admin' ? 'bg-purple-500/20 text-purple-400' :
                    u.role === 'analyst' ? 'bg-blue-500/20 text-blue-400' :
                    'bg-gray-600 text-gray-300'
                  }`}>
                    {u.role}
                  </span>
                </td>
                <td className="px-6 py-4 text-gray-300">{Math.floor(Math.random() * 10000).toLocaleString()}</td>
                <td className="px-6 py-4 text-gray-300">{Math.floor(Math.random() * 5000).toLocaleString()}</td>
                <td className="px-6 py-4">
                  <span className={`px-3 py-1 rounded-full text-xs ${
                    u.is_active ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                  }`}>
                    {u.is_active ? 'Active' : 'Inactive'}
                  </span>
                </td>
                <td className="px-6 py-4">
                  <button className="px-3 py-1 bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600 text-sm">
                    Manage
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// API Tab (includes B2B Partners)
function ApiTab({ apiKeys, onGenerateKey }) {
  const [copiedKey, setCopiedKey] = useState(null)

  const copyKey = (key) => {
    navigator.clipboard.writeText(key)
    setCopiedKey(key)
    setTimeout(() => setCopiedKey(null), 2000)
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold">API Management</h2>
        <button
          onClick={onGenerateKey}
          className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 flex items-center gap-2"
        >
          <span>+</span> Generate New Key
        </button>
      </div>

      {/* API Documentation Link */}
      <div className="bg-gradient-to-r from-blue-500/20 to-purple-500/20 rounded-2xl p-6 border border-blue-500/30 mb-6">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold">API Documentation</h3>
            <p className="text-gray-400 text-sm mt-1">Learn how to integrate Valora AI into your applications</p>
          </div>
          <button className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">
            View Docs →
          </button>
        </div>
      </div>

      {/* API Keys List */}
      <div className="bg-gray-800 rounded-2xl border border-gray-700 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-700/50">
            <tr>
              <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Name</th>
              <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">API Key</th>
              <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Created</th>
              <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Requests</th>
              <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Status</th>
              <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Actions</th>
            </tr>
          </thead>
          <tbody>
            {apiKeys.map((key, i) => (
              <tr key={i} className="border-t border-gray-700 hover:bg-gray-700/30">
                <td className="px-6 py-4 font-medium">{key.name}</td>
                <td className="px-6 py-4">
                  <code className="bg-gray-700 px-3 py-1 rounded text-sm text-gray-300">{key.key}</code>
                </td>
                <td className="px-6 py-4 text-gray-400">{key.created}</td>
                <td className="px-6 py-4">{key.requests.toLocaleString()}</td>
                <td className="px-6 py-4">
                  <span className={`px-3 py-1 rounded-full text-xs ${
                    key.status === 'active' ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                  }`}>
                    {key.status}
                  </span>
                </td>
                <td className="px-6 py-4 flex gap-2">
                  <button
                    onClick={() => copyKey(key.key)}
                    className="px-3 py-1 bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600 text-sm"
                  >
                    {copiedKey === key.key ? '✓ Copied' : 'Copy'}
                  </button>
                  <button className="px-3 py-1 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 text-sm">
                    Revoke
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* API Endpoints Preview */}
      <h3 className="text-lg font-semibold mt-8 mb-4">Available Endpoints</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {[
          { method: 'POST', path: '/api/predict/price', desc: 'Get property price prediction', credits: 10 },
          { method: 'POST', path: '/api/chat', desc: 'AI chat assistant', credits: 5 },
          { method: 'GET', path: '/api/market/analysis', desc: 'Market analysis data', credits: 15 },
          { method: 'POST', path: '/api/properties/search', desc: 'Search properties', credits: 2 }
        ].map((ep, i) => (
          <div key={i} className="bg-gray-800 rounded-xl p-4 border border-gray-700">
            <div className="flex items-center gap-3">
              <span className={`px-2 py-1 rounded text-xs font-mono ${
                ep.method === 'GET' ? 'bg-green-500/20 text-green-400' : 'bg-blue-500/20 text-blue-400'
              }`}>
                {ep.method}
              </span>
              <code className="text-sm text-gray-300">{ep.path}</code>
            </div>
            <p className="text-gray-400 text-sm mt-2">{ep.desc}</p>
            <p className="text-xs text-purple-400 mt-1">{ep.credits} credits per request</p>
          </div>
        ))}
      </div>
    </div>
  )
}

// Cities Tab
function CitiesTab() {
  const cities = [
    { name: 'Bangalore', status: 'active', data: true, models: true, requests: '12,450' },
    { name: 'Mumbai', status: 'active', data: false, models: false, requests: '0' },
    { name: 'Delhi NCR', status: 'active', data: false, models: false, requests: '0' },
    { name: 'Hyderabad', status: 'active', data: false, models: false, requests: '0' },
    { name: 'Chennai', status: 'active', data: false, models: false, requests: '0' },
    { name: 'Pune', status: 'active', data: false, models: false, requests: '0' }
  ]

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold">City Management</h2>
        <button className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">
          + Add City
        </button>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {cities.map((city, i) => (
          <div key={i} className="bg-gray-800 rounded-2xl p-6 border border-gray-700 hover:border-gray-600 transition">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold">{city.name}</h3>
              <span className={`px-3 py-1 rounded-full text-xs ${
                city.data ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'
              }`}>
                {city.data ? 'Live' : 'Setup Required'}
              </span>
            </div>
            
            <div className="space-y-2 mb-4">
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">Raw Data</span>
                <span className={city.data ? 'text-green-400' : 'text-yellow-400'}>
                  {city.data ? '✓ Loaded' : '⏳ Pending'}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">ML Models</span>
                <span className={city.models ? 'text-green-400' : 'text-yellow-400'}>
                  {city.models ? '✓ Trained' : '⏳ Pending'}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-400">API Requests</span>
                <span className="text-white">{city.requests}</span>
              </div>
            </div>
            
            <button className="w-full py-2 bg-blue-500/20 text-blue-400 rounded-lg hover:bg-blue-500/30 transition text-sm">
              Configure
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}

// Analytics Tab
function AnalyticsTab() {
  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Analytics</h2>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        {[
          { label: 'API Requests Today', value: '15,420', change: '+12%' },
          { label: 'Avg Response Time', value: '245ms', change: '-8%' },
          { label: 'Error Rate', value: '0.02%', change: '-15%' }
        ].map((stat, i) => (
          <div key={i} className="bg-gray-800 rounded-2xl p-5 border border-gray-700">
            <p className="text-gray-400 text-sm">{stat.label}</p>
            <p className="text-3xl font-bold mt-1">{stat.value}</p>
            <p className={`text-sm mt-1 ${stat.change.startsWith('+') && !stat.label.includes('Error') ? 'text-green-400' : stat.change.startsWith('-') && stat.label.includes('Error') ? 'text-green-400' : stat.change.startsWith('-') ? 'text-green-400' : 'text-red-400'}`}>
              {stat.change} from yesterday
            </p>
          </div>
        ))}
      </div>

      <div className="bg-gray-800 rounded-2xl p-6 border border-gray-700 mb-6">
        <h3 className="text-lg font-semibold mb-4">Popular Queries</h3>
        <div className="space-y-3">
          {[
            { query: 'Property prices in Koramangala', count: 1256, endpoint: '/api/predict/price' },
            { query: 'Best areas to invest in Bangalore', count: 984, endpoint: '/api/chat' },
            { query: 'Rental yield analysis Whitefield', count: 756, endpoint: '/api/market/analysis' },
            { query: 'Metro impact on property prices', count: 623, endpoint: '/api/chat' }
          ].map((item, i) => (
            <div key={i} className="flex justify-between items-center py-3 border-b border-gray-700 last:border-0">
              <div>
                <p className="text-gray-300">{item.query}</p>
                <p className="text-xs text-gray-500">{item.endpoint}</p>
              </div>
              <span className="text-gray-400">{item.count.toLocaleString()} requests</span>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-gray-800 rounded-2xl p-6 border border-gray-700">
        <h3 className="text-lg font-semibold mb-4">Endpoint Performance</h3>
        <div className="space-y-4">
          {[
            { endpoint: '/api/predict/price', calls: 8420, avgTime: '312ms', successRate: '99.8%' },
            { endpoint: '/api/chat', calls: 4230, avgTime: '1.2s', successRate: '99.5%' },
            { endpoint: '/api/market/analysis', calls: 1890, avgTime: '456ms', successRate: '99.9%' },
            { endpoint: '/api/properties/search', calls: 880, avgTime: '89ms', successRate: '100%' }
          ].map((ep, i) => (
            <div key={i} className="flex items-center justify-between py-2">
              <code className="text-blue-400 text-sm">{ep.endpoint}</code>
              <div className="flex gap-8 text-sm">
                <span className="text-gray-400">{ep.calls.toLocaleString()} calls</span>
                <span className="text-gray-400">{ep.avgTime}</span>
                <span className="text-green-400">{ep.successRate}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// Error Logs Tab
function ErrorLogsTab() {
  const [errors, setErrors] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState({ severity: '', category: '', resolved: '' })
  const [selectedError, setSelectedError] = useState(null)

  useEffect(() => {
    fetchErrors()
    fetchStats()
    const interval = setInterval(fetchStats, 30000) // Refresh stats every 30s
    return () => clearInterval(interval)
  }, [filter])

  const fetchErrors = async () => {
    try {
      const params = new URLSearchParams()
      if (filter.severity) params.append('severity', filter.severity)
      if (filter.category) params.append('category', filter.category)
      if (filter.resolved !== '') params.append('resolved', filter.resolved)
      
      const res = await fetch(`http://localhost:8000/api/errors?${params}`)
      const data = await res.json()
      if (data.success) setErrors(data.errors || [])
    } catch (err) {
      console.error('Failed to fetch errors:', err)
    } finally {
      setLoading(false)
    }
  }

  const fetchStats = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/errors/statistics')
      const data = await res.json()
      if (data.success) setStats(data.statistics)
    } catch (err) {
      console.error('Failed to fetch error stats:', err)
    }
  }

  const resolveError = async (errorId) => {
    try {
      await fetch(`http://localhost:8000/api/errors/${errorId}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resolved_by: 'admin' })
      })
      fetchErrors()
      fetchStats()
    } catch (err) {
      console.error('Failed to resolve error:', err)
    }
  }

  const resolveAll = async () => {
    try {
      await fetch('http://localhost:8000/api/errors/resolve-all', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resolved_by: 'admin' })
      })
      fetchErrors()
      fetchStats()
    } catch (err) {
      console.error('Failed to resolve all:', err)
    }
  }

  const createTestError = async () => {
    try {
      await fetch('http://localhost:8000/api/errors/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: 'Test error from admin panel', severity: 'error', category: 'system' })
      })
      fetchErrors()
      fetchStats()
    } catch (err) {
      console.error('Failed to create test error:', err)
    }
  }

  const getSeverityColor = (severity) => {
    switch (severity) {
      case 'critical': return 'bg-red-500/20 text-red-400 border-red-500/30'
      case 'error': return 'bg-orange-500/20 text-orange-400 border-orange-500/30'
      case 'warning': return 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
      case 'info': return 'bg-blue-500/20 text-blue-400 border-blue-500/30'
      default: return 'bg-gray-500/20 text-gray-400 border-gray-500/30'
    }
  }

  const getCategoryIcon = (category) => {
    const icons = {
      api: '🌐', database: '🗄️', auth: '🔐', voice: '🎤', llm: '🤖',
      scraping: '🕷️', map: '🗺️', prediction: '📊', agent: '🤝', system: '⚙️'
    }
    return icons[category] || '❓'
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold">🚨 Error Logs</h2>
        <div className="flex gap-2">
          <button onClick={createTestError} className="px-3 py-1.5 bg-gray-700 text-gray-300 rounded-lg text-sm hover:bg-gray-600">
            + Test Error
          </button>
          <button onClick={resolveAll} className="px-3 py-1.5 bg-green-600 text-white rounded-lg text-sm hover:bg-green-700">
            ✓ Resolve All
          </button>
          <button onClick={fetchErrors} className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700">
            ↻ Refresh
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
            <div className="text-3xl mb-1">🔴</div>
            <div className="text-2xl font-bold text-red-400">{stats.unresolved_critical || 0}</div>
            <div className="text-sm text-gray-400">Critical</div>
          </div>
          <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
            <div className="text-3xl mb-1">🟠</div>
            <div className="text-2xl font-bold text-orange-400">{stats.unresolved_errors || 0}</div>
            <div className="text-sm text-gray-400">Errors</div>
          </div>
          <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
            <div className="text-3xl mb-1">⏰</div>
            <div className="text-2xl font-bold text-yellow-400">{stats.last_hour || 0}</div>
            <div className="text-sm text-gray-400">Last Hour</div>
          </div>
          <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
            <div className="text-3xl mb-1">📋</div>
            <div className="text-2xl font-bold">{stats.total_errors || 0}</div>
            <div className="text-sm text-gray-400">Total Logged</div>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-gray-800 rounded-xl p-4 border border-gray-700 mb-6">
        <div className="flex flex-wrap gap-4">
          <select 
            value={filter.severity} 
            onChange={(e) => setFilter({...filter, severity: e.target.value})}
            className="bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-sm"
          >
            <option value="">All Severities</option>
            <option value="critical">🔴 Critical</option>
            <option value="error">🟠 Error</option>
            <option value="warning">🟡 Warning</option>
            <option value="info">🔵 Info</option>
          </select>
          <select 
            value={filter.category} 
            onChange={(e) => setFilter({...filter, category: e.target.value})}
            className="bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-sm"
          >
            <option value="">All Categories</option>
            <option value="api">🌐 API</option>
            <option value="database">🗄️ Database</option>
            <option value="auth">🔐 Auth</option>
            <option value="voice">🎤 Voice</option>
            <option value="llm">🤖 LLM</option>
            <option value="map">🗺️ Map</option>
            <option value="prediction">📊 Prediction</option>
            <option value="agent">🤝 Agent</option>
            <option value="system">⚙️ System</option>
          </select>
          <select 
            value={filter.resolved} 
            onChange={(e) => setFilter({...filter, resolved: e.target.value})}
            className="bg-gray-700 border border-gray-600 rounded-lg px-3 py-2 text-sm"
          >
            <option value="">All Status</option>
            <option value="false">❌ Unresolved</option>
            <option value="true">✅ Resolved</option>
          </select>
        </div>
      </div>

      {/* Error List */}
      <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
        {loading ? (
          <div className="p-8 text-center text-gray-400">Loading errors...</div>
        ) : errors.length === 0 ? (
          <div className="p-8 text-center text-gray-400">
            <div className="text-4xl mb-2">✨</div>
            <p>No errors found. System is healthy!</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-700">
            {errors.map((error) => (
              <div 
                key={error.id} 
                className={`p-4 hover:bg-gray-700/50 cursor-pointer transition ${error.resolved ? 'opacity-50' : ''}`}
                onClick={() => setSelectedError(selectedError?.id === error.id ? null : error)}
              >
                <div className="flex items-start gap-3">
                  <span className="text-xl">{getCategoryIcon(error.category)}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`px-2 py-0.5 rounded text-xs border ${getSeverityColor(error.severity)}`}>
                        {error.severity?.toUpperCase()}
                      </span>
                      <span className="text-xs text-gray-500">{error.category}</span>
                      {error.resolved && <span className="text-xs text-green-400">✓ Resolved</span>}
                    </div>
                    <p className="text-sm font-medium truncate">{error.message}</p>
                    <p className="text-xs text-gray-400 mt-1">
                      {new Date(error.timestamp).toLocaleString()}
                      {error.endpoint && <span className="ml-2">• {error.endpoint}</span>}
                    </p>
                    
                    {/* Expanded Details */}
                    {selectedError?.id === error.id && (
                      <div className="mt-3 p-3 bg-gray-900 rounded-lg text-xs">
                        {error.details && (
                          <div className="mb-2">
                            <span className="text-gray-400">Details:</span>
                            <p className="text-gray-300 mt-1">{error.details}</p>
                          </div>
                        )}
                        {error.stack_trace && (
                          <div className="mb-2">
                            <span className="text-gray-400">Stack Trace:</span>
                            <pre className="text-red-300 mt-1 overflow-x-auto max-h-32 text-[10px]">{error.stack_trace}</pre>
                          </div>
                        )}
                        {!error.resolved && (
                          <button 
                            onClick={(e) => { e.stopPropagation(); resolveError(error.id); }}
                            className="mt-2 px-3 py-1 bg-green-600 text-white rounded text-xs hover:bg-green-700"
                          >
                            Mark as Resolved
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

// Platform Tests Tab - Comprehensive system validation
function PlatformTestsTab() {
  const [activeCategory, setActiveCategory] = useState('citybrain')
  const [testResults, setTestResults] = useState({})
  const [runningTest, setRunningTest] = useState(null)
  const [allTestsRunning, setAllTestsRunning] = useState(false)
  const [testHistory, setTestHistory] = useState([])

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

  const testCategories = [
    { id: 'citybrain', name: 'City Brain Architecture', icon: '🧠', color: 'purple' },
    { id: 'advanced', name: 'Advanced Reasoning', icon: '🔬', color: 'indigo' },
    { id: 'persona', name: 'Persona Validation', icon: '👤', color: 'blue' },
    { id: 'spatial', name: 'Spatial & Infrastructure', icon: '🌐', color: 'green' },
    { id: 'narrative', name: 'Narrative Layer', icon: '🤖', color: 'orange' },
    { id: 'technical', name: 'Technical Failures', icon: '⚙️', color: 'red' },
    { id: 'performance', name: 'Performance Benchmarks', icon: '⚡', color: 'yellow' },
    { id: 'mlvalidation', name: 'ML Model Validation', icon: '🎯', color: 'pink' },
    { id: 'metrics', name: 'Validation Metrics', icon: '📊', color: 'cyan' }
  ]

  const allTests = {
    citybrain: [
      {
        id: 'causal_reasoning',
        name: 'Causal Reasoning',
        prompt: 'Simulate the impact of delaying Metro Line 6 in Bangalore by 2 years. Show ripple effects on property prices in Whitefield, Sarjapur Road, and Hebbal. Include confidence intervals.',
        expected: 'Quantifiable price delta projections + risk-adjusted timelines',
        category: 'Knowledge → Memory'
      },
      {
        id: 'memory_feedback',
        name: 'Memory Feedback Loop',
        prompt: 'Compare your predicted 2024 price growth for Kengeri with actual transaction data from Q3 2024. Adjust your 2025 forecast based on this error.',
        expected: 'Self-corrected forecast + error analysis report',
        category: 'Learning Loop'
      },
      {
        id: 'ontology_stress',
        name: 'Ontology Stress Test',
        prompt: 'How does a "flood risk downgrade" in Electronic City affect its Growth Phase classification? Recalculate investor type and risk index.',
        expected: 'Updated Locality Personality Model with version history',
        category: 'Knowledge Graph'
      },
      {
        id: 'cross_zone',
        name: 'Cross-Zone Contagion',
        prompt: 'If a new IT park opens in Devanahalli, which micro-markets in North Bangalore will see secondary demand spikes? Rank by probability.',
        expected: 'Heatmap of correlated zones + migration probability scores',
        category: 'Spatial Reasoning'
      },
      {
        id: 'temporal_cascade',
        name: 'Temporal Cascade Analysis',
        prompt: 'Model the 5-year price trajectory cascade when: (1) ORR completion in 2025, (2) Airport expansion in 2026, (3) New SEZ in Devanahalli 2027. Show interference patterns between events.',
        expected: 'Multi-event timeline with compounding effect analysis',
        category: 'Temporal Reasoning'
      },
      {
        id: 'market_regime',
        name: 'Market Regime Detection',
        prompt: 'Identify the current market regime (bull/bear/sideways) for each Bangalore zone. What signals would trigger regime change? Backtest against 2019-2024 data.',
        expected: 'Regime classification per zone with transition probabilities',
        category: 'Pattern Recognition'
      }
    ],
    advanced: [
      {
        id: 'multi_variable_causality',
        name: 'Multi-Variable Causality',
        prompt: 'Analyze how these 5 variables interact to affect Whitefield prices: (1) IT hiring trends, (2) Metro ridership, (3) Water availability, (4) School ratings, (5) Air quality index. Show causal DAG with strength coefficients.',
        expected: 'Causal directed acyclic graph with quantified relationships',
        category: 'Causal Inference',
        difficulty: 'expert'
      },
      {
        id: 'bayesian_belief_update',
        name: 'Bayesian Belief Update',
        prompt: 'Your prior belief: Sarjapur will grow 12% in 2025. New evidence: 3 major IT companies announced WFH permanent policy. Update your posterior probability distribution.',
        expected: 'Updated probability distribution with likelihood ratios',
        category: 'Probabilistic Reasoning',
        difficulty: 'expert'
      },
      {
        id: 'game_theory_pricing',
        name: 'Game Theory Pricing',
        prompt: 'Model the Nash equilibrium for pricing strategy when 3 competing projects launch in Whitefield simultaneously. Each has 200 units. What is the optimal price point?',
        expected: 'Equilibrium analysis with payoff matrix',
        category: 'Strategic Reasoning',
        difficulty: 'expert'
      },
      {
        id: 'anomaly_detection',
        name: 'Anomaly Detection',
        prompt: 'Identify statistical anomalies in Bangalore property transactions from last 6 months. Flag potential fraud indicators, data quality issues, or genuine market disruptions.',
        expected: 'Anomaly report with confidence scores and explanations',
        category: 'Statistical Analysis',
        difficulty: 'advanced'
      },
      {
        id: 'sentiment_integration',
        name: 'Sentiment-Price Integration',
        prompt: 'Correlate social media sentiment about Bangalore localities with actual price movements. Which localities show sentiment-price divergence (potential opportunities)?',
        expected: 'Sentiment-price correlation matrix with divergence alerts',
        category: 'NLP + Finance',
        difficulty: 'advanced'
      },
      {
        id: 'monte_carlo_forecast',
        name: 'Monte Carlo Simulation',
        prompt: 'Run 10,000 Monte Carlo simulations for Koramangala 3-year price trajectory. Show probability density function, VaR at 95%, and worst-case scenarios.',
        expected: 'PDF visualization with risk metrics',
        category: 'Stochastic Modeling',
        difficulty: 'expert'
      },
      {
        id: 'reinforcement_learning',
        name: 'RL Investment Strategy',
        prompt: 'Train a reinforcement learning agent to optimize a ₹5Cr real estate portfolio across 6 Bangalore localities over 5 years. Show learned policy and expected returns.',
        expected: 'Optimal allocation policy with Sharpe ratio',
        category: 'ML Optimization',
        difficulty: 'expert'
      },
      {
        id: 'graph_neural_prediction',
        name: 'Graph Neural Network Prediction',
        prompt: 'Use the property transaction graph to predict which properties in HSR Layout will sell within 30 days. Show node embedding visualization and prediction confidence.',
        expected: 'Node-level predictions with attention weights',
        category: 'GNN Analysis',
        difficulty: 'expert'
      }
    ],
    persona: [
      {
        id: 'agent_negotiation',
        name: 'Agent: Negotiation Script',
        prompt: 'Generate a negotiation script for a 2BHK in Bellandur showing: current valuation vs. predicted 12-month value, flood risk score, and comparable sales with confidence bands.',
        expected: 'Complete negotiation document with data-backed talking points',
        category: 'Real Estate Agents',
        persona: '🏠'
      },
      {
        id: 'agent_staging',
        name: 'Agent: Virtual Staging',
        prompt: 'Show virtual staging options for this raw unit in ORR that appeal to IT professionals. Overlay rental yield projections.',
        expected: 'Staging recommendations + ROI analysis',
        category: 'Real Estate Agents',
        persona: '🏠'
      },
      {
        id: 'developer_pricing',
        name: 'Developer: Pricing Strategy',
        prompt: 'Simulate pricing strategy for a luxury tower in MG Road: run 3 scenarios (premium pricing vs. volume focus vs. hybrid) with absorption rate forecasts under current infrastructure constraints.',
        expected: '3 pricing models with absorption forecasts',
        category: 'Property Developers',
        persona: '🏗️'
      },
      {
        id: 'developer_mix',
        name: 'Developer: Unit Mix',
        prompt: 'What\'s the optimal unit mix (1BHK/2BHK/3BHK) for a new project near Airport Road based on 5-year demand evolution models?',
        expected: 'Unit mix recommendation with demand forecasts',
        category: 'Property Developers',
        persona: '🏗️'
      },
      {
        id: 'nri_comparison',
        name: 'NRI: Investment Comparison',
        prompt: 'Compare investment potential: ₹50L in Pune Hinjewadi vs. Chennai OMR. Factor in currency risk, rental yield stability, and exit liquidity timelines.',
        expected: 'Cross-city investment comparison with risk factors',
        category: 'NRI Investors',
        persona: '🌍'
      },
      {
        id: 'nri_duediligence',
        name: 'NRI: Remote Due Diligence',
        prompt: 'Do a remote due diligence walkthrough of this Chennai property. Flag structural risks visible in 3D scan and overlay future metro impact.',
        expected: 'Due diligence report with risk flags',
        category: 'NRI Investors',
        persona: '🌍'
      },
      {
        id: 'bank_stresstest',
        name: 'Bank: Collateral Stress Test',
        prompt: 'Stress-test this collateral property in Hyderabad: show value erosion under 3 scenarios (flood event, metro delay, job loss surge in local IT sector).',
        expected: 'Stress test report with value erosion scenarios',
        category: 'Banks & Lenders',
        persona: '🏦'
      },
      {
        id: 'bank_valuation',
        name: 'Bank: Automated Valuation',
        prompt: 'Generate automated valuation report API response for PIN 560103 with audit trail of data sources.',
        expected: 'AVM report with data provenance',
        category: 'Banks & Lenders',
        persona: '🏦'
      },
      {
        id: 'buyer_alternatives',
        name: 'Buyer: Alternative Localities',
        prompt: 'Why is my dream locality (Koramangala) showing "Saturated Growth Phase"? Show alternative neighborhoods with similar lifestyle but accelerating growth.',
        expected: 'Growth phase explanation + alternatives',
        category: 'Homebuyers',
        persona: '🏡'
      },
      {
        id: 'buyer_tour',
        name: 'Buyer: Virtual Tour',
        prompt: 'Walk me through this virtual tour of a Marathahalli apartment. Highlight rooms with highest value-add potential and future noise risk from upcoming flyover.',
        expected: 'Interactive tour with value insights',
        category: 'Homebuyers',
        persona: '🏡'
      }
    ],
    spatial: [
      {
        id: 'water_evolution',
        name: 'Environmental Causality',
        prompt: 'Animate 10-year evolution of water bodies in Bangalore. Overlay property price trajectories in 1km buffer zones around disappearing lakes.',
        expected: 'Time-series visualization with price correlation',
        category: 'GIS + Simulation'
      },
      {
        id: 'shapefile_import',
        name: 'GIS Pipeline Integrity',
        prompt: 'Import this shapefile of proposed peripheral ring road. Recompute accessibility scores for all localities and flag undervalued micro-markets within 5km of new exits.',
        expected: 'Updated accessibility scores + investment opportunities',
        category: 'GIS + Simulation'
      },
      {
        id: 'pedestrian_flow',
        name: 'Urban Behavior Synthesis',
        prompt: 'Show pedestrian flow heatmaps around KR Puram station during monsoon. How does this correlate with retail space vacancies?',
        expected: 'Flow heatmap + retail correlation analysis',
        category: 'Multi-modal Analysis'
      },
      {
        id: 'metro_impact',
        name: 'Infrastructure Maturity',
        prompt: 'What happens to property values within 800m of metro stations when Phase 3 gets fully operational? Segment by residential vs. commercial.',
        expected: 'Segmented impact analysis with confidence intervals',
        category: 'Infrastructure Curves'
      }
    ],
    narrative: [
      {
        id: 'contradiction',
        name: 'Contradiction Test',
        prompt: 'Last month you predicted Sarjapur Road would outperform Whitefield. Today\'s data shows opposite trends. Explain the pivot with evidence.',
        expected: 'Transparent explanation with data citations',
        category: 'Reasoning Validation'
      },
      {
        id: 'counterfactual',
        name: 'Counterfactual Reasoning',
        prompt: 'If Bengaluru never built the metro, which areas would have dominated growth? Contrast with actual trajectory.',
        expected: 'Counterfactual analysis with historical comparison',
        category: 'Causal Reasoning'
      },
      {
        id: 'risk_transparency',
        name: 'Risk Transparency',
        prompt: 'Show me the 3 weakest assumptions behind your 2027 price forecast for Electronic City.',
        expected: 'Explicit assumption list with uncertainty quantification',
        category: 'Explainability'
      },
      {
        id: 'jargon_filter',
        name: 'Jargon Filter Test',
        prompt: 'Explain "liquidity risk index" to a first-time homebuyer using only Bangalore-specific analogies.',
        expected: 'Plain-language explanation with local context',
        category: 'Accessibility'
      }
    ],
    technical: [
      {
        id: 'partial_data',
        name: 'Partial Data Failure',
        prompt: 'Run Whitefield forecast with 40% missing transaction data. Show confidence degradation and fallback data sources used.',
        expected: 'Degraded forecast + fallback documentation',
        category: 'Resilience',
        severity: 'warning'
      },
      {
        id: 'hallucination_trap',
        name: 'LLM Hallucination Trap',
        prompt: 'Cite exact data sources for your claim about "declining water tables in North Bangalore affecting property values".',
        expected: 'Verifiable source citations or honest uncertainty',
        category: 'Accuracy',
        severity: 'critical'
      },
      {
        id: 'extreme_scenario',
        name: 'Extreme Scenario',
        prompt: 'Simulate hyperinflation (30% YoY) + simultaneous metro strike. Which asset classes become defensive havens?',
        expected: 'Scenario analysis with defensive recommendations',
        category: 'Stress Testing',
        severity: 'warning'
      },
      {
        id: 'viewer_failure',
        name: '3D Viewer Fallback',
        prompt: 'When WebGL fails on low-end devices, show fallback data visualization preserving risk overlays.',
        expected: 'Graceful degradation with preserved information',
        category: 'UI Resilience',
        severity: 'info'
      },
      {
        id: 'concurrent_requests',
        name: 'Concurrent Request Handling',
        prompt: 'Simulate 100 concurrent valuation requests for different properties. Report success rate, average latency, and error distribution.',
        expected: 'Load test results with percentile latencies',
        category: 'Scalability',
        severity: 'critical'
      },
      {
        id: 'cache_invalidation',
        name: 'Cache Invalidation Test',
        prompt: 'Update a property price in the database. Verify cache invalidation across all layers (Redis, in-memory, CDN) within 5 seconds.',
        expected: 'Cache consistency verification report',
        category: 'Data Integrity',
        severity: 'critical'
      },
      {
        id: 'database_failover',
        name: 'Database Failover',
        prompt: 'Simulate primary database failure. Verify automatic failover to read replica and graceful degradation of write operations.',
        expected: 'Failover timeline and data consistency report',
        category: 'High Availability',
        severity: 'critical'
      },
      {
        id: 'memory_leak_detection',
        name: 'Memory Leak Detection',
        prompt: 'Run continuous property searches for 1 hour. Monitor memory usage pattern. Flag if growth exceeds 5% per hour.',
        expected: 'Memory profile with leak indicators',
        category: 'Resource Management',
        severity: 'warning'
      }
    ],
    performance: [
      {
        id: 'api_latency_p50',
        name: 'API Latency P50',
        prompt: 'Measure 50th percentile latency for /api/properties/search endpoint over 1000 requests.',
        expected: '<200ms P50 latency',
        category: 'API Performance',
        benchmark: { target: 200, unit: 'ms', type: 'latency' }
      },
      {
        id: 'api_latency_p99',
        name: 'API Latency P99',
        prompt: 'Measure 99th percentile latency for /api/agent/plan endpoint over 1000 requests.',
        expected: '<2000ms P99 latency',
        category: 'API Performance',
        benchmark: { target: 2000, unit: 'ms', type: 'latency' }
      },
      {
        id: 'valuation_throughput',
        name: 'Valuation Throughput',
        prompt: 'Calculate maximum valuations per second the AVM agent can process with 4 CPU cores.',
        expected: '>50 valuations/second',
        category: 'Throughput',
        benchmark: { target: 50, unit: 'req/s', type: 'throughput' }
      },
      {
        id: 'heatmap_generation',
        name: 'City Heatmap Generation',
        prompt: 'Generate full Bangalore price heatmap with 500+ localities. Measure end-to-end time.',
        expected: '<3 seconds for full city heatmap',
        category: 'Spatial Performance',
        benchmark: { target: 3000, unit: 'ms', type: 'latency' }
      },
      {
        id: 'vector_search',
        name: 'Vector Similarity Search',
        prompt: 'Find 10 most similar properties using pgvector from 100K property embeddings.',
        expected: '<100ms for top-10 similarity search',
        category: 'Vector DB Performance',
        benchmark: { target: 100, unit: 'ms', type: 'latency' }
      },
      {
        id: 'graph_traversal',
        name: 'Property Graph Traversal',
        prompt: 'Find all properties within 3 hops of a given property in the transaction graph (10K nodes).',
        expected: '<500ms for 3-hop traversal',
        category: 'Graph Performance',
        benchmark: { target: 500, unit: 'ms', type: 'latency' }
      },
      {
        id: 'forecast_batch',
        name: 'Batch Forecast Performance',
        prompt: 'Generate 12-month price forecasts for all 198 Bangalore localities in parallel.',
        expected: '<10 seconds for full city forecast',
        category: 'Batch Processing',
        benchmark: { target: 10000, unit: 'ms', type: 'latency' }
      },
      {
        id: 'llm_response_time',
        name: 'LLM Response Time',
        prompt: 'Measure average response time for complex real estate queries through OpenRouter.',
        expected: '<5 seconds for detailed analysis',
        category: 'LLM Performance',
        benchmark: { target: 5000, unit: 'ms', type: 'latency' }
      },
      {
        id: 'concurrent_users',
        name: 'Concurrent Users Capacity',
        prompt: 'Simulate 500 concurrent users browsing properties and asking questions. Measure degradation.',
        expected: '<20% latency increase at 500 users',
        category: 'Scalability',
        benchmark: { target: 500, unit: 'users', type: 'capacity' }
      },
      {
        id: 'cold_start_time',
        name: 'Cold Start Time',
        prompt: 'Measure time from container start to first successful API response.',
        expected: '<30 seconds cold start',
        category: 'Startup Performance',
        benchmark: { target: 30000, unit: 'ms', type: 'latency' }
      },
      {
        id: 'database_query_p95',
        name: 'Database Query P95',
        prompt: 'Measure 95th percentile for complex spatial queries with PostGIS.',
        expected: '<500ms P95 for spatial queries',
        category: 'Database Performance',
        benchmark: { target: 500, unit: 'ms', type: 'latency' }
      },
      {
        id: 'cache_hit_rate',
        name: 'Cache Hit Rate',
        prompt: 'Measure Redis cache hit rate over 10,000 property detail requests.',
        expected: '>85% cache hit rate',
        category: 'Caching Efficiency',
        benchmark: { target: 85, unit: '%', type: 'percentage' }
      }
    ],
    mlvalidation: [
      {
        id: 'avm_mape',
        name: 'AVM MAPE Score',
        prompt: 'Calculate Mean Absolute Percentage Error for AVM predictions against last 1000 actual sales.',
        expected: '<12% MAPE on test set',
        category: 'Valuation Accuracy',
        benchmark: { target: 12, unit: '%', type: 'error' }
      },
      {
        id: 'avm_r2_score',
        name: 'AVM R² Score',
        prompt: 'Calculate R-squared score for AVM model on held-out test data (20% of dataset).',
        expected: '>0.85 R² score',
        category: 'Model Fit',
        benchmark: { target: 0.85, unit: 'R²', type: 'score' }
      },
      {
        id: 'forecast_rmse',
        name: 'Forecast RMSE',
        prompt: 'Calculate Root Mean Square Error for 6-month price forecasts against actuals.',
        expected: '<8% RMSE on validation set',
        category: 'Forecast Accuracy',
        benchmark: { target: 8, unit: '%', type: 'error' }
      },
      {
        id: 'classification_f1',
        name: 'Growth Phase F1 Score',
        prompt: 'Calculate F1 score for growth phase classification (Emerging/Accelerating/Mature/Saturated).',
        expected: '>0.80 macro F1 score',
        category: 'Classification Accuracy',
        benchmark: { target: 0.80, unit: 'F1', type: 'score' }
      },
      {
        id: 'risk_calibration',
        name: 'Risk Score Calibration',
        prompt: 'Verify that predicted risk scores are well-calibrated: 80% risk should mean 80% actual occurrence.',
        expected: 'Calibration error <5%',
        category: 'Probability Calibration',
        benchmark: { target: 5, unit: '%', type: 'error' }
      },
      {
        id: 'feature_importance',
        name: 'Feature Importance Stability',
        prompt: 'Compare feature importance rankings across 5 random train/test splits. Check for stability.',
        expected: 'Top 10 features stable across splits',
        category: 'Model Robustness',
        benchmark: { target: 80, unit: '%', type: 'percentage' }
      },
      {
        id: 'model_drift',
        name: 'Model Drift Detection',
        prompt: 'Compare model performance on last month vs. last year data. Flag if accuracy drop >5%.',
        expected: 'No significant drift detected',
        category: 'Model Monitoring',
        benchmark: { target: 5, unit: '%', type: 'drift' }
      },
      {
        id: 'embedding_quality',
        name: 'Property Embedding Quality',
        prompt: 'Evaluate embedding quality: similar properties should have cosine similarity >0.8.',
        expected: 'Intra-cluster similarity >0.8',
        category: 'Representation Learning',
        benchmark: { target: 0.8, unit: 'cosine', type: 'similarity' }
      },
      {
        id: 'shap_consistency',
        name: 'SHAP Value Consistency',
        prompt: 'Verify SHAP explanations are consistent for similar properties. Correlation should be >0.9.',
        expected: 'SHAP correlation >0.9 for similar inputs',
        category: 'Explainability',
        benchmark: { target: 0.9, unit: 'correlation', type: 'consistency' }
      },
      {
        id: 'ab_test_power',
        name: 'A/B Test Statistical Power',
        prompt: 'Calculate minimum sample size for 80% power to detect 5% improvement in conversion.',
        expected: 'Statistical power analysis report',
        category: 'Experimentation',
        benchmark: { target: 80, unit: '%', type: 'power' }
      },
      {
        id: 'fairness_audit',
        name: 'Model Fairness Audit',
        prompt: 'Check if AVM predictions show bias across different localities or property types.',
        expected: 'No significant bias detected (p>0.05)',
        category: 'Fairness',
        benchmark: { target: 0.05, unit: 'p-value', type: 'fairness' }
      },
      {
        id: 'adversarial_robustness',
        name: 'Adversarial Robustness',
        prompt: 'Test model robustness against adversarial inputs (e.g., unrealistic property features).',
        expected: 'Model rejects invalid inputs gracefully',
        category: 'Security',
        benchmark: { target: 95, unit: '%', type: 'rejection' }
      }
    ],
    metrics: [
      {
        id: 'knowledge_consistency',
        name: 'Knowledge Layer',
        metric: 'Ontology consistency across 100+ locality attributes',
        tool: 'Neo4j schema validator',
        threshold: '100%',
        currentValue: '98.5%',
        status: 'warning'
      },
      {
        id: 'reasoning_accuracy',
        name: 'Reasoning Layer',
        metric: 'Prediction error vs. actuals on historical benchmarks',
        tool: 'Backtesting dashboard',
        threshold: '<15%',
        currentValue: '12.3%',
        status: 'pass'
      },
      {
        id: 'narrative_clarity',
        name: 'Narrative Layer',
        metric: 'Explanations pass "grandma test" (non-expert comprehension)',
        tool: 'User testing panel',
        threshold: '95%',
        currentValue: '91.2%',
        status: 'warning'
      },
      {
        id: 'memory_improvement',
        name: 'Memory Layer',
        metric: 'Forecast accuracy improvement after quarterly feedback',
        tool: 'Drift detection monitor',
        threshold: '7%',
        currentValue: '8.4%',
        status: 'pass'
      },
      {
        id: 'spatial_latency',
        name: 'Spatial Layer',
        metric: 'Latency for city-wide heatmap generation',
        tool: 'Load testing (k6)',
        threshold: '<500ms',
        currentValue: '342ms',
        status: 'pass'
      },
      {
        id: 'api_availability',
        name: 'API Availability',
        metric: 'Uptime over last 30 days',
        tool: 'UptimeRobot',
        threshold: '99.9%',
        currentValue: '99.95%',
        status: 'pass'
      },
      {
        id: 'avm_accuracy',
        name: 'AVM Accuracy',
        metric: 'Mean Absolute Percentage Error on valuations',
        tool: 'Model validation suite',
        threshold: '<12%',
        currentValue: '10.8%',
        status: 'pass'
      },
      {
        id: 'forecast_accuracy',
        name: 'Forecast Accuracy',
        metric: '6-month price forecast RMSE',
        tool: 'Backtesting dashboard',
        threshold: '<8%',
        currentValue: '7.2%',
        status: 'pass'
      },
      {
        id: 'cache_efficiency',
        name: 'Cache Efficiency',
        metric: 'Redis cache hit rate',
        tool: 'Redis monitoring',
        threshold: '>85%',
        currentValue: '89.3%',
        status: 'pass'
      },
      {
        id: 'model_drift',
        name: 'Model Drift',
        metric: 'Performance degradation since last retrain',
        tool: 'Drift detection monitor',
        threshold: '<5%',
        currentValue: '2.1%',
        status: 'pass'
      },
      {
        id: 'data_freshness',
        name: 'Data Freshness',
        metric: 'Average age of property listings in database',
        tool: 'Data pipeline monitor',
        threshold: '<24h',
        currentValue: '18h',
        status: 'pass'
      },
      {
        id: 'query_performance',
        name: 'Query Performance',
        metric: 'P95 latency for complex spatial queries',
        tool: 'PostgreSQL pg_stat',
        threshold: '<500ms',
        currentValue: '387ms',
        status: 'pass'
      },
      {
        id: 'llm_cost',
        name: 'LLM Cost Efficiency',
        metric: 'Cost per 1000 AI queries',
        tool: 'OpenRouter billing',
        threshold: '<$5',
        currentValue: '$3.42',
        status: 'pass'
      },
      {
        id: 'error_rate',
        name: 'Error Rate',
        metric: 'API error rate (5xx responses)',
        tool: 'Application monitoring',
        threshold: '<0.1%',
        currentValue: '0.03%',
        status: 'pass'
      },
      {
        id: 'user_satisfaction',
        name: 'User Satisfaction',
        metric: 'Average rating from in-app feedback',
        tool: 'Feedback analytics',
        threshold: '>4.5/5',
        currentValue: '4.7/5',
        status: 'pass'
      }
    ]
  }

  const runTest = async (testId, prompt) => {
    setRunningTest(testId)
    try {
      const res = await fetch(`${API_URL}/api/agent/plan`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: prompt, context: { testMode: true } })
      })
      const data = await res.json()
      
      const result = {
        testId,
        timestamp: new Date().toISOString(),
        success: data.response && data.response.length > 50,
        response: data.response || data.error || 'No response',
        confidence: data.confidence || 0,
        latency: data.latency || 0
      }
      
      setTestResults(prev => ({ ...prev, [testId]: result }))
      setTestHistory(prev => [result, ...prev.slice(0, 49)])
    } catch (err) {
      setTestResults(prev => ({
        ...prev,
        [testId]: {
          testId,
          timestamp: new Date().toISOString(),
          success: false,
          response: err.message,
          error: true
        }
      }))
    } finally {
      setRunningTest(null)
    }
  }

  const runAllTests = async () => {
    setAllTestsRunning(true)
    const tests = allTests[activeCategory]
    if (tests && !tests[0]?.metric) {
      for (const test of tests) {
        await runTest(test.id, test.prompt)
        await new Promise(r => setTimeout(r, 500))
      }
    }
    setAllTestsRunning(false)
  }

  const getPassRate = () => {
    const tests = allTests[activeCategory]
    if (!tests || tests[0]?.metric) return null
    const completed = tests.filter(t => testResults[t.id])
    const passed = completed.filter(t => testResults[t.id]?.success)
    return completed.length > 0 ? Math.round((passed.length / completed.length) * 100) : null
  }

  const renderTests = () => {
    const tests = allTests[activeCategory]
    if (!tests) return null

    if (activeCategory === 'metrics') {
      const passCount = tests.filter(m => m.status === 'pass').length
      const warnCount = tests.filter(m => m.status === 'warning').length
      const failCount = tests.filter(m => m.status === 'fail').length
      
      return (
        <div className="space-y-6">
          {/* Metrics Summary */}
          <div className="grid grid-cols-4 gap-4">
            <div className="bg-gray-800 rounded-xl p-4 border border-gray-700 text-center">
              <div className="text-3xl font-bold text-white">{tests.length}</div>
              <div className="text-sm text-gray-400">Total Metrics</div>
            </div>
            <div className="bg-green-500/10 rounded-xl p-4 border border-green-500/30 text-center">
              <div className="text-3xl font-bold text-green-400">{passCount}</div>
              <div className="text-sm text-green-400">Passing</div>
            </div>
            <div className="bg-yellow-500/10 rounded-xl p-4 border border-yellow-500/30 text-center">
              <div className="text-3xl font-bold text-yellow-400">{warnCount}</div>
              <div className="text-sm text-yellow-400">Warning</div>
            </div>
            <div className="bg-red-500/10 rounded-xl p-4 border border-red-500/30 text-center">
              <div className="text-3xl font-bold text-red-400">{failCount}</div>
              <div className="text-sm text-red-400">Failing</div>
            </div>
          </div>

          {/* Metrics Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {tests.map(metric => (
              <div key={metric.id} className={`bg-gray-800 rounded-2xl p-5 border ${
                metric.status === 'pass' ? 'border-green-500/30' :
                metric.status === 'warning' ? 'border-yellow-500/30' :
                'border-red-500/30'
              }`}>
                <div className="flex items-center justify-between mb-3">
                  <h4 className="font-semibold">{metric.name}</h4>
                  <span className={`px-3 py-1 rounded-full text-sm font-bold ${
                    metric.status === 'pass' ? 'bg-green-500/20 text-green-400' :
                    metric.status === 'warning' ? 'bg-yellow-500/20 text-yellow-400' :
                    'bg-red-500/20 text-red-400'
                  }`}>
                    {metric.currentValue}
                  </span>
                </div>
                <p className="text-xs text-gray-400 mb-3">{metric.metric}</p>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-500">
                    <span className="text-gray-400">Threshold:</span> {metric.threshold}
                  </span>
                  <span className="text-gray-500">
                    <span className="text-gray-400">Tool:</span> {metric.tool}
                  </span>
                </div>
                <div className="mt-3 h-1.5 bg-gray-700 rounded-full overflow-hidden">
                  <div 
                    className={`h-full ${
                      metric.status === 'pass' ? 'bg-gradient-to-r from-green-500 to-emerald-400' :
                      metric.status === 'warning' ? 'bg-gradient-to-r from-yellow-500 to-orange-400' :
                      'bg-gradient-to-r from-red-500 to-pink-400'
                    }`}
                    style={{ width: metric.currentValue.includes('/') ? '94%' : metric.currentValue }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )
    }

    return (
      <div className="space-y-4">
        {tests.map(test => {
          const result = testResults[test.id]
          const isRunning = runningTest === test.id
          
          return (
            <div key={test.id} className="bg-gray-800 rounded-2xl p-6 border border-gray-700">
              <div className="flex items-start justify-between mb-4">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    {test.persona && <span className="text-xl">{test.persona}</span>}
                    <h4 className="text-lg font-semibold">{test.name}</h4>
                    <span className="px-2 py-0.5 bg-gray-700 rounded text-xs text-gray-400">{test.category}</span>
                    {test.difficulty && (
                      <span className={`px-2 py-0.5 rounded text-xs ${
                        test.difficulty === 'expert' ? 'bg-purple-500/20 text-purple-400' :
                        test.difficulty === 'advanced' ? 'bg-blue-500/20 text-blue-400' :
                        'bg-green-500/20 text-green-400'
                      }`}>🎯 {test.difficulty}</span>
                    )}
                    {test.severity && (
                      <span className={`px-2 py-0.5 rounded text-xs ${
                        test.severity === 'critical' ? 'bg-red-500/20 text-red-400' :
                        test.severity === 'warning' ? 'bg-yellow-500/20 text-yellow-400' :
                        'bg-blue-500/20 text-blue-400'
                      }`}>{test.severity}</span>
                    )}
                    {test.benchmark && (
                      <span className="px-2 py-0.5 bg-yellow-500/20 text-yellow-400 rounded text-xs">
                        ⚡ {test.benchmark.target}{test.benchmark.unit}
                      </span>
                    )}
                  </div>
                  <p className="text-sm text-gray-300 mb-2">{test.prompt}</p>
                  <div className="flex items-center gap-4 text-xs">
                    <p className="text-gray-500">
                      <span className="text-gray-400">Expected:</span> {test.expected}
                    </p>
                    {test.benchmark && (
                      <p className="text-yellow-400">
                        <span className="text-gray-400">Target:</span> {test.benchmark.type === 'latency' ? '<' : '>'}{test.benchmark.target}{test.benchmark.unit}
                      </p>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => runTest(test.id, test.prompt)}
                  disabled={isRunning || allTestsRunning}
                  className={`px-4 py-2 rounded-lg font-medium transition flex items-center gap-2 ${
                    isRunning ? 'bg-blue-500/20 text-blue-400' :
                    result?.success ? 'bg-green-500 text-white hover:bg-green-600' :
                    result?.error ? 'bg-red-500 text-white hover:bg-red-600' :
                    'bg-blue-500 text-white hover:bg-blue-600'
                  } disabled:opacity-50`}
                >
                  {isRunning ? (
                    <><span className="animate-spin">⚙️</span> Running...</>
                  ) : result ? (
                    result.success ? '✅ Passed' : '❌ Failed'
                  ) : (
                    '▶️ Run Test'
                  )}
                </button>
              </div>
              
              {result && (
                <div className={`mt-4 p-4 rounded-xl border ${
                  result.success 
                    ? 'bg-green-500/10 border-green-500/30' 
                    : 'bg-red-500/10 border-red-500/30'
                }`}>
                  <div className="flex items-center justify-between mb-2">
                    <span className={`font-medium ${result.success ? 'text-green-400' : 'text-red-400'}`}>
                      {result.success ? '✅ Test Passed' : '❌ Test Failed'}
                    </span>
                    <span className="text-xs text-gray-400">
                      {new Date(result.timestamp).toLocaleTimeString()}
                      {result.latency > 0 && ` • ${result.latency}ms`}
                    </span>
                  </div>
                  <p className="text-sm text-gray-300 whitespace-pre-wrap max-h-40 overflow-y-auto">
                    {typeof result.response === 'string' 
                      ? result.response.substring(0, 500) + (result.response.length > 500 ? '...' : '')
                      : JSON.stringify(result.response, null, 2).substring(0, 500)
                    }
                  </p>
                </div>
              )}
            </div>
          )
        })}
      </div>
    )
  }

  const passRate = getPassRate()

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-2xl font-bold">🧪 Platform Validation Tests</h2>
          <p className="text-gray-400 text-sm mt-1">Comprehensive system testing across all layers</p>
        </div>
        <div className="flex items-center gap-4">
          {passRate !== null && (
            <div className={`px-4 py-2 rounded-lg ${
              passRate >= 80 ? 'bg-green-500/20 text-green-400' :
              passRate >= 50 ? 'bg-yellow-500/20 text-yellow-400' :
              'bg-red-500/20 text-red-400'
            }`}>
              <span className="font-bold">{passRate}%</span> Pass Rate
            </div>
          )}
          {activeCategory !== 'metrics' && (
            <button
              onClick={runAllTests}
              disabled={allTestsRunning}
              className="px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-lg font-medium hover:from-blue-600 hover:to-purple-600 disabled:opacity-50 flex items-center gap-2"
            >
              {allTestsRunning ? (
                <><span className="animate-spin">⚙️</span> Running All...</>
              ) : (
                <>🚀 Run All Tests</>
              )}
            </button>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Category Sidebar */}
        <div className="lg:col-span-1">
          <div className="bg-gray-800 rounded-2xl p-4 border border-gray-700 space-y-2">
            {testCategories.map(cat => {
              const tests = allTests[cat.id]
              const completed = tests?.filter(t => testResults[t.id]).length || 0
              const total = tests?.length || 0
              
              return (
                <button
                  key={cat.id}
                  onClick={() => setActiveCategory(cat.id)}
                  className={`w-full flex items-center justify-between px-4 py-3 rounded-xl transition ${
                    activeCategory === cat.id
                      ? 'bg-blue-500/20 border border-blue-500/30 text-white'
                      : 'text-gray-400 hover:bg-gray-700 hover:text-white'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{cat.icon}</span>
                    <span className="text-sm font-medium">{cat.name}</span>
                  </div>
                  {cat.id !== 'metrics' && completed > 0 && (
                    <span className="text-xs bg-gray-700 px-2 py-1 rounded">
                      {completed}/{total}
                    </span>
                  )}
                </button>
              )
            })}
          </div>

          {/* Execution Protocol */}
          <div className="mt-4 bg-gradient-to-br from-purple-500/20 to-blue-500/20 rounded-2xl p-4 border border-purple-500/30">
            <h4 className="font-semibold mb-2">🚀 Execution Protocol</h4>
            <ol className="text-xs text-gray-300 space-y-1">
              <li>1. Start with City Brain tests</li>
              <li>2. Run Persona validations</li>
              <li>3. Spatial & Infrastructure</li>
              <li>4. Narrative stress tests</li>
              <li>5. Technical failure scenarios</li>
              <li>6. Review metrics dashboard</li>
            </ol>
          </div>

          {/* Validation Sources */}
          <div className="mt-4 bg-gray-800 rounded-2xl p-4 border border-gray-700">
            <h4 className="font-semibold mb-2 text-sm">📚 Validation Sources</h4>
            <ul className="text-xs text-gray-400 space-y-1">
              <li>• BBMP transaction data (2019-2024)</li>
              <li>• KSDRF flood risk maps</li>
              <li>• BMRCL metro ridership data</li>
              <li>• Census 2021 demographics</li>
            </ul>
          </div>
        </div>

        {/* Test List */}
        <div className="lg:col-span-3">
          {renderTests()}
        </div>
      </div>

      {/* Test History */}
      {testHistory.length > 0 && (
        <div className="mt-8">
          <h3 className="text-lg font-semibold mb-4">📜 Recent Test History</h3>
          <div className="bg-gray-800 rounded-2xl border border-gray-700 overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-700/50">
                <tr>
                  <th className="text-left px-4 py-3 text-sm text-gray-400">Test</th>
                  <th className="text-left px-4 py-3 text-sm text-gray-400">Status</th>
                  <th className="text-left px-4 py-3 text-sm text-gray-400">Time</th>
                  <th className="text-left px-4 py-3 text-sm text-gray-400">Latency</th>
                </tr>
              </thead>
              <tbody>
                {testHistory.slice(0, 10).map((result, i) => (
                  <tr key={i} className="border-t border-gray-700">
                    <td className="px-4 py-3 text-sm">{result.testId}</td>
                    <td className="px-4 py-3">
                      <span className={`px-2 py-1 rounded text-xs ${
                        result.success ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                      }`}>
                        {result.success ? 'Passed' : 'Failed'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-400">
                      {new Date(result.timestamp).toLocaleTimeString()}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-400">
                      {result.latency > 0 ? `${result.latency}ms` : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

// Cloud Services Tab - Complete configuration UI
function CloudServicesTab() {
  const [activeService, setActiveService] = useState('supabase')
  const [settings, setSettings] = useState({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState({})
  const [testResults, setTestResults] = useState({})
  const [successMessage, setSuccessMessage] = useState('')

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

  useEffect(() => {
    fetchAllSettings()
  }, [])

  const fetchAllSettings = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_URL}/api/settings/all`)
      const data = await res.json()
      if (data.success) {
        setSettings(data.settings)
      }
    } catch (err) {
      console.error('Error fetching settings:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleInputChange = (service, field, value) => {
    setSettings(prev => ({
      ...prev,
      [service]: {
        ...prev[service],
        [field]: value
      }
    }))
  }

  const saveSettings = async (service) => {
    setSaving(true)
    try {
      const res = await fetch(`${API_URL}/api/settings/${service}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ settings: settings[service] })
      })
      const data = await res.json()
      
      if (data.success) {
        setSuccessMessage(`${service} settings saved successfully!`)
        setTimeout(() => setSuccessMessage(''), 3000)
      }
    } catch (err) {
      console.error('Error saving settings:', err)
    } finally {
      setSaving(false)
    }
  }

  const testConnection = async (service) => {
    setTesting(prev => ({ ...prev, [service]: true }))
    try {
      const res = await fetch(`${API_URL}/api/settings/${service}/test`, {
        method: 'POST'
      })
      const data = await res.json()
      setTestResults(prev => ({ ...prev, [service]: data }))
    } catch (err) {
      setTestResults(prev => ({ ...prev, [service]: { success: false, message: 'Connection failed' } }))
    } finally {
      setTesting(prev => ({ ...prev, [service]: false }))
    }
  }

  const services = [
    { id: 'supabase', name: 'Supabase', icon: '🗄️', color: 'emerald', desc: 'PostgreSQL Database' },
    { id: 'upstash', name: 'Upstash Redis', icon: '⚡', color: 'green', desc: 'Cache & Rate Limiting' },
    { id: 'cloudflare_r2', name: 'Cloudflare R2', icon: '☁️', color: 'orange', desc: 'Object Storage' },
    { id: 'openrouter', name: 'OpenRouter', icon: '🤖', color: 'purple', desc: 'LLM Gateway' },
    { id: 'mappls', name: 'Mappls', icon: '🗺️', color: 'blue', desc: 'Maps & Geocoding' },
    { id: 'pinecone', name: 'Pinecone', icon: '🌲', color: 'cyan', desc: 'Vector Database' },
    { id: 'apify', name: 'Apify', icon: '🕷️', color: 'red', desc: 'Web Scraping' },
    { id: 'deepgram', name: 'Deepgram', icon: '🎙️', color: 'pink', desc: 'Voice AI (STT/TTS)' },
    { id: 'huggingface', name: 'HuggingFace', icon: '🤗', color: 'yellow', desc: 'ML Models' }
  ]

  const renderServiceForm = () => {
    const service = services.find(s => s.id === activeService)
    if (!service) return null

    const config = settings[activeService] || {}
    const testResult = testResults[activeService]

    return (
      <div className="bg-gray-800 rounded-2xl p-6 border border-gray-700">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <span className="text-3xl">{service.icon}</span>
            <div>
              <h3 className="text-xl font-bold">{service.name}</h3>
              <p className="text-sm text-gray-400">Configure API credentials</p>
            </div>
          </div>
          <button
            onClick={() => testConnection(activeService)}
            disabled={testing[activeService]}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 flex items-center gap-2"
          >
            {testing[activeService] ? (
              <><span className="animate-spin">⚙️</span> Testing...</>
            ) : (
              <>🔍 Test Connection</>
            )}
          </button>
        </div>

        {testResult && (
          <div className={`mb-4 p-4 rounded-xl border ${
            testResult.success 
              ? 'bg-green-500/10 border-green-500/30 text-green-400'
              : 'bg-red-500/10 border-red-500/30 text-red-400'
          }`}>
            <div className="flex items-center gap-2">
              <span>{testResult.success ? '✅' : '❌'}</span>
              <span className="font-medium">{testResult.message}</span>
            </div>
            {testResult.details && (
              <div className="mt-2 text-sm">
                {Object.entries(testResult.details).map(([key, value]) => (
                  <div key={key}>
                    <span className="opacity-70">{key}:</span> {JSON.stringify(value)}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        <div className="space-y-4">
          {activeService === 'supabase' && (
            <>
              <div>
                <label className="block text-sm text-gray-400 mb-2">Project URL</label>
                <input
                  type="text"
                  value={config.url || ''}
                  onChange={(e) => handleInputChange('supabase', 'url', e.target.value)}
                  placeholder="https://[PROJECT-REF].supabase.co"
                  className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl text-white focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">Database URL (Connection Pooling)</label>
                <input
                  type="text"
                  value={config.database_url || ''}
                  onChange={(e) => handleInputChange('supabase', 'database_url', e.target.value)}
                  placeholder="postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:6543/postgres"
                  className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl text-white focus:border-blue-500 focus:outline-none"
                />
                {typeof config.database_url === 'string' && config.database_url.includes('db.') && config.database_url.includes('.supabase.co') && (
                  <p className="mt-2 text-xs text-yellow-400">
                    Use the Supabase <span className="font-semibold">Connection Pooling</span> URL (pooler host on port 6543). The direct host <span className="font-mono">db.&lt;ref&gt;.supabase.co</span> often fails on some networks.
                  </p>
                )}
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">Anon Key (Public)</label>
                <input
                  type="password"
                  value={config.anon_key || ''}
                  onChange={(e) => handleInputChange('supabase', 'anon_key', e.target.value)}
                  placeholder="eyJhbGc..."
                  className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl text-white focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">Service Role Key (Secret)</label>
                <input
                  type="password"
                  value={config.service_key || ''}
                  onChange={(e) => handleInputChange('supabase', 'service_key', e.target.value)}
                  placeholder="eyJhbGc..."
                  className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl text-white focus:border-blue-500 focus:outline-none"
                />
              </div>
            </>
          )}

          {activeService === 'upstash' && (
            <>
              <div>
                <label className="block text-sm text-gray-400 mb-2">Redis URL</label>
                <input
                  type="text"
                  value={config.redis_url || ''}
                  onChange={(e) => handleInputChange('upstash', 'redis_url', e.target.value)}
                  placeholder="redis://default:[PASSWORD]@[ENDPOINT].upstash.io:6379"
                  className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl text-white focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">REST API URL</label>
                <input
                  type="text"
                  value={config.rest_url || ''}
                  onChange={(e) => handleInputChange('upstash', 'rest_url', e.target.value)}
                  placeholder="https://[ENDPOINT].upstash.io"
                  className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl text-white focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">REST API Token</label>
                <input
                  type="password"
                  value={config.rest_token || ''}
                  onChange={(e) => handleInputChange('upstash', 'rest_token', e.target.value)}
                  placeholder="AXXx..."
                  className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl text-white focus:border-blue-500 focus:outline-none"
                />
              </div>
            </>
          )}

          {activeService === 'cloudflare_r2' && (
            <>
              <div>
                <label className="block text-sm text-gray-400 mb-2">Account ID</label>
                <input
                  type="text"
                  value={config.account_id || ''}
                  onChange={(e) => handleInputChange('cloudflare_r2', 'account_id', e.target.value)}
                  placeholder="Your Cloudflare Account ID"
                  className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl text-white focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">Access Key ID</label>
                <input
                  type="text"
                  value={config.access_key_id || ''}
                  onChange={(e) => handleInputChange('cloudflare_r2', 'access_key_id', e.target.value)}
                  placeholder="Access Key ID"
                  className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl text-white focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">Secret Access Key</label>
                <input
                  type="password"
                  value={config.secret_access_key || ''}
                  onChange={(e) => handleInputChange('cloudflare_r2', 'secret_access_key', e.target.value)}
                  placeholder="Secret Access Key"
                  className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl text-white focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">Bucket Name</label>
                <input
                  type="text"
                  value={config.bucket_name || 'valora-storage'}
                  onChange={(e) => handleInputChange('cloudflare_r2', 'bucket_name', e.target.value)}
                  placeholder="valora-storage"
                  className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl text-white focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">Endpoint URL</label>
                <input
                  type="text"
                  value={config.endpoint || ''}
                  onChange={(e) => handleInputChange('cloudflare_r2', 'endpoint', e.target.value)}
                  placeholder="https://[ACCOUNT_ID].r2.cloudflarestorage.com"
                  className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl text-white focus:border-blue-500 focus:outline-none"
                />
              </div>
            </>
          )}

          {activeService === 'openrouter' && (
            <>
              <div>
                <label className="block text-sm text-gray-400 mb-2">API Key</label>
                <input
                  type="password"
                  value={config.api_key || ''}
                  onChange={(e) => handleInputChange('openrouter', 'api_key', e.target.value)}
                  placeholder="sk-or-v1-..."
                  className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl text-white focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">Default Model</label>
                <select
                  value={config.model || 'anthropic/claude-3-haiku'}
                  onChange={(e) => handleInputChange('openrouter', 'model', e.target.value)}
                  className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl text-white focus:border-blue-500 focus:outline-none"
                >
                  <option value="anthropic/claude-3-haiku">Claude 3 Haiku</option>
                  <option value="anthropic/claude-3-5-sonnet">Claude 3.5 Sonnet</option>
                  <option value="openai/gpt-4o">GPT-4o</option>
                  <option value="google/gemini-pro">Gemini Pro</option>
                  <option value="meta-llama/llama-3.2-3b-instruct:free">Llama 3.2 3B (Free)</option>
                </select>
              </div>
            </>
          )}

          {activeService === 'mappls' && (
            <>
              <div>
                <label className="block text-sm text-gray-400 mb-2">API Key</label>
                <input
                  type="password"
                  value={config.api_key || ''}
                  onChange={(e) => handleInputChange('mappls', 'api_key', e.target.value)}
                  placeholder="Your Mappls API Key"
                  className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl text-white focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">Vite API Key (Frontend)</label>
                <input
                  type="password"
                  value={config.vite_api_key || ''}
                  onChange={(e) => handleInputChange('mappls', 'vite_api_key', e.target.value)}
                  placeholder="Same as API Key"
                  className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl text-white focus:border-blue-500 focus:outline-none"
                />
              </div>
            </>
          )}

          {activeService === 'pinecone' && (
            <>
              <div>
                <label className="block text-sm text-gray-400 mb-2">API Key</label>
                <input
                  type="password"
                  value={config.api_key || ''}
                  onChange={(e) => handleInputChange('pinecone', 'api_key', e.target.value)}
                  placeholder="pcsk_..."
                  className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl text-white focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">Environment</label>
                <input
                  type="text"
                  value={config.environment || 'us-west1-gcp-free'}
                  onChange={(e) => handleInputChange('pinecone', 'environment', e.target.value)}
                  placeholder="us-west1-gcp-free"
                  className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl text-white focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">Index Name</label>
                <input
                  type="text"
                  value={config.index || 'valora-realestate'}
                  onChange={(e) => handleInputChange('pinecone', 'index', e.target.value)}
                  placeholder="valora-realestate"
                  className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl text-white focus:border-blue-500 focus:outline-none"
                />
              </div>
            </>
          )}

          {activeService === 'apify' && (
            <div>
              <label className="block text-sm text-gray-400 mb-2">API Token</label>
              <input
                type="password"
                value={config.api_token || ''}
                onChange={(e) => handleInputChange('apify', 'api_token', e.target.value)}
                placeholder="apify_api_..."
                className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl text-white focus:border-blue-500 focus:outline-none"
              />
            </div>
          )}

          {activeService === 'deepgram' && (
            <>
              <div>
                <label className="block text-sm text-gray-400 mb-2">API Key</label>
                <input
                  type="password"
                  value={config.api_key || ''}
                  onChange={(e) => handleInputChange('deepgram', 'api_key', e.target.value)}
                  placeholder="Your Deepgram API Key"
                  className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl text-white focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">Default Language</label>
                <select
                  value={config.language || 'en-IN'}
                  onChange={(e) => handleInputChange('deepgram', 'language', e.target.value)}
                  className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl text-white focus:border-blue-500 focus:outline-none"
                >
                  <option value="en-IN">English (India)</option>
                  <option value="en-US">English (US)</option>
                  <option value="hi">Hindi</option>
                  <option value="ta">Tamil</option>
                  <option value="te">Telugu</option>
                  <option value="kn">Kannada</option>
                  <option value="mr">Marathi</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">Voice Model</label>
                <select
                  value={config.model || 'nova-2'}
                  onChange={(e) => handleInputChange('deepgram', 'model', e.target.value)}
                  className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl text-white focus:border-blue-500 focus:outline-none"
                >
                  <option value="nova-2">Nova 2 (Best Accuracy)</option>
                  <option value="nova-2-general">Nova 2 General</option>
                  <option value="nova-2-meeting">Nova 2 Meeting</option>
                  <option value="nova-2-phonecall">Nova 2 Phone Call</option>
                  <option value="enhanced">Enhanced</option>
                  <option value="base">Base</option>
                </select>
              </div>
              <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-xl">
                <p className="text-sm text-blue-400">🎙️ <strong>Voice Features:</strong></p>
                <ul className="text-xs text-gray-400 mt-2 space-y-1">
                  <li>• Real-time speech-to-text transcription</li>
                  <li>• Text-to-speech synthesis</li>
                  <li>• Multi-language support (Indian languages)</li>
                  <li>• Voice-enabled property search</li>
                </ul>
              </div>
            </>
          )}

          {activeService === 'huggingface' && (
            <>
              <div>
                <label className="block text-sm text-gray-400 mb-2">API Key</label>
                <input
                  type="password"
                  value={config.api_key || ''}
                  onChange={(e) => handleInputChange('huggingface', 'api_key', e.target.value)}
                  placeholder="hf_..."
                  className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl text-white focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-2">Embedding Model</label>
                <input
                  type="text"
                  value={config.embedding_model || 'sentence-transformers/all-MiniLM-L6-v2'}
                  onChange={(e) => handleInputChange('huggingface', 'embedding_model', e.target.value)}
                  placeholder="sentence-transformers/all-MiniLM-L6-v2"
                  className="w-full px-4 py-3 bg-gray-700 border border-gray-600 rounded-xl text-white focus:border-blue-500 focus:outline-none"
                />
              </div>
              <div className="p-4 bg-yellow-500/10 border border-yellow-500/30 rounded-xl">
                <p className="text-sm text-yellow-400">🤗 <strong>HuggingFace Features:</strong></p>
                <ul className="text-xs text-gray-400 mt-2 space-y-1">
                  <li>• Text embeddings for semantic search</li>
                  <li>• Property description analysis</li>
                  <li>• Sentiment analysis for reviews</li>
                  <li>• Named entity recognition</li>
                </ul>
              </div>
            </>
          )}

          <button
            onClick={() => saveSettings(activeService)}
            disabled={saving}
            className="w-full py-3 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-xl font-semibold hover:from-blue-600 hover:to-purple-600 disabled:opacity-50 transition"
          >
            {saving ? 'Saving...' : '💾 Save Configuration'}
          </button>
        </div>
      </div>
    )
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-2xl font-bold">☁️ Cloud Services Configuration</h2>
          <p className="text-gray-400 text-sm mt-1">Manage all your cloud service credentials in one place</p>
        </div>
        {successMessage && (
          <div className="bg-green-500/20 border border-green-500/30 text-green-400 px-4 py-2 rounded-lg">
            ✅ {successMessage}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Service List */}
        <div className="lg:col-span-1">
          <div className="bg-gray-800 rounded-2xl p-4 border border-gray-700 space-y-2">
            {services.map(service => (
              <button
                key={service.id}
                onClick={() => setActiveService(service.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl transition ${
                  activeService === service.id
                    ? 'bg-blue-500/20 border border-blue-500/30 text-white'
                    : 'text-gray-400 hover:bg-gray-700 hover:text-white'
                }`}
              >
                <span className="text-2xl">{service.icon}</span>
                <div className="text-left flex-1">
                  <p className="font-medium text-sm">{service.name}</p>
                  <p className="text-xs text-gray-500">{service.desc}</p>
                  {testResults[service.id] && (
                    <span className={`text-xs ${
                      testResults[service.id].success ? 'text-green-400' : 'text-red-400'
                    }`}>
                      {testResults[service.id].success ? '✓ Connected' : '✗ Failed'}
                    </span>
                  )}
                </div>
              </button>
            ))}
          </div>

          <div className="mt-4 bg-gradient-to-br from-blue-500/20 to-purple-500/20 rounded-2xl p-4 border border-blue-500/30">
            <p className="text-sm text-gray-300">💡 <strong>Pro Tip:</strong> Test connections after saving to verify your credentials.</p>
          </div>
        </div>

        {/* Service Configuration Form */}
        <div className="lg:col-span-3">
          {loading ? (
            <div className="flex items-center justify-center h-64 bg-gray-800 rounded-2xl border border-gray-700">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
            </div>
          ) : (
            renderServiceForm()
          )}
        </div>
      </div>
    </div>
  )
}

// Settings Tab
function SettingsTab() {
  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Settings</h2>
      
      <div className="space-y-6">
        <div className="bg-gray-800 rounded-2xl p-6 border border-gray-700">
          <h3 className="text-lg font-semibold mb-4">API Configuration</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">OpenRouter API Key</label>
              <input type="password" value="sk-or-v1-xxxxxxxxxx" readOnly className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2" />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Mappls API Key</label>
              <input type="password" value="xxxxxxxxxx" readOnly className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-2" />
            </div>
          </div>
        </div>

        <div className="bg-gray-800 rounded-2xl p-6 border border-gray-700">
          <h3 className="text-lg font-semibold mb-4">System Settings</h3>
          <div className="space-y-4">
            {[
              { name: 'Auto Model Retraining', desc: 'Automatically retrain models weekly', enabled: true },
              { name: 'API Rate Limiting', desc: 'Limit requests per user per minute', enabled: true },
              { name: 'Usage Alerts', desc: 'Send alerts when credits are low', enabled: true },
              { name: 'Debug Mode', desc: 'Enable detailed logging', enabled: false }
            ].map((setting, i) => (
              <div key={i} className="flex justify-between items-center py-2">
                <div>
                  <p className="font-medium">{setting.name}</p>
                  <p className="text-sm text-gray-400">{setting.desc}</p>
                </div>
                <button className={`w-12 h-6 rounded-full relative transition ${setting.enabled ? 'bg-blue-500' : 'bg-gray-600'}`}>
                  <span className={`absolute w-4 h-4 bg-white rounded-full top-1 transition ${setting.enabled ? 'right-1' : 'left-1'}`}></span>
                </button>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-gray-800 rounded-2xl p-6 border border-gray-700">
          <h3 className="text-lg font-semibold mb-4">Danger Zone</h3>
          <div className="space-y-4">
            <div className="flex justify-between items-center">
              <div>
                <p className="font-medium text-red-400">Reset All API Keys</p>
                <p className="text-sm text-gray-400">Invalidate all existing API keys</p>
              </div>
              <button className="px-4 py-2 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30">
                Reset Keys
              </button>
            </div>
            <div className="flex justify-between items-center">
              <div>
                <p className="font-medium text-red-400">Clear All Data</p>
                <p className="text-sm text-gray-400">Remove all cached and processed data</p>
              </div>
              <button className="px-4 py-2 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30">
                Clear Data
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// Data Layer Tab - Comprehensive data monitoring and management
function DataLayerTab() {
  const [dataView, setDataView] = useState('overview')
  const [sources, setSources] = useState([])
  const [stats, setStats] = useState(null)
  const [jobs, setJobs] = useState([])
  const [issues, setIssues] = useState([])
  const [uploads, setUploads] = useState([])
  const [loading, setLoading] = useState(true)
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [showAddSourceModal, setShowAddSourceModal] = useState(false)
  
  // Scraping state
  const [schedulerRunning, setSchedulerRunning] = useState(true)
  const [runningJob, setRunningJob] = useState(null)
  const [scrapingJobs, setScrapingJobs] = useState([])

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

  useEffect(() => {
    fetchDataLayerData()
  }, [])

  const fetchDataLayerData = async () => {
    setLoading(true)
    try {
      // Try to fetch from API, fallback to mock data
      const res = await fetch(`${API_URL}/api/data-layer/dashboard`)
      if (res.ok) {
        const data = await res.json()
        setSources(data.sources || [])
        setStats(data.statistics || getMockStats())
        setJobs(data.recent_jobs || [])
        setIssues(data.open_issues || [])
        setUploads(data.recent_uploads || [])
      } else {
        // Use mock data
        loadMockData()
      }
    } catch (err) {
      console.log('Using mock data for data layer')
      loadMockData()
    }
    setLoading(false)
  }

  const loadMockData = () => {
    setSources(getMockSources())
    setStats(getMockStats())
    setJobs(getMockJobs())
    setIssues(getMockIssues())
    setUploads(getMockUploads())
    setScrapingJobs(getMockScrapingJobs())
  }
  
  const getMockScrapingJobs = () => [
    { id: 'scrape_001', name: 'Bangalore Localities - Google Maps', source: 'google_maps', status: 'scheduled', frequency: 'weekly', cron: '0 2 * * 0', nextRun: '2024-12-22 02:00', lastRun: '2024-12-15 02:15', runCount: 12, successCount: 11, records: 8450, enabled: true },
    { id: 'scrape_002', name: 'Bangalore Infrastructure POIs', source: 'google_maps', status: 'scheduled', frequency: 'monthly', cron: '0 3 1 * *', nextRun: '2025-01-01 03:00', lastRun: '2024-12-01 03:22', runCount: 3, successCount: 3, records: 4520, enabled: true },
    { id: 'scrape_003', name: 'Real Estate News', source: 'news_articles', status: 'scheduled', frequency: 'daily', cron: '0 6 * * *', nextRun: '2024-12-19 06:00', lastRun: '2024-12-18 06:05', runCount: 89, successCount: 85, records: 6780, enabled: true },
    { id: 'scrape_004', name: 'Property Price Updates', source: 'property_listings', status: 'scheduled', frequency: 'daily', cron: '0 4 * * *', nextRun: '2024-12-19 04:00', lastRun: '2024-12-18 04:12', runCount: 52, successCount: 49, records: 4810, enabled: true }
  ]
  
  const handleRunScrapingJob = async (jobId) => {
    setRunningJob(jobId)
    try {
      await fetch(`${API_URL}/api/scraping/jobs/${jobId}/run`, { method: 'POST' })
    } catch (e) { console.log('Using mock for scraping job run') }
    setTimeout(() => setRunningJob(null), 3000)
  }
  
  const toggleScheduler = async () => {
    try {
      await fetch(`${API_URL}/api/scraping/scheduler/${schedulerRunning ? 'stop' : 'start'}`, { method: 'POST' })
    } catch (e) { console.log('Using mock for scheduler toggle') }
    setSchedulerRunning(!schedulerRunning)
  }

  const getMockSources = () => [
    { id: 'src-001', name: 'MagicBricks Scraper', source_type: 'scraped', category: 'properties', status: 'active', health_status: 'healthy', total_records: 45230, records_today: 156, avg_quality_score: 0.92, last_sync_at: new Date(Date.now() - 2*60*60*1000).toISOString(), city_id: 'bangalore' },
    { id: 'src-002', name: '99acres Scraper', source_type: 'scraped', category: 'properties', status: 'active', health_status: 'healthy', total_records: 38450, records_today: 203, avg_quality_score: 0.89, last_sync_at: new Date(Date.now() - 4*60*60*1000).toISOString(), city_id: 'bangalore' },
    { id: 'src-003', name: 'Manual Uploads', source_type: 'upload', category: 'properties', status: 'active', health_status: 'healthy', total_records: 12560, records_today: 0, avg_quality_score: 0.95, last_sync_at: new Date(Date.now() - 24*60*60*1000).toISOString() },
    { id: 'src-004', name: 'GIS Data Folder', source_type: 'folder', category: 'gis', status: 'active', health_status: 'healthy', total_records: 481, records_today: 0, avg_quality_score: 0.98, last_sync_at: new Date(Date.now() - 72*60*60*1000).toISOString(), city_id: 'bangalore' },
    { id: 'src-005', name: 'Mappls API', source_type: 'api', category: 'pois', status: 'active', health_status: 'healthy', total_records: 8920, records_today: 45, avg_quality_score: 0.97, last_sync_at: new Date().toISOString() },
    { id: 'src-006', name: 'Registry Transactions', source_type: 'upload', category: 'transactions', status: 'active', health_status: 'degraded', total_records: 23450, records_today: 0, avg_quality_score: 0.85, last_sync_at: new Date(Date.now() - 14*24*60*60*1000).toISOString(), city_id: 'bangalore' },
    { id: 'src-007', name: 'Real-time Price Stream', source_type: 'streaming', category: 'market', status: 'active', health_status: 'healthy', total_records: 156780, records_today: 2340, avg_quality_score: 0.91, last_sync_at: new Date().toISOString() },
    { id: 'src-008', name: 'Housing.com API', source_type: 'api', category: 'properties', status: 'paused', health_status: 'unknown', total_records: 5600, records_today: 0, avg_quality_score: 0.88, last_sync_at: new Date(Date.now() - 7*24*60*60*1000).toISOString(), city_id: 'bangalore' }
  ]

  const getMockStats = () => ({
    total_sources: 8,
    by_type: { scraped: 2, upload: 2, folder: 1, api: 2, streaming: 1 },
    by_status: { active: 7, paused: 1 },
    by_health: { healthy: 6, degraded: 1, unknown: 1 },
    total_records: 290871,
    records_today: 2744,
    active_jobs: 2,
    open_issues: 8
  })

  const getMockJobs = () => [
    { id: 'job-001', source_name: 'MagicBricks Scraper', source_type: 'scraped', job_type: 'incremental', status: 'completed', started_at: new Date(Date.now() - 2.25*60*60*1000).toISOString(), duration_seconds: 900, total_records: 156, success_records: 152, failed_records: 4, avg_quality_score: 0.92 },
    { id: 'job-002', source_name: '99acres Scraper', source_type: 'scraped', job_type: 'incremental', status: 'running', started_at: new Date(Date.now() - 12*60*1000).toISOString(), total_records: 250, processed_records: 178, success_records: 175, failed_records: 3 },
    { id: 'job-003', source_name: 'Manual Uploads', source_type: 'upload', job_type: 'upload', status: 'completed', started_at: new Date(Date.now() - 27*60*60*1000).toISOString(), duration_seconds: 900, total_records: 450, success_records: 448, failed_records: 2, avg_quality_score: 0.95 },
    { id: 'job-004', source_name: 'Real-time Price Stream', source_type: 'streaming', job_type: 'stream_batch', status: 'running', started_at: new Date(Date.now() - 6*60*60*1000).toISOString(), total_records: 2340, success_records: 2320, failed_records: 20 }
  ]

  const getMockIssues = () => [
    { id: 'issue-001', source_name: 'MagicBricks Scraper', issue_type: 'missing_field', severity: 'warning', field_name: 'pincode', message: 'Missing pincode for 15 properties in Whitefield', status: 'open', created_at: new Date(Date.now() - 2*60*60*1000).toISOString() },
    { id: 'issue-002', source_name: '99acres Scraper', issue_type: 'out_of_range', severity: 'error', field_name: 'price', message: '3 properties have zero price value', status: 'open', created_at: new Date(Date.now() - 4*60*60*1000).toISOString() },
    { id: 'issue-003', source_name: 'Registry Transactions', issue_type: 'duplicate', severity: 'warning', message: '12 duplicate transaction records detected', status: 'open', created_at: new Date(Date.now() - 24*60*60*1000).toISOString() },
    { id: 'issue-004', source_name: '99acres Scraper', issue_type: 'schema_mismatch', severity: 'error', message: 'New field "possession_date" not in schema', status: 'open', created_at: new Date(Date.now() - 6*60*60*1000).toISOString() }
  ]

  const getMockUploads = () => [
    { id: 'upl-001', original_filename: 'bangalore_properties_dec2024.csv', file_size: 2456000, file_type: 'csv', category: 'properties', city_id: 'bangalore', status: 'completed', record_count: 450, created_at: new Date(Date.now() - 24*60*60*1000).toISOString() },
    { id: 'upl-002', original_filename: 'ward_boundaries_v2.geojson', file_size: 1234000, file_type: 'geojson', category: 'gis', city_id: 'bangalore', status: 'completed', record_count: 198, created_at: new Date(Date.now() - 72*60*60*1000).toISOString() },
    { id: 'upl-003', original_filename: 'transactions_q4_2024.xlsx', file_size: 3890000, file_type: 'xlsx', category: 'transactions', city_id: 'bangalore', status: 'processing', record_count: 1250, created_at: new Date(Date.now() - 2*60*60*1000).toISOString() }
  ]

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
  }

  const formatTimeAgo = (dateStr) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diff = (now - date) / 1000
    if (diff < 60) return 'Just now'
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
    return `${Math.floor(diff / 86400)}d ago`
  }

  const getSourceTypeIcon = (type) => {
    const icons = { scraped: '🕷️', upload: '📤', folder: '📁', api: '🔌', streaming: '📡' }
    return icons[type] || '📦'
  }

  const getHealthColor = (status) => {
    const colors = { healthy: 'bg-green-500', degraded: 'bg-yellow-500', unhealthy: 'bg-red-500', unknown: 'bg-gray-500' }
    return colors[status] || 'bg-gray-500'
  }

  const getSeverityColor = (severity) => {
    const colors = { error: 'bg-red-500/20 text-red-400', warning: 'bg-yellow-500/20 text-yellow-400', info: 'bg-blue-500/20 text-blue-400' }
    return colors[severity] || 'bg-gray-500/20 text-gray-400'
  }

  const getStatusColor = (status) => {
    const colors = { active: 'bg-green-500/20 text-green-400', paused: 'bg-yellow-500/20 text-yellow-400', error: 'bg-red-500/20 text-red-400', completed: 'bg-green-500/20 text-green-400', running: 'bg-blue-500/20 text-blue-400', failed: 'bg-red-500/20 text-red-400', processing: 'bg-blue-500/20 text-blue-400' }
    return colors[status] || 'bg-gray-500/20 text-gray-400'
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-2xl font-bold">Data Layer</h2>
          <p className="text-gray-400 text-sm mt-1">Monitor and manage all data sources, uploads, and quality</p>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setShowUploadModal(true)} className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600 flex items-center gap-2">
            <span>📤</span> Upload Data
          </button>
          <button onClick={() => setShowAddSourceModal(true)} className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 flex items-center gap-2">
            <span>+</span> Add Source
          </button>
        </div>
      </div>

      {/* Sub-navigation */}
      <div className="flex gap-2 mb-6 flex-wrap">
        {['overview', 'sources', 'scraping', 'uploads', 'quality', 'jobs'].map(view => (
          <button
            key={view}
            onClick={() => setDataView(view)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition ${dataView === view ? 'bg-blue-500 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'}`}
          >
            {view === 'scraping' ? '🕷️ Scraping (Apify)' : view.charAt(0).toUpperCase() + view.slice(1)}
          </button>
        ))}
      </div>

      {/* Overview View */}
      {dataView === 'overview' && (
        <div>
          {/* Cloud Services Status Banner */}
          <div className="bg-gradient-to-r from-blue-500/20 to-purple-500/20 rounded-2xl p-6 border border-blue-500/30 mb-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold mb-1">☁️ Cloud Data Layer Active</h3>
                <p className="text-gray-400 text-sm">Using Supabase (Database), Upstash (Cache), Cloudflare R2 (Storage)</p>
              </div>
              <div className="flex gap-4">
                <div className="text-center">
                  <div className="w-3 h-3 bg-green-500 rounded-full mx-auto mb-1 animate-pulse"></div>
                  <span className="text-xs text-gray-400">Supabase</span>
                </div>
                <div className="text-center">
                  <div className="w-3 h-3 bg-green-500 rounded-full mx-auto mb-1 animate-pulse"></div>
                  <span className="text-xs text-gray-400">Redis</span>
                </div>
                <div className="text-center">
                  <div className="w-3 h-3 bg-green-500 rounded-full mx-auto mb-1 animate-pulse"></div>
                  <span className="text-xs text-gray-400">R2</span>
                </div>
              </div>
            </div>
          </div>

          {/* Stats Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700">
              <div className="flex items-center justify-between mb-2">
                <span className="text-3xl">🗄️</span>
                <span className="px-2 py-1 rounded-full text-xs bg-green-500/20 text-green-400">{stats?.by_status?.active || 0} active</span>
              </div>
              <h3 className="text-gray-400 text-sm">Data Sources</h3>
              <p className="text-2xl font-bold mt-1">{stats?.total_sources || 0}</p>
            </div>
            <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700">
              <div className="flex items-center justify-between mb-2">
                <span className="text-3xl">📊</span>
                <span className="px-2 py-1 rounded-full text-xs bg-blue-500/20 text-blue-400">+{(stats?.records_today || 0).toLocaleString()} today</span>
              </div>
              <h3 className="text-gray-400 text-sm">Total Records</h3>
              <p className="text-2xl font-bold mt-1">{(stats?.total_records || 0).toLocaleString()}</p>
            </div>
            <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700">
              <div className="flex items-center justify-between mb-2">
                <span className="text-3xl">⚡</span>
                <span className="px-2 py-1 rounded-full text-xs bg-purple-500/20 text-purple-400">{stats?.active_jobs || 0} running</span>
              </div>
              <h3 className="text-gray-400 text-sm">Active Jobs</h3>
              <p className="text-2xl font-bold mt-1">{jobs.filter(j => j.status === 'running').length}</p>
            </div>
            <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700">
              <div className="flex items-center justify-between mb-2">
                <span className="text-3xl">⚠️</span>
                <span className={`px-2 py-1 rounded-full text-xs ${issues.length > 5 ? 'bg-red-500/20 text-red-400' : 'bg-yellow-500/20 text-yellow-400'}`}>{issues.filter(i => i.severity === 'error').length} errors</span>
              </div>
              <h3 className="text-gray-400 text-sm">Open Issues</h3>
              <p className="text-2xl font-bold mt-1">{stats?.open_issues || issues.length}</p>
            </div>
          </div>

          {/* Source Types Breakdown */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
            <div className="bg-gray-800 rounded-2xl p-6 border border-gray-700">
              <h3 className="text-lg font-semibold mb-4">Sources by Type</h3>
              <div className="space-y-3">
                {Object.entries(stats?.by_type || {}).map(([type, count]) => (
                  <div key={type} className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <span className="text-xl">{getSourceTypeIcon(type)}</span>
                      <span className="capitalize">{type}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="w-32 h-2 bg-gray-700 rounded-full overflow-hidden">
                        <div className="h-full bg-blue-500" style={{ width: `${(count / stats?.total_sources) * 100}%` }}></div>
                      </div>
                      <span className="text-gray-400 w-8 text-right">{count}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-gray-800 rounded-2xl p-6 border border-gray-700">
              <h3 className="text-lg font-semibold mb-4">Health Status</h3>
              <div className="flex items-center justify-center gap-8">
                {Object.entries(stats?.by_health || {}).map(([status, count]) => (
                  <div key={status} className="text-center">
                    <div className={`w-16 h-16 rounded-full ${getHealthColor(status)} bg-opacity-20 flex items-center justify-center mx-auto mb-2`}>
                      <span className="text-2xl font-bold">{count}</span>
                    </div>
                    <span className="text-sm text-gray-400 capitalize">{status}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Recent Activity */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Recent Jobs */}
            <div className="bg-gray-800 rounded-2xl p-6 border border-gray-700">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold">Recent Jobs</h3>
                <button onClick={() => setDataView('jobs')} className="text-blue-400 text-sm hover:underline">View All →</button>
              </div>
              <div className="space-y-3">
                {jobs.slice(0, 4).map(job => (
                  <div key={job.id} className="flex items-center justify-between py-2 border-b border-gray-700 last:border-0">
                    <div className="flex items-center gap-3">
                      <span className="text-lg">{getSourceTypeIcon(job.source_type)}</span>
                      <div>
                        <p className="text-sm font-medium">{job.source_name}</p>
                        <p className="text-xs text-gray-400">{job.job_type} • {formatTimeAgo(job.started_at)}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <span className={`px-2 py-1 rounded-full text-xs ${getStatusColor(job.status)}`}>{job.status}</span>
                      <p className="text-xs text-gray-400 mt-1">{job.success_records?.toLocaleString() || 0} records</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Open Issues */}
            <div className="bg-gray-800 rounded-2xl p-6 border border-gray-700">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold">Open Issues</h3>
                <button onClick={() => setDataView('quality')} className="text-blue-400 text-sm hover:underline">View All →</button>
              </div>
              <div className="space-y-3">
                {issues.slice(0, 4).map(issue => (
                  <div key={issue.id} className="flex items-center justify-between py-2 border-b border-gray-700 last:border-0">
                    <div className="flex items-center gap-3">
                      <span className={`w-2 h-2 rounded-full ${issue.severity === 'error' ? 'bg-red-500' : issue.severity === 'warning' ? 'bg-yellow-500' : 'bg-blue-500'}`}></span>
                      <div>
                        <p className="text-sm">{issue.message}</p>
                        <p className="text-xs text-gray-400">{issue.source_name} • {formatTimeAgo(issue.created_at)}</p>
                      </div>
                    </div>
                    <span className={`px-2 py-1 rounded-full text-xs ${getSeverityColor(issue.severity)}`}>{issue.severity}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Sources View */}
      {dataView === 'sources' && (
        <div className="bg-gray-800 rounded-2xl border border-gray-700 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-700/50">
              <tr>
                <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Source</th>
                <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Type</th>
                <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Category</th>
                <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Records</th>
                <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Quality</th>
                <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Last Sync</th>
                <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Health</th>
                <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Actions</th>
              </tr>
            </thead>
            <tbody>
              {sources.map(source => (
                <tr key={source.id} className="border-t border-gray-700 hover:bg-gray-700/30">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <span className="text-xl">{getSourceTypeIcon(source.source_type)}</span>
                      <div>
                        <p className="font-medium">{source.name}</p>
                        <span className={`text-xs px-2 py-0.5 rounded ${getStatusColor(source.status)}`}>{source.status}</span>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-gray-400 capitalize">{source.source_type}</td>
                  <td className="px-6 py-4 text-gray-400 capitalize">{source.category}</td>
                  <td className="px-6 py-4">
                    <p className="font-medium">{source.total_records?.toLocaleString()}</p>
                    <p className="text-xs text-green-400">+{source.records_today?.toLocaleString()} today</p>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <div className="w-16 h-2 bg-gray-700 rounded-full overflow-hidden">
                        <div className={`h-full ${source.avg_quality_score >= 0.9 ? 'bg-green-500' : source.avg_quality_score >= 0.8 ? 'bg-yellow-500' : 'bg-red-500'}`} style={{ width: `${(source.avg_quality_score || 0) * 100}%` }}></div>
                      </div>
                      <span className="text-sm">{Math.round((source.avg_quality_score || 0) * 100)}%</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-gray-400">{formatTimeAgo(source.last_sync_at)}</td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <span className={`w-2.5 h-2.5 rounded-full ${getHealthColor(source.health_status)}`}></span>
                      <span className="text-sm capitalize">{source.health_status}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex gap-2">
                      <button className="px-3 py-1 bg-blue-500/20 text-blue-400 rounded-lg hover:bg-blue-500/30 text-sm">Sync</button>
                      <button className="px-3 py-1 bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600 text-sm">Config</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Scraping View (Apify) */}
      {dataView === 'scraping' && (
        <div>
          {/* Scheduler Status */}
          <div className={`mb-6 p-4 rounded-xl flex items-center justify-between ${schedulerRunning ? 'bg-green-500/10 border border-green-500/30' : 'bg-red-500/10 border border-red-500/30'}`}>
            <div className="flex items-center gap-3">
              <span className={`w-3 h-3 rounded-full ${schedulerRunning ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></span>
              <span className="font-medium">Scheduler:</span>
              <span className={schedulerRunning ? 'text-green-400' : 'text-red-400'}>{schedulerRunning ? 'Running' : 'Stopped'}</span>
              <span className="text-gray-500">|</span>
              <span className="text-sm text-gray-400">Apify API: Connected ✓</span>
            </div>
            <button onClick={toggleScheduler} className={`px-4 py-2 rounded-lg text-sm ${schedulerRunning ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30' : 'bg-green-500/20 text-green-400 hover:bg-green-500/30'}`}>
              {schedulerRunning ? '⏹ Stop' : '▶ Start'}
            </button>
          </div>

          {/* Scraping Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
              <p className="text-gray-400 text-sm">Scheduled Jobs</p>
              <p className="text-2xl font-bold">{scrapingJobs.length}</p>
            </div>
            <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
              <p className="text-gray-400 text-sm">Total Runs</p>
              <p className="text-2xl font-bold">{scrapingJobs.reduce((sum, j) => sum + j.runCount, 0)}</p>
            </div>
            <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
              <p className="text-gray-400 text-sm">Success Rate</p>
              <p className="text-2xl font-bold text-green-400">{Math.round((scrapingJobs.reduce((sum, j) => sum + j.successCount, 0) / Math.max(1, scrapingJobs.reduce((sum, j) => sum + j.runCount, 0))) * 100)}%</p>
            </div>
            <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
              <p className="text-gray-400 text-sm">Records Scraped</p>
              <p className="text-2xl font-bold">{scrapingJobs.reduce((sum, j) => sum + j.records, 0).toLocaleString()}</p>
            </div>
          </div>

          {/* Scraping Jobs Table */}
          <div className="bg-gray-800 rounded-2xl border border-gray-700 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-700 flex justify-between items-center">
              <h3 className="text-lg font-semibold">Scheduled Scraping Jobs</h3>
              <span className="text-sm text-gray-400">Cron-based scheduling via Apify</span>
            </div>
            <table className="w-full">
              <thead className="bg-gray-700/50">
                <tr>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium text-sm">Job Name</th>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium text-sm">Source</th>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium text-sm">Schedule</th>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium text-sm">Next Run</th>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium text-sm">Last Run</th>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium text-sm">Records</th>
                  <th className="text-left px-6 py-3 text-gray-400 font-medium text-sm">Actions</th>
                </tr>
              </thead>
              <tbody>
                {scrapingJobs.map(job => (
                  <tr key={job.id} className="border-t border-gray-700 hover:bg-gray-700/30">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${job.enabled ? 'bg-green-500' : 'bg-gray-500'}`}></span>
                        <span className="font-medium">{job.name}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-2 py-1 rounded text-xs ${job.source === 'google_maps' ? 'bg-blue-500/20 text-blue-400' : job.source === 'property_listings' ? 'bg-green-500/20 text-green-400' : 'bg-purple-500/20 text-purple-400'}`}>
                        {job.source.replace('_', ' ')}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div><span className="text-sm">{job.frequency}</span><p className="text-xs text-gray-500 font-mono">{job.cron}</p></div>
                    </td>
                    <td className="px-6 py-4 text-sm">{job.nextRun}</td>
                    <td className="px-6 py-4 text-sm text-gray-400">{job.lastRun}</td>
                    <td className="px-6 py-4">{job.records.toLocaleString()}</td>
                    <td className="px-6 py-4">
                      <button onClick={() => handleRunScrapingJob(job.id)} disabled={runningJob === job.id} className="px-3 py-1 bg-blue-500/20 text-blue-400 rounded-lg hover:bg-blue-500/30 text-sm disabled:opacity-50">
                        {runningJob === job.id ? '⏳ Running...' : '▶ Run Now'}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Uploads View */}
      {dataView === 'uploads' && (
        <div>
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-lg font-semibold">File Uploads</h3>
            <button onClick={() => setShowUploadModal(true)} className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600">Upload New File</button>
          </div>
          <div className="bg-gray-800 rounded-2xl border border-gray-700 overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-700/50">
                <tr>
                  <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Filename</th>
                  <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Type</th>
                  <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Category</th>
                  <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Size</th>
                  <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Records</th>
                  <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Status</th>
                  <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Uploaded</th>
                  <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Actions</th>
                </tr>
              </thead>
              <tbody>
                {uploads.map(upload => (
                  <tr key={upload.id} className="border-t border-gray-700 hover:bg-gray-700/30">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <span className="text-xl">{upload.file_type === 'csv' ? '📄' : upload.file_type === 'json' ? '📋' : upload.file_type === 'geojson' ? '🗺️' : upload.file_type === 'xlsx' ? '📊' : '📁'}</span>
                        <span className="font-medium truncate max-w-xs">{upload.original_filename}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-gray-400 uppercase text-sm">{upload.file_type}</td>
                    <td className="px-6 py-4 text-gray-400 capitalize">{upload.category}</td>
                    <td className="px-6 py-4 text-gray-400">{formatBytes(upload.file_size)}</td>
                    <td className="px-6 py-4">{upload.record_count?.toLocaleString() || '-'}</td>
                    <td className="px-6 py-4"><span className={`px-2 py-1 rounded-full text-xs ${getStatusColor(upload.status)}`}>{upload.status}</span></td>
                    <td className="px-6 py-4 text-gray-400">{formatTimeAgo(upload.created_at)}</td>
                    <td className="px-6 py-4">
                      <div className="flex gap-2">
                        {upload.status === 'uploaded' && <button className="px-3 py-1 bg-blue-500/20 text-blue-400 rounded-lg hover:bg-blue-500/30 text-sm">Process</button>}
                        <button className="px-3 py-1 bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600 text-sm">View</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Quality View */}
      {dataView === 'quality' && (
        <div>
          {/* Quality Stats */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
            <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
              <p className="text-gray-400 text-sm">Total Issues</p>
              <p className="text-2xl font-bold">{issues.length}</p>
            </div>
            <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
              <p className="text-gray-400 text-sm">Errors</p>
              <p className="text-2xl font-bold text-red-400">{issues.filter(i => i.severity === 'error').length}</p>
            </div>
            <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
              <p className="text-gray-400 text-sm">Warnings</p>
              <p className="text-2xl font-bold text-yellow-400">{issues.filter(i => i.severity === 'warning').length}</p>
            </div>
            <div className="bg-gray-800 rounded-xl p-4 border border-gray-700">
              <p className="text-gray-400 text-sm">Avg Quality</p>
              <p className="text-2xl font-bold text-green-400">91%</p>
            </div>
          </div>

          {/* Issues List */}
          <div className="bg-gray-800 rounded-2xl border border-gray-700 overflow-hidden">
            <table className="w-full">
              <thead className="bg-gray-700/50">
                <tr>
                  <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Severity</th>
                  <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Source</th>
                  <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Issue Type</th>
                  <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Message</th>
                  <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Created</th>
                  <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Actions</th>
                </tr>
              </thead>
              <tbody>
                {issues.map(issue => (
                  <tr key={issue.id} className="border-t border-gray-700 hover:bg-gray-700/30">
                    <td className="px-6 py-4"><span className={`px-3 py-1 rounded-full text-xs ${getSeverityColor(issue.severity)}`}>{issue.severity}</span></td>
                    <td className="px-6 py-4">{issue.source_name}</td>
                    <td className="px-6 py-4 text-gray-400 capitalize">{issue.issue_type?.replace(/_/g, ' ')}</td>
                    <td className="px-6 py-4 max-w-md truncate">{issue.message}</td>
                    <td className="px-6 py-4 text-gray-400">{formatTimeAgo(issue.created_at)}</td>
                    <td className="px-6 py-4">
                      <div className="flex gap-2">
                        <button className="px-3 py-1 bg-green-500/20 text-green-400 rounded-lg hover:bg-green-500/30 text-sm">Resolve</button>
                        <button className="px-3 py-1 bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600 text-sm">Ignore</button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Jobs View */}
      {dataView === 'jobs' && (
        <div className="bg-gray-800 rounded-2xl border border-gray-700 overflow-hidden">
          <table className="w-full">
            <thead className="bg-gray-700/50">
              <tr>
                <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Source</th>
                <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Job Type</th>
                <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Status</th>
                <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Progress</th>
                <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Duration</th>
                <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Quality</th>
                <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Started</th>
                <th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Actions</th>
              </tr>
            </thead>
            <tbody>
              {jobs.map(job => (
                <tr key={job.id} className="border-t border-gray-700 hover:bg-gray-700/30">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <span className="text-lg">{getSourceTypeIcon(job.source_type)}</span>
                      <span className="font-medium">{job.source_name}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-gray-400 capitalize">{job.job_type?.replace(/_/g, ' ')}</td>
                  <td className="px-6 py-4"><span className={`px-2 py-1 rounded-full text-xs ${getStatusColor(job.status)}`}>{job.status}</span></td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <div className="w-24 h-2 bg-gray-700 rounded-full overflow-hidden">
                        <div className="h-full bg-blue-500" style={{ width: `${((job.processed_records || job.success_records) / (job.total_records || 1)) * 100}%` }}></div>
                      </div>
                      <span className="text-sm text-gray-400">{job.success_records?.toLocaleString()}/{job.total_records?.toLocaleString()}</span>
                    </div>
                  </td>
                  <td className="px-6 py-4 text-gray-400">{job.duration_seconds ? `${Math.floor(job.duration_seconds / 60)}m ${job.duration_seconds % 60}s` : job.status === 'running' ? 'Running...' : '-'}</td>
                  <td className="px-6 py-4">{job.avg_quality_score ? `${Math.round(job.avg_quality_score * 100)}%` : '-'}</td>
                  <td className="px-6 py-4 text-gray-400">{formatTimeAgo(job.started_at)}</td>
                  <td className="px-6 py-4">
                    {job.status === 'running' ? (
                      <button className="px-3 py-1 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/30 text-sm">Cancel</button>
                    ) : (
                      <button className="px-3 py-1 bg-gray-700 text-gray-300 rounded-lg hover:bg-gray-600 text-sm">Details</button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-2xl p-6 w-full max-w-lg border border-gray-700">
            <h3 className="text-xl font-bold mb-4">Upload Data File</h3>
            <div className="space-y-4">
              <div className="border-2 border-dashed border-gray-600 rounded-xl p-8 text-center hover:border-blue-500 transition cursor-pointer">
                <span className="text-4xl mb-2 block">📤</span>
                <p className="text-gray-400">Drag & drop files here or click to browse</p>
                <p className="text-xs text-gray-500 mt-2">Supports: CSV, JSON, Excel, GeoJSON, Shapefile</p>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Category</label>
                <select className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white">
                  <option value="properties">Properties</option>
                  <option value="transactions">Transactions</option>
                  <option value="gis">GIS/Spatial</option>
                  <option value="pois">POIs</option>
                  <option value="market">Market Data</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">City (Optional)</label>
                <select className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white">
                  <option value="">All Cities</option>
                  <option value="bangalore">Bangalore</option>
                  <option value="mumbai">Mumbai</option>
                  <option value="delhi">Delhi</option>
                  <option value="hyderabad">Hyderabad</option>
                  <option value="chennai">Chennai</option>
                  <option value="pune">Pune</option>
                </select>
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button onClick={() => setShowUploadModal(false)} className="flex-1 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600">Cancel</button>
              <button className="flex-1 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">Upload</button>
            </div>
          </div>
        </div>
      )}

      {/* Add Source Modal */}
      {showAddSourceModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-gray-800 rounded-2xl p-6 w-full max-w-lg border border-gray-700">
            <h3 className="text-xl font-bold mb-4">Add Data Source</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm text-gray-400 mb-1">Source Name</label>
                <input type="text" placeholder="e.g., PropTiger API" className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white" />
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Source Type</label>
                <select className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white">
                  <option value="api">API</option>
                  <option value="scraped">Scraper</option>
                  <option value="folder">Folder Watch</option>
                  <option value="streaming">Stream</option>
                  <option value="upload">Manual Upload</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Category</label>
                <select className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white">
                  <option value="properties">Properties</option>
                  <option value="transactions">Transactions</option>
                  <option value="gis">GIS/Spatial</option>
                  <option value="pois">POIs</option>
                  <option value="market">Market Data</option>
                </select>
              </div>
              <div>
                <label className="block text-sm text-gray-400 mb-1">Sync Frequency</label>
                <select className="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white">
                  <option value="realtime">Real-time</option>
                  <option value="hourly">Hourly</option>
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="manual">Manual</option>
                </select>
              </div>
            </div>
            <div className="flex gap-3 mt-6">
              <button onClick={() => setShowAddSourceModal(false)} className="flex-1 py-2 bg-gray-700 text-white rounded-lg hover:bg-gray-600">Cancel</button>
              <button className="flex-1 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">Add Source</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// Knowledge Layer Tab - Database, Embeddings, Cache monitoring
function KnowledgeLayerTab() {
  const [dbStats, setDbStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    setDbStats({
      postgres: { status: 'healthy', tables: 12, rows: 156780, size: '2.4 GB', connections: 8 },
      postgis: { status: 'healthy', spatial_tables: 6, geometries: 45230 },
      pgvector: { status: 'healthy', embeddings: 89450, dimensions: 1536, indexes: 4 },
      cache: { status: 'healthy', hit_rate: 94.5, memory_used: '512 MB', keys: 15420 }
    })
    setLoading(false)
  }, [])

  if (loading) return <div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div></div>

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-2xl font-bold">Knowledge Layer</h2>
          <p className="text-gray-400 text-sm mt-1">Database, vector embeddings, and caching services</p>
        </div>
        <button className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">Refresh Stats</button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700">
          <div className="flex items-center justify-between mb-3"><span className="text-3xl">🐘</span><span className="px-2 py-1 rounded-full text-xs bg-green-500/20 text-green-400">healthy</span></div>
          <h3 className="text-gray-400 text-sm">PostgreSQL</h3>
          <p className="text-2xl font-bold mt-1">{dbStats?.postgres?.tables} Tables</p>
          <p className="text-xs text-gray-500 mt-1">{dbStats?.postgres?.rows?.toLocaleString()} rows • {dbStats?.postgres?.size}</p>
        </div>
        <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700">
          <div className="flex items-center justify-between mb-3"><span className="text-3xl">🗺️</span><span className="px-2 py-1 rounded-full text-xs bg-green-500/20 text-green-400">healthy</span></div>
          <h3 className="text-gray-400 text-sm">PostGIS (Spatial)</h3>
          <p className="text-2xl font-bold mt-1">{dbStats?.postgis?.spatial_tables} Tables</p>
          <p className="text-xs text-gray-500 mt-1">{dbStats?.postgis?.geometries?.toLocaleString()} geometries</p>
        </div>
        <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700">
          <div className="flex items-center justify-between mb-3"><span className="text-3xl">🧬</span><span className="px-2 py-1 rounded-full text-xs bg-green-500/20 text-green-400">healthy</span></div>
          <h3 className="text-gray-400 text-sm">pgvector (Embeddings)</h3>
          <p className="text-2xl font-bold mt-1">{(dbStats?.pgvector?.embeddings / 1000).toFixed(1)}K</p>
          <p className="text-xs text-gray-500 mt-1">{dbStats?.pgvector?.dimensions}d vectors • {dbStats?.pgvector?.indexes} indexes</p>
        </div>
        <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700">
          <div className="flex items-center justify-between mb-3"><span className="text-3xl">⚡</span><span className="px-2 py-1 rounded-full text-xs bg-green-500/20 text-green-400">{dbStats?.cache?.hit_rate}% hit</span></div>
          <h3 className="text-gray-400 text-sm">Cache (Redis)</h3>
          <p className="text-2xl font-bold mt-1">{(dbStats?.cache?.keys / 1000).toFixed(1)}K Keys</p>
          <p className="text-xs text-gray-500 mt-1">{dbStats?.cache?.memory_used} memory</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div className="bg-gray-800 rounded-2xl p-6 border border-gray-700">
          <h3 className="text-lg font-semibold mb-4">Knowledge Services</h3>
          <div className="space-y-3">
            {[
              { name: 'LocalityStateService', desc: 'Ward-level market snapshots', lastRun: '5m ago' },
              { name: 'PropertyGraphStore', desc: 'Property network relationships', lastRun: '2h ago' },
              { name: 'MarketTimeSeriesStore', desc: 'Historical price trends', lastRun: '1h ago' },
              { name: 'VectorStore (RAG)', desc: 'Document embeddings', lastRun: '30m ago' }
            ].map((svc, i) => (
              <div key={i} className="flex items-center justify-between py-2 border-b border-gray-700 last:border-0">
                <div className="flex items-center gap-3">
                  <span className="w-2 h-2 rounded-full bg-green-500"></span>
                  <div><p className="font-medium text-sm">{svc.name}</p><p className="text-xs text-gray-400">{svc.desc}</p></div>
                </div>
                <span className="text-xs text-gray-400">{svc.lastRun}</span>
              </div>
            ))}
          </div>
        </div>
        <div className="bg-gray-800 rounded-2xl p-6 border border-gray-700">
          <h3 className="text-lg font-semibold mb-4">Database Tables</h3>
          <div className="space-y-2 max-h-64 overflow-y-auto">
            {[
              { name: 'properties', rows: 45230, size: '890 MB', type: 'core' },
              { name: 'transactions', rows: 23450, size: '345 MB', type: 'core' },
              { name: 'pois', rows: 8920, size: '120 MB', type: 'spatial' },
              { name: 'property_spatial_features', rows: 45230, size: '234 MB', type: 'spatial' },
              { name: 'market_statistics', rows: 198, size: '12 MB', type: 'analytics' },
              { name: 'bbmp_wards', rows: 198, size: '45 MB', type: 'spatial' }
            ].map((tbl, i) => (
              <div key={i} className="flex items-center justify-between py-2 px-3 bg-gray-700/30 rounded-lg">
                <div className="flex items-center gap-2">
                  <span className="text-xs px-2 py-0.5 rounded bg-blue-500/20 text-blue-400">{tbl.type}</span>
                  <span className="text-sm font-mono">{tbl.name}</span>
                </div>
                <div className="flex items-center gap-4 text-xs text-gray-400"><span>{tbl.rows?.toLocaleString()} rows</span><span>{tbl.size}</span></div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

// Intelligence Layer Tab - AI Agents and ML Models
function IntelligenceLayerTab() {
  const [agentView, setAgentView] = useState('all')
  const agents = [
    { name: 'AVMAgent', stack: 'Valuation', status: 'active', accuracy: 94.2, predictions: 12450, file: 'avm_agent.py' },
    { name: 'DMPEEngine', stack: 'Valuation', status: 'active', accuracy: 92.8, predictions: 45230, file: 'dmpe_engine.py' },
    { name: 'ProphetAgent', stack: 'Forecasting', status: 'active', accuracy: 87.3, predictions: 5600, file: 'forecasting_agent.py' },
    { name: 'EnsembleForecaster', stack: 'Forecasting', status: 'active', accuracy: 91.2, predictions: 8900, file: 'forecasting_agent.py' },
    { name: 'GeospatialAgent', stack: 'Spatial', status: 'active', accuracy: null, predictions: 15600, file: 'geospatial_agent.py' },
    { name: 'GraphAgent', stack: 'Spatial', status: 'active', accuracy: null, predictions: 3400, file: 'graph_agent.py' },
    { name: 'MapAgent', stack: 'Spatial', status: 'active', accuracy: null, predictions: 23450, file: 'agent_implementations.py' },
    { name: 'MarketRiskAgent', stack: 'Risk', status: 'active', accuracy: 88.5, predictions: 6700, file: 'risk_agent.py' },
    { name: 'SHAPAgent', stack: 'Explainability', status: 'active', accuracy: null, predictions: 12300, file: 'explainability_agent.py' }
  ]
  const stacks = ['all', 'Valuation', 'Forecasting', 'Spatial', 'Risk', 'Explainability']
  const filteredAgents = agentView === 'all' ? agents : agents.filter(a => a.stack === agentView)
  const stackColors = { Valuation: 'bg-blue-500/20 text-blue-400', Forecasting: 'bg-purple-500/20 text-purple-400', Spatial: 'bg-green-500/20 text-green-400', Risk: 'bg-red-500/20 text-red-400', Explainability: 'bg-yellow-500/20 text-yellow-400' }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div><h2 className="text-2xl font-bold">Intelligence Layer</h2><p className="text-gray-400 text-sm mt-1">AI agents organized by functional stacks</p></div>
        <button className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">Train Models</button>
      </div>
      <div className="flex gap-2 mb-6 flex-wrap">
        {stacks.map(stack => (<button key={stack} onClick={() => setAgentView(stack)} className={`px-4 py-2 rounded-lg text-sm font-medium transition ${agentView === stack ? 'bg-blue-500 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'}`}>{stack === 'all' ? 'All Agents' : stack}</button>))}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700"><h3 className="text-gray-400 text-sm">Total Agents</h3><p className="text-2xl font-bold mt-1">{agents.length}</p></div>
        <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700"><h3 className="text-gray-400 text-sm">Total Predictions</h3><p className="text-2xl font-bold mt-1">{agents.reduce((sum, a) => sum + a.predictions, 0).toLocaleString()}</p></div>
        <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700"><h3 className="text-gray-400 text-sm">Avg Accuracy</h3><p className="text-2xl font-bold mt-1">{(agents.filter(a => a.accuracy).reduce((sum, a) => sum + a.accuracy, 0) / agents.filter(a => a.accuracy).length).toFixed(1)}%</p></div>
        <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700"><h3 className="text-gray-400 text-sm">Agent Stacks</h3><p className="text-2xl font-bold mt-1">5</p></div>
      </div>
      <div className="bg-gray-800 rounded-2xl border border-gray-700 overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-700/50"><tr><th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Agent</th><th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Stack</th><th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Status</th><th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Accuracy</th><th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Predictions</th><th className="text-left px-6 py-4 text-gray-400 font-medium text-sm">Actions</th></tr></thead>
          <tbody>
            {filteredAgents.map((agent, i) => (
              <tr key={i} className="border-t border-gray-700 hover:bg-gray-700/30">
                <td className="px-6 py-4 font-medium">{agent.name}</td>
                <td className="px-6 py-4"><span className={`px-2 py-1 rounded-full text-xs ${stackColors[agent.stack]}`}>{agent.stack}</span></td>
                <td className="px-6 py-4"><span className="px-2 py-1 rounded-full text-xs bg-green-500/20 text-green-400">{agent.status}</span></td>
                <td className="px-6 py-4">{agent.accuracy ? `${agent.accuracy}%` : '-'}</td>
                <td className="px-6 py-4">{agent.predictions.toLocaleString()}</td>
                <td className="px-6 py-4"><button className="px-3 py-1 bg-blue-500/20 text-blue-400 rounded-lg hover:bg-blue-500/30 text-sm">Test</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// Orchestration Tab - Multi-Agent System monitoring
function OrchestrationTab() {
  const tasks = [
    { id: 'task-001', query: 'Find 3BHK apartments in Whitefield under 1.5Cr', status: 'completed', agents: ['Planner', 'Map', 'Forecast', 'Recommender'], duration: 2.3, confidence: 0.92 },
    { id: 'task-002', query: 'What is the price trend in Koramangala?', status: 'completed', agents: ['Planner', 'Forecast', 'DMPE'], duration: 1.8, confidence: 0.88 },
    { id: 'task-003', query: 'Draw 2km buffer around Manyata Tech Park', status: 'completed', agents: ['Planner', 'Geospatial', 'Map'], duration: 1.2, confidence: 0.95 },
    { id: 'task-004', query: 'Compare investment: HSR vs Electronic City', status: 'running', agents: ['Planner', 'Geospatial', 'Risk'], duration: null, confidence: null }
  ]
  const metrics = { total_requests: 15420, avg_response_time: 1.8, success_rate: 98.5, active_tasks: 1, agents_used: 16 }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div><h2 className="text-2xl font-bold">Orchestration Layer</h2><p className="text-gray-400 text-sm mt-1">Multi-agent task coordination and monitoring</p></div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-6">
        <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700"><h3 className="text-gray-400 text-sm">Total Requests</h3><p className="text-2xl font-bold mt-1">{metrics.total_requests.toLocaleString()}</p></div>
        <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700"><h3 className="text-gray-400 text-sm">Avg Response</h3><p className="text-2xl font-bold mt-1">{metrics.avg_response_time}s</p></div>
        <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700"><h3 className="text-gray-400 text-sm">Success Rate</h3><p className="text-2xl font-bold mt-1 text-green-400">{metrics.success_rate}%</p></div>
        <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700"><h3 className="text-gray-400 text-sm">Active Tasks</h3><p className="text-2xl font-bold mt-1">{metrics.active_tasks}</p></div>
        <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700"><h3 className="text-gray-400 text-sm">Agents Available</h3><p className="text-2xl font-bold mt-1">{metrics.agents_used}</p></div>
      </div>
      <div className="bg-gray-800 rounded-2xl p-6 border border-gray-700 mb-6">
        <h3 className="text-lg font-semibold mb-4">Orchestration Pipeline</h3>
        <div className="flex items-center justify-between">
          {['Parse Intent', 'Plan Tasks', 'Execute Agents', 'Critique Output', 'Generate Response'].map((step, i) => (
            <div key={i} className="flex items-center">
              <div className="text-center"><div className="w-16 h-16 bg-blue-500/20 rounded-xl flex items-center justify-center mb-2"><span className="text-2xl">{['🎯', '📋', '⚡', '🔍', '💬'][i]}</span></div><p className="text-xs text-gray-400">{step}</p></div>
              {i < 4 && <span className="text-gray-600 mx-4">→</span>}
            </div>
          ))}
        </div>
      </div>
      <div className="bg-gray-800 rounded-2xl border border-gray-700 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-700"><h3 className="text-lg font-semibold">Recent Tasks</h3></div>
        <table className="w-full">
          <thead className="bg-gray-700/50"><tr><th className="text-left px-6 py-3 text-gray-400 font-medium text-sm">Query</th><th className="text-left px-6 py-3 text-gray-400 font-medium text-sm">Status</th><th className="text-left px-6 py-3 text-gray-400 font-medium text-sm">Agents Used</th><th className="text-left px-6 py-3 text-gray-400 font-medium text-sm">Duration</th><th className="text-left px-6 py-3 text-gray-400 font-medium text-sm">Confidence</th></tr></thead>
          <tbody>
            {tasks.map(task => (
              <tr key={task.id} className="border-t border-gray-700 hover:bg-gray-700/30">
                <td className="px-6 py-4 max-w-md truncate">{task.query}</td>
                <td className="px-6 py-4"><span className={`px-2 py-1 rounded-full text-xs ${task.status === 'completed' ? 'bg-green-500/20 text-green-400' : 'bg-blue-500/20 text-blue-400'}`}>{task.status}</span></td>
                <td className="px-6 py-4"><div className="flex gap-1 flex-wrap">{task.agents.map((agent, i) => (<span key={i} className="px-2 py-0.5 bg-gray-700 rounded text-xs">{agent}</span>))}</div></td>
                <td className="px-6 py-4">{task.duration ? `${task.duration}s` : 'Running...'}</td>
                <td className="px-6 py-4">{task.confidence ? `${Math.round(task.confidence * 100)}%` : '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// LLM & Self-Learning Tab
function LLMTab() {
  const [currentProvider, setCurrentProvider] = useState('openrouter')
  const [switchingProvider, setSwitchingProvider] = useState(false)
  const [showExperimentModal, setShowExperimentModal] = useState(false)
  
  const providers = [
    { id: 'openrouter', name: 'OpenRouter', desc: 'Cloud LLMs (GPT-4, Claude, DeepSeek)', status: 'active', icon: '☁️' },
    { id: 'qwen_local', name: 'Qwen Local', desc: 'Self-hosted fine-tuned Qwen models', status: 'configured', icon: '🏠' },
    { id: 'hybrid', name: 'Hybrid Router', desc: 'Intelligent routing between models', status: 'configured', icon: '🔀' }
  ]
  
  const models = [
    { id: 'deepseek-chat', name: 'DeepSeek Chat', provider: 'openrouter', type: 'General', interactions: 15420, satisfaction: 92.3, latency: 1200, status: 'active' },
    { id: 'gpt-4o', name: 'GPT-4o', provider: 'openrouter', type: 'Vision', interactions: 3250, satisfaction: 95.1, latency: 2100, status: 'active' },
    { id: 'claude-3.5-sonnet', name: 'Claude 3.5 Sonnet', provider: 'openrouter', type: 'Reasoning', interactions: 1890, satisfaction: 94.8, latency: 1800, status: 'active' },
    { id: 'qwen3-vl-32b', name: 'Qwen3 VL 32B', provider: 'local', type: 'Vision', interactions: 0, satisfaction: 0, latency: 0, status: 'pending', fineTuned: true },
    { id: 'qwen3-72b', name: 'Qwen3 72B', provider: 'local', type: 'Reasoning', interactions: 0, satisfaction: 0, latency: 0, status: 'pending', fineTuned: true },
    { id: 'qwen3-next-80b', name: 'Qwen3 Next 80B', provider: 'local', type: 'Advanced', interactions: 0, satisfaction: 0, latency: 0, status: 'pending', fineTuned: true }
  ]
  
  const learningStats = {
    totalInteractions: 20560,
    totalFeedback: 4520,
    trainingExamplesGenerated: 1245,
    pendingTraining: 356,
    driftAlerts: 0,
    shouldRetrain: false
  }
  
  const experiments = [
    { id: 'exp_001', name: 'DeepSeek vs Claude', control: 'deepseek-chat', challenger: 'claude-3.5-sonnet', controlQuality: 0.87, challengerQuality: 0.91, improvement: 4.6, status: 'active' }
  ]
  
  const handleSwitchProvider = async (providerId) => {
    setSwitchingProvider(true)
    // Simulate API call
    await new Promise(r => setTimeout(r, 1000))
    setCurrentProvider(providerId)
    setSwitchingProvider(false)
  }

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-2xl font-bold">LLM & Self-Learning</h2>
          <p className="text-gray-400 text-sm mt-1">Manage AI models, switch providers, and monitor self-learning</p>
        </div>
        <div className="flex gap-3">
          <button onClick={() => setShowExperimentModal(true)} className="px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600">
            + New Experiment
          </button>
          <button className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600">
            Generate Training Data
          </button>
        </div>
      </div>

      {/* Provider Selection */}
      <div className="bg-gray-800 rounded-2xl p-6 border border-gray-700 mb-6">
        <h3 className="text-lg font-semibold mb-4">LLM Provider</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {providers.map(p => (
            <div 
              key={p.id}
              onClick={() => !switchingProvider && handleSwitchProvider(p.id)}
              className={`p-4 rounded-xl border-2 cursor-pointer transition ${currentProvider === p.id ? 'border-blue-500 bg-blue-500/10' : 'border-gray-600 hover:border-gray-500'}`}
            >
              <div className="flex items-center gap-3 mb-2">
                <span className="text-2xl">{p.icon}</span>
                <div>
                  <p className="font-semibold">{p.name}</p>
                  <span className={`text-xs px-2 py-0.5 rounded ${p.status === 'active' ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'}`}>{p.status}</span>
                </div>
              </div>
              <p className="text-sm text-gray-400">{p.desc}</p>
              {currentProvider === p.id && <div className="mt-2 text-xs text-blue-400">✓ Currently Active</div>}
            </div>
          ))}
        </div>
      </div>

      {/* Self-Learning Stats */}
      <div className="grid grid-cols-1 md:grid-cols-6 gap-4 mb-6">
        <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700">
          <h3 className="text-gray-400 text-sm">Total Interactions</h3>
          <p className="text-2xl font-bold mt-1">{learningStats.totalInteractions.toLocaleString()}</p>
        </div>
        <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700">
          <h3 className="text-gray-400 text-sm">User Feedback</h3>
          <p className="text-2xl font-bold mt-1">{learningStats.totalFeedback.toLocaleString()}</p>
        </div>
        <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700">
          <h3 className="text-gray-400 text-sm">Training Examples</h3>
          <p className="text-2xl font-bold mt-1 text-green-400">{learningStats.trainingExamplesGenerated}</p>
        </div>
        <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700">
          <h3 className="text-gray-400 text-sm">Pending Training</h3>
          <p className="text-2xl font-bold mt-1 text-yellow-400">{learningStats.pendingTraining}</p>
        </div>
        <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700">
          <h3 className="text-gray-400 text-sm">Drift Alerts</h3>
          <p className="text-2xl font-bold mt-1">{learningStats.driftAlerts}</p>
        </div>
        <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700">
          <h3 className="text-gray-400 text-sm">Retrain Status</h3>
          <p className={`text-lg font-bold mt-1 ${learningStats.shouldRetrain ? 'text-red-400' : 'text-green-400'}`}>
            {learningStats.shouldRetrain ? 'Needed' : 'Up to Date'}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Learning Pipeline */}
        <div className="bg-gray-800 rounded-2xl p-6 border border-gray-700">
          <h3 className="text-lg font-semibold mb-4">Self-Learning Pipeline</h3>
          <div className="space-y-4">
            {[
              { step: '1. Log Interactions', icon: '📝', desc: 'Capture all user-AI conversations', status: 'active' },
              { step: '2. Collect Feedback', icon: '👍', desc: 'Thumbs up/down, ratings, corrections', status: 'active' },
              { step: '3. Quality Scoring', icon: '⭐', desc: 'Auto-score responses for training', status: 'active' },
              { step: '4. Generate Training Data', icon: '📊', desc: 'Teacher model creates examples', status: 'active' },
              { step: '5. Fine-tune Students', icon: '🎓', desc: 'LoRA training on Qwen models', status: 'pending' },
              { step: '6. A/B Test & Deploy', icon: '🚀', desc: 'Compare and switch to better model', status: 'pending' }
            ].map((item, i) => (
              <div key={i} className="flex items-center gap-4 p-3 bg-gray-700/30 rounded-xl">
                <span className="text-2xl">{item.icon}</span>
                <div className="flex-1">
                  <p className="font-medium">{item.step}</p>
                  <p className="text-xs text-gray-400">{item.desc}</p>
                </div>
                <span className={`px-2 py-1 rounded text-xs ${item.status === 'active' ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'}`}>
                  {item.status}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* A/B Experiments */}
        <div className="bg-gray-800 rounded-2xl p-6 border border-gray-700">
          <h3 className="text-lg font-semibold mb-4">A/B Experiments</h3>
          {experiments.length > 0 ? (
            <div className="space-y-4">
              {experiments.map(exp => (
                <div key={exp.id} className="p-4 bg-gray-700/30 rounded-xl">
                  <div className="flex justify-between items-start mb-3">
                    <div>
                      <p className="font-semibold">{exp.name}</p>
                      <p className="text-xs text-gray-400">{exp.control} vs {exp.challenger}</p>
                    </div>
                    <span className="px-2 py-1 rounded text-xs bg-blue-500/20 text-blue-400">{exp.status}</span>
                  </div>
                  <div className="grid grid-cols-3 gap-4 text-center">
                    <div><p className="text-xs text-gray-400">Control</p><p className="font-bold">{(exp.controlQuality * 100).toFixed(1)}%</p></div>
                    <div><p className="text-xs text-gray-400">Challenger</p><p className="font-bold text-green-400">{(exp.challengerQuality * 100).toFixed(1)}%</p></div>
                    <div><p className="text-xs text-gray-400">Improvement</p><p className={`font-bold ${exp.improvement > 0 ? 'text-green-400' : 'text-red-400'}`}>+{exp.improvement}%</p></div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-gray-400 text-sm">No active experiments. Create one to compare models.</p>
          )}
        </div>
      </div>

      {/* Models Table */}
      <div className="bg-gray-800 rounded-2xl border border-gray-700 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-700"><h3 className="text-lg font-semibold">Model Registry</h3></div>
        <table className="w-full">
          <thead className="bg-gray-700/50">
            <tr>
              <th className="text-left px-6 py-3 text-gray-400 font-medium text-sm">Model</th>
              <th className="text-left px-6 py-3 text-gray-400 font-medium text-sm">Provider</th>
              <th className="text-left px-6 py-3 text-gray-400 font-medium text-sm">Type</th>
              <th className="text-left px-6 py-3 text-gray-400 font-medium text-sm">Interactions</th>
              <th className="text-left px-6 py-3 text-gray-400 font-medium text-sm">Satisfaction</th>
              <th className="text-left px-6 py-3 text-gray-400 font-medium text-sm">Latency</th>
              <th className="text-left px-6 py-3 text-gray-400 font-medium text-sm">Status</th>
            </tr>
          </thead>
          <tbody>
            {models.map(m => (
              <tr key={m.id} className="border-t border-gray-700 hover:bg-gray-700/30">
                <td className="px-6 py-4">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{m.name}</span>
                    {m.fineTuned && <span className="px-1.5 py-0.5 bg-purple-500/20 text-purple-400 text-xs rounded">Fine-tuned</span>}
                  </div>
                </td>
                <td className="px-6 py-4 text-gray-400">{m.provider}</td>
                <td className="px-6 py-4"><span className="px-2 py-1 bg-blue-500/20 text-blue-400 text-xs rounded">{m.type}</span></td>
                <td className="px-6 py-4">{m.interactions.toLocaleString()}</td>
                <td className="px-6 py-4">{m.satisfaction > 0 ? `${m.satisfaction}%` : '-'}</td>
                <td className="px-6 py-4">{m.latency > 0 ? `${m.latency}ms` : '-'}</td>
                <td className="px-6 py-4">
                  <span className={`px-2 py-1 rounded-full text-xs ${m.status === 'active' ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'}`}>
                    {m.status}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

// Digital Twin Tab - 3D Building Visualization Management
function DigitalTwinTab() {
  const [selectedBuilding, setSelectedBuilding] = useState(null)
  
  const buildings = [
    { id: 'bldg_001', name: 'Prestige Lakeside Habitat', locality: 'Whitefield', floors: 15, units: 60, has3D: true, views: 1245, lastUpdated: '2h ago' },
    { id: 'bldg_002', name: 'Sobha Dream Acres', locality: 'Sarjapur', floors: 22, units: 88, has3D: true, views: 890, lastUpdated: '5h ago' },
    { id: 'bldg_003', name: 'Brigade Metropolis', locality: 'Whitefield', floors: 18, units: 72, has3D: true, views: 756, lastUpdated: '1d ago' },
    { id: 'bldg_004', name: 'Embassy Springs', locality: 'Sarjapur', floors: 12, units: 48, has3D: false, views: 0, lastUpdated: '-' },
    { id: 'bldg_005', name: 'Godrej Splendour', locality: 'Electronic City', floors: 20, units: 80, has3D: true, views: 623, lastUpdated: '3h ago' }
  ]
  
  const stats = {
    totalBuildings: buildings.length,
    with3DModels: buildings.filter(b => b.has3D).length,
    totalViews: buildings.reduce((sum, b) => sum + b.views, 0),
    avgFloors: Math.round(buildings.reduce((sum, b) => sum + b.floors, 0) / buildings.length)
  }
  
  const features = [
    { name: 'Floor-by-Floor View', icon: '🏗️', status: 'active', description: 'Interactive floor selection' },
    { name: 'Occupancy Colors', icon: '📊', status: 'active', description: 'Color-coded occupancy rates' },
    { name: 'Day/Night Mode', icon: '🌓', status: 'active', description: 'Toggle lighting effects' },
    { name: 'Environmental Data', icon: '🌡️', status: 'active', description: 'Temperature, humidity, AQI' },
    { name: 'Investment Analysis', icon: '💰', status: 'active', description: 'Price trends and yields' },
    { name: 'Unit Details', icon: '🏠', status: 'active', description: 'Click for unit info' },
    { name: 'Auto-Rotate', icon: '🔄', status: 'active', description: '360° rotation' },
    { name: 'Orbit Controls', icon: '🖱️', status: 'active', description: 'Drag, scroll, pan' }
  ]

  return (
    <div>
      <div className="flex justify-between items-center mb-6">
        <div>
          <h2 className="text-2xl font-bold">Digital Twin 3D Viewer</h2>
          <p className="text-gray-400 text-sm mt-1">3D building visualization and management</p>
        </div>
        <button className="px-4 py-2 bg-gradient-to-r from-blue-500 to-purple-500 text-white rounded-lg hover:from-blue-600 hover:to-purple-600">
          + Add Building
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700"><h3 className="text-gray-400 text-sm">Total Buildings</h3><p className="text-2xl font-bold mt-1">{stats.totalBuildings}</p></div>
        <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700"><h3 className="text-gray-400 text-sm">With 3D Models</h3><p className="text-2xl font-bold mt-1 text-green-400">{stats.with3DModels}</p></div>
        <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700"><h3 className="text-gray-400 text-sm">Total 3D Views</h3><p className="text-2xl font-bold mt-1">{stats.totalViews.toLocaleString()}</p></div>
        <div className="bg-gray-800 rounded-2xl p-5 border border-gray-700"><h3 className="text-gray-400 text-sm">Avg Floors</h3><p className="text-2xl font-bold mt-1">{stats.avgFloors}</p></div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div className="bg-gray-800 rounded-2xl p-6 border border-gray-700">
          <h3 className="text-lg font-semibold mb-4">3D Viewer Features</h3>
          <div className="grid grid-cols-2 gap-3">
            {features.map((f, i) => (
              <div key={i} className="flex items-center gap-2 p-2 bg-gray-700/30 rounded-lg">
                <span className="text-lg">{f.icon}</span>
                <div><p className="text-sm font-medium">{f.name}</p><p className="text-xs text-gray-400">{f.description}</p></div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-gray-800 rounded-2xl p-6 border border-gray-700">
          <h3 className="text-lg font-semibold mb-4">Technology Stack</h3>
          <div className="space-y-3">
            {[
              { name: 'Three.js', version: 'v0.160.0', desc: '3D graphics library', icon: '🎮' },
              { name: 'React Three Fiber', version: 'v8.15.12', desc: 'React renderer', icon: '⚛️' },
              { name: '@react-three/drei', version: 'v9.92.0', desc: 'Helpers & controls', icon: '🧰' },
              { name: 'WebGL 2.0', version: 'Native', desc: 'GPU acceleration', icon: '🖥️' }
            ].map((tech, i) => (
              <div key={i} className="flex items-center gap-3 p-3 bg-gray-700/30 rounded-xl">
                <span className="text-xl">{tech.icon}</span>
                <div className="flex-1"><p className="font-medium">{tech.name} <span className="text-xs px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded ml-2">{tech.version}</span></p><p className="text-xs text-gray-400">{tech.desc}</p></div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="bg-gray-800 rounded-2xl border border-gray-700 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-700"><h3 className="text-lg font-semibold">Building Models</h3></div>
        <table className="w-full">
          <thead className="bg-gray-700/50"><tr><th className="text-left px-6 py-3 text-gray-400 font-medium text-sm">Building</th><th className="text-left px-6 py-3 text-gray-400 font-medium text-sm">Locality</th><th className="text-left px-6 py-3 text-gray-400 font-medium text-sm">Floors</th><th className="text-left px-6 py-3 text-gray-400 font-medium text-sm">3D Status</th><th className="text-left px-6 py-3 text-gray-400 font-medium text-sm">Views</th><th className="text-left px-6 py-3 text-gray-400 font-medium text-sm">Actions</th></tr></thead>
          <tbody>
            {buildings.map((b) => (
              <tr key={b.id} className="border-t border-gray-700 hover:bg-gray-700/30">
                <td className="px-6 py-4 font-medium">{b.name}</td>
                <td className="px-6 py-4 text-gray-400">{b.locality}</td>
                <td className="px-6 py-4">{b.floors}</td>
                <td className="px-6 py-4">{b.has3D ? <span className="px-2 py-1 rounded-full text-xs bg-green-500/20 text-green-400">Ready</span> : <span className="px-2 py-1 rounded-full text-xs bg-yellow-500/20 text-yellow-400">Pending</span>}</td>
                <td className="px-6 py-4">{b.views.toLocaleString()}</td>
                <td className="px-6 py-4"><button className="px-3 py-1 bg-blue-500/20 text-blue-400 rounded-lg hover:bg-blue-500/30 text-sm">{b.has3D ? 'View 3D' : 'Generate'}</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
