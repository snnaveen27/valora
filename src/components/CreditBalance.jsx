/**
 * CreditBalance - Credit balance widget for UI header
 * Shows current credits, tier, and top-up button
 */

import { useState, useEffect } from 'react';
import { Coins, Zap, Crown, Plus, RefreshCw, Calendar } from 'lucide-react';
import { API_URL } from '../apiConfig';
import { useLanguage } from '../contexts/LanguageContext';

export default function CreditBalance({ userId = 'anonymous', onUpgrade }) {
  const { t } = useLanguage()
  const [balance, setBalance] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showTopUp, setShowTopUp] = useState(false);

  // Fetch credit balance
  useEffect(() => {
    fetchBalance();
    
    // Listen for credit deduction events
    const handleCreditDeduction = (e) => {
      if (e.detail?.remaining_credits !== undefined) {
        setBalance(prev => prev ? { ...prev, total_available: e.detail.remaining_credits } : prev);
      }
    };
    
    window.addEventListener('valora-credits-deducted', handleCreditDeduction);
    
    // Refresh balance every 60 seconds
    const interval = setInterval(fetchBalance, 60000);
    
    return () => {
      window.removeEventListener('valora-credits-deducted', handleCreditDeduction);
      clearInterval(interval);
    };
  }, [userId]);

  const fetchBalance = async () => {
    try {
      const response = await fetch(`${API_URL}/api/credits/balance?user_id=${userId}`);
      if (response.ok) {
        const data = await response.json();
        setBalance(data);
      }
    } catch (error) {
      console.error('Failed to fetch credit balance:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleTopUp = async (packageId) => {
    try {
      const response = await fetch(`${API_URL}/api/credits/top-up`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, package: packageId })
      });
      
      if (response.ok) {
        const data = await response.json();
        setBalance(prev => ({ ...prev, total_available: data.new_balance }));
        setShowTopUp(false);
      }
    } catch (error) {
      console.error('Top-up failed:', error);
    }
  };

  const tierColors = {
    'free': 'from-slate-500 to-slate-600',
    'pro': 'from-blue-500 to-purple-500',
    'team': 'from-emerald-500 to-teal-500'
  };

  const tierIcons = {
    'free': <Coins className="w-3.5 h-3.5" />,
    'pro': <Zap className="w-3.5 h-3.5" />,
    'team': <Crown className="w-3.5 h-3.5" />
  };

  if (loading) {
    return (
      <div className="credit-balance flex items-center gap-2 px-3 py-1.5 bg-slate-800/50 rounded-lg">
        <RefreshCw className="w-4 h-4 text-slate-400 animate-spin" />
        <span className="text-xs text-slate-400">{t('loading')}</span>
      </div>
    );
  }

  const tier = balance?.tier || 'free';
  const credits = balance?.total_available || 0;
  
  // Calculate days remaining for pro membership
  const getDaysRemaining = () => {
    if (tier !== 'pro' || !balance?.next_reset) return null;
    const resetTime = balance.next_reset * 1000; // Convert to milliseconds
    const now = Date.now();
    const diffMs = resetTime - now;
    const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));
    return diffDays > 0 ? diffDays : 0;
  };
  
  const daysRemaining = getDaysRemaining();

  return (
    <div className="credit-balance flex items-center gap-2">
      {/* Tier Badge */}
      <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-gradient-to-r ${tierColors[tier]} text-white`}>
        {tierIcons[tier]}
        <span className="text-xs font-medium capitalize">{tier}</span>
        {daysRemaining !== null && (
          <span className="text-[10px] opacity-80 ml-1">({t('daysLeft', { days: daysRemaining })})</span>
        )}
      </div>

      {/* Credit Count */}
      <div className="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800/50 rounded-lg border border-slate-700">
        <Coins className="w-4 h-4 text-amber-400" />
        <span className="text-sm font-medium text-white">{credits.toLocaleString()}</span>
        <span className="text-xs text-slate-400">{t('credits')}</span>
      </div>

      {/* Top-up Button */}
      <div className="relative">
        <button
          onClick={() => setShowTopUp(!showTopUp)}
          className="flex items-center gap-1 px-2.5 py-1.5 bg-blue-500/20 hover:bg-blue-500/30 text-blue-400 rounded-lg transition"
        >
          <Plus className="w-3.5 h-3.5" />
          <span className="text-xs font-medium">{t('topUp')}</span>
        </button>

        {/* Top-up Dropdown - Admin Panel Style */}
        {showTopUp && (
          <>
            {/* Backdrop */}
            <div className="fixed inset-0 z-[90]" onClick={() => setShowTopUp(false)} />
            
            {/* Dropdown Panel */}
            <div className="absolute right-0 top-full mt-2 w-72 bg-slate-800 border border-slate-700 rounded-xl shadow-2xl z-[100] overflow-hidden">
              <div className="p-3 border-b border-slate-700 bg-slate-800/80">
                <h3 className="text-sm font-semibold text-white">{t('topUpCredits')}</h3>
                <p className="text-xs text-slate-400 mt-0.5">{t('choosePackage')}</p>
              </div>
              
              <div className="p-2 space-y-1">
                {/* Starter Package */}
                <button
                  onClick={() => handleTopUp('starter')}
                  className="w-full flex items-center justify-between p-3 bg-slate-700/30 hover:bg-slate-700/60 rounded-lg transition"
                >
                  <div className="text-left">
                    <div className="text-white font-medium text-sm">{t('starter')}</div>
                    <div className="text-xs text-slate-400">{t('credits100', { credits: 100 })}</div>
                  </div>
                  <div className="text-green-400 font-bold text-sm">₹59</div>
                </button>

                {/* Standard Package */}
                <button
                  onClick={() => handleTopUp('standard')}
                  className="w-full flex items-center justify-between p-3 bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500/40 rounded-lg transition relative"
                >
                  <div className="absolute -top-1 right-2 bg-blue-500 text-white text-[9px] px-1.5 py-0.5 rounded-full font-medium">
                    POPULAR
                  </div>
                  <div className="text-left">
                    <div className="text-white font-medium text-sm">{t('standard')}</div>
                    <div className="text-xs text-slate-400">{t('credits300', { credits: 300 })}</div>
                  </div>
                  <div className="text-green-400 font-bold text-sm">₹139</div>
                </button>

                {/* Power Package */}
                <button
                  onClick={() => handleTopUp('power')}
                  className="w-full flex items-center justify-between p-3 bg-slate-700/30 hover:bg-slate-700/60 rounded-lg transition"
                >
                  <div className="text-left">
                    <div className="text-white font-medium text-sm">{t('power')}</div>
                    <div className="text-xs text-slate-400">{t('credits1000', { credits: 1000 })}</div>
                  </div>
                  <div className="text-green-400 font-bold text-sm">₹399</div>
                </button>
              </div>

              {/* Pro Subscription - Only show for free users */}
              {tier === 'free' && (
                <div className="p-2 border-t border-slate-700">
                  <button
                    onClick={() => {
                      setShowTopUp(false);
                      onUpgrade?.();
                    }}
                    className="w-full flex items-center justify-between p-3 bg-gradient-to-r from-purple-500/20 to-blue-500/20 hover:from-purple-500/30 hover:to-blue-500/30 border border-purple-500/40 rounded-lg transition"
                  >
                    <div className="text-left">
                      <div className="text-white font-medium text-sm flex items-center gap-2">
                        <Zap className="w-3.5 h-3.5 text-amber-400" />
                        {t('proSubscription')}
                      </div>
                      <div className="text-xs text-slate-400">{t('proSubscriptionCredits')}</div>
                    </div>
                    <div className="text-purple-400 font-bold text-sm">₹599/mo</div>
                  </button>
                </div>
              )}

              {/* Team Subscription - Only show for pro users */}
              {tier === 'pro' && (
                <div className="p-2 border-t border-slate-700">
                  <button
                    onClick={() => {
                      setShowTopUp(false);
                      onUpgrade?.();
                    }}
                    className="w-full flex items-center justify-between p-3 bg-gradient-to-r from-emerald-500/20 to-teal-500/20 hover:from-emerald-500/30 hover:to-teal-500/30 border border-emerald-500/40 rounded-lg transition"
                  >
                    <div className="text-left">
                      <div className="text-white font-medium text-sm flex items-center gap-2">
                        <Crown className="w-3.5 h-3.5 text-emerald-400" />
                        {t('teamSubscription')}
                      </div>
                      <div className="text-xs text-slate-400">{t('teamSubscriptionCredits')}</div>
                    </div>
                    <div className="text-emerald-400 font-bold text-sm">₹999/mo</div>
                  </button>
                </div>
              )}

              <div className="p-2 border-t border-slate-700/50">
                <button
                  onClick={() => setShowTopUp(false)}
                  className="w-full text-center text-xs text-slate-400 hover:text-white transition py-1"
                >
                  {t('cancel')}
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
