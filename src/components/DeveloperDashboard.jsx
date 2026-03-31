/**
 * DeveloperDashboard - Project analytics, demand density, pricing intelligence.
 * 
 * For developers and builder sales teams launching projects in Bengaluru.
 * Shows micro-market confidence, pricing insights, competitor analysis.
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Building2, TrendingUp, MapPin, BarChart3, RefreshCw,
  ArrowUpRight, ArrowDownRight, Target, Calendar,
  DollarSign, Users, Eye, FileText
} from 'lucide-react';
import { API_URL } from '../apiConfig';
import { useAuth } from '../contexts/AuthContext';

const DEMO_PROJECTS = {
  active: 3,
  planned: 2,
  completed: 7,
  totalUnits: 1240,
};

const DEMO_MARKET_DATA = {
  avgPricePerSqft: 6850,
  priceChange: 4.2,
  demandIndex: 78,
  supplyIndex: 62,
  absorptionRate: 68,
  inventoryMonths: 8.5,
};

const DEMO_MICRO_MARKETS = [
  { name: 'Whitefield', demand: 85, avgPrice: 7200, supply: 70, trend: 'up' },
  { name: 'Sarjapur Road', demand: 78, avgPrice: 6500, supply: 65, trend: 'up' },
  { name: 'Electronic City', demand: 72, avgPrice: 5800, supply: 80, trend: 'stable' },
  { name: 'Hebbal', demand: 80, avgPrice: 8100, supply: 45, trend: 'up' },
  { name: 'Kanakapura Road', demand: 65, avgPrice: 5200, supply: 90, trend: 'down' },
];

const DEMO_COMPETITORS = [
  { name: 'Prestige Group', projects: 4, avgPrice: 8500, units: 320 },
  { name: 'Brigade Group', projects: 3, avgPrice: 7800, units: 280 },
  { name: 'Sobha Limited', projects: 2, avgPrice: 9200, units: 180 },
];

const DEMO_WEEKLY_LEADS = [
  { day: 'Mon', inquiries: 12, siteVisits: 4 },
  { day: 'Tue', inquiries: 18, siteVisits: 6 },
  { day: 'Wed', inquiries: 15, siteVisits: 5 },
  { day: 'Thu', inquiries: 22, siteVisits: 8 },
  { day: 'Fri', inquiries: 20, siteVisits: 7 },
  { day: 'Sat', inquiries: 28, siteVisits: 12 },
  { day: 'Sun', inquiries: 10, siteVisits: 3 },
];

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

function MarketBar({ name, demand, avgPrice, supply, trend }) {
  const trendColor = trend === 'up' ? 'text-emerald-400' : trend === 'down' ? 'text-red-400' : 'text-slate-400';
  return (
    <div className="p-2 bg-slate-800/60 rounded-lg">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs font-medium text-white">{name}</span>
        <span className={`text-[10px] ${trendColor}`}>{trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'} {trend}</span>
      </div>
      <div className="grid grid-cols-3 gap-2 text-[10px]">
        <div>
          <div className="text-slate-500">Demand</div>
          <div className="text-emerald-400 font-bold">{demand}</div>
        </div>
        <div>
          <div className="text-slate-500">Avg ₹/sqft</div>
          <div className="text-blue-400 font-bold">₹{avgPrice.toLocaleString()}</div>
        </div>
        <div>
          <div className="text-slate-500">Supply</div>
          <div className="text-amber-400 font-bold">{supply}</div>
        </div>
      </div>
    </div>
  );
}

export default function DeveloperDashboard({ locality }) {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [projects, setProjects] = useState(DEMO_PROJECTS);
  const [marketData, setMarketData] = useState(DEMO_MARKET_DATA);
  const [microMarkets, setMicroMarkets] = useState(DEMO_MICRO_MARKETS);
  const [competitors, setCompetitors] = useState(DEMO_COMPETITORS);
  const [weeklyLeads, setWeeklyLeads] = useState(DEMO_WEEKLY_LEADS);

  const fetchMetrics = useCallback(async () => {
    setLoading(true);
    try {
      const userId = user?.email || user?.id || 'anonymous';
      const res = await fetch(`${API_URL}/api/developer-dashboard/metrics?user_id=${userId}`, { signal: AbortSignal.timeout(5000) });
      if (res.ok) {
        const data = await res.json();
        if (data.projects) setProjects(data.projects);
        if (data.market_data) setMarketData(data.market_data);
        if (data.micro_markets) setMicroMarkets(data.micro_markets);
        if (data.competitors) setCompetitors(data.competitors);
        if (data.weekly_leads) setWeeklyLeads(data.weekly_leads);
      }
    } catch (fetchError) {
      // Silently fall back to demo data
    } finally {
      setLoading(false);
    }
  }, [user]);

  useEffect(() => { fetchMetrics(); }, [fetchMetrics]);

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
            <Building2 className="w-4 h-4 text-blue-400" />
            Developer Dashboard
          </h2>
          <p className="text-[10px] text-slate-400 mt-0.5">
            {locality ? `Focused on ${locality}` : 'All micro-markets'} · {user?.name || 'Developer'}
          </p>
        </div>
        <button onClick={fetchMetrics} className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-700/50 rounded transition" title="Refresh">
          <RefreshCw className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <MetricCard icon={Building2} label="Active Projects" value={projects.active} change={1} changeType="up" color="blue" />
        <MetricCard icon={TrendingUp} label="Avg ₹/sqft" value={`₹${marketData.avgPricePerSqft.toLocaleString()}`} change={marketData.priceChange} changeType="up" color="green" />
        <MetricCard icon={Target} label="Demand Index" value={marketData.demandIndex} change={3} changeType="up" color="purple" />
        <MetricCard icon={Users} label="Absorption Rate" value={`${marketData.absorptionRate}%`} change={2} changeType="up" color="amber" />
      </div>

      <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-3">
        <h3 className="text-xs font-semibold text-white mb-3 flex items-center gap-1.5">
          <MapPin className="w-3.5 h-3.5 text-blue-400" />
          Micro-Market Intelligence
        </h3>
        <div className="space-y-2">
          {microMarkets.map(m => (
            <MarketBar key={m.name} name={m.name} demand={m.demand} avgPrice={m.avgPrice} supply={m.supply} trend={m.trend} />
          ))}
        </div>
      </div>

      <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-3">
        <h3 className="text-xs font-semibold text-white mb-3 flex items-center gap-1.5">
          <BarChart3 className="w-3.5 h-3.5 text-blue-400" />
          Competitor Analysis
        </h3>
        <div className="space-y-2">
          {competitors.map(c => (
            <div key={c.name} className="flex items-center justify-between p-2 bg-slate-800/60 rounded-lg">
              <div>
                <div className="text-xs font-medium text-white">{c.name}</div>
                <div className="text-[10px] text-slate-400">{c.projects} projects · {c.units} units</div>
              </div>
              <div className="text-right">
                <div className="text-xs font-bold text-blue-400">₹{c.avgPrice.toLocaleString()}/sqft</div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-3">
        <h3 className="text-xs font-semibold text-white mb-3 flex items-center gap-1.5">
          <Calendar className="w-3.5 h-3.5 text-blue-400" />
          Weekly Inquiry Activity
        </h3>
        <div className="flex items-end justify-between gap-1 px-1">
          {weeklyLeads.map(d => {
            const maxI = Math.max(...weeklyLeads.map(x => x.inquiries), 1);
            const pct = Math.round((d.inquiries / maxI) * 100);
            const days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
            const isToday = days[new Date().getDay()] === d.day;
            return (
              <div key={d.day} className="flex flex-col items-center gap-1">
                <div className="w-6 h-16 bg-slate-700/30 rounded-sm relative overflow-hidden">
                  <div className={`absolute bottom-0 w-full rounded-sm transition-all duration-300 ${isToday ? 'bg-gradient-to-t from-blue-600 to-blue-400' : 'bg-slate-600/50'}`} style={{ height: `${pct}%` }} />
                </div>
                <span className={`text-[9px] ${isToday ? 'text-blue-400 font-bold' : 'text-slate-500'}`}>{d.day}</span>
              </div>
            );
          })}
        </div>
        <div className="flex items-center justify-between mt-2 text-[9px] text-slate-500">
          <span>{weeklyLeads.reduce((s, d) => s + d.inquiries, 0)} inquiries this week</span>
          <span>{weeklyLeads.reduce((s, d) => s + d.siteVisits, 0)} site visits</span>
        </div>
      </div>

      <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-3">
        <h3 className="text-xs font-semibold text-white mb-2 flex items-center gap-1.5">
          <FileText className="w-3.5 h-3.5 text-amber-400" />
          Quick Actions
        </h3>
        <div className="grid grid-cols-2 gap-2">
          <button onClick={() => window.dispatchEvent(new CustomEvent('valora-smart-tab-change', { detail: { tab: 'market_snapshot' } }))} className="flex items-center gap-2 p-2 bg-blue-500/10 border border-blue-500/30 rounded-lg hover:bg-blue-500/20 transition text-xs text-blue-300">
            <TrendingUp className="w-3.5 h-3.5" />
            Market Sentiment
          </button>
          <button onClick={() => window.dispatchEvent(new CustomEvent('valora-smart-tab-change', { detail: { tab: 'roi_projection' } }))} className="flex items-center gap-2 p-2 bg-emerald-500/10 border border-emerald-500/30 rounded-lg hover:bg-emerald-500/20 transition text-xs text-emerald-300">
            <DollarSign className="w-3.5 h-3.5" />
            Pricing Analysis
          </button>
          <button onClick={() => window.dispatchEvent(new CustomEvent('valora-smart-tab-change', { detail: { tab: 'spatial_intelligence' } }))} className="flex items-center gap-2 p-2 bg-purple-500/10 border border-purple-500/30 rounded-lg hover:bg-purple-500/20 transition text-xs text-purple-300">
            <Eye className="w-3.5 h-3.5" />
            Area Analysis
          </button>
          <button onClick={() => window.dispatchEvent(new CustomEvent('valora-smart-tab-change', { detail: { tab: 'free_analysis' } }))} className="flex items-center gap-2 p-2 bg-amber-500/10 border border-amber-500/30 rounded-lg hover:bg-amber-500/20 transition text-xs text-amber-300">
            <MapPin className="w-3.5 h-3.5" />
            Run Analysis
          </button>
        </div>
      </div>
    </div>
  );
}
