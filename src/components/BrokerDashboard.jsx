/**
 * BrokerDashboard - Lead pipeline, activity metrics, and quick actions for brokers.
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Users, TrendingUp, AlertCircle, Zap, Clock,
  Phone, Mail, MapPin, Eye, RefreshCw,
  ArrowUpRight, ArrowDownRight, Target, Calendar
} from 'lucide-react';
import { API_URL } from '../apiConfig';
import { useAuth } from '../contexts/AuthContext';

const DEMO_PIPELINE = {
  stages: [
    { id: 'new', label: 'New Leads', count: 12, color: 'from-blue-500 to-cyan-500', icon: '🆕' },
    { id: 'contacted', label: 'Contacted', count: 8, color: 'from-amber-500 to-orange-500', icon: '📞' },
    { id: 'negotiating', label: 'Negotiating', count: 5, color: 'from-purple-500 to-pink-500', icon: '🤝' },
    { id: 'closed', label: 'Closed', count: 3, color: 'from-emerald-500 to-green-500', icon: '✅' },
  ],
  total: 28,
  conversionRate: 10.7,
};

const DEMO_RECENT_LEADS = [
  { id: 1, name: 'Rahul Sharma', locality: 'Whitefield', budget: '₹85L', status: 'new' },
  { id: 2, name: 'Priya Nair', locality: 'HSR Layout', budget: '₹1.2Cr', status: 'contacted' },
  { id: 3, name: 'Amit Patel', locality: 'Sarjapur Road', budget: '₹65L', status: 'negotiating' },
  { id: 4, name: 'Sneha Reddy', locality: 'Electronic City', budget: '₹55L', status: 'new' },
  { id: 5, name: 'Vikram Singh', locality: 'Koramangala', budget: '₹2.1Cr', status: 'negotiating' },
];

const DEMO_ALERT_PERFORMANCE = { totalAlerts: 15, engaged: 9, converted: 3, engagementRate: 60 };

const DEMO_WEEKLY_ACTIVITY = [
  { day: 'Mon', queries: 8, reports: 2 },
  { day: 'Tue', queries: 12, reports: 3 },
  { day: 'Wed', queries: 6, reports: 1 },
  { day: 'Thu', queries: 15, reports: 4 },
  { day: 'Fri', queries: 10, reports: 2 },
  { day: 'Sat', queries: 4, reports: 1 },
  { day: 'Sun', queries: 2, reports: 0 },
];

const statusBadge = (status) => {
  const map = {
    new: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    contacted: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    negotiating: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
    closed: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
  };
  return map[status] || 'bg-slate-500/20 text-slate-400 border-slate-500/30';
};

function MetricCard({ icon: Icon, label, value, change, changeType, color = 'blue' }) {
  const cm = {
    blue: 'from-blue-500/20 to-cyan-500/10 border-blue-500/30',
    green: 'from-emerald-500/20 to-green-500/10 border-emerald-500/30',
    purple: 'from-purple-500/20 to-pink-500/10 border-purple-500/30',
    amber: 'from-amber-500/20 to-orange-500/10 border-amber-500/30',
  };
  const ic = { blue: 'text-blue-400', green: 'text-emerald-400', purple: 'text-purple-400', amber: 'text-amber-400' };
  return (
    <div className={`bg-gradient-to-br ${cm[color]} border rounded-lg p-3`}>
      <div className="flex items-center justify-between mb-2">
        <Icon className={`w-4 h-4 ${ic[color]}`} />
        {change !== undefined && (
          <span className={`text-[10px] font-medium flex items-center gap-0.5 ${changeType === 'up' ? 'text-emerald-400' : 'text-red-400'}`}>
            {changeType === 'up' ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
            {change}%
          </span>
        )}
      </div>
      <div className="text-xl font-bold text-white">{value}</div>
      <div className="text-[10px] text-slate-400 mt-0.5">{label}</div>
    </div>
  );
}

function PipelineBar({ stage, total }) {
  const pct = total > 0 ? Math.round((stage.count / total) * 100) : 0;
  return (
    <div className="mb-3">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-slate-300 flex items-center gap-1.5">
          <span>{stage.icon}</span>
          {stage.label}
        </span>
        <span className="text-xs font-bold text-white">{stage.count}</span>
      </div>
      <div className="w-full h-2 bg-slate-700/50 rounded-full overflow-hidden">
        <div
          className={`h-full bg-gradient-to-r ${stage.color} rounded-full transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function ActivityBar({ day, queries, maxQueries }) {
  const pct = maxQueries > 0 ? Math.round((queries / maxQueries) * 100) : 0;
  const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  const isToday = days[new Date().getDay()] === day;
  return (
    <div className="flex flex-col items-center gap-1">
      <div className="w-6 h-16 bg-slate-700/30 rounded-sm relative overflow-hidden">
        <div
          className={`absolute bottom-0 w-full rounded-sm transition-all duration-300 ${
            isToday ? 'bg-gradient-to-t from-blue-600 to-blue-400' : 'bg-slate-600/50'
          }`}
          style={{ height: `${pct}%` }}
        />
      </div>
      <span className={`text-[9px] ${isToday ? 'text-blue-400 font-bold' : 'text-slate-500'}`}>{day}</span>
    </div>
  );
}

export default function BrokerDashboard({ locality }) {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [pipeline, setPipeline] = useState(DEMO_PIPELINE);
  const [recentLeads, setRecentLeads] = useState(DEMO_RECENT_LEADS);
  const [alertPerf, setAlertPerf] = useState(DEMO_ALERT_PERFORMANCE);
  const [weeklyActivity, setWeeklyActivity] = useState(DEMO_WEEKLY_ACTIVITY);
  const [credits, setCredits] = useState({ used: 342, limit: 1000 });

  const fetchMetrics = useCallback(async () => {
    setLoading(true);
    try {
      const userId = user?.email || user?.id || 'anonymous';
      const res = await fetch(`${API_URL}/api/broker-dashboard/metrics?user_id=${userId}`, { signal: AbortSignal.timeout(5000) });
      if (res.ok) {
        const data = await res.json();
        if (data.pipeline) setPipeline(data.pipeline);
        if (data.recent_leads) setRecentLeads(data.recent_leads);
        if (data.alert_performance) setAlertPerf(data.alert_performance);
        if (data.weekly_activity) setWeeklyActivity(data.weekly_activity);
        if (data.credits) setCredits(data.credits);
      }
    } catch (fetchError) {
      // Silently fall back to demo data
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => { fetchMetrics(); }, [fetchMetrics]);
  const maxQ = Math.max(...weeklyActivity.map(d => d.queries), 1);

  if (loading) return (
    <div className="flex flex-col items-center justify-center h-48 gap-3">
      <div className="w-8 h-8 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
      <p className="text-xs text-slate-400">Loading dashboard...</p>
    </div>
  );

  return (
    <div className="p-3 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-bold text-white flex items-center gap-2">
            <Target className="w-4 h-4 text-blue-400" />
            Broker Dashboard
          </h2>
          <p className="text-[10px] text-slate-400 mt-0.5">
            {locality ? `Focused on ${locality}` : 'All micro-markets'} · {user?.name || 'Broker'}
          </p>
        </div>
        <button onClick={fetchMetrics} className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-700/50 rounded transition" title="Refresh">
          <RefreshCw className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <MetricCard icon={Users} label="Total Leads" value={pipeline.total} change={12} changeType="up" color="blue" />
        <MetricCard icon={TrendingUp} label="Conversion Rate" value={`${pipeline.conversionRate}%`} change={2.3} changeType="up" color="green" />
        <MetricCard icon={AlertCircle} label="Alert Engagement" value={`${alertPerf.engagementRate}%`} change={5} changeType="up" color="purple" />
        <MetricCard icon={Zap} label="Credits Used" value={`${credits.used}/${credits.limit}`} color="amber" />
      </div>

      <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-3">
        <h3 className="text-xs font-semibold text-white mb-3 flex items-center gap-1.5">
          <TrendingUp className="w-3.5 h-3.5 text-blue-400" />
          Lead Pipeline
        </h3>
        {pipeline.stages.map(stage => (
          <PipelineBar key={stage.id} stage={stage} total={pipeline.total} />
        ))}
      </div>

      <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-3">
        <h3 className="text-xs font-semibold text-white mb-3 flex items-center gap-1.5">
          <Calendar className="w-3.5 h-3.5 text-blue-400" />
          Weekly Activity
        </h3>
        <div className="flex items-end justify-between gap-1 px-1">
          {weeklyActivity.map(d => (
            <ActivityBar key={d.day} day={d.day} queries={d.queries} maxQueries={maxQ} />
          ))}
        </div>
        <div className="flex items-center justify-between mt-2 text-[9px] text-slate-500">
          <span>{weeklyActivity.reduce((s, d) => s + d.queries, 0)} queries this week</span>
          <span>{weeklyActivity.reduce((s, d) => s + d.reports, 0)} reports</span>
        </div>
      </div>

      <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-3">
        <h3 className="text-xs font-semibold text-white mb-2 flex items-center gap-1.5">
          <Users className="w-3.5 h-3.5 text-blue-400" />
          Recent Leads
        </h3>
        <div className="space-y-2">
          {recentLeads.slice(0, 5).map(lead => (
            <div key={lead.id} className="flex items-center justify-between p-2 bg-slate-800/60 rounded-lg hover:bg-slate-700/40 transition cursor-pointer group">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-white truncate">{lead.name}</span>
                  <span className={`text-[9px] px-1.5 py-0.5 rounded border ${statusBadge(lead.status)}`}>
                    {lead.status.charAt(0).toUpperCase() + lead.status.slice(1)}
                  </span>
                </div>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-[10px] text-slate-400 flex items-center gap-0.5">
                    <MapPin className="w-2.5 h-2.5" />
                    {lead.locality}
                  </span>
                  <span className="text-[10px] text-slate-400">{lead.budget}</span>
                </div>
              </div>
              <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition">
                <button className="p-1 text-slate-400 hover:text-emerald-400 hover:bg-emerald-500/10 rounded" title="Call">
                  <Phone className="w-3 h-3" />
                </button>
                <button className="p-1 text-slate-400 hover:text-blue-400 hover:bg-blue-500/10 rounded" title="View">
                  <Eye className="w-3 h-3" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-3">
        <h3 className="text-xs font-semibold text-white mb-2 flex items-center gap-1.5">
          <Zap className="w-3.5 h-3.5 text-amber-400" />
          Quick Actions
        </h3>
        <div className="grid grid-cols-2 gap-2">
          <button onClick={() => window.dispatchEvent(new CustomEvent('valora-smart-tab-change', { detail: { tab: 'free_analysis' } }))} className="flex items-center gap-2 p-2 bg-blue-500/10 border border-blue-500/30 rounded-lg hover:bg-blue-500/20 transition text-xs text-blue-300">
            <Eye className="w-3.5 h-3.5" />
            Run Analysis
          </button>
          <button onClick={() => window.dispatchEvent(new CustomEvent('valora-smart-tab-change', { detail: { tab: 'agent_control' } }))} className="flex items-center gap-2 p-2 bg-cyan-500/10 border border-cyan-500/30 rounded-lg hover:bg-cyan-500/20 transition text-xs text-cyan-300">
            <Clock className="w-3.5 h-3.5" />
            Schedule Alert
          </button>
          <button onClick={() => window.dispatchEvent(new CustomEvent('valora-smart-tab-change', { detail: { tab: 'client_pitch' } }))} className="flex items-center gap-2 p-2 bg-amber-500/10 border border-amber-500/30 rounded-lg hover:bg-amber-500/20 transition text-xs text-amber-300">
            <Mail className="w-3.5 h-3.5" />
            Client Pitch
          </button>
          <button onClick={() => window.dispatchEvent(new CustomEvent('valora-smart-tab-change', { detail: { tab: 'comparables' } }))} className="flex items-center gap-2 p-2 bg-purple-500/10 border border-purple-500/30 rounded-lg hover:bg-purple-500/20 transition text-xs text-purple-300">
            <TrendingUp className="w-3.5 h-3.5" />
            Comparables
          </button>
        </div>
      </div>
    </div>
  );
}
