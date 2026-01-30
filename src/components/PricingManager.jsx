import React, { useState, useEffect } from 'react';
import { DollarSign, Save, RefreshCw, AlertCircle, CheckCircle, Edit2 } from 'lucide-react';

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
      const response = await fetch('/api/admin/pricing/config', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      
      if (!response.ok) throw new Error('Failed to fetch pricing config');
      
      const data = await response.json();
      setConfig(data.config);
      setMessage(null);
    } catch (err) {
      setMessage({ type: 'error', text: err.message });
    } finally {
      setLoading(false);
    }
  };

  const saveConfig = async () => {
    try {
      setSaving(true);
      const response = await fetch('/api/admin/pricing/config', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
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
      const response = await fetch('/api/admin/pricing/reload', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
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
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <p className="text-red-800">Failed to load pricing configuration</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <DollarSign className="h-6 w-6" />
            Pricing Configuration
          </h2>
          <p className="text-sm text-gray-600 mt-1">
            Manage action costs, tier limits, and promotional pricing
          </p>
        </div>
        
        <div className="flex gap-2">
          <button
            onClick={fetchConfig}
            className="px-4 py-2 border border-gray-300 rounded-lg text-gray-700 hover:bg-gray-50 flex items-center gap-2"
          >
            <RefreshCw className="h-4 w-4" />
            Refresh
          </button>
          <button
            onClick={saveConfig}
            disabled={saving}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
          >
            <Save className="h-4 w-4" />
            {saving ? 'Saving...' : 'Save & Reload'}
          </button>
        </div>
      </div>

      {/* Message */}
      {message && (
        <div className={`rounded-lg p-4 flex items-center gap-3 ${
          message.type === 'success' ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
        }`}>
          {message.type === 'success' ? (
            <CheckCircle className="h-5 w-5 text-green-600 flex-shrink-0" />
          ) : (
            <AlertCircle className="h-5 w-5 text-red-600 flex-shrink-0" />
          )}
          <p className={message.type === 'success' ? 'text-green-800' : 'text-red-800'}>
            {message.text}
          </p>
        </div>
      )}

      {/* Last Updated */}
      {config.last_updated && (
        <div className="text-sm text-gray-600">
          Last updated: {new Date(config.last_updated).toLocaleString()} by {config.updated_by || 'system'}
        </div>
      )}

      {/* Promotional Pricing */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Promotional Pricing</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Promo Price per Unit (₹)
            </label>
            <input
              type="number"
              value={config.pricing?.promo_per_unit_inr || 2}
              onChange={(e) => updatePricing('promo_per_unit_inr', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Regular Price per Unit (₹)
            </label>
            <input
              type="number"
              value={config.pricing?.regular_per_unit_inr || 10}
              onChange={(e) => updatePricing('regular_per_unit_inr', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Discount Percentage (%)
            </label>
            <input
              type="number"
              value={config.pricing?.promo_discount_percent || 80}
              onChange={(e) => updatePricing('promo_discount_percent', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Valid Until
            </label>
            <input
              type="date"
              value={config.pricing?.promo_valid_until || '2026-03-31'}
              onChange={(e) => updatePricing('promo_valid_until', e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div className="flex items-center">
            <input
              type="checkbox"
              checked={config.pricing?.promo_active !== false}
              onChange={(e) => updatePricing('promo_active', e.target.checked)}
              className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <label className="ml-2 block text-sm text-gray-700">
              Promo Active
            </label>
          </div>
        </div>
      </div>

      {/* Tier Monthly Limits */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Tier Monthly Limits</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Object.entries(config.tier_monthly_limits || {}).map(([tier, limit]) => (
            <div key={tier}>
              <label className="block text-sm font-medium text-gray-700 mb-1 capitalize">
                {tier} Tier
              </label>
              <input
                type="number"
                value={limit}
                onChange={(e) => updateTierLimit(tier, e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="-1 for unlimited"
              />
              <p className="text-xs text-gray-500 mt-1">
                {limit === -1 ? 'Unlimited' : `${limit} units/month`}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Action Costs */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">Action Costs (Units)</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Object.entries(config.action_costs || {}).sort((a, b) => b[1] - a[1]).map(([action, cost]) => (
            <div key={action} className="flex items-center gap-2">
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  {action.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                </label>
                <input
                  type="number"
                  value={cost}
                  onChange={(e) => updateActionCost(action, e.target.value)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  min="0"
                  max="1000"
                />
              </div>
              <div className="text-sm text-gray-500 mt-6">
                {cost === 0 ? 'FREE' : `${cost} units`}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Warning */}
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 flex items-start gap-3">
        <AlertCircle className="h-5 w-5 text-yellow-600 flex-shrink-0 mt-0.5" />
        <div className="text-sm text-yellow-800">
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
