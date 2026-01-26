import { useState, useEffect } from 'react'
import { 
  X, Settings, Database, Server, Cpu, CheckCircle, XCircle, 
  RefreshCw, Play, Zap, HardDrive, Cloud, AlertTriangle,
  Activity, BarChart3, TestTube, FileText, Loader2
} from 'lucide-react'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function AdminPanel({ isOpen, onClose }) {
  const [activeTab, setActiveTab] = useState('status')
  const [systemStatus, setSystemStatus] = useState(null)
  const [loading, setLoading] = useState(false)
  const [vectorBackend, setVectorBackend] = useState('pinecone') // pinecone or faiss
  const [testResults, setTestResults] = useState(null)
  const [runningTest, setRunningTest] = useState(false)
  const [processingStatus, setProcessingStatus] = useState(null)

  useEffect(() => {
    if (isOpen) {
      fetchSystemStatus()
      fetchVectorBackend()
    }
  }, [isOpen])

  const fetchSystemStatus = async () => {
    setLoading(true)
    try {
      const resp = await fetch(`${API_URL}/api/admin/status`)
      if (resp.ok) {
        const data = await resp.json()
        setSystemStatus(data)
      }
    } catch (err) {
      console.error('Failed to fetch system status:', err)
      setSystemStatus({ error: 'Failed to connect to backend' })
    }
    setLoading(false)
  }

  const fetchVectorBackend = async () => {
    try {
      const resp = await fetch(`${API_URL}/api/admin/vector-backend`)
      if (resp.ok) {
        const data = await resp.json()
        setVectorBackend(data.backend || 'pinecone')
      }
    } catch (err) {
      console.error('Failed to fetch vector backend:', err)
    }
  }

  const toggleVectorBackend = async () => {
    const newBackend = vectorBackend === 'pinecone' ? 'faiss' : 'pinecone'
    try {
      const resp = await fetch(`${API_URL}/api/admin/vector-backend`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ backend: newBackend })
      })
      if (resp.ok) {
        setVectorBackend(newBackend)
      }
    } catch (err) {
      console.error('Failed to toggle vector backend:', err)
    }
  }

  const runTests = async () => {
    setRunningTest(true)
    setTestResults(null)
    try {
      const resp = await fetch(`${API_URL}/api/admin/run-tests`, { method: 'POST' })
      if (resp.ok) {
        const data = await resp.json()
        setTestResults(data)
      }
    } catch (err) {
      console.error('Failed to run tests:', err)
      setTestResults({ error: 'Failed to run tests' })
    }
    setRunningTest(false)
  }

  const fetchProcessingStatus = async () => {
    try {
      const resp = await fetch(`${API_URL}/api/admin/processing-status`)
      if (resp.ok) {
        const data = await resp.json()
        setProcessingStatus(data)
      }
    } catch (err) {
      console.error('Failed to fetch processing status:', err)
    }
  }

  const triggerIndexing = async (target) => {
    try {
      await fetch(`${API_URL}/api/admin/trigger-indexing`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target })
      })
      fetchProcessingStatus()
    } catch (err) {
      console.error('Failed to trigger indexing:', err)
    }
  }

  if (!isOpen) return null

  const tabs = [
    { id: 'status', label: 'System Status', icon: Activity },
    { id: 'data', label: 'Data', icon: Database },
    { id: 'processing', label: 'Processing', icon: Cpu },
    { id: 'tests', label: 'Tests', icon: TestTube },
    { id: 'config', label: 'Config', icon: Settings },
  ]

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-slate-800 rounded-xl border border-slate-700 shadow-2xl w-full max-w-4xl max-h-[85vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-slate-700">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-pink-600 rounded-lg flex items-center justify-center">
              <Settings className="w-6 h-6 text-white" />
            </div>
            <div>
              <h2 className="text-white font-bold text-lg">Admin Panel</h2>
              <p className="text-slate-400 text-xs">System management & monitoring</p>
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
                if (tab.id === 'processing') fetchProcessingStatus()
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
                </div>

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

          {/* Data Tab */}
          {activeTab === 'data' && (
            <div className="space-y-4">
              <h3 className="text-white font-semibold">Data Overview</h3>
              
              <div className="grid grid-cols-3 gap-4">
                <DataCard title="Properties" count={systemStatus?.database?.properties || 0} icon={Database} />
                <DataCard title="POIs" count={systemStatus?.database?.pois || 0} icon={Database} />
                <DataCard title="Buildings" count={systemStatus?.database?.buildings || 0} icon={Database} />
                <DataCard title="Places" count={systemStatus?.database?.places || 0} icon={Database} />
                <DataCard title="Transport" count={systemStatus?.database?.transport || 0} icon={Database} />
                <DataCard title="Vectors" count={systemStatus?.pinecone?.vectors || 0} icon={Cloud} />
              </div>

              <div className="bg-slate-700/50 rounded-lg p-4 mt-6">
                <h4 className="text-white font-medium mb-3">Data Sources</h4>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between text-slate-300">
                    <span>99acres</span>
                    <span>{systemStatus?.sources?.['99acres'] || 0}</span>
                  </div>
                  <div className="flex justify-between text-slate-300">
                    <span>Housing.com</span>
                    <span>{systemStatus?.sources?.housing || 0}</span>
                  </div>
                  <div className="flex justify-between text-slate-300">
                    <span>MagicBricks</span>
                    <span>{systemStatus?.sources?.magicbricks || 0}</span>
                  </div>
                  <div className="flex justify-between text-slate-300">
                    <span>NoBroker</span>
                    <span>{systemStatus?.sources?.nobroker || 0}</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Processing Tab */}
          {activeTab === 'processing' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-white font-semibold">Processing & Indexing</h3>
                <button
                  onClick={fetchProcessingStatus}
                  className="flex items-center gap-2 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-white rounded-lg text-sm transition"
                >
                  <RefreshCw className="w-4 h-4" />
                  Refresh
                </button>
              </div>

              {/* Vector Backend Toggle */}
              <div className="bg-gradient-to-r from-purple-500/10 to-blue-500/10 border border-purple-500/30 rounded-lg p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h4 className="text-white font-medium">Vector Search Backend</h4>
                    <p className="text-slate-400 text-sm mt-1">
                      {vectorBackend === 'pinecone' 
                        ? 'Using Pinecone (cloud) for vector search'
                        : 'Using FAISS (local) for vector search'}
                    </p>
                  </div>
                  <button
                    onClick={toggleVectorBackend}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition ${
                      vectorBackend === 'pinecone'
                        ? 'bg-blue-600 hover:bg-blue-700 text-white'
                        : 'bg-green-600 hover:bg-green-700 text-white'
                    }`}
                  >
                    {vectorBackend === 'pinecone' ? (
                      <>
                        <Cloud className="w-4 h-4" />
                        Pinecone
                      </>
                    ) : (
                      <>
                        <HardDrive className="w-4 h-4" />
                        FAISS
                      </>
                    )}
                  </button>
                </div>
              </div>

              {/* Indexing Actions */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-slate-700/50 rounded-lg p-4">
                  <h4 className="text-white font-medium mb-2">Pinecone Indexing</h4>
                  <p className="text-slate-400 text-xs mb-3">Index database to Pinecone cloud</p>
                  <button
                    onClick={() => triggerIndexing('pinecone')}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm transition"
                  >
                    <Play className="w-4 h-4" />
                    Start Pinecone Index
                  </button>
                </div>

                <div className="bg-slate-700/50 rounded-lg p-4">
                  <h4 className="text-white font-medium mb-2">FAISS Export</h4>
                  <p className="text-slate-400 text-xs mb-3">Export vectors to local FAISS</p>
                  <button
                    onClick={() => triggerIndexing('faiss')}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm transition"
                  >
                    <Play className="w-4 h-4" />
                    Start FAISS Export
                  </button>
                </div>
              </div>

              {/* Processing Status */}
              {processingStatus && (
                <div className="bg-slate-700/50 rounded-lg p-4">
                  <h4 className="text-white font-medium mb-3">Current Jobs</h4>
                  {processingStatus.jobs?.length > 0 ? (
                    <div className="space-y-2">
                      {processingStatus.jobs.map((job, i) => (
                        <div key={i} className="flex items-center justify-between text-sm">
                          <span className="text-slate-300">{job.name}</span>
                          <span className={`px-2 py-0.5 rounded text-xs ${
                            job.status === 'running' ? 'bg-blue-500/20 text-blue-400' :
                            job.status === 'completed' ? 'bg-green-500/20 text-green-400' :
                            'bg-yellow-500/20 text-yellow-400'
                          }`}>
                            {job.status}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-slate-400 text-sm">No active jobs</p>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Tests Tab */}
          {activeTab === 'tests' && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h3 className="text-white font-semibold">System Tests</h3>
                <button
                  onClick={runTests}
                  disabled={runningTest}
                  className="flex items-center gap-2 px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm transition disabled:opacity-50"
                >
                  {runningTest ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Running...
                    </>
                  ) : (
                    <>
                      <Play className="w-4 h-4" />
                      Run All Tests
                    </>
                  )}
                </button>
              </div>

              {testResults?.error ? (
                <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400">
                  {testResults.error}
                </div>
              ) : testResults ? (
                <div className="space-y-3">
                  {testResults.tests?.map((test, i) => (
                    <div key={i} className="bg-slate-700/50 rounded-lg p-3 flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {test.passed ? (
                          <CheckCircle className="w-5 h-5 text-green-400" />
                        ) : (
                          <XCircle className="w-5 h-5 text-red-400" />
                        )}
                        <div>
                          <p className="text-white text-sm font-medium">{test.name}</p>
                          <p className="text-slate-400 text-xs">{test.description}</p>
                        </div>
                      </div>
                      <span className={`text-xs ${test.passed ? 'text-green-400' : 'text-red-400'}`}>
                        {test.duration}ms
                      </span>
                    </div>
                  ))}
                  
                  <div className="bg-slate-700/30 rounded-lg p-4 mt-4">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-slate-300">Total Tests</span>
                      <span className="text-white font-medium">{testResults.total}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm mt-2">
                      <span className="text-slate-300">Passed</span>
                      <span className="text-green-400 font-medium">{testResults.passed}</span>
                    </div>
                    <div className="flex items-center justify-between text-sm mt-2">
                      <span className="text-slate-300">Failed</span>
                      <span className="text-red-400 font-medium">{testResults.failed}</span>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-12 text-slate-400">
                  <TestTube className="w-12 h-12 mx-auto mb-3 opacity-50" />
                  <p>Click "Run All Tests" to check system health</p>
                </div>
              )}
            </div>
          )}

          {/* Config Tab */}
          {activeTab === 'config' && (
            <div className="space-y-4">
              <h3 className="text-white font-semibold">Configuration</h3>
              
              <div className="bg-slate-700/50 rounded-lg p-4">
                <h4 className="text-white font-medium mb-3">Environment</h4>
                <div className="space-y-2 text-sm font-mono">
                  <ConfigRow label="PINECONE_INDEX" value="valora-realestate" />
                  <ConfigRow label="OPENROUTER_MODEL" value="claude-3.5-sonnet" />
                  <ConfigRow label="BACKEND_URL" value="http://localhost:8000" />
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

              <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-yellow-400 shrink-0 mt-0.5" />
                  <div>
                    <p className="text-yellow-400 font-medium text-sm">Configuration is read-only</p>
                    <p className="text-slate-400 text-xs mt-1">
                      Edit .env file to change configuration, then restart the server.
                    </p>
                  </div>
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
