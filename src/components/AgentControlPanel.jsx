import { useCallback, useEffect, useMemo, useState } from 'react'
import { Bot, Bell, CalendarClock, Users, Activity, Plus, Trash2, RefreshCw } from 'lucide-react'
import { API_URL } from '../apiConfig'

const DAY_OPTIONS = [
  { label: 'Monday', value: 0 },
  { label: 'Tuesday', value: 1 },
  { label: 'Wednesday', value: 2 },
  { label: 'Thursday', value: 3 },
  { label: 'Friday', value: 4 },
  { label: 'Saturday', value: 5 },
  { label: 'Sunday', value: 6 },
]

const formatTimestamp = (ts) => {
  if (!ts) return 'Never'
  try {
    return new Date(ts * 1000).toLocaleString()
  } catch {
    return 'Unknown'
  }
}

const describeAlertCriteria = (criteria = {}) => {
  const parts = []
  if (criteria.bhk) parts.push(`${criteria.bhk}BHK`)
  if (criteria.locality) parts.push(`in ${criteria.locality}`)
  if (criteria.max_price) parts.push(`under ₹${Math.round(criteria.max_price / 100000)}L`)
  return parts.length ? parts.join(' ') : 'Custom criteria'
}

export default function AgentControlPanel({ userTier = 'free', authToken = null }) {
  const normalizedTier = (userTier || 'free').toLowerCase()
  const isPro = normalizedTier === 'pro' || normalizedTier === 'premium'

  const headers = useMemo(() => {
    if (!authToken) return { 'Content-Type': 'application/json' }
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${authToken}`
    }
  }, [authToken])

  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [summary, setSummary] = useState(null)
  const [alerts, setAlerts] = useState([])
  const [tasks, setTasks] = useState([])
  const [leads, setLeads] = useState([])
  const [activity, setActivity] = useState([])

  const [alertForm, setAlertForm] = useState({
    name: '',
    locality: '',
    bhk: '',
    maxPriceLakh: '',
    frequency: 'instant',
    emailAlert: false
  })

  const [taskForm, setTaskForm] = useState({
    locality: '',
    recipientEmail: '',
    dayOfWeek: 0,
    time: '09:00',
    requiresConfirmation: !isPro
  })

  const [leadForm, setLeadForm] = useState({
    fullName: '',
    email: '',
    phone: '',
    notes: ''
  })

  const fetchJson = useCallback(async (path, options = {}) => {
    const response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: options.headers || headers
    })
    const data = await response.json().catch(() => ({}))
    if (!response.ok) {
      throw new Error(data.detail || data.message || `Request failed (${response.status})`)
    }
    return data
  }, [headers])

  const loadAll = useCallback(async () => {
    if (!authToken) return
    setLoading(true)
    setError('')
    try {
      const [summaryRes, alertsRes, tasksRes, leadsRes, activityRes] = await Promise.all([
        fetchJson('/api/digital-employee/summary'),
        fetchJson('/api/digital-employee/alerts'),
        fetchJson('/api/digital-employee/scheduled-tasks'),
        fetchJson('/api/digital-employee/leads?limit=50'),
        fetchJson('/api/digital-employee/activity?limit=40')
      ])
      setSummary(summaryRes.summary || null)
      setAlerts(alertsRes.alerts || [])
      setTasks(tasksRes.tasks || [])
      setLeads(leadsRes.leads || [])
      setActivity(activityRes.activity || [])
    } catch (err) {
      setError(err.message || 'Failed to load digital employee data')
    } finally {
      setLoading(false)
    }
  }, [authToken, fetchJson])

  useEffect(() => {
    setTaskForm(prev => ({ ...prev, requiresConfirmation: !isPro }))
  }, [isPro])

  useEffect(() => {
    loadAll()
  }, [loadAll])

  const handleCreateAlert = async (e) => {
    e.preventDefault()
    if (!authToken) return
    try {
      const criteria = {}
      if (alertForm.locality.trim()) criteria.locality = alertForm.locality.trim()
      if (alertForm.bhk) criteria.bhk = Number(alertForm.bhk)
      if (alertForm.maxPriceLakh) criteria.max_price_lakh = Number(alertForm.maxPriceLakh)
      if (Object.keys(criteria).length === 0) {
        setError('Add at least one alert criterion (locality, BHK, or budget).')
        return
      }

      const channels = ['in_app']
      if (isPro && alertForm.emailAlert) channels.push('email')

      await fetchJson('/api/digital-employee/alerts', {
        method: 'POST',
        body: JSON.stringify({
          name: alertForm.name || undefined,
          criteria,
          frequency: alertForm.frequency,
          channels
        })
      })

      setAlertForm({
        name: '',
        locality: '',
        bhk: '',
        maxPriceLakh: '',
        frequency: 'instant',
        emailAlert: false
      })
      await loadAll()
    } catch (err) {
      setError(err.message || 'Failed to create alert')
    }
  }

  const handleDeleteAlert = async (alertId) => {
    try {
      await fetchJson(`/api/digital-employee/alerts/${alertId}`, { method: 'DELETE' })
      await loadAll()
    } catch (err) {
      setError(err.message || 'Failed to deactivate alert')
    }
  }

  const handleCreateTask = async (e) => {
    e.preventDefault()
    if (!authToken) return
    try {
      const channels = ['in_app']
      if (isPro && taskForm.recipientEmail.trim()) channels.push('email')
      await fetchJson('/api/digital-employee/scheduled-tasks', {
        method: 'POST',
        body: JSON.stringify({
          name: `Weekly Report${taskForm.locality ? ` - ${taskForm.locality}` : ''}`,
          task_type: 'weekly_market_report',
          schedule: {
            type: 'weekly',
            day_of_week: Number(taskForm.dayOfWeek),
            time: taskForm.time || '09:00'
          },
          payload: {
            locality: taskForm.locality || null,
            recipient_email: taskForm.recipientEmail || null,
            channels
          },
          requires_confirmation: !!taskForm.requiresConfirmation
        })
      })
      setTaskForm({
        locality: '',
        recipientEmail: '',
        dayOfWeek: 0,
        time: '09:00',
        requiresConfirmation: !isPro
      })
      await loadAll()
    } catch (err) {
      setError(err.message || 'Failed to create task')
    }
  }

  const handleDeleteTask = async (taskId) => {
    try {
      await fetchJson(`/api/digital-employee/scheduled-tasks/${taskId}`, { method: 'DELETE' })
      await loadAll()
    } catch (err) {
      setError(err.message || 'Failed to deactivate task')
    }
  }

  const handleCreateLead = async (e) => {
    e.preventDefault()
    if (!authToken) return
    if (!leadForm.fullName.trim()) {
      setError('Lead name is required.')
      return
    }
    try {
      await fetchJson('/api/digital-employee/leads', {
        method: 'POST',
        body: JSON.stringify({
          full_name: leadForm.fullName,
          email: leadForm.email || null,
          phone: leadForm.phone || null,
          notes: leadForm.notes || null,
          source: 'agent_panel',
          status: 'new'
        })
      })
      setLeadForm({ fullName: '', email: '', phone: '', notes: '' })
      await loadAll()
    } catch (err) {
      setError(err.message || 'Failed to create lead')
    }
  }

  const handleArchiveLead = async (leadId) => {
    try {
      await fetchJson(`/api/digital-employee/leads/${leadId}`, { method: 'DELETE' })
      await loadAll()
    } catch (err) {
      setError(err.message || 'Failed to archive lead')
    }
  }

  if (!authToken) {
    return (
      <div className="p-4 text-slate-300">
        <div className="flex items-center gap-2 text-sm text-slate-200">
          <Bot className="w-4 h-4 text-cyan-400" />
          Login required for Digital Employee features.
        </div>
      </div>
    )
  }

  return (
    <div className="p-3 space-y-3 text-xs text-slate-200">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Bot className="w-4 h-4 text-cyan-400" />
          <span className="font-semibold">Digital Employee</span>
          <span className={`px-2 py-0.5 rounded-full ${isPro ? 'bg-blue-500/20 text-blue-300' : 'bg-slate-600/30 text-slate-300'}`}>
            {isPro ? 'PRO' : 'FREE'}
          </span>
        </div>
        <button
          onClick={loadAll}
          className="inline-flex items-center gap-1 px-2 py-1 rounded bg-slate-700/50 hover:bg-slate-700 transition"
        >
          <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="rounded border border-red-500/40 bg-red-500/10 px-3 py-2 text-red-200">
          {error}
        </div>
      )}

      {summary && (
        <div className="grid grid-cols-3 gap-2">
          <div className="rounded bg-slate-800/60 border border-slate-700 p-2">
            <div className="flex items-center gap-1 text-slate-400"><Bell className="w-3 h-3" /> Alerts</div>
            <div className="text-sm font-semibold">{summary.counts?.active_alerts ?? 0}</div>
            <div className="text-[10px] text-slate-500">
              Limit: {summary.policy?.max_alerts ?? 'Unlimited'}
            </div>
          </div>
          <div className="rounded bg-slate-800/60 border border-slate-700 p-2">
            <div className="flex items-center gap-1 text-slate-400"><CalendarClock className="w-3 h-3" /> Tasks</div>
            <div className="text-sm font-semibold">{summary.counts?.active_scheduled_tasks ?? 0}</div>
            <div className="text-[10px] text-slate-500">
              Auto-run: {summary.policy?.auto_execute_tasks ? 'Yes' : 'Manual confirm'}
            </div>
          </div>
          <div className="rounded bg-slate-800/60 border border-slate-700 p-2">
            <div className="flex items-center gap-1 text-slate-400"><Users className="w-3 h-3" /> Leads</div>
            <div className="text-sm font-semibold">{summary.counts?.active_leads ?? 0}</div>
            <div className="text-[10px] text-slate-500">CRM pipeline</div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
        <section className="rounded border border-slate-700 bg-slate-900/40 p-3 space-y-2">
          <div className="font-medium flex items-center gap-1"><Bell className="w-3.5 h-3.5 text-emerald-400" /> Property Alerts</div>
          <form className="grid grid-cols-2 gap-2" onSubmit={handleCreateAlert}>
            <input
              className="col-span-2 px-2 py-1 rounded bg-slate-800 border border-slate-700"
              placeholder="Alert name (optional)"
              value={alertForm.name}
              onChange={(e) => setAlertForm(prev => ({ ...prev, name: e.target.value }))}
            />
            <input
              className="px-2 py-1 rounded bg-slate-800 border border-slate-700"
              placeholder="Locality (e.g. Andheri)"
              value={alertForm.locality}
              onChange={(e) => setAlertForm(prev => ({ ...prev, locality: e.target.value }))}
            />
            <input
              className="px-2 py-1 rounded bg-slate-800 border border-slate-700"
              placeholder="BHK"
              type="number"
              min="1"
              value={alertForm.bhk}
              onChange={(e) => setAlertForm(prev => ({ ...prev, bhk: e.target.value }))}
            />
            <input
              className="px-2 py-1 rounded bg-slate-800 border border-slate-700"
              placeholder="Max Price (Lakh)"
              type="number"
              min="1"
              value={alertForm.maxPriceLakh}
              onChange={(e) => setAlertForm(prev => ({ ...prev, maxPriceLakh: e.target.value }))}
            />
            <select
              className="px-2 py-1 rounded bg-slate-800 border border-slate-700"
              value={alertForm.frequency}
              onChange={(e) => setAlertForm(prev => ({ ...prev, frequency: e.target.value }))}
            >
              <option value="instant">Instant</option>
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
            </select>
            <label className={`col-span-2 flex items-center gap-2 ${isPro ? 'text-slate-300' : 'text-slate-500'}`}>
              <input
                type="checkbox"
                disabled={!isPro}
                checked={alertForm.emailAlert}
                onChange={(e) => setAlertForm(prev => ({ ...prev, emailAlert: e.target.checked }))}
              />
              Email notification {isPro ? '' : '(Pro only)'}
            </label>
            <button className="col-span-2 inline-flex items-center justify-center gap-1 px-2 py-1 rounded bg-emerald-600 hover:bg-emerald-500 text-white">
              <Plus className="w-3 h-3" />
              Create Alert
            </button>
          </form>
          <div className="space-y-1 max-h-40 overflow-auto">
            {alerts.length === 0 && <div className="text-slate-500">No active alerts</div>}
            {alerts.map(alert => (
              <div key={alert.id} className="rounded bg-slate-800/60 border border-slate-700 p-2 flex items-start justify-between gap-2">
                <div>
                  <div className="font-medium">{alert.name}</div>
                  <div className="text-slate-400">{describeAlertCriteria(alert.criteria)}</div>
                  <div className="text-[10px] text-slate-500">Triggered {alert.trigger_count} times</div>
                </div>
                <button onClick={() => handleDeleteAlert(alert.id)} className="text-red-300 hover:text-red-200">
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded border border-slate-700 bg-slate-900/40 p-3 space-y-2">
          <div className="font-medium flex items-center gap-1"><CalendarClock className="w-3.5 h-3.5 text-blue-400" /> Scheduled Tasks</div>
          <form className="grid grid-cols-2 gap-2" onSubmit={handleCreateTask}>
            <input
              className="col-span-2 px-2 py-1 rounded bg-slate-800 border border-slate-700"
              placeholder="Locality for weekly report"
              value={taskForm.locality}
              onChange={(e) => setTaskForm(prev => ({ ...prev, locality: e.target.value }))}
            />
            <select
              className="px-2 py-1 rounded bg-slate-800 border border-slate-700"
              value={taskForm.dayOfWeek}
              onChange={(e) => setTaskForm(prev => ({ ...prev, dayOfWeek: Number(e.target.value) }))}
            >
              {DAY_OPTIONS.map(day => (
                <option key={day.value} value={day.value}>{day.label}</option>
              ))}
            </select>
            <input
              className="px-2 py-1 rounded bg-slate-800 border border-slate-700"
              type="time"
              value={taskForm.time}
              onChange={(e) => setTaskForm(prev => ({ ...prev, time: e.target.value }))}
            />
            <input
              className={`col-span-2 px-2 py-1 rounded border ${isPro ? 'bg-slate-800 border-slate-700' : 'bg-slate-800/40 border-slate-700/40 text-slate-500'}`}
              disabled={!isPro}
              placeholder={isPro ? 'Recipient email (optional)' : 'Email automation is Pro only'}
              value={taskForm.recipientEmail}
              onChange={(e) => setTaskForm(prev => ({ ...prev, recipientEmail: e.target.value }))}
            />
            <label className="col-span-2 flex items-center gap-2 text-slate-300">
              <input
                type="checkbox"
                checked={taskForm.requiresConfirmation}
                onChange={(e) => setTaskForm(prev => ({ ...prev, requiresConfirmation: e.target.checked }))}
              />
              Require manual confirmation before execution
            </label>
            <button className="col-span-2 inline-flex items-center justify-center gap-1 px-2 py-1 rounded bg-blue-600 hover:bg-blue-500 text-white">
              <Plus className="w-3 h-3" />
              Schedule Task
            </button>
          </form>
          <div className="space-y-1 max-h-40 overflow-auto">
            {tasks.length === 0 && <div className="text-slate-500">No scheduled tasks</div>}
            {tasks.map(task => (
              <div key={task.id} className="rounded bg-slate-800/60 border border-slate-700 p-2 flex items-start justify-between gap-2">
                <div>
                  <div className="font-medium">{task.name}</div>
                  <div className="text-slate-400">{task.task_type}</div>
                  <div className="text-[10px] text-slate-500">Next run: {formatTimestamp(task.next_run_at)}</div>
                </div>
                <button onClick={() => handleDeleteTask(task.id)} className="text-red-300 hover:text-red-200">
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        </section>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-3">
        <section className="rounded border border-slate-700 bg-slate-900/40 p-3 space-y-2">
          <div className="font-medium flex items-center gap-1"><Users className="w-3.5 h-3.5 text-amber-400" /> Lead Manager</div>
          <form className="grid grid-cols-2 gap-2" onSubmit={handleCreateLead}>
            <input
              className="col-span-2 px-2 py-1 rounded bg-slate-800 border border-slate-700"
              placeholder="Lead full name"
              value={leadForm.fullName}
              onChange={(e) => setLeadForm(prev => ({ ...prev, fullName: e.target.value }))}
            />
            <input
              className="px-2 py-1 rounded bg-slate-800 border border-slate-700"
              placeholder="Email"
              value={leadForm.email}
              onChange={(e) => setLeadForm(prev => ({ ...prev, email: e.target.value }))}
            />
            <input
              className="px-2 py-1 rounded bg-slate-800 border border-slate-700"
              placeholder="Phone"
              value={leadForm.phone}
              onChange={(e) => setLeadForm(prev => ({ ...prev, phone: e.target.value }))}
            />
            <input
              className="col-span-2 px-2 py-1 rounded bg-slate-800 border border-slate-700"
              placeholder="Notes"
              value={leadForm.notes}
              onChange={(e) => setLeadForm(prev => ({ ...prev, notes: e.target.value }))}
            />
            <button className="col-span-2 inline-flex items-center justify-center gap-1 px-2 py-1 rounded bg-amber-600 hover:bg-amber-500 text-white">
              <Plus className="w-3 h-3" />
              Add Lead
            </button>
          </form>
          <div className="space-y-1 max-h-40 overflow-auto">
            {leads.length === 0 && <div className="text-slate-500">No leads added</div>}
            {leads.map(lead => (
              <div key={lead.id} className="rounded bg-slate-800/60 border border-slate-700 p-2 flex items-start justify-between gap-2">
                <div>
                  <div className="font-medium">{lead.full_name}</div>
                  <div className="text-slate-400">{lead.email || lead.phone || 'No contact details'}</div>
                  <div className="text-[10px] text-slate-500">Status: {lead.status}</div>
                </div>
                <button onClick={() => handleArchiveLead(lead.id)} className="text-red-300 hover:text-red-200">
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded border border-slate-700 bg-slate-900/40 p-3 space-y-2">
          <div className="font-medium flex items-center gap-1"><Activity className="w-3.5 h-3.5 text-purple-400" /> Automation Activity</div>
          <div className="space-y-1 max-h-64 overflow-auto">
            {activity.length === 0 && <div className="text-slate-500">No automation events yet</div>}
            {activity.map(event => (
              <div key={event.id} className="rounded bg-slate-800/60 border border-slate-700 p-2">
                <div className="flex items-center justify-between gap-2">
                  <div className="font-medium">{event.action}</div>
                  <div className={`text-[10px] ${event.status === 'error' ? 'text-red-300' : event.status === 'warning' ? 'text-amber-300' : 'text-emerald-300'}`}>
                    {event.status}
                  </div>
                </div>
                <div className="text-slate-400 text-[10px]">
                  {event.entity_type}{event.entity_id ? ` #${event.entity_id}` : ''}
                </div>
                <div className="text-slate-500 text-[10px]">{formatTimestamp(event.created_at)}</div>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  )
}

