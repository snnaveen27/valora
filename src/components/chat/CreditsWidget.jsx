/**
 * CreditsWidget — Compact credits bar for the chat panel.
 * Shows remaining credits, tier badge, and quick upgrade/purchase actions.
 */

import { useState, useCallback } from 'react'
import { Zap, Crown, ChevronUp, ChevronDown, ShoppingCart, ArrowUpCircle, X } from 'lucide-react'
import { API_URL } from '../../apiConfig'

const TIER_COLORS = {
  free: 'text-slate-400 bg-slate-700/40',
  pro: 'text-amber-400 bg-amber-700/30',
  team: 'text-purple-400 bg-purple-700/30',
}

const TIER_ICONS = {
  free: Zap,
  pro: Crown,
  team: Crown,
}

export default function CreditsWidget({ credits, userId, onCreditsUpdate }) {
  const [expanded, setExpanded] = useState(false)
  const [purchasing, setPurchasing] = useState(false)
  const [upgrading, setUpgrading] = useState(false)
  const [message, setMessage] = useState(null)

  const tier = credits?.tier || 'free'
  const remaining = credits?.credits?.remaining ?? '...'
  const total = credits?.credits?.total ?? '...'
  const pct = total > 0 ? Math.round((remaining / total) * 100) : 0

  const TierIcon = TIER_ICONS[tier] || Zap
  const tierColor = TIER_COLORS[tier] || TIER_COLORS.free

  const handlePurchase = useCallback(async (packId) => {
    setPurchasing(true)
    setMessage(null)
    try {
      const resp = await fetch(`${API_URL}/api/credits/purchase`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, pack_id: packId }),
      })
      const data = await resp.json()
      if (data.success) {
        setMessage({ type: 'success', text: `+${data.credits_added} credits added!` })
        if (onCreditsUpdate) onCreditsUpdate()
      } else {
        setMessage({ type: 'error', text: data.detail || 'Purchase failed' })
      }
    } catch (err) {
      setMessage({ type: 'error', text: err.message })
    } finally {
      setPurchasing(false)
      setTimeout(() => setMessage(null), 3000)
    }
  }, [userId, onCreditsUpdate])

  const handleUpgrade = useCallback(async (planId) => {
    setUpgrading(true)
    setMessage(null)
    try {
      const resp = await fetch(`${API_URL}/api/credits/upgrade`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, plan_id: planId }),
      })
      const data = await resp.json()
      if (data.success) {
        setMessage({ type: 'success', text: `Upgraded to ${data.plan}!` })
        if (onCreditsUpdate) onCreditsUpdate()
      } else {
        setMessage({ type: 'error', text: data.detail || 'Upgrade failed' })
      }
    } catch (err) {
      setMessage({ type: 'error', text: err.message })
    } finally {
      setUpgrading(false)
      setTimeout(() => setMessage(null), 3000)
    }
  }, [userId, onCreditsUpdate])

  if (!credits) return null

  return (
    <div className="border-t border-primary-700/30 bg-surface-primary/60">
      {/* Compact bar */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between px-3 py-1.5 hover:bg-primary-700/20 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span className={`flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase ${tierColor}`}>
            <TierIcon className="w-3 h-3" />
            {tier}
          </span>
          <div className="flex items-center gap-1.5">
            <div className="w-16 h-1.5 bg-primary-800 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${
                  pct > 50 ? 'bg-emerald-500' : pct > 20 ? 'bg-amber-500' : 'bg-red-500'
                }`}
                style={{ width: `${pct}%` }}
              />
            </div>
            <span className="text-[10px] text-primary-400">
              {remaining}/{total}
            </span>
          </div>
        </div>
        {expanded ? <ChevronDown className="w-3 h-3 text-primary-500" /> : <ChevronUp className="w-3 h-3 text-primary-500" />}
      </button>

      {/* Expanded panel */}
      {expanded && (
        <div className="px-3 pb-3 space-y-2 animate-in slide-in-from-bottom-2 duration-200">
          {/* Message toast */}
          {message && (
            <div className={`flex items-center justify-between px-2 py-1 rounded text-xs ${
              message.type === 'success' ? 'bg-emerald-900/50 text-emerald-300' : 'bg-red-900/50 text-red-300'
            }`}>
              <span>{message.text}</span>
              <button onClick={() => setMessage(null)}><X className="w-3 h-3" /></button>
            </div>
          )}

          {/* Quick top-up */}
          <div>
            <p className="text-[10px] text-primary-500 mb-1 font-medium">Quick Top-up</p>
            <div className="flex gap-1.5">
              {[
                { id: 'starter', label: '100', price: '59' },
                { id: 'standard', label: '300', price: '139' },
                { id: 'bulk', label: '1000', price: '399' },
              ].map(pack => (
                <button
                  key={pack.id}
                  onClick={() => handlePurchase(pack.id)}
                  disabled={purchasing}
                  className="flex-1 flex flex-col items-center gap-0.5 px-2 py-1.5 rounded-lg bg-primary-800/50 hover:bg-primary-700/50 border border-primary-700/30 hover:border-primary-600/50 transition-all disabled:opacity-50"
                >
                  <span className="text-xs font-semibold text-white">+{pack.label}</span>
                  <span className="text-[9px] text-primary-400">{'\u20B9'}{pack.price}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Upgrade */}
          {tier === 'free' && (
            <div>
              <p className="text-[10px] text-primary-500 mb-1 font-medium">Upgrade Plan</p>
              <div className="flex gap-1.5">
                <button
                  onClick={() => handleUpgrade('pro_monthly')}
                  disabled={upgrading}
                  className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded-lg bg-amber-900/30 hover:bg-amber-800/40 border border-amber-700/30 text-amber-300 text-xs font-medium transition-all disabled:opacity-50"
                >
                  <ArrowUpCircle className="w-3 h-3" />
                  Pro {'\u20B9'}599/mo
                </button>
                <button
                  onClick={() => handleUpgrade('team_monthly')}
                  disabled={upgrading}
                  className="flex-1 flex items-center justify-center gap-1 px-2 py-1.5 rounded-lg bg-purple-900/30 hover:bg-purple-800/40 border border-purple-700/30 text-purple-300 text-xs font-medium transition-all disabled:opacity-50"
                >
                  <ArrowUpCircle className="w-3 h-3" />
                  Team {'\u20B9'}999/mo
                </button>
              </div>
            </div>
          )}

          {tier !== 'free' && (
            <p className="text-[9px] text-primary-500 text-center">
              {tier === 'pro' ? '5,000 credits/month' : '20,000 credits/month'} &bull; Resets monthly
            </p>
          )}
        </div>
      )}
    </div>
  )
}
