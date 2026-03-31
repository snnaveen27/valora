import { useState, useEffect, useCallback } from 'react'
import { 
  X, Settings, Database, Server, CheckCircle, XCircle, 
  RefreshCw, Zap, HardDrive, Cloud, AlertTriangle,
  BarChart3, TestTube, FileText, Loader2, Save, Brain,
  Users, MapPin, Clock, Download, Trash2, Eye, UserPlus, Edit, Crown,
  TrendingUp, Target, Gauge, PlayCircle,
  ArrowUpRight, DollarSign
} from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import PricingManager from './PricingManager'

import { API_URL } from '../apiConfig'

export default function AdminPanel({ isOpen, onClose }) {
  const { token } = useAuth()
  const [activeTab, setActiveTab] = useState('status')
  const [systemStatus, setSystemStatus] = useState(null)
  const [loading, setLoading] = useState(false)
  const [vectorBackend, setVectorBackend] = useState('pinecone') // pinecone or faiss
  const [testResults, setTestResults] = useState(null)
  const [runningTest, setRunningTest] = useState(false)
  const [selectedTier, setSelectedTier] = useState(null) // null = all tiers

  const [processingStatus, setProcessingStatus] = useState(null)
  const [llmConfig, setLlmConfig] = useState({
    provider: 'ollama',
    local_url: 'http://127.0.0.1:11434/v1/chat/completions',
    local_model: 'valora-ai-mini:latest',
    max_context: 8192
  })
  const [llmSaving, setLlmSaving] = useState(false)
  const [llmTestResult, setLlmTestResult] = useState(null)
  const [brainStatus, setBrainStatus] = useState(null)
  const [rebuildingBrain, setRebuildingBrain] = useState(false)
  const [brainResult, setBrainResult] = useState(null)
  const [lastRefresh, setLastRefresh] = useState(null)
  const [systemVersion, setSystemVersion] = useState('2025.2.5')
  const [userPrefs, setUserPrefs] = useState(null)
  const [loadingPrefs, setLoadingPrefs] = useState(false)
  const [prefsUserId, setPrefsUserId] = useState('default')
  
  // User Management State
  const [userAccounts, setUserAccounts] = useState([])
  const [userStats, setUserStats] = useState(null)
  const [loadingUsers, setLoadingUsers] = useState(false)
  const [userError, setUserError] = useState(null)
  const [editingUser, setEditingUser] = useState(null)
  const [showCreateUser, setShowCreateUser] = useState(false)
  const [newUser, setNewUser] = useState({ email: '', password: '', name: '', tier: 'free', role: 'user' })
  const [formErrors, setFormErrors] = useState({})

  // Weekly Metrics Dashboard State
  const [weeklyMetrics, setWeeklyMetrics] = useState(null)
  const [loadingMetrics, setLoadingMetrics] = useState(false)
  const [demoMode, setDemoMode] = useState(false)

  const [revenueData, setRevenueData] = useState(null)
  const [ingestionData, setIngestionData] = useState(null)
  const [coverageData, setCoverageData] = useState(null)
  const [learningData, setLearningData] = useState(null)

  // Demo data for the metrics dashboard
  const DEMO_WEEKLY_METRICS = {
    success: true,
    generated_at: new Date().toISOString(),
    period: "demo_7_days",
    is_demo: true,
    wawu: {
      total_active_users: 247,
      workflow_actions: {
        alerts: 892,
        scheduled_tasks: 1456,
        leads: 423,
        automation_commands: 2187
      }
    },
    conversions: {
      free_to_pro_new: 34,
      free_to_pro_rate: 0.18,
      topups_purchased: 67,
      topup_attach_rate: 0.42,
      broker_team_expansions: 12,
      b2b_pilot_to_retainer: 5
    },
    retention: {
      week_4_cohort_retention: 0.72,
      cohort_size: 189
    },
    workflow_activation: {
      total_active_users: 247,
      users_with_alerts: 156,
      users_with_tasks: 198,
      users_with_leads: 89,
      activation_rate: 0.81
    },
    guardrails: {
      billing_incidents: 3,
      data_freshness_breaches: 2,
      low_confidence_recommendations: 124,
      avg_time_to_first_value_hours: 14.5
    }
  }

  useEffect(() => {
    if (isOpen) {
      fetchSystemStatus()
      fetchVectorBackend()
      fetchLlmConfig()
      fetchRuntimeConfig()
      fetchBrainStatus()
      setLastRefresh(new Date())
    }
  }, [isOpen])

  // User Management Functions with useCallback
  const fetchUserAccounts = useCallback(async () => {
    if (!token) return
    setLoadingUsers(true)
    setUserError(null)
    try {
      const [usersResp, statsResp] = await Promise.all([
        fetch(`${API_URL}/api/auth/admin/users`, {
          headers: { 'Authorization': `Bearer ${token}` }
        }),
        fetch(`${API_URL}/api/auth/admin/stats`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })
      ])
      if (usersResp.ok) {
        const users = await usersResp.json()
        setUserAccounts(users)
      } else {
        setUserError('Failed to fetch user accounts')
      }
      if (statsResp.ok) {
        const stats = await statsResp.json()
        setUserStats(stats)
      }
    } catch (err) {
      console.error('Failed to fetch users:', err)
      setUserError('Network error while fetching users')
    }
    setLoadingUsers(false)
  }, [token])

  const validateUserForm = () => {
    const errors = {}
    if (!newUser.name || newUser.name.length < 2) {
      errors.name = 'Name must be at least 2 characters'
    }
    if (!newUser.email || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(newUser.email)) {
      errors.email = 'Please enter a valid email address'
    }
    if (!newUser.password || newUser.password.length < 6) {
      errors.password = 'Password must be at least 6 characters'
    }
    setFormErrors(errors)
    return Object.keys(errors).length === 0
  }

  // Fetch Weekly Metrics Dashboard
  const fetchWeeklyMetrics = useCallback(async () => {
    if (!token) return
    setLoadingMetrics(true)
    
    // If demo mode is on, use demo data
    if (demoMode) {
      setWeeklyMetrics(DEMO_WEEKLY_METRICS)
      setLoadingMetrics(false)
      return
    }
    
    try {
      const resp = await fetch(`${API_URL}/api/admin/dashboard/weekly`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (resp.ok) {
        const data = await resp.json()
        setWeeklyMetrics(data)
      }
    } catch (err) {
      console.error('Failed to fetch weekly metrics:', err)
    }
    setLoadingMetrics(false)
  }, [token, demoMode])

  const createUserAccount = useCallback(async () => {
    if (!token) return
    if (!validateUserForm()) return
    
    try {
      const resp = await fetch(`${API_URL}/api/auth/admin/users?tier=${newUser.tier}&role=${newUser.role}`, {
        method: 'POST',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          email: newUser.email,
          password: newUser.password,
          name: newUser.name
        })
      })
      if (resp.ok) {
        setShowCreateUser(false)
        setNewUser({ email: '', password: '', name: '', tier: 'free', role: 'user' })
        setFormErrors({})
        fetchUserAccounts()
      } else {
        const err = await resp.json().catch(() => ({ detail: 'Failed to create user' }))
        setFormErrors({ submit: err.detail || 'Failed to create user' })
      }
    } catch (err) {
      console.error('Failed to create user:', err)
      setFormErrors({ submit: 'Network error while creating user' })
    }
  }, [token, newUser, fetchUserAccounts])

  const updateUserAccount = useCallback(async (userId, updates) => {
    if (!token) return
    try {
      const resp = await fetch(`${API_URL}/api/auth/admin/users/${userId}`, {
        method: 'PUT',
        headers: { 
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(updates)
      })
      if (resp.ok) {
        setEditingUser(null)
        fetchUserAccounts()
      } else {
        const err = await resp.json().catch(() => ({ detail: 'Update failed' }))
        alert(err.detail || 'Failed to update user')
      }
    } catch (err) {
      console.error('Failed to update user:', err)
      alert('Network error while updating user')
    }
  }, [token, fetchUserAccounts])

  const deleteUserAccount = useCallback(async (userId) => {
    if (!token || !confirm('Are you sure you want to delete this user? This action cannot be undone.')) return
    try {
      const resp = await fetch(`${API_URL}/api/auth/admin/users/${userId}`, {
        method: 'DELETE',
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (resp.ok) {
        fetchUserAccounts()
      } else {
        const err = await resp.json().catch(() => ({ detail: 'Delete failed' }))
        alert(err.detail || 'Failed to delete user')
      }
    } catch (err) {
      console.error('Failed to delete user:', err)
      alert('Network error while deleting user')
    }
  }, [token, fetchUserAccounts])

  const fetchBrainStatus = useCallback(async () => {
    if (!token) return
    try {
      const resp = await fetch(`${API_URL}/api/admin/locality-brain-status`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (resp.ok) {
        const data = await resp.json()
        setBrainStatus(data.status)
      }
    } catch (err) {
      console.error('Failed to fetch brain status:', err)
    }
  }, [token])

  const rebuildBrain = useCallback(async () => {
    if (!token) return
    setRebuildingBrain(true)
    setBrainResult(null)
    try {
      const resp = await fetch(`${API_URL}/api/admin/rebuild-locality-brain`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      })
      const data = await resp.json()
      setBrainResult(data)
      if (data.success) {
        fetchBrainStatus()
      }
    } catch (err) {
      setBrainResult({ success: false, message: `Error: ${err.message}` })
    }
    setRebuildingBrain(false)
  }, [fetchBrainStatus, token])

  const fetchSystemStatus = useCallback(async () => {
    if (!token) return
    setLoading(true)
    try {
      const resp = await fetch(`${API_URL}/api/admin/status`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (resp.ok) {
        const data = await resp.json()
        setSystemStatus(data)
        setLastRefresh(new Date())
      }
    } catch (err) {
      console.error('Failed to fetch system status:', err)
      setSystemStatus({ error: 'Failed to connect to backend' })
    }
    setLoading(false)
  }, [token])

  const fetchUserPreferences = useCallback(async (userId = prefsUserId) => {
    setLoadingPrefs(true)
    try {
      const resp = await fetch(`${API_URL}/api/preferences/${userId}`)
      if (resp.ok) {
        const data = await resp.json()
        setUserPrefs(data)
      } else {
        setUserPrefs({ error: 'User not found' })
      }
    } catch (err) {
      console.error('Failed to fetch user preferences:', err)
      setUserPrefs({ error: 'Failed to fetch preferences' })
    }
    setLoadingPrefs(false)
  }, [prefsUserId])

  const clearUserPreferences = useCallback(async (userId = prefsUserId) => {
    try {
      const resp = await fetch(`${API_URL}/api/preferences/${userId}`, { method: 'DELETE' })
      if (resp.ok) {
        setUserPrefs(null)
        fetchUserPreferences(userId)
      }
    } catch (err) {
      console.error('Failed to clear preferences:', err)
    }
  }, [prefsUserId, fetchUserPreferences])

  const fetchVectorBackend = useCallback(async () => {
    if (!token) return
    try {
      const resp = await fetch(`${API_URL}/api/admin/vector-backend`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (resp.ok) {
        const data = await resp.json()
        setVectorBackend(data.backend || 'pinecone')
      }
    } catch (err) {
      console.error('Failed to fetch vector backend:', err)
    }
  }, [token])

  const toggleVectorBackend = useCallback(async () => {
    if (!token) return
    const newBackend = vectorBackend === 'pinecone' ? 'faiss' : 'pinecone'
    try {
      const resp = await fetch(`${API_URL}/api/admin/vector-backend`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ backend: newBackend })
      })
      if (resp.ok) {
        setVectorBackend(newBackend)
      } else {
        alert('Failed to toggle vector backend')
      }
    } catch (err) {
      console.error('Failed to toggle vector backend:', err)
      alert('Network error while toggling backend')
    }
  }, [vectorBackend, token])

  const runTests = useCallback(async (tier = null) => {
    if (!token) return
    setRunningTest(true)
    setTestResults(null)
    try {
      // Use the new test suite API
      const body = tier ? { tier } : {}
      const resp = await fetch(`${API_URL}/api/test-suite/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify(body)
      })
      if (resp.ok) {
        const data = await resp.json()
        setTestResults(data)
      } else {
        setTestResults({ error: 'Failed to run tests' })
      }
    } catch (err) {
      console.error('Failed to run tests:', err)
      setTestResults({ error: 'Failed to run tests' })
    }
    setRunningTest(false)
  }, [token])



  const fetchProcessingStatus = useCallback(async () => {
    if (!token) return
    try {
      const resp = await fetch(`${API_URL}/api/admin/processing-status`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (resp.ok) {
        const data = await resp.json()
        setProcessingStatus(data)
      }
    } catch (err) {
      console.error('Failed to fetch processing status:', err)
    }
  }, [token])

  const triggerIndexing = useCallback(async (target) => {
    if (!token) return
    try {
      const resp = await fetch(`${API_URL}/api/admin/trigger-indexing`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify({ target })
      })
      if (!resp.ok) {
        alert('Failed to trigger indexing')
      }
      fetchProcessingStatus()
    } catch (err) {
      console.error('Failed to trigger indexing:', err)
      alert('Network error while triggering indexing')
    }
  }, [fetchProcessingStatus, token])

  const fetchRuntimeConfig = useCallback(async () => {
    if (!token) return
    try {
      const resp = await fetch(`${API_URL}/api/admin/agent-runtime-config`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (resp.ok) {
        const data = await resp.json()
        setRuntimeConfig(prev => ({ ...prev, ...data }))
      }
    } catch (err) {
      console.error('Failed to fetch Runtime config:', err)
    }
  }, [token])

  const fetchLlmConfig = useCallback(async () => {
    if (!token) return
    try {
      const resp = await fetch(`${API_URL}/api/admin/llm-config`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (resp.ok) {
        const data = await resp.json()
        setLlmConfig(prev => ({ ...prev, ...data }))
      }
    } catch (err) {
      console.error('Failed to fetch LLM config:', err)
    }
  }, [token])

  const saveLlmConfig = useCallback(async () => {
    if (!token) return
    setLlmSaving(true)
    setLlmTestResult(null)
    try {
      const resp = await fetch(`${API_URL}/api/admin/llm-config`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify(llmConfig)
      })
      if (resp.ok) {
        setLlmTestResult({ success: true, message: 'Configuration saved!' })
      } else {
        const err = await resp.json()
        setLlmTestResult({ success: false, message: err.detail || 'Failed to save' })
      }
    } catch (err) {
      setLlmTestResult({ success: false, message: 'Failed to connect to backend' })
    }
    setLlmSaving(false)
  }, [llmConfig, token])

  const testLlmConnection = useCallback(async () => {
    if (!token) return
    setLlmSaving(true)
    setLlmTestResult(null)
    try {
      const resp = await fetch(`${API_URL}/api/admin/llm-test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify(llmConfig)
      })
      const data = await resp.json()
      setLlmTestResult(data)
    } catch (err) {
      setLlmTestResult({ success: false, message: 'Failed to test connection' })
    }
    setLlmSaving(false)
  }, [llmConfig, token])

  const fetchRevenueData = async () => {
    try {
      const [usageRes, revenueRes, cloudRes] = await Promise.all([
        fetch(`${API_URL}/api/admin/usage/stats`, { headers: { 'Authorization': `Bearer ${token}` } }),
        fetch(`${API_URL}/api/admin/usage/revenue-estimate?days=30`, { headers: { 'Authorization': `Bearer ${token}` } }),
        fetch(`${API_URL}/api/admin/cloud-cost/stats?days=7`, { headers: { 'Authorization': `Bearer ${token}` } })
      ])
      const usage = await usageRes.json()
      const revenue = await revenueRes.json()
      const cloud = await cloudRes.json()
      setRevenueData({ usage: usage.stats, revenue: revenue, cloud: cloud.stats })
    } catch (err) { console.error('Failed to fetch revenue data:', err) }
  }

  const fetchIngestionData = async () => {
    try {
      const [brainRes, statusRes] = await Promise.all([
        fetch(`${API_URL}/api/admin/locality-brain-status`, { headers: { 'Authorization': `Bearer ${token}` } }),
        fetch(`${API_URL}/api/admin/status`, { headers: { 'Authorization': `Bearer ${token}` } })
      ])
      const brain = await brainRes.json()
      const status = await statusRes.json()
      setIngestionData({ brain, status })
    } catch (err) { console.error('Failed to fetch ingestion data:', err) }
  }

  const fetchCoverageData = async () => {
    try {
      const res = await fetch(`${API_URL}/api/admin/locality-brain-status`, { headers: { 'Authorization': `Bearer ${token}` } })
      const data = await res.json()
      setCoverageData(data)
    } catch (err) { console.error('Failed to fetch coverage data:', err) }
  }

  const fetchLearningData = async () => {
    try {
      const [learningRes, toolsRes] = await Promise.all([
        fetch(`${API_URL}/api/admin/agentic/learning`, { headers: { 'Authorization': `Bearer ${token}` } }),
        fetch(`${API_URL}/api/admin/agentic/learning/tools`, { headers: { 'Authorization': `Bearer ${token}` } })
      ])
      const learning = await learningRes.json()
      const tools = await toolsRes.json()
      setLearningData({ ...learning, tool_scores: tools.tool_scores || {} })
    } catch (err) { console.error('Failed to fetch learning data:', err) }
  }

  if (!isOpen) return null

  const tabs = [
    { id: 'status', label: 'System', icon: Server },
    { id: 'users', label: 'Users', icon: Users },
    { id: 'data', label: 'Data', icon: Database },
    { id: 'revenue', label: 'Revenue', icon: ArrowUpRight },
    { id: 'pricing', label: 'Pricing', icon: DollarSign },
    { id: 'ai', label: 'AI & Models', icon: Brain },
    { id: 'tests', label: 'Tests', icon: TestTube },
  ]

  return (
    <div className="fixed inset-0 bg-slate-900 z-40 flex">
      <div className="w-full h-full flex flex-col bg-slate-800">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-700">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-pink-600 rounded-lg flex items-center justify-center">
              <Settings className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="text-white font-bold text-lg">Admin Panel</h2>
              <p className="text-slate-400 text-xs">
                v{systemVersion} • {lastRefresh ? `Last refresh: ${lastRefresh.toLocaleTimeString()}` : 'System management'}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-slate-400 hover:text-white hover:bg-slate-700 rounded-lg transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex gap-1 p-2 border-b border-slate-700 bg-slate-800/50">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => {
                setActiveTab(tab.id)
                if (tab.id === 'users') fetchUserPreferences()
                if (tab.id === 'revenue' && !revenueData) fetchRevenueData()
                if (tab.id === 'data' && !ingestionData) fetchIngestionData()
                if (tab.id === 'ai' && !learningData) fetchLearningData()
              }}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition ${
                activeTab === tab.id
                  ? 'bg-purple-600 text-white'
                  : 'text-slate-400 hover:bg-slate-700 hover:text-white'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-4">
          {/* User Accounts Tab */}
          {activeTab === 'users' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-white font-semibold">User Account Management</h3>
                <div className="flex gap-2">
                  <button
                    onClick={fetchUserAccounts}
                    disabled={loadingUsers}
                    className="flex items-center gap-2 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-white rounded-lg text-sm transition"
                  >
                    <RefreshCw className={`w-4 h-4 ${loadingUsers ? 'animate-spin' : ''}`} />
                    Refresh
                  </button>
                  <button
                    onClick={() => setShowCreateUser(true)}
                    className="flex items-center gap-2 px-3 py-1.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm transition"
                  >
                    <UserPlus className="w-4 h-4" />
                    Add User
                  </button>
                </div>
              </div>

              {/* Stats Cards */}
              {userStats && (
                <div className="grid grid-cols-4 gap-3">
                  <div className="bg-slate-700/50 rounded-lg p-3 border border-slate-600">
                    <p className="text-slate-400 text-xs">Total Users</p>
                    <p className="text-2xl font-bold text-white">{userStats.total_users || 0}</p>
                  </div>
                  <div className="bg-green-500/10 rounded-lg p-3 border border-green-500/30">
                    <p className="text-green-400 text-xs">Pro Users</p>
                    <p className="text-2xl font-bold text-green-300">{userStats.users_by_tier?.pro || 0}</p>
                  </div>
                  <div className="bg-blue-500/10 rounded-lg p-3 border border-blue-500/30">
                    <p className="text-blue-400 text-xs">Team Users</p>
                    <p className="text-2xl font-bold text-blue-300">{userStats.users_by_tier?.team || 0}</p>
                  </div>
                  <div className="bg-purple-500/10 rounded-lg p-3 border border-purple-500/30">
                    <p className="text-purple-400 text-xs">Active Today</p>
                    <p className="text-2xl font-bold text-purple-300">{userStats.active_users_today || 0}</p>
                  </div>
                </div>
              )}

              {/* Create User Modal */}
              {showCreateUser && (
                <div className="bg-slate-700/50 rounded-lg p-4 border border-purple-500/30">
                  <h4 className="text-white font-medium mb-3 flex items-center gap-2">
                    <UserPlus className="w-4 h-4 text-purple-400" />
                    Create New User
                  </h4>
                  
                  {/* Submit Error */}
                  {formErrors.submit && (
                    <div className="mb-3 p-2 bg-red-500/20 border border-red-500/30 rounded text-red-400 text-sm">
                      {formErrors.submit}
                    </div>
                  )}
                  
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <input
                        type="text"
                        placeholder="Full Name"
                        value={newUser.name}
                        onChange={(e) => setNewUser({ ...newUser, name: e.target.value })}
                        className={`w-full bg-slate-800 border rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-purple-500 ${
                          formErrors.name ? 'border-red-500' : 'border-slate-600'
                        }`}
                      />
                      {formErrors.name && (
                        <p className="text-red-400 text-xs mt-1">{formErrors.name}</p>
                      )}
                    </div>
                    <div>
                      <input
                        type="email"
                        placeholder="Email"
                        value={newUser.email}
                        onChange={(e) => setNewUser({ ...newUser, email: e.target.value })}
                        className={`w-full bg-slate-800 border rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-purple-500 ${
                          formErrors.email ? 'border-red-500' : 'border-slate-600'
                        }`}
                      />
                      {formErrors.email && (
                        <p className="text-red-400 text-xs mt-1">{formErrors.email}</p>
                      )}
                    </div>
                    <div>
                      <input
                        type="password"
                        placeholder="Password (min 6 chars)"
                        value={newUser.password}
                        onChange={(e) => setNewUser({ ...newUser, password: e.target.value })}
                        className={`w-full bg-slate-800 border rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-purple-500 ${
                          formErrors.password ? 'border-red-500' : 'border-slate-600'
                        }`}
                      />
                      {formErrors.password && (
                        <p className="text-red-400 text-xs mt-1">{formErrors.password}</p>
                      )}
                    </div>
                    <select
                      value={newUser.tier}
                      onChange={(e) => setNewUser({ ...newUser, tier: e.target.value })}
                      className="bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-purple-500"
                    >
                      <option value="free">Free</option>
                      <option value="pro">Pro</option>
                    </select>
                  </div>
                  <div className="flex justify-end gap-2 mt-3">
                    <button
                      type="button"
                      onClick={() => {
                        setShowCreateUser(false)
                        setFormErrors({})
                      }}
                      className="px-4 py-2 text-slate-400 hover:text-white transition text-sm"
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      onClick={createUserAccount}
                      className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm transition"
                    >
                      Create User
                    </button>
                  </div>
                </div>
              )}

              {/* Error Display */}
              {userError && (
                <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400 flex items-center gap-2">
                  <AlertTriangle className="w-5 h-5" />
                  {userError}
                </div>
              )}

              {/* Users List */}
              {loadingUsers ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-8 h-8 text-purple-500 animate-spin" />
                </div>
              ) : userAccounts.length > 0 ? (
                <div className="bg-slate-700/30 rounded-lg border border-slate-600 overflow-hidden">
                  <table className="w-full text-sm">
                    <thead className="bg-slate-700/50">
                      <tr>
                        <th className="text-left p-3 text-slate-400 font-medium">User</th>
                        <th className="text-left p-3 text-slate-400 font-medium">Tier</th>
                        <th className="text-left p-3 text-slate-400 font-medium">Usage</th>
                        <th className="text-left p-3 text-slate-400 font-medium">Status</th>
                        <th className="text-right p-3 text-slate-400 font-medium">Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {userAccounts.map((u) => (
                        <tr key={u.id} className="border-t border-slate-700 hover:bg-slate-700/30">
                          <td className="p-3">
                            <div>
                              <p className="text-white font-medium">{u.name}</p>
                              <p className="text-slate-400 text-xs">{u.email}</p>
                            </div>
                          </td>
                          <td className="p-3">
                            {editingUser === u.id ? (
                              <select
                                defaultValue={u.tier}
                                onChange={(e) => updateUserAccount(u.id, { tier: e.target.value })}
                                className="bg-slate-800 border border-slate-600 rounded px-2 py-1 text-white text-xs"
                              >
                                <option value="free">Free</option>
                                <option value="pro">Pro</option>
                                <option value="admin">Admin</option>
                              </select>
                            ) : (
                              <span className={`px-2 py-1 rounded text-xs font-medium ${
                                u.tier === 'admin' ? 'bg-purple-500/20 text-purple-300' :
                                u.tier === 'pro' ? 'bg-green-500/20 text-green-300' :
                                'bg-slate-600/50 text-slate-300'
                              }`}>
                                {u.tier === 'admin' && <Crown className="w-3 h-3 inline mr-1" />}
                                {u.tier?.toUpperCase()}
                              </span>
                            )}
                          </td>
                          <td className="p-3">
                            <span className="text-slate-300 text-xs">
                              {u.queries_today || 0} queries today
                            </span>
                          </td>
                          <td className="p-3">
                            <span className={`px-2 py-1 rounded text-xs ${
                              u.is_active ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                            }`}>
                              {u.is_active ? 'Active' : 'Inactive'}
                            </span>
                          </td>
                          <td className="p-3 text-right">
                            <div className="flex items-center justify-end gap-1">
                              <button
                                onClick={() => setEditingUser(editingUser === u.id ? null : u.id)}
                                className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-600 rounded transition"
                                title="Edit"
                              >
                                <Edit className="w-4 h-4" />
                              </button>
                              {u.role !== 'admin' && (
                                <button
                                  onClick={() => deleteUserAccount(u.id)}
                                  className="p-1.5 text-red-400 hover:text-red-300 hover:bg-red-500/20 rounded transition"
                                  title="Delete"
                                >
                                  <Trash2 className="w-4 h-4" />
                                </button>
                              )}
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-10 text-slate-400">
                  <Users className="w-10 h-10 mx-auto mb-3 opacity-50" />
                  <p>No users found. Click "Add User" to create one.</p>
                </div>
              )}
            </div>
          )}

          {/* Metrics Dashboard Tab */}
          {activeTab === 'status' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-white font-semibold">Founder Metrics Dashboard</h3>
                <div className="flex items-center gap-3">
                  {/* Demo Mode Toggle */}
                  <label className="flex items-center gap-2 cursor-pointer">
                    <span className={`text-xs ${demoMode ? 'text-yellow-400' : 'text-slate-400'}`}>Demo</span>
                    <div 
                      className={`relative w-10 h-5 rounded-full transition-colors ${demoMode ? 'bg-yellow-500' : 'bg-slate-600'}`}
                      onClick={() => {
                        setDemoMode(!demoMode)
                        // Trigger fetch with new mode after state update
                        setTimeout(() => fetchWeeklyMetrics(), 0)
                      }}
                    >
                      <div className={`absolute top-0.5 w-4 h-4 bg-white rounded-full transition-transform ${demoMode ? 'translate-x-5' : 'translate-x-0.5'}`} />
                    </div>
                  </label>
                  <button
                    onClick={fetchWeeklyMetrics}
                    disabled={loadingMetrics}
                    className="flex items-center gap-2 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-white rounded-lg text-sm transition"
                  >
                    <RefreshCw className={`w-4 h-4 ${loadingMetrics ? 'animate-spin' : ''}`} />
                    Refresh
                  </button>
                </div>
              </div>

              {weeklyMetrics?.success ? (
                <>
                  {/* Demo Mode Banner */}
                  {weeklyMetrics.is_demo && (
                    <div className="bg-yellow-500/20 border border-yellow-500/50 rounded-lg p-3 mb-4">
                      <p className="text-yellow-400 text-sm flex items-center gap-2">
                        <PlayCircle className="w-4 h-4" />
                        Demo Mode: Showing sample data to visualize the dashboard layout
                      </p>
                    </div>
                  )}

                  {/* WAWU Section */}
                  <div className="bg-slate-700/30 rounded-lg p-4 border border-slate-600">
                    <h4 className="text-white font-medium mb-3 flex items-center gap-2">
                      <Target className="w-4 h-4 text-purple-400" />
                      WAWU (Weekly Active Workflow Users)
                    </h4>
                    <div className="grid grid-cols-5 gap-3">
                      <div className="bg-purple-500/10 rounded-lg p-3 border border-purple-500/30">
                        <p className="text-purple-400 text-xs">Total Active Users</p>
                        <p className="text-2xl font-bold text-white">{weeklyMetrics.wawu?.total_active_users || 0}</p>
                      </div>
                      <div className="bg-slate-700/50 rounded-lg p-3 border border-slate-600">
                        <p className="text-slate-400 text-xs">Alerts Created</p>
                        <p className="text-xl font-bold text-white">{weeklyMetrics.wawu?.workflow_actions?.alerts || 0}</p>
                      </div>
                      <div className="bg-slate-700/50 rounded-lg p-3 border border-slate-600">
                        <p className="text-slate-400 text-xs">Tasks Scheduled</p>
                        <p className="text-xl font-bold text-white">{weeklyMetrics.wawu?.workflow_actions?.scheduled_tasks || 0}</p>
                      </div>
                      <div className="bg-slate-700/50 rounded-lg p-3 border border-slate-600">
                        <p className="text-slate-400 text-xs">Leads Created</p>
                        <p className="text-xl font-bold text-white">{weeklyMetrics.wawu?.workflow_actions?.leads || 0}</p>
                      </div>
                      <div className="bg-slate-700/50 rounded-lg p-3 border border-slate-600">
                        <p className="text-slate-400 text-xs">Automation Commands</p>
                        <p className="text-xl font-bold text-white">{weeklyMetrics.wawu?.workflow_actions?.automation_commands || 0}</p>
                      </div>
                    </div>
                  </div>

                  {/* Conversions Section */}
                  <div className="bg-slate-700/30 rounded-lg p-4 border border-slate-600">
                    <h4 className="text-white font-medium mb-3 flex items-center gap-2">
                      <TrendingUp className="w-4 h-4 text-green-400" />
                      Conversion Metrics
                    </h4>
                    <div className="grid grid-cols-3 gap-3">
                      <div className="bg-green-500/10 rounded-lg p-3 border border-green-500/30">
                        <p className="text-green-400 text-xs">Free to Pro (New)</p>
                        <p className="text-2xl font-bold text-white">{weeklyMetrics.conversions?.free_to_pro_new || 0}</p>
                        <p className="text-green-300 text-xs">Rate: {((weeklyMetrics.conversions?.free_to_pro_rate || 0) * 100).toFixed(1)}%</p>
                      </div>
                      <div className="bg-blue-500/10 rounded-lg p-3 border border-blue-500/30">
                        <p className="text-blue-400 text-xs">Top-ups Purchased</p>
                        <p className="text-2xl font-bold text-white">{weeklyMetrics.conversions?.topups_purchased || 0}</p>
                        <p className="text-blue-300 text-xs">Attach Rate: {((weeklyMetrics.conversions?.topup_attach_rate || 0) * 100).toFixed(1)}%</p>
                      </div>
                      <div className="bg-orange-500/10 rounded-lg p-3 border border-orange-500/30">
                        <p className="text-orange-400 text-xs">Team/Agency Expansions</p>
                        <p className="text-2xl font-bold text-white">{weeklyMetrics.conversions?.broker_team_expansions || 0}</p>
                        <p className="text-orange-300 text-xs">B2B Pilot → Retainer: {weeklyMetrics.conversions?.b2b_pilot_to_retainer || 0}</p>
                      </div>
                    </div>
                  </div>

                  {/* Retention Section */}
                  <div className="bg-slate-700/30 rounded-lg p-4 border border-slate-600">
                    <h4 className="text-white font-medium mb-3 flex items-center gap-2">
                      <Users className="w-4 h-4 text-cyan-400" />
                      Retention (4-Week Cohort)
                    </h4>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="bg-cyan-500/10 rounded-lg p-3 border border-cyan-500/30">
                        <p className="text-cyan-400 text-xs">Cohort Size</p>
                        <p className="text-2xl font-bold text-white">{weeklyMetrics.retention?.cohort_size || 0}</p>
                      </div>
                      <div className="bg-cyan-500/10 rounded-lg p-3 border border-cyan-500/30">
                        <p className="text-cyan-400 text-xs">Retention Rate</p>
                        <p className="text-2xl font-bold text-white">{((weeklyMetrics.retention?.week_4_cohort_retention || 0) * 100).toFixed(1)}%</p>
                      </div>
                    </div>
                  </div>

                  {/* Workflow Activation Section */}
                  <div className="bg-slate-700/30 rounded-lg p-4 border border-slate-600">
                    <h4 className="text-white font-medium mb-3 flex items-center gap-2">
                      <Gauge className="w-4 h-4 text-yellow-400" />
                      Workflow Activation
                    </h4>
                    <div className="grid grid-cols-5 gap-3">
                      <div className="bg-yellow-500/10 rounded-lg p-3 border border-yellow-500/30">
                        <p className="text-yellow-400 text-xs">Activation Rate</p>
                        <p className="text-2xl font-bold text-white">{((weeklyMetrics.workflow_activation?.activation_rate || 0) * 100).toFixed(1)}%</p>
                      </div>
                      <div className="bg-slate-700/50 rounded-lg p-3 border border-slate-600">
                        <p className="text-slate-400 text-xs">Users with Alerts</p>
                        <p className="text-xl font-bold text-white">{weeklyMetrics.workflow_activation?.users_with_alerts || 0}</p>
                      </div>
                      <div className="bg-slate-700/50 rounded-lg p-3 border border-slate-600">
                        <p className="text-slate-400 text-xs">Users with Tasks</p>
                        <p className="text-xl font-bold text-white">{weeklyMetrics.workflow_activation?.users_with_tasks || 0}</p>
                      </div>
                      <div className="bg-slate-700/50 rounded-lg p-3 border border-slate-600">
                        <p className="text-slate-400 text-xs">Users with Leads</p>
                        <p className="text-xl font-bold text-white">{weeklyMetrics.workflow_activation?.users_with_leads || 0}</p>
                      </div>
                      <div className="bg-slate-700/50 rounded-lg p-3 border border-slate-600">
                        <p className="text-slate-400 text-xs">Total Active</p>
                        <p className="text-xl font-bold text-white">{weeklyMetrics.workflow_activation?.total_active_users || 0}</p>
                      </div>
                    </div>
                  </div>

                  {/* Guardrails Section */}
                  <div className="bg-slate-700/30 rounded-lg p-4 border border-slate-600">
                    <h4 className="text-white font-medium mb-3 flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 text-red-400" />
                      Guardrail Metrics
                    </h4>
                    <div className="grid grid-cols-4 gap-3">
                      <div className={`rounded-lg p-3 border ${weeklyMetrics.guardrails?.billing_incidents > 5 ? 'bg-red-500/20 border-red-500/50' : 'bg-slate-700/50 border-slate-600'}`}>
                        <p className="text-slate-400 text-xs">Billing Incidents</p>
                        <p className={`text-2xl font-bold ${weeklyMetrics.guardrails?.billing_incidents > 5 ? 'text-red-400' : 'text-white'}`}>
                          {weeklyMetrics.guardrails?.billing_incidents || 0}
                        </p>
                      </div>
                      <div className={`rounded-lg p-3 border ${weeklyMetrics.guardrails?.data_freshness_breaches > 10 ? 'bg-red-500/20 border-red-500/50' : 'bg-slate-700/50 border-slate-600'}`}>
                        <p className="text-slate-400 text-xs">Data Freshness Breaches</p>
                        <p className={`text-2xl font-bold ${weeklyMetrics.guardrails?.data_freshness_breaches > 10 ? 'text-red-400' : 'text-white'}`}>
                          {weeklyMetrics.guardrails?.data_freshness_breaches || 0}
                        </p>
                      </div>
                      <div className={`rounded-lg p-3 border ${weeklyMetrics.guardrails?.low_confidence_recommendations > 100 ? 'bg-red-500/20 border-red-500/50' : 'bg-slate-700/50 border-slate-600'}`}>
                        <p className="text-slate-400 text-xs">Low Confidence Recs</p>
                        <p className={`text-2xl font-bold ${weeklyMetrics.guardrails?.low_confidence_recommendations > 100 ? 'text-red-400' : 'text-white'}`}>
                          {weeklyMetrics.guardrails?.low_confidence_recommendations || 0}
                        </p>
                      </div>
                      <div className={`rounded-lg p-3 border ${weeklyMetrics.guardrails?.avg_time_to_first_value_hours > 48 ? 'bg-red-500/20 border-red-500/50' : 'bg-slate-700/50 border-slate-600'}`}>
                        <p className="text-slate-400 text-xs">Avg Time to First Value</p>
                        <p className={`text-2xl font-bold ${weeklyMetrics.guardrails?.avg_time_to_first_value_hours > 48 ? 'text-red-400' : 'text-white'}`}>
                          {weeklyMetrics.guardrails?.avg_time_to_first_value_hours || 0}h
                        </p>
                      </div>
                    </div>
                  </div>

                  <p className="text-slate-500 text-xs text-center">
                    Generated at: {weeklyMetrics.generated_at ? new Date(weeklyMetrics.generated_at).toLocaleString() : 'N/A'} • Period: {weeklyMetrics.period}
                  </p>
                </>
              ) : (
                <div className="text-center py-10 text-slate-400">
                  <TrendingUp className="w-10 h-10 mx-auto mb-3 opacity-50" />
                  <p>No metrics data available. Click "Refresh" to load.</p>
                </div>
              )}
            </div>
          )}

          {/* Pricing Config Tab */}
          {activeTab === 'pricing' && (
            <PricingManager />
          )}

          {/* Revenue Tab */}
          {activeTab === 'revenue' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                  <ArrowUpRight className="h-5 w-5 text-green-400" />
                  Revenue Dashboard
                </h3>
                <button onClick={fetchRevenueData} className="px-3 py-1.5 bg-slate-700 rounded-lg text-slate-300 hover:bg-slate-600 flex items-center gap-2 text-sm">
                  <RefreshCw className="h-4 w-4" /> Refresh
                </button>
              </div>
              {revenueData ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-gradient-to-br from-green-900/40 to-green-800/20 rounded-xl p-4 border border-green-700/50">
                      <p className="text-xs text-green-400 uppercase tracking-wide">Promo Revenue (30d)</p>
                      <p className="text-2xl font-bold text-white mt-1">₹{(revenueData.revenue?.revenue_estimate?.promo_inr || 0).toLocaleString()}</p>
                      <p className="text-xs text-slate-400 mt-1">{revenueData.revenue?.total_units_charged || 0} units @ ₹2/unit</p>
                    </div>
                    <div className="bg-gradient-to-br from-blue-900/40 to-blue-800/20 rounded-xl p-4 border border-blue-700/50">
                      <p className="text-xs text-blue-400 uppercase tracking-wide">Regular Revenue (30d)</p>
                      <p className="text-2xl font-bold text-white mt-1">₹{(revenueData.revenue?.revenue_estimate?.regular_inr || 0).toLocaleString()}</p>
                      <p className="text-xs text-slate-400 mt-1">{revenueData.revenue?.total_units_charged || 0} units @ ₹10/unit</p>
                    </div>
                    <div className="bg-gradient-to-br from-purple-900/40 to-purple-800/20 rounded-xl p-4 border border-purple-700/50">
                      <p className="text-xs text-purple-400 uppercase tracking-wide">Active Users (30d)</p>
                      <p className="text-2xl font-bold text-white mt-1">{revenueData.revenue?.active_users || 0}</p>
                      <p className="text-xs text-slate-400 mt-1">{revenueData.revenue?.avg_units_per_user || 0} avg units/user</p>
                    </div>
                  </div>
                  {revenueData.cloud && (
                    <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
                      <h4 className="text-sm font-semibold text-white mb-3">Cloud LLM Costs (7d)</h4>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        <div><p className="text-xs text-slate-400">Total Cost</p><p className="text-lg text-white">${(revenueData.cloud.total_cost_usd || 0).toFixed(4)}</p></div>
                        <div><p className="text-xs text-slate-400">Total Calls</p><p className="text-lg text-white">{revenueData.cloud.total_calls || 0}</p></div>
                        <div><p className="text-xs text-slate-400">Avg Cost/Call</p><p className="text-lg text-white">${(revenueData.cloud.avg_cost_per_call_usd || 0).toFixed(6)}</p></div>
                        <div><p className="text-xs text-slate-400">Local Calls</p><p className="text-lg text-white">{revenueData.cloud.local_calls || 0}</p></div>
                      </div>
                    </div>
                  )}
                  <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
                    <h4 className="text-sm font-semibold text-white mb-3">Usage Breakdown (7d vs 30d)</h4>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-xs text-slate-400 mb-2">Last 7 Days</p>
                        {revenueData.usage?.last_7_days?.total_actions ? Object.entries(revenueData.usage.last_7_days.total_actions).slice(0, 6).map(([action, count]) => (
                          <div key={action} className="flex justify-between text-sm py-1 border-b border-slate-700/50">
                            <span className="text-slate-300">{action.replace(/_/g, ' ')}</span>
                            <span className="text-white font-medium">{count}</span>
                          </div>
                        )) : <p className="text-xs text-slate-500">No data available</p>}
                      </div>
                      <div>
                        <p className="text-xs text-slate-400 mb-2">Last 30 Days</p>
                        {revenueData.usage?.last_30_days?.total_actions ? Object.entries(revenueData.usage.last_30_days.total_actions).slice(0, 6).map(([action, count]) => (
                          <div key={action} className="flex justify-between text-sm py-1 border-b border-slate-700/50">
                            <span className="text-slate-300">{action.replace(/_/g, ' ')}</span>
                            <span className="text-white font-medium">{count}</span>
                          </div>
                        )) : <p className="text-xs text-slate-500">No data available</p>}
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-center py-12">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500"></div>
                </div>
              )}
            </div>
          )}

          {/* Ingestion Tab */}
          {activeTab === 'data' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                  <Database className="h-5 w-5 text-blue-400" />
                  Data Ingestion & Freshness
                </h3>
                <button onClick={fetchIngestionData} className="px-3 py-1.5 bg-slate-700 rounded-lg text-slate-300 hover:bg-slate-600 flex items-center gap-2 text-sm">
                  <RefreshCw className="h-4 w-4" /> Refresh
                </button>
              </div>
              {ingestionData ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
                      <p className="text-xs text-slate-400 uppercase tracking-wide">Properties</p>
                      <p className="text-2xl font-bold text-white mt-1">{ingestionData.status?.database?.properties?.toLocaleString() || 0}</p>
                    </div>
                    <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
                      <p className="text-xs text-slate-400 uppercase tracking-wide">POIs</p>
                      <p className="text-2xl font-bold text-white mt-1">{ingestionData.status?.database?.pois?.toLocaleString() || 0}</p>
                    </div>
                    <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
                      <p className="text-xs text-slate-400 uppercase tracking-wide">Buildings</p>
                      <p className="text-2xl font-bold text-white mt-1">{ingestionData.status?.database?.buildings?.toLocaleString() || 0}</p>
                    </div>
                  </div>
                  {ingestionData.brain?.success && (
                    <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
                      <h4 className="text-sm font-semibold text-white mb-3">Locality Brain Status</h4>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        <div><p className="text-xs text-slate-400">Total Localities</p><p className="text-lg text-white">{ingestionData.brain.status?.total_localities || 0}</p></div>
                        <div><p className="text-xs text-slate-400">With POIs</p><p className="text-lg text-white">{ingestionData.brain.status?.with_pois || 0}</p></div>
                        <div><p className="text-xs text-slate-400">With Transport</p><p className="text-lg text-white">{ingestionData.brain.status?.with_transport || 0}</p></div>
                        <div><p className="text-xs text-slate-400">Last Updated</p><p className="text-lg text-white">{ingestionData.brain.status?.last_updated ? new Date(ingestionData.brain.status.last_updated).toLocaleDateString() : 'N/A'}</p></div>
                      </div>
                      {ingestionData.brain.status?.growth_phases && (
                        <div className="mt-3">
                          <p className="text-xs text-slate-400 mb-2">Growth Phase Distribution</p>
                          <div className="flex flex-wrap gap-2">
                            {Object.entries(ingestionData.brain.status.growth_phases).map(([phase, count]) => (
                              <span key={phase} className="px-2 py-1 bg-slate-700 rounded text-xs text-slate-300">
                                {phase}: {count}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                  {ingestionData.status?.sources && Object.keys(ingestionData.status.sources).length > 0 && (
                    <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
                      <h4 className="text-sm font-semibold text-white mb-3">Data Sources</h4>
                      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                        {Object.entries(ingestionData.status.sources).map(([source, count]) => (
                          <div key={source} className="flex justify-between text-sm py-1 px-3 bg-slate-700/50 rounded">
                            <span className="text-slate-300">{source}</span>
                            <span className="text-white font-medium">{count}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  <button onClick={() => fetch(`${API_URL}/api/admin/rebuild-locality-brain`, { method: 'POST', headers: { 'Authorization': `Bearer ${token}` } }).then(r => r.json()).then(() => fetchIngestionData())}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2 text-sm">
                    <RefreshCw className="h-4 w-4" /> Rebuild Locality Brain
                  </button>
                </div>
              ) : (
                <div className="flex items-center justify-center py-12">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500"></div>
                </div>
              )}
            </div>
          )}

          {/* Coverage Tab */}
          {activeTab === 'data' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                  <MapPin className="h-5 w-5 text-orange-400" />
                  Micro-Market Coverage
                </h3>
                <button onClick={fetchCoverageData} className="px-3 py-1.5 bg-slate-700 rounded-lg text-slate-300 hover:bg-slate-600 flex items-center gap-2 text-sm">
                  <RefreshCw className="h-4 w-4" /> Refresh
                </button>
              </div>
              {coverageData ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-gradient-to-br from-green-900/40 to-green-800/20 rounded-xl p-4 border border-green-700/50">
                      <p className="text-xs text-green-400 uppercase tracking-wide">Confident Coverage</p>
                      <p className="text-2xl font-bold text-white mt-1">{coverageData.status?.with_pois || 0}</p>
                      <p className="text-xs text-slate-400">Localities with POI data</p>
                    </div>
                    <div className="bg-gradient-to-br from-yellow-900/40 to-yellow-800/20 rounded-xl p-4 border border-yellow-700/50">
                      <p className="text-xs text-yellow-400 uppercase tracking-wide">Partial Coverage</p>
                      <p className="text-2xl font-bold text-white mt-1">{Math.max(0, (coverageData.status?.total_localities || 0) - (coverageData.status?.with_pois || 0))}</p>
                      <p className="text-xs text-slate-400">Localities without POI data</p>
                    </div>
                    <div className="bg-gradient-to-br from-blue-900/40 to-blue-800/20 rounded-xl p-4 border border-blue-700/50">
                      <p className="text-xs text-blue-400 uppercase tracking-wide">Total Localities</p>
                      <p className="text-2xl font-bold text-white mt-1">{coverageData.status?.total_localities || 0}</p>
                      <p className="text-xs text-slate-400">In locality brain</p>
                    </div>
                  </div>
                  {coverageData.status?.growth_phases && (
                    <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
                      <h4 className="text-sm font-semibold text-white mb-3">Growth Phase Distribution</h4>
                      <div className="space-y-2">
                        {Object.entries(coverageData.status.growth_phases).map(([phase, count]) => {
                          const total = coverageData.status?.total_localities || 1
                          const pct = ((count / total) * 100).toFixed(1)
                          return (
                            <div key={phase} className="flex items-center gap-3">
                              <span className="text-sm text-slate-300 w-24 capitalize">{phase || 'Unknown'}</span>
                              <div className="flex-1 bg-slate-700 rounded-full h-2">
                                <div className={`h-2 rounded-full ${phase === 'emerging' ? 'bg-yellow-500' : phase === 'growing' ? 'bg-blue-500' : phase === 'mature' ? 'bg-green-500' : 'bg-slate-500'}`}
                                  style={{ width: `${pct}%` }} />
                              </div>
                              <span className="text-sm text-slate-400 w-16 text-right">{count} ({pct}%)</span>
                            </div>
                          )
                        })}
                      </div>
                    </div>
                  )}
                  <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
                    <h4 className="text-sm font-semibold text-white mb-3">Coverage Health Summary</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="flex items-center gap-3">
                        <div className="w-3 h-3 rounded-full bg-green-500"></div>
                        <span className="text-sm text-slate-300">High confidence: POIs + Transport + Properties</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                        <span className="text-sm text-slate-300">Medium confidence: POIs OR Transport only</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="w-3 h-3 rounded-full bg-orange-500"></div>
                        <span className="text-sm text-slate-300">Low confidence: Properties only</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="w-3 h-3 rounded-full bg-red-500"></div>
                        <span className="text-sm text-slate-300">No data: Empty locality</span>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-center py-12">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500"></div>
                </div>
              )}
            </div>
          )}

          {/* Learning Tab */}
          {activeTab === 'ai' && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                  <Brain className="h-5 w-5 text-pink-400" />
                  Self-Learning Engine
                </h3>
                <div className="flex gap-2">
                  <button onClick={() => fetchLearningData()} className="px-3 py-1.5 bg-slate-700 rounded-lg text-slate-300 hover:bg-slate-600 flex items-center gap-2 text-sm">
                    <RefreshCw className="h-4 w-4" /> Refresh
                  </button>
                  <button onClick={() => { if (window.confirm('Reset all learning data?')) fetch(`${API_URL}/api/admin/agentic/learning/reset`, { method: 'POST', headers: { 'Authorization': `Bearer ${token}` } }).then(() => fetchLearningData()) }}
                    className="px-3 py-1.5 bg-red-900/50 rounded-lg text-red-300 hover:bg-red-800/50 flex items-center gap-2 text-sm">
                    <Trash2 className="h-4 w-4" /> Reset
                  </button>
                </div>
              </div>
              {learningData ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
                      <p className="text-xs text-slate-400 uppercase tracking-wide">Total Feedback</p>
                      <p className="text-2xl font-bold text-white mt-1">{learningData.total_feedback || 0}</p>
                    </div>
                    <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
                      <p className="text-xs text-slate-400 uppercase tracking-wide">Patterns Learned</p>
                      <p className="text-2xl font-bold text-white mt-1">{learningData.patterns_learned || 0}</p>
                    </div>
                    <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
                      <p className="text-xs text-slate-400 uppercase tracking-wide">Cache Hit Rate</p>
                      <p className="text-2xl font-bold text-white mt-1">{learningData.cache_hit_rate ? `${(learningData.cache_hit_rate * 100).toFixed(0)}%` : 'N/A'}</p>
                    </div>
                    <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
                      <p className="text-xs text-slate-400 uppercase tracking-wide">Avg Rating</p>
                      <p className="text-2xl font-bold text-white mt-1">{learningData.avg_rating?.toFixed(1) || 'N/A'}</p>
                    </div>
                  </div>
                  {learningData.tool_scores && Object.keys(learningData.tool_scores).length > 0 && (
                    <div className="bg-slate-800/50 rounded-xl p-4 border border-slate-700">
                      <h4 className="text-sm font-semibold text-white mb-3">Tool Effectiveness</h4>
                      <div className="space-y-2">
                        {Object.entries(learningData.tool_scores).map(([tool, score]) => (
                          <div key={tool} className="flex items-center gap-3">
                            <span className="text-sm text-slate-300 w-32 truncate">{tool}</span>
                            <div className="flex-1 bg-slate-700 rounded-full h-2">
                              <div className={`h-2 rounded-full ${score > 0.7 ? 'bg-green-500' : score > 0.4 ? 'bg-yellow-500' : 'bg-red-500'}`}
                                style={{ width: `${(score * 100)}%` }} />
                            </div>
                            <span className="text-sm text-slate-400 w-12 text-right">{(score * 100).toFixed(0)}%</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="flex items-center justify-center py-12">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500"></div>
                </div>
              )}
            </div>
          )}

          {/* System Status Tab */}
          {activeTab === 'status' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-white font-semibold">System Health</h3>
                <button
                  onClick={fetchSystemStatus}
                  disabled={loading}
                  className="flex items-center gap-2 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-white rounded-lg text-sm transition"
                >
                  <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
                  Refresh
                </button>
              </div>

              {loading ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-8 h-8 text-purple-500 animate-spin" />
                </div>
              ) : systemStatus?.error ? (
                <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400">
                  {systemStatus.error}
                </div>
              ) : systemStatus ? (
                <>
                <div className="grid grid-cols-2 gap-4">
                  {/* Backend */}
                  <StatusCard
                    title="Backend Server"
                    status={systemStatus.backend?.status || 'unknown'}
                    icon={Server}
                    details={[
                      { label: 'FastAPI', value: systemStatus.backend?.fastapi ? 'Running' : 'Down' },
                      { label: 'Port', value: '8000' },
                    ]}
                  />

                  {/* Database */}
                  <StatusCard
                    title="Database"
                    status={systemStatus.database?.status || 'unknown'}
                    icon={Database}
                    details={[
                      { label: 'Properties', value: systemStatus.database?.properties?.toLocaleString() || '0' },
                      { label: 'POIs', value: systemStatus.database?.pois?.toLocaleString() || '0' },
                      { label: 'Buildings', value: systemStatus.database?.buildings?.toLocaleString() || '0' },
                    ]}
                  />

                  {/* Pinecone */}
                  <StatusCard
                    title="Pinecone (RAG)"
                    status={systemStatus.pinecone?.status || 'unknown'}
                    icon={Cloud}
                    details={[
                      { label: 'Vectors', value: systemStatus.pinecone?.vectors?.toLocaleString() || '0' },
                      { label: 'Index', value: systemStatus.pinecone?.index || 'N/A' },
                    ]}
                  />

                  {/* FAISS */}
                  <StatusCard
                    title="FAISS (Local)"
                    status={systemStatus.faiss?.status || 'unknown'}
                    icon={HardDrive}
                    details={[
                      { label: 'Vectors', value: systemStatus.faiss?.vectors?.toLocaleString() || '0' },
                      { label: 'Namespaces', value: systemStatus.faiss?.namespaces || '0' },
                    ]}
                  />

                  {/* AI Services */}
                  <StatusCard
                    title="AI Services"
                    status={systemStatus.ai?.status || 'unknown'}
                    icon={Zap}
                    details={[
                      { label: 'Embeddings', value: systemStatus.ai?.embeddings ? 'Ready' : 'Down' },
                      { label: 'Reasoning', value: systemStatus.ai?.reasoning ? 'Ready' : 'Down' },
                    ]}
                  />

                  {/* Cache */}
                  <StatusCard
                    title="Query Cache"
                    status={systemStatus.cache?.status || 'unknown'}
                    icon={BarChart3}
                    details={[
                      { label: 'Entries', value: systemStatus.cache?.entries?.toLocaleString() || '0' },
                      { label: 'Hit Rate', value: `${systemStatus.cache?.hitRate || 0}%` },
                    ]}
                  />

                  {/* Insight Cache */}
                  <StatusCard
                    title="AI Insight Cache"
                    status={systemStatus.insight_cache?.status || 'unknown'}
                    icon={Brain}
                    details={[
                      { label: 'Cached Insights', value: systemStatus.insight_cache?.cached_insights?.toLocaleString() || '0' },
                      { label: 'Cache Hits', value: systemStatus.insight_cache?.cache_hits?.toLocaleString() || '0' },
                      { label: 'Users', value: systemStatus.insight_cache?.unique_users?.toLocaleString() || '0' },
                      { label: 'TTL', value: `${systemStatus.insight_cache?.ttl_days || 30} days` },
                    ]}
                  />
                </div>

                {/* Insight Cache Details */}
                {systemStatus.insight_cache && systemStatus.insight_cache.status !== 'down' && (
                  <div className="mt-4 bg-slate-700/30 rounded-lg p-4">
                    <h4 className="text-white font-medium mb-2 flex items-center gap-2">
                      <Zap className="w-4 h-4" />
                      AI Insights & Training Data
                    </h4>
                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div className="flex justify-between">
                        <span className="text-slate-400">Total Charges:</span>
                        <span className="text-white font-medium">
                          {systemStatus.insight_cache.total_charges?.toLocaleString() || 0}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Units Charged:</span>
                        <span className="text-white font-medium">
                          {systemStatus.insight_cache.total_units?.toLocaleString() || 0}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Training Samples:</span>
                        <span className="text-green-400 font-medium">
                          {systemStatus.insight_cache.training_samples?.toLocaleString() || 0}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Cache Radius:</span>
                        <span className="text-blue-400">
                          {systemStatus.insight_cache.radius_km || 2}km
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Dedup Window:</span>
                        <span className="text-blue-400">
                          30 days
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Efficiency:</span>
                        <span className="text-green-400">
                          {systemStatus.insight_cache.cache_hits > 0 
                            ? `${Math.round((systemStatus.insight_cache.cache_hits / (systemStatus.insight_cache.total_charges + systemStatus.insight_cache.cache_hits)) * 100)}% saved`
                            : '0% saved'}
                        </span>
                      </div>
                    </div>
                  </div>
                )}

                {/* Duplicates Check */}
                {systemStatus.duplicates && (
                  <div className="mt-4 bg-slate-700/30 rounded-lg p-4">
                    <h4 className="text-white font-medium mb-2">Data Integrity</h4>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div className="flex justify-between">
                        <span className="text-slate-400">Database Duplicates:</span>
                        <span className={systemStatus.duplicates.database === 0 ? 'text-green-400' : 'text-red-400'}>
                          {systemStatus.duplicates.database === 0 ? '✓ None' : systemStatus.duplicates.database}
                        </span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-slate-400">Pinecone Sync:</span>
                        <span className="text-green-400">
                          {systemStatus.pinecone?.vectors === systemStatus.database?.properties 
                            ? '✓ In Sync' 
                            : `${systemStatus.pinecone?.vectors || 0} vectors`}
                        </span>
                      </div>
                    </div>
                  </div>
                )}
                </>
              ) : null}
            </div>
          )}

          {/* Tests Tab */}
          {activeTab === 'tests' && (
            <div className="space-y-4">
              {/* Header with tier filters and actions */}
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div>
                  <h3 className="text-white font-semibold text-lg">Unified Test Suite</h3>
                  <p className="text-slate-400 text-xs mt-0.5">33 tests across Infrastructure, Core AI, APIs, Business Logic, Quality & Debug</p>
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                  <button
                    onClick={() => { setSelectedTier(null); runTests(null) }}
                    disabled={runningTest}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition disabled:opacity-50 ${selectedTier === null ? 'bg-purple-600 text-white ring-2 ring-purple-400' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'}`}
                  >
                    All Tests
                  </button>
                  <button
                    onClick={() => { setSelectedTier(1); runTests(1) }}
                    disabled={runningTest}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition disabled:opacity-50 ${selectedTier === 1 ? 'bg-red-600 text-white ring-2 ring-red-400' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'}`}
                  >
                    🔴 Critical
                  </button>
                  <button
                    onClick={() => { setSelectedTier(2); runTests(2) }}
                    disabled={runningTest}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition disabled:opacity-50 ${selectedTier === 2 ? 'bg-yellow-600 text-white ring-2 ring-yellow-400' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'}`}
                  >
                    🟡 Functional
                  </button>
                  <button
                    onClick={() => { setSelectedTier(3); runTests(3) }}
                    disabled={runningTest}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition disabled:opacity-50 ${selectedTier === 3 ? 'bg-green-600 text-white ring-2 ring-green-400' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'}`}
                  >
                    🟢 Quality
                  </button>
                  {testResults && !testResults.error && (
                    <button
                      onClick={async () => {
                        try {
                          const resp = await fetch(`${API_URL}/api/test-suite/report`, { headers: { 'Authorization': `Bearer ${token}` } })
                          if (resp.ok) {
                            const data = await resp.json()
                            const blob = new Blob([data.report], { type: 'text/markdown' })
                            const url = URL.createObjectURL(blob)
                            const a = document.createElement('a')
                            a.href = url; a.download = `valora_test_report_${new Date().toISOString().split('T')[0]}.md`
                            a.click(); URL.revokeObjectURL(url)
                          }
                        } catch (e) { console.error('Download failed:', e) }
                      }}
                      className="flex items-center gap-1 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded-lg text-xs transition"
                    >
                      <Download className="w-3 h-3" />
                      Report
                    </button>
                  )}
                </div>
              </div>

              {/* Running indicator */}
              {runningTest && (
                <div className="bg-purple-500/10 border border-purple-500/30 rounded-lg p-4 flex items-center gap-3">
                  <Loader2 className="w-6 h-6 text-purple-400 animate-spin" />
                  <div>
                    <p className="text-purple-300 font-medium text-sm">Running tests...</p>
                    <p className="text-purple-400/70 text-xs">Testing local LLM, database, APIs, business logic, and quality checks</p>
                  </div>
                </div>
              )}

              {testResults?.error ? (
                <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400">
                  <p className="font-medium mb-1">Test Suite Error</p>
                  <pre className="text-xs whitespace-pre-wrap opacity-80">{testResults.error}</pre>
                </div>
              ) : testResults ? (
                <div className="space-y-4">
                  {/* Summary Cards */}
                  <div className="grid grid-cols-5 gap-3">
                    <div className="bg-slate-700/50 rounded-lg p-3 border border-slate-600 text-center">
                      <p className="text-2xl font-bold text-white">{testResults.total}</p>
                      <p className="text-slate-400 text-xs">Total</p>
                    </div>
                    <div className="bg-green-500/10 rounded-lg p-3 border border-green-500/30 text-center">
                      <p className="text-2xl font-bold text-green-400">{testResults.passed}</p>
                      <p className="text-green-400/70 text-xs">Passed</p>
                    </div>
                    <div className="bg-red-500/10 rounded-lg p-3 border border-red-500/30 text-center">
                      <p className="text-2xl font-bold text-red-400">{testResults.failed}</p>
                      <p className="text-red-400/70 text-xs">Failed</p>
                    </div>
                    <div className={`rounded-lg p-3 border text-center ${testResults.pass_rate >= 80 ? 'bg-green-500/10 border-green-500/30' : testResults.pass_rate >= 50 ? 'bg-yellow-500/10 border-yellow-500/30' : 'bg-red-500/10 border-red-500/30'}`}>
                      <p className={`text-2xl font-bold ${testResults.pass_rate >= 80 ? 'text-green-400' : testResults.pass_rate >= 50 ? 'text-yellow-400' : 'text-red-400'}`}>{testResults.pass_rate}%</p>
                      <p className="text-slate-400 text-xs">Pass Rate</p>
                    </div>
                    <div className="bg-slate-700/50 rounded-lg p-3 border border-slate-600 text-center">
                      <p className="text-2xl font-bold text-blue-400">{(testResults.duration_ms / 1000).toFixed(1)}s</p>
                      <p className="text-slate-400 text-xs">Duration</p>
                    </div>
                  </div>

                  {/* Tier Breakdown */}
                  {testResults.tier_results && (
                    <div className="grid grid-cols-3 gap-3">
                      {Object.entries(testResults.tier_results).map(([tier, data]) => {
                        const pct = data.total > 0 ? Math.round(data.passed / data.total * 100) : 0
                        return (
                          <div key={tier} className={`rounded-lg p-3 border ${
                            tier === 'Critical' ? 'bg-red-500/10 border-red-500/30' :
                            tier === 'Functional' ? 'bg-yellow-500/10 border-yellow-500/30' :
                            'bg-green-500/10 border-green-500/30'
                          }`}>
                            <div className="flex items-center justify-between">
                              <p className="text-slate-300 text-xs font-medium">{tier}</p>
                              <span className={`text-xs font-bold ${pct === 100 ? 'text-green-400' : 'text-red-400'}`}>{pct}%</span>
                            </div>
                            <div className="mt-2 h-1.5 bg-slate-700 rounded-full overflow-hidden">
                              <div className={`h-full rounded-full transition-all duration-500 ${pct === 100 ? 'bg-green-500' : pct >= 50 ? 'bg-yellow-500' : 'bg-red-500'}`} style={{ width: `${pct}%` }} />
                            </div>
                            <p className="text-slate-400 text-xs mt-1">{data.passed}/{data.total} passed</p>
                          </div>
                        )
                      })}
                    </div>
                  )}

                  {/* Category Breakdown */}
                  {testResults.category_results && (
                    <div className="bg-slate-700/30 rounded-lg p-3 border border-slate-600">
                      <p className="text-slate-300 text-xs font-medium mb-2">By Category</p>
                      <div className="grid grid-cols-3 gap-2">
                        {Object.entries(testResults.category_results).map(([cat, data]) => (
                          <div key={cat} className="flex items-center justify-between bg-slate-800/50 rounded px-2 py-1.5">
                            <span className="text-slate-300 text-xs">{cat}</span>
                            <span className={`text-xs font-medium ${data.failed === 0 ? 'text-green-400' : 'text-red-400'}`}>
                              {data.passed}/{data.total}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Grouped Test Results */}
                  {(() => {
                    const tests = testResults.results || testResults.tests || []
                    const groups = {}
                    tests.forEach(t => {
                      const cat = t.category || 'Other'
                      if (!groups[cat]) groups[cat] = []
                      groups[cat].push(t)
                    })
                    return Object.entries(groups).map(([category, catTests]) => (
                      <div key={category} className="space-y-1">
                        <div className="flex items-center gap-2 mt-3 mb-1">
                          <span className="text-slate-300 text-xs font-semibold uppercase tracking-wider">{category}</span>
                          <span className="text-slate-500 text-xs">({catTests.filter(t => t.passed).length}/{catTests.length})</span>
                        </div>
                        {catTests.map((test, i) => (
                          <div key={i} className={`rounded-lg p-3 border transition ${test.passed ? 'bg-slate-700/30 border-slate-700 hover:border-slate-600' : 'bg-red-500/5 border-red-500/20 hover:border-red-500/40'}`}>
                            <div className="flex items-center justify-between">
                              <div className="flex items-center gap-3 min-w-0">
                                {test.passed ? (
                                  <CheckCircle className="w-4 h-4 text-green-400 flex-shrink-0" />
                                ) : (
                                  <XCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
                                )}
                                <div className="min-w-0 flex-1">
                                  <p className="text-white text-sm font-medium">{test.test_name || test.name}</p>
                                  {test.details && <p className="text-slate-400 text-xs mt-0.5">{test.details}</p>}
                                  {test.error && (
                                    <p className="text-red-400 text-xs mt-0.5 break-words" title={test.error}>
                                      ⚠ {test.error}
                                    </p>
                                  )}
                                </div>
                              </div>
                              <div className="flex items-center gap-2 flex-shrink-0 ml-2">
                                {test.severity === 'critical' && (
                                  <span className="px-1.5 py-0.5 bg-red-500/20 text-red-400 text-[10px] rounded font-medium">CRITICAL</span>
                                )}
                                {test.severity === 'warning' && (
                                  <span className="px-1.5 py-0.5 bg-yellow-500/20 text-yellow-400 text-[10px] rounded font-medium">WARN</span>
                                )}
                                <span className={`text-xs font-mono ${test.passed ? 'text-green-400/70' : 'text-red-400/70'}`}>
                                  {test.duration_ms || 0}ms
                                </span>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    ))
                  })()}

                  {/* Run metadata */}
                  <div className="bg-slate-700/20 rounded-lg p-3 text-center">
                    <p className="text-slate-500 text-xs">
                      Run: {testResults.run_id} • {testResults.started_at ? new Date(testResults.started_at).toLocaleString() : ''}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="text-center py-12 text-slate-400">
                  <TestTube className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p className="font-medium">Click a tier button or "All Tests" to run the unified test suite</p>
                  <p className="text-xs mt-2 text-slate-500">Tests include: LLM health, database, APIs, business logic, intent classification, quality & debug checks</p>
                </div>
              )}


              {/* Production Debug Recommendations */}
              <div className="border-t border-slate-700 pt-4"></div>
              <div className="bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/30 rounded-lg p-4">
                <h4 className="text-white font-medium text-sm flex items-center gap-2 mb-3">
                  <FileText className="w-4 h-4 text-blue-400" />
                  Production Debug Recommendations
                </h4>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="bg-slate-800/50 rounded p-2">
                    <span className="text-blue-400 font-medium">💡 LLM Latency Monitor</span>
                    <p className="text-slate-400 mt-1">Track p50/p95/p99 response times for chat endpoint</p>
                  </div>
                  <div className="bg-slate-800/50 rounded p-2">
                    <span className="text-blue-400 font-medium">💡 Error Rate Dashboard</span>
                    <p className="text-slate-400 mt-1">Alert when 5xx rate exceeds 1% in 5-min window</p>
                  </div>
                  <div className="bg-slate-800/50 rounded p-2">
                    <span className="text-blue-400 font-medium">💡 Credit Burn Auditing</span>
                    <p className="text-slate-400 mt-1">Verify no double-charges or credit leaks per session</p>
                  </div>
                  <div className="bg-slate-800/50 rounded p-2">
                    <span className="text-blue-400 font-medium">💡 DB Query Performance</span>
                    <p className="text-slate-400 mt-1">Track slow queries (&gt;500ms) and missing indexes</p>
                  </div>
                  <div className="bg-slate-800/50 rounded p-2">
                    <span className="text-blue-400 font-medium">💡 Cache Hit/Miss Ratio</span>
                    <p className="text-slate-400 mt-1">Monitor RAG and query cache efficiency over time</p>
                  </div>
                  <div className="bg-slate-800/50 rounded p-2">
                    <span className="text-blue-400 font-medium">💡 Hallucination Detection</span>
                    <p className="text-slate-400 mt-1">Flag responses with unverifiable claims or wrong data</p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* User Memory Tab */}
          {activeTab === 'users' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-white font-semibold">User Session Memory</h3>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={prefsUserId}
                    onChange={(e) => setPrefsUserId(e.target.value)}
                    placeholder="User ID"
                    className="bg-slate-700 border border-slate-600 rounded-lg px-3 py-1.5 text-white text-sm w-32 focus:outline-none focus:border-purple-500"
                  />
                  <button
                    onClick={() => fetchUserPreferences(prefsUserId)}
                    disabled={loadingPrefs}
                    className="flex items-center gap-2 px-3 py-1.5 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm transition disabled:opacity-50"
                  >
                    {loadingPrefs ? <Loader2 className="w-4 h-4 animate-spin" /> : <Eye className="w-4 h-4" />}
                    Load
                  </button>
                </div>
              </div>

              {loadingPrefs ? (
                <div className="flex items-center justify-center py-12">
                  <Loader2 className="w-8 h-8 text-purple-500 animate-spin" />
                </div>
              ) : userPrefs?.error ? (
                <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400">
                  {userPrefs.error}
                </div>
              ) : userPrefs ? (
                <div className="space-y-4">
                  {/* User Info Header */}
                  <div className="bg-gradient-to-r from-purple-500/10 to-blue-500/10 border border-purple-500/30 rounded-lg p-4">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-purple-600 rounded-full flex items-center justify-center">
                          <Users className="w-5 h-5 text-white" />
                        </div>
                        <div>
                          <h4 className="text-white font-medium">{userPrefs.user_id}</h4>
                          <p className="text-slate-400 text-xs">Session Memory Active</p>
                        </div>
                      </div>
                      <button
                        onClick={() => clearUserPreferences(prefsUserId)}
                        className="flex items-center gap-2 px-3 py-1.5 bg-red-600/20 hover:bg-red-600/40 text-red-400 rounded-lg text-sm transition border border-red-500/30"
                      >
                        <Trash2 className="w-4 h-4" />
                        Clear Session
                      </button>
                    </div>
                  </div>

                  {/* Preferences */}
                  <div className="bg-slate-700/50 rounded-lg p-4">
                    <h4 className="text-white font-medium mb-3 flex items-center gap-2">
                      <Settings className="w-4 h-4 text-purple-400" />
                      Learned Preferences
                    </h4>
                    <div className="grid grid-cols-2 gap-4 text-sm">
                      <div>
                        <span className="text-slate-400 block text-xs mb-1">Preferred Areas</span>
                        <div className="flex flex-wrap gap-1">
                          {userPrefs.preferences?.preferred_areas?.length > 0 ? (
                            userPrefs.preferences.preferred_areas.map((area, i) => (
                              <span key={i} className="px-2 py-0.5 bg-purple-500/20 text-purple-300 rounded text-xs">
                                {area}
                              </span>
                            ))
                          ) : (
                            <span className="text-slate-500 text-xs">None learned yet</span>
                          )}
                        </div>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-xs mb-1">Budget Range</span>
                        <span className="text-white">
                          {userPrefs.preferences?.budget_range 
                            ? `₹${userPrefs.preferences.budget_range[0]}L - ₹${userPrefs.preferences.budget_range[1]}L`
                            : 'Not set'}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-xs mb-1">Property Types</span>
                        <div className="flex flex-wrap gap-1">
                          {userPrefs.preferences?.preferred_property_types?.length > 0 ? (
                            userPrefs.preferences.preferred_property_types.map((type, i) => (
                              <span key={i} className="px-2 py-0.5 bg-blue-500/20 text-blue-300 rounded text-xs">
                                {type}
                              </span>
                            ))
                          ) : (
                            <span className="text-slate-500 text-xs">None learned yet</span>
                          )}
                        </div>
                      </div>
                      <div>
                        <span className="text-slate-400 block text-xs mb-1">Exploration Style</span>
                        <span className="text-white capitalize">
                          {userPrefs.preferences?.exploration_style || 'balanced'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Recent Locations */}
                  <div className="bg-slate-700/50 rounded-lg p-4">
                    <h4 className="text-white font-medium mb-3 flex items-center gap-2">
                      <MapPin className="w-4 h-4 text-green-400" />
                      Recent Location Visits ({userPrefs.recent_locations?.length || 0})
                    </h4>
                    {userPrefs.recent_locations?.length > 0 ? (
                      <div className="space-y-2 max-h-40 overflow-y-auto">
                        {userPrefs.recent_locations.map((loc, i) => (
                          <div key={i} className="flex items-center justify-between bg-slate-800/50 rounded p-2 text-sm">
                            <div className="flex items-center gap-2">
                              <MapPin className="w-3 h-3 text-slate-400" />
                              <span className="text-white">{loc.name || 'Unknown'}</span>
                              <span className={`px-1.5 py-0.5 rounded text-xs ${
                                loc.sentiment === 'positive' ? 'bg-green-500/20 text-green-400' :
                                loc.sentiment === 'negative' ? 'bg-red-500/20 text-red-400' :
                                'bg-slate-500/20 text-slate-400'
                              }`}>
                                {loc.sentiment || 'neutral'}
                              </span>
                            </div>
                            <div className="flex items-center gap-2 text-xs text-slate-400">
                              <Clock className="w-3 h-3" />
                              {loc.timestamp ? new Date(loc.timestamp).toLocaleDateString() : 'N/A'}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-slate-500 text-sm">No location visits recorded</p>
                    )}
                  </div>

                  {/* Comparisons */}
                  {userPrefs.comparisons?.length > 0 && (
                    <div className="bg-slate-700/50 rounded-lg p-4">
                      <h4 className="text-white font-medium mb-3 flex items-center gap-2">
                        <BarChart3 className="w-4 h-4 text-blue-400" />
                        Property Comparisons ({userPrefs.comparisons.length})
                      </h4>
                      <div className="space-y-2">
                        {userPrefs.comparisons.map((comp, i) => (
                          <div key={i} className="flex items-center justify-between bg-slate-800/50 rounded p-2 text-sm">
                            <span className="text-slate-300">{comp.location_a} vs {comp.location_b}</span>
                            <span className="text-green-400 font-medium">Winner: {comp.winner}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-12 text-slate-400">
                  <Users className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>Enter a user ID and click Load to view session memory</p>
                  <p className="text-xs mt-2 text-slate-500">Try "default" or "test_user"</p>
                </div>
              )}
            </div>
          )}

          {/* Config Tab */}
          {activeTab === 'ai' && (
            <div className="space-y-4">
              <h3 className="text-white font-semibold">Configuration</h3>

              {/* Local LLM Settings Only */}
              <div className="bg-gradient-to-r from-green-500/10 to-blue-500/10 border border-green-500/30 rounded-lg p-4">
                <div className="flex items-center gap-3 mb-4">
                  <HardDrive className="w-5 h-5 text-green-400" />
                  <div>
                    <h4 className="text-white font-medium">Local LLM (Ollama)</h4>
                    <p className="text-slate-400 text-xs mt-0.5">
                      Using local Ollama instance - fully offline
                    </p>
                  </div>
                </div>

                <div className="space-y-3 mt-4 pt-4 border-t border-slate-600">
                  <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-3 mb-3">
                    <p className="text-green-400 text-xs">
                      <strong>Offline Mode:</strong> Requires Ollama running locally.
                    </p>
                  </div>
                  <div>
                    <label className="text-slate-300 text-xs block mb-1">Server URL</label>
                    <input
                      type="text"
                      value={llmConfig.local_url}
                      onChange={(e) => setLlmConfig(prev => ({ ...prev, local_url: e.target.value }))}
                      placeholder="http://127.0.0.1:11434/v1/chat/completions"
                      className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-green-500"
                    />
                  </div>
                  <div>
                    <label className="text-slate-300 text-xs block mb-1">Model Name</label>
                    <input
                      type="text"
                      value={llmConfig.local_model}
                      onChange={(e) => setLlmConfig(prev => ({ ...prev, local_model: e.target.value }))}
                      placeholder="valora-ai-mini:latest"
                      className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-green-500"
                    />
                  </div>
                  <div>
                    <label className="text-slate-300 text-xs block mb-1">Max Context (0 = unlimited)</label>
                    <input
                      type="number"
                      value={llmConfig.max_context}
                      onChange={(e) => setLlmConfig(prev => ({ ...prev, max_context: parseInt(e.target.value) || 0 }))}
                      placeholder="8192"
                      min="0"
                      className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-green-500"
                    />
                  </div>
                </div>

                {llmTestResult && (
                  <div className={`mt-3 p-2 rounded text-sm ${llmTestResult.success ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'}`}>
                    {llmTestResult.success ? <CheckCircle className="w-4 h-4 inline mr-2" /> : <XCircle className="w-4 h-4 inline mr-2" />}
                    {llmTestResult.message}
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex gap-2 mt-4">
                  <button
                    onClick={testLlmConnection}
                    disabled={llmSaving}
                    className="flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600 text-white rounded-lg text-sm transition disabled:opacity-50"
                  >
                    {llmSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
                    Test Connection
                  </button>
                  <button
                    onClick={saveLlmConfig}
                    disabled={llmSaving}
                    className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm transition disabled:opacity-50"
                  >
                    {llmSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                    Save Configuration
                  </button>
                </div>
              </div>

              <div className="bg-slate-700/50 rounded-lg p-4">
                <h4 className="text-white font-medium mb-3">Environment</h4>
                <div className="space-y-2 text-sm font-mono">
                  <ConfigRow label="PINECONE_INDEX" value="valora-realestate" />
                  <ConfigRow label="BACKEND_URL" value={API_URL} />
                  <ConfigRow label="EMBEDDING_MODEL" value="all-MiniLM-L6-v2" />
                </div>
              </div>

              <div className="bg-slate-700/50 rounded-lg p-4">
                <h4 className="text-white font-medium mb-3">Cache Settings</h4>
                <div className="space-y-2 text-sm">
                  <ConfigRow label="TTL (minutes)" value="5" />
                  <ConfigRow label="Max Entries" value="1000" />
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function StatusCard({ title, status, icon: Icon, details }) {
  const statusColors = {
    healthy: 'bg-green-500/20 text-green-400 border-green-500/30',
    degraded: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    down: 'bg-red-500/20 text-red-400 border-red-500/30',
    unknown: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
  }

  return (
    <div className={`rounded-lg border p-4 ${statusColors[status] || statusColors.unknown}`}>
      <div className="flex items-center gap-3 mb-3">
        <Icon className="w-5 h-5" />
        <span className="font-medium">{title}</span>
        {status === 'healthy' && <CheckCircle className="w-4 h-4 ml-auto" />}
        {status === 'down' && <XCircle className="w-4 h-4 ml-auto" />}
      </div>
      <div className="space-y-1">
        {details?.map((d, i) => (
          <div key={i} className="flex justify-between text-xs">
            <span className="opacity-70">{d.label}</span>
            <span className="font-medium">{d.value}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function DataCard({ title, count, icon: Icon }) {
  return (
    <div className="bg-slate-700/50 rounded-lg p-4 text-center">
      <Icon className="w-6 h-6 text-blue-400 mx-auto mb-2" />
      <p className="text-2xl font-bold text-white">{count.toLocaleString()}</p>
      <p className="text-slate-400 text-xs">{title}</p>
    </div>
  )
}

function ConfigRow({ label, value }) {
  return (
    <div className="flex justify-between">
      <span className="text-slate-400">{label}</span>
      <span className="text-blue-400">{value}</span>
    </div>
  )
}
