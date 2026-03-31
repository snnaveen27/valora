/**
 * BuyerDashboard - Property tracking, ROI analysis, saved searches, alerts.
 * 
 * For home buyers, investors, and NRI users.
 * Shows watchlist performance, saved searches, price alerts, investment insights.
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Home, TrendingUp, Heart, Bell, RefreshCw,
  ArrowUpRight, ArrowDownRight, Target,
  DollarSign, MapPin, Eye, FileText, Search
} from 'lucide-react';
import { API_URL } from '../apiConfig';
import { useAuth } from '../contexts/AuthContext';

const DEMO_WATCHLIST = {
  total: 8,
  priceDropped: 2,
  newMatches: 3,
  avgPriceChange: -1.2,
};

const DEMO_WATCHLIST_PROPERTIES = [
  { id: 1, name: '3BHK in Whitefield', locality: 'Whitefield', price: '₹1.2Cr', priceChange: -2, status: 'watching', daysAgo: 5 },
  { id: 2, name: '2BHK in HSR Layout', locality: 'HSR Layout', price: '₹85L', priceChange: 0, status: 'visited', daysAgo: 3 },
  { id: 3, name: '4BHK in Koramangala', locality: 'Koramangala', price: '₹2.5Cr', priceChange: -5, status: 'watching', daysAgo: 1 },
  { id: 4, name: '2BHK in Electronic City', locality: 'Electronic City', price: '₹55L', priceChange: 3, status: 'shortlisted', daysAgo: 7 },
];

const DEMO_SAVED_SEARCHES = [
  { id: 1, name: '3BHK under ₹1.5Cr', locality: 'Whitefield, Sarjapur', results: 12, newResults: 3 },
  { id: 2, name: '2BHK near Metro', locality: 'HSR, Koramangala', results: 8, newResults: 1 },
  { id: 3, name: 'Villa under ₹3Cr', locality: 'North Bangalore', results: 5, newResults: 2 },
];

const DEMO_PRICE_ALERTS = [
  { id: 1, locality: 'Whitefield', threshold: '₹7,000/sqft', current: '₹7,200/sqft', triggered: false },
  { id: 2, locality: 'Electronic City', threshold: '₹5,500/sqft', current: '₹5,400/sqft', triggered: true },
  { id: 3, locality: 'Sarjapur Road', threshold: '₹6,000/sqft', current: '₹6,500/sqft', triggered: false },
];

const DEMO_INVESTMENT_INSIGHTS = {
  avgRentalYield: 3.2,
  priceAppreciation: 4.5,
  topLocality: 'Whitefield',
  riskLevel: 'Moderate',
};

const DEMO_ACTIVITY = [
  { day: 'Mon', views: 5, saves: 1 },
  { day: 'Tue', views: 8, saves: 2 },
  { day: 'Wed', views: 3, saves: 0 },
  { day: 'Thu', views: 12, saves: 3 },
  { day: 'Fri', views: 7, saves: 1 },
  { day: 'Sat', views: 15, saves: 4 },
  { day: 'Sun', views: 6, saves: 2 },
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

export default function BuyerDashboard({ locality }) {
  const { user } = useAuth();
  const [loading, setLoading] = useState(true);
  const [watchlist, setWatchlist] = useState(DEMO_WATCHLIST);
  const [properties, setProperties] = useState(DEMO_WATCHLIST_PROPERTIES);
  const [savedSearches, setSavedSearches] = useState(DEMO_SAVED_SEARCHES);
  const [priceAlerts, setPriceAlerts] = useState(DEMO_PRICE_ALERTS);
  const [insights, setInsights] = useState(DEMO_INVESTMENT_INSIGHTS);
  const [activity, setActivity] = useState(DEMO_ACTIVITY);

  const fetchMetrics = useCallback(async () => {
    setLoading(true);
    try {
      const userId = user?.email || user?.id || 'anonymous';
      const res = await fetch(`${API_URL}/api/buyer-dashboard/metrics?user_id=${userId}`, { signal: AbortSignal.timeout(5000) });
      if (res.ok) {
        const data = await res.json();
        if (data.watchlist) setWatchlist(data.watchlist);
        if (data.properties) setProperties(data.properties);
        if (data.saved_searches) setSavedSearches(data.saved_searches);
        if (data.price_alerts) setPriceAlerts(data.price_alerts);
        if (data.insights) setInsights(data.insights);
        if (data.activity) setActivity(data.activity);
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
            <Home className="w-4 h-4 text-blue-400" />
            Buyer Dashboard
          </h2>
          <p className="text-[10px] text-slate-400 mt-0.5">
            {locality ? `Focused on ${locality}` : 'All micro-markets'} · {user?.name || 'Buyer'}
          </p>
        </div>
        <button onClick={fetchMetrics} className="p-1.5 text-slate-400 hover:text-white hover:bg-slate-700/50 rounded transition" title="Refresh">
          <RefreshCw className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <MetricCard icon={Heart} label="Watchlist" value={watchlist.total} change={watchlist.newMatches} changeType="up" color="blue" />
        <MetricCard icon={TrendingUp} label="Avg Price Change" value={`${watchlist.avgPriceChange}%`} change={Math.abs(watchlist.avgPriceChange)} changeType={watchlist.avgPriceChange < 0 ? 'up' : 'down'} color="green" />
        <MetricCard icon={Bell} label="Active Alerts" value={priceAlerts.length} change={priceAlerts.filter(a => a.triggered).length} changeType="up" color="purple" />
        <MetricCard icon={DollarSign} label="Rental Yield" value={`${insights.avgRentalYield}%`} change={0.3} changeType="up" color="amber" />
      </div>

      <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-3">
        <h3 className="text-xs font-semibold text-white mb-3 flex items-center gap-1.5">
          <Heart className="w-3.5 h-3.5 text-pink-400" />
          Watchlist Properties
        </h3>
        <div className="space-y-2">
          {properties.slice(0, 4).map(p => (
            <div key={p.id} className="flex items-center justify-between p-2 bg-slate-800/60 rounded-lg hover:bg-slate-700/40 transition cursor-pointer group">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-white truncate">{p.name}</span>
                  <span className={`text-[9px] px-1.5 py-0.5 rounded border ${
                    p.priceChange < 0 ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30' :
                    p.priceChange > 0 ? 'bg-red-500/20 text-red-400 border-red-500/30' :
                    'bg-slate-500/20 text-slate-400 border-slate-500/30'
                  }`}>
                    {p.priceChange > 0 ? '↑' : p.priceChange < 0 ? '↓' : '→'} {Math.abs(p.priceChange)}%
                  </span>
                </div>
                <div className="flex items-center gap-2 mt-0.5">
                  <span className="text-[10px] text-slate-400 flex items-center gap-0.5">
                    <MapPin className="w-2.5 h-2.5" />{p.locality}
                  </span>
                  <span className="text-[10px] text-slate-400">{p.price}</span>
                </div>
              </div>
              <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition">
                <button className="p-1 text-slate-400 hover:text-blue-400 hover:bg-blue-500/10 rounded" title="View">
                  <Eye className="w-3 h-3" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-3">
        <h3 className="text-xs font-semibold text-white mb-3 flex items-center gap-1.5">
          <Search className="w-3.5 h-3.5 text-blue-400" />
          Saved Searches
        </h3>
        <div className="space-y-2">
          {savedSearches.map(s => (
            <div key={s.id} className="flex items-center justify-between p-2 bg-slate-800/60 rounded-lg hover:bg-slate-700/40 transition cursor-pointer">
              <div>
                <div className="text-xs font-medium text-white">{s.name}</div>
                <div className="text-[10px] text-slate-400">{s.locality} · {s.results} results</div>
              </div>
              {s.newResults > 0 && (
                <span className="text-[9px] px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded-full">
                  +{s.newResults} new
                </span>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-3">
        <h3 className="text-xs font-semibold text-white mb-3 flex items-center gap-1.5">
          <Bell className="w-3.5 h-3.5 text-amber-400" />
          Price Alerts
        </h3>
        <div className="space-y-2">
          {priceAlerts.map(a => (
            <div key={a.id} className={`flex items-center justify-between p-2 rounded-lg ${a.triggered ? 'bg-emerald-500/10 border border-emerald-500/30' : 'bg-slate-800/60'}`}>
              <div>
                <div className="text-xs font-medium text-white">{a.locality}</div>
                <div className="text-[10px] text-slate-400">Target: {a.threshold} · Current: {a.current}</div>
              </div>
              {a.triggered && (
                <span className="text-[9px] px-2 py-0.5 bg-emerald-500/20 text-emerald-400 rounded-full">
                  Triggered!
                </span>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="bg-slate-800/40 border border-slate-700/50 rounded-lg p-3">
        <h3 className="text-xs font-semibold text-white mb-2 flex items-center gap-1.5">
          <FileText className="w-3.5 h-3.5 text-amber-400" />
          Quick Actions
        </h3>
        <div className="grid grid-cols-2 gap-2">
          <button onClick={() => window.dispatchEvent(new CustomEvent('valora-smart-tab-change', { detail: { tab: 'free_analysis' } }))} className="flex items-center gap-2 p-2 bg-blue-500/10 border border-blue-500/30 rounded-lg hover:bg-blue-500/20 transition text-xs text-blue-300">
            <Eye className="w-3.5 h-3.5" />
            Run Analysis
          </button>
          <button onClick={() => window.dispatchEvent(new CustomEvent('valora-smart-tab-change', { detail: { tab: 'roi_projection' } }))} className="flex items-center gap-2 p-2 bg-emerald-500/10 border border-emerald-500/30 rounded-lg hover:bg-emerald-500/20 transition text-xs text-emerald-300">
            <TrendingUp className="w-3.5 h-3.5" />
            ROI Projection
          </button>
          <button onClick={() => window.dispatchEvent(new CustomEvent('valora-smart-tab-change', { detail: { tab: 'risk_analysis' } }))} className="flex items-center gap-2 p-2 bg-purple-500/10 border border-purple-500/30 rounded-lg hover:bg-purple-500/20 transition text-xs text-purple-300">
            <Target className="w-3.5 h-3.5" />
            Risk Analysis
          </button>
          <button onClick={() => window.dispatchEvent(new CustomEvent('valora-smart-tab-change', { detail: { tab: 'comparables' } }))} className="flex items-center gap-2 p-2 bg-amber-500/10 border border-amber-500/30 rounded-lg hover:bg-amber-500/20 transition text-xs text-amber-300">
            <MapPin className="w-3.5 h-3.5" />
            Comparables
          </button>
        </div>
      </div>
    </div>
  );
}
