import React, { useState, useEffect } from 'react';
import { BarChart3, Coins, TrendingUp, Info, AlertCircle, Download } from 'lucide-react';

const UsageDashboard = ({ user }) => {
  const [usageData, setUsageData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [period, setPeriod] = useState(30); // days

  useEffect(() => {
    if (user && user.id) {
      fetchUsageData();
    }
  }, [user, period]);

  const fetchUsageData = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/admin/usage/user/${user.id}?days=${period}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('valora_token')}`
        }
      });
      
      if (!response.ok) throw new Error('Failed to fetch usage data');
      
      const data = await response.json();
      setUsageData(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const formatNumber = (num) => {
    return new Intl.NumberFormat('en-IN').format(num || 0);
  };

  const getBalanceColor = (balance) => {
    if (balance > 500) return 'text-green-600';
    if (balance > 100) return 'text-yellow-600';
    return 'text-red-600';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 flex items-center gap-3">
        <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0" />
        <div>
          <p className="text-sm font-medium text-red-800">Error loading usage data</p>
          <p className="text-xs text-red-600 mt-1">{error}</p>
        </div>
      </div>
    );
  }

  const balance = usageData?.balance?.units_available || 0;
  const usage = usageData?.usage || {};
  const topActions = usage.top_actions || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Usage & Balance</h2>
          <p className="text-sm text-gray-600 mt-1">Track your compute usage and balance</p>
        </div>
        
        {/* Period Selector */}
        <select
          value={period}
          onChange={(e) => setPeriod(Number(e.target.value))}
          className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      {/* Balance Card - Prominent */}
      <div className="bg-gradient-to-br from-blue-500 to-blue-700 rounded-xl p-6 text-white shadow-lg">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Coins className="h-5 w-5" />
              <span className="text-sm font-medium opacity-90">Available Balance</span>
            </div>
            <div className="text-4xl font-bold">{formatNumber(balance)}</div>
            <div className="text-sm opacity-75 mt-1">compute units</div>
          </div>
          
          <div className="text-right">
            <div className="text-sm opacity-75 mb-1">Lifetime Usage</div>
            <div className="text-2xl font-semibold">{formatNumber(usage.lifetime_usage || 0)}</div>
            <div className="text-xs opacity-75 mt-1">units used</div>
          </div>
        </div>
        
        {/* Low balance warning */}
        {balance < 100 && (
          <div className="mt-4 bg-white/20 rounded-lg p-3 flex items-center gap-2">
            <AlertCircle className="h-4 w-4" />
            <span className="text-sm">Low balance! Consider topping up to continue using premium features.</span>
          </div>
        )}
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center gap-2 text-gray-600 mb-2">
            <BarChart3 className="h-4 w-4" />
            <span className="text-sm font-medium">Actions</span>
          </div>
          <div className="text-2xl font-bold text-gray-900">{formatNumber(usage.event_count || 0)}</div>
          <div className="text-xs text-gray-500 mt-1">in last {period} days</div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center gap-2 text-gray-600 mb-2">
            <TrendingUp className="h-4 w-4" />
            <span className="text-sm font-medium">Units Used</span>
          </div>
          <div className="text-2xl font-bold text-gray-900">{formatNumber(usage.total_units_used || 0)}</div>
          <div className="text-xs text-gray-500 mt-1">in last {period} days</div>
        </div>

        <div className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-center gap-2 text-gray-600 mb-2">
            <Coins className="h-4 w-4" />
            <span className="text-sm font-medium">Units Earned</span>
          </div>
          <div className="text-2xl font-bold text-green-600">{formatNumber(usageData?.balance?.units_earned || 0)}</div>
          <div className="text-xs text-gray-500 mt-1">from contributions</div>
        </div>
      </div>

      {/* Top Actions */}
      {topActions.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">Top Actions</h3>
          <div className="space-y-3">
            {topActions.map((action, idx) => {
              const percentage = usage.total_units_used > 0 
                ? (action.units / usage.total_units_used) * 100 
                : 0;
              
              return (
                <div key={idx} className="space-y-1">
                  <div className="flex items-center justify-between text-sm">
                    <span className="font-medium text-gray-700">
                      {action.action.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                    </span>
                    <div className="flex items-center gap-3 text-gray-600">
                      <span>{action.count}×</span>
                      <span className="font-semibold">{formatNumber(action.units)} units</span>
                    </div>
                  </div>
                  <div className="w-full bg-gray-100 rounded-full h-2 overflow-hidden">
                    <div 
                      className="bg-blue-500 h-full rounded-full transition-all duration-300"
                      style={{ width: `${Math.min(percentage, 100)}%` }}
                    ></div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Info Box */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex gap-3">
          <Info className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-blue-800">
            <p className="font-medium mb-1">How Usage Works</p>
            <ul className="space-y-1 text-blue-700">
              <li>• Each action (query, analysis, simulation) costs compute units</li>
              <li>• Your contributions help improve our AI and earn you bonus units</li>
              <li>• Top up anytime to continue using premium features</li>
              <li>• All data collection is anonymized and privacy-compliant</li>
            </ul>
          </div>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3">
        <button 
          onClick={() => window.location.href = '/payments'}
          className="flex-1 bg-blue-600 text-white rounded-lg px-4 py-3 font-medium hover:bg-blue-700 transition-colors"
        >
          Top Up Balance
        </button>
        <button 
          onClick={fetchUsageData}
          className="px-6 py-3 border border-gray-300 rounded-lg font-medium text-gray-700 hover:bg-gray-50 transition-colors"
        >
          Refresh
        </button>
      </div>
    </div>
  );
};

export default UsageDashboard;
