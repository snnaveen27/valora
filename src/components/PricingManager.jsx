import React, { useState, useEffect } from 'react';
import { DollarSign, Save, RefreshCw, AlertCircle, CheckCircle, Edit2 } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const PricingManager = () => {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);
  const [editMode, setEditMode] = useState({});

  useEffect(() => {
    fetchConfig();
  }, []);

  const fetchConfig = async () => {
    try {
      setLoading(true);
      const token = localStorage.getItem('valora_token');
      
      if (!token) {
        setMessage({ type: 'error', text: 'No authentication token found. Please log in again.' });
        setLoading(false);
        return;
      }
      
      console.log('[PricingManager] Fetching from:', `${API_URL}/api/admin/pricing/config`);
      
      const response = await fetch(`${API_URL}/api/admin/pricing/config`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
      
      if (response.status === 401) {
        const errorData = await response.json();
        setMessage({ type: 'error', text: `Authentication failed: ${errorData.detail || 'Please log in again'}` });
        setLoading(false);
        return;
      }
      
      if (response.status === 403) {
        const errorData = await response.json();
        setMessage({ type: 'error', text: `Access denied: ${errorData.detail || 'Admin access required'}` });
        setLoading(false);
        return;
      }
      
      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }
      
      const data = await response.json();
      console.log('[PricingManager] Config loaded:', data);
      setConfig(data.config || data);
      setMessage(null);
    } catch (err) {
      console.error('[PricingManager] Error:', err);
      setMessage({ type: 'error', text: err.message });
    } finally {
      setLoading(false);
    }
  };

  const saveConfig = async () => {
    try {
      setSaving(true);
      const response = await fetch(`${API_URL}/api/admin/pricing/config`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('valora_token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(config)
      });
      
      if (!response.ok) throw new Error('Failed to save pricing config');
      
      const data = await response.json();
      setMessage({ type: 'success', text: 'Pricing configuration saved successfully!' });
      setEditMode({});
      
      // Reload config
      await reloadConfig();
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    } finally {
      setSaving(false);
    }
  };

  const reloadConfig = async () => {
    try {
      const response = await fetch(`${API_URL}/api/admin/pricing/reload`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('valora_token')}`
        }
      });
      
      if (!response.ok) throw new Error('Failed to reload config');
      
      setMessage({ type: 'success', text: 'Configuration reloaded without restart!' });
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    }
  };

  const updateActionCost = (action, value) => {
    setConfig({
      ...config,
      action_costs: {
        ...config.action_costs,
        [action]: parseInt(value) || 0
      }
    });
  };

  const updateTierLimit = (tier, value) => {
    setConfig({
      ...config,
      tier_monthly_limits: {
        ...config.tier_monthly_limits,
        [tier]: parseInt(value)
      }
    });
  };

  const updatePricing = (key, value) => {
    setConfig({
      ...config,
      pricing: {
        ...config.pricing,
        [key]: key.includes('percent') ? parseInt(value) : 
                key.includes('active') ? value : 
                key.includes('inr') ? parseInt(value) : value
      }
    });
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500"></div>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="bg-red-900/30 border border-red-700 rounded-lg p-4">
        <p className="text-red-400">Failed to load pricing configuration</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <DollarSign className="h-5 w-5" />
            Pricing Configuration
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Manage action costs, tier limits, and promotional pricing
          </p>
        </div>
        
        <div className="flex gap-2">
          <button
            onClick={fetchConfig}
            className="px-3 py-1.5 border border-slate-600 rounded-lg text-slate-300 hover:bg-slate-700 flex items-center gap-2 text-sm transition"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
          <button
            onClick={saveConfig}
            disabled={saving}
            className="px-3 py-1.5 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:opacity-50 flex items-center gap-2 text-sm transition"
          >
            <Save className="h-4 w-4" />
            {saving ? 'Saving...' : 'Save & Reload'}
          </button>
        </div>
      </div>

      {/* Message */}
      {message && (
        <div className={`rounded-lg p-3 flex items-center gap-3 ${
          message.type === 'success' ? 'bg-green-900/30 border border-green-700' : 'bg-red-900/30 border border-red-700'
        }`}>
          {message.type === 'success' ? (
            <CheckCircle className="h-5 w-5 text-green-400 flex-shrink-0" />
          ) : (
            <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0" />
          )}
          <p className={message.type === 'success' ? 'text-green-400' : 'text-red-400'}>
            {message.text}
          </p>
        </div>
      )}

      {/* Last Updated */}
      {config.last_updated && (
        <div className="text-sm text-slate-400">
          Last updated: {new Date(config.last_updated).toLocaleString()} by {config.updated_by || 'system'}
        </div>
      )}

      {/* Promotional Pricing */}
      <div className="bg-slate-700/50 rounded-lg border border-slate-600 p-4">
        <h3 className="text-md font-semibold text-white mb-3">Promotional Pricing</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">
              Promo Price per Unit (₹)
            </label>
            <input
              type="number"
              value={config.pricing?.promo_per_unit_inr || 2}
              onChange={(e) => updatePricing('promo_per_unit_inr', e.target.value)}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">
              Regular Price per Unit (₹)
            </label>
            <input
              type="number"
              value={config.pricing?.regular_per_unit_inr || 10}
              onChange={(e) => updatePricing('regular_per_unit_inr', e.target.value)}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">
              Discount Percentage (%)
            </label>
            <input
              type="number"
              value={config.pricing?.promo_discount_percent || 80}
              onChange={(e) => updatePricing('promo_discount_percent', e.target.value)}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">
              Valid Until
            </label>
            <input
              type="date"
              value={config.pricing?.promo_valid_until || '2026-03-31'}
              onChange={(e) => updatePricing('promo_valid_until', e.target.value)}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
            />
          </div>
          <div className="flex items-center">
            <input
              type="checkbox"
              checked={config.pricing?.promo_active !== false}
              onChange={(e) => updatePricing('promo_active', e.target.checked)}
              className="h-4 w-4 text-purple-600 focus:ring-purple-500 border-slate-600 rounded bg-slate-800"
            />
            <label className="ml-2 block text-sm text-slate-300">
              Promo Active
            </label>
          </div>
        </div>
      </div>

      {/* Tier Monthly Limits */}
      <div className="bg-slate-700/50 rounded-lg border border-slate-600 p-4">
        <h3 className="text-md font-semibold text-white mb-3">Tier Monthly Limits</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Object.entries(config.tier_monthly_limits || {}).map(([tier, limit]) => (
            <div key={tier}>
              <label className="block text-sm font-medium text-slate-300 mb-1 capitalize">
                {tier} Tier
              </label>
              <input
                type="number"
                value={limit}
                onChange={(e) => updateTierLimit(tier, e.target.value)}
                className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                placeholder="-1 for unlimited"
              />
              <p className="text-xs text-slate-400 mt-1">
                {limit === -1 ? 'Unlimited' : `${limit} units/month`}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Action Costs */}
      <div className="bg-slate-700/50 rounded-lg border border-slate-600 p-4">
        <h3 className="text-md font-semibold text-white mb-3">Action Costs (Units)</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Object.entries(config.action_costs || {}).sort((a, b) => b[1] - a[1]).map(([action, cost]) => (
            <div key={action} className="flex items-center gap-2">
              <div className="flex-1">
                <label className="block text-sm font-medium text-slate-300 mb-1">
                  {action.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                </label>
                <input
                  type="number"
                  value={cost}
                  onChange={(e) => updateActionCost(action, e.target.value)}
                  className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
                  min="0"
                  max="1000"
                />
              </div>
              <div className="text-sm text-slate-400 mt-6">
                {cost === 0 ? 'FREE' : `${cost} units`}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Warning */}
      <div className="bg-yellow-900/30 border border-yellow-700 rounded-lg p-4 flex items-start gap-3">
        <AlertCircle className="h-5 w-5 text-yellow-500 flex-shrink-0 mt-0.5" />
        <div className="text-sm text-yellow-300">
          <p className="font-medium">Important Notes:</p>
          <ul className="list-disc list-inside mt-2 space-y-1">
            <li>Changes are saved immediately and reloaded without server restart</li>
            <li>All changes are logged for audit purposes</li>
            <li>Free actions (0 units) remain accessible even when users run out of units</li>
            <li>Set tier limit to -1 for unlimited usage</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default PricingManager;
