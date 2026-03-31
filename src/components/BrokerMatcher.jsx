/**
 * BrokerMatcher - Match users with relevant brokers
 * 
 * Shows:
 * - Top 3 recommended brokers for a property
 * - Matching logic: locality expertise, property type, past activity
 * - "Connect with broker" flow
 * - "Share listing with brokers" option
 */

import { useState } from 'react'
import { Star, MapPin, Phone, Share2, Check, Users } from 'lucide-react'
import { API_URL } from '../apiConfig'

export default function BrokerMatcher({ listing, locality }) {
  const [brokers, setBrokers] = useState([])
  const [loading, setLoading] = useState(false)
  const [connected, setConnected] = useState({})

  const findBrokers = async () => {
    setLoading(true)
    try {
      const response = await fetch(`${API_URL}/api/brokers/match`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          property_type: listing.property_type,
          locality: listing.locality || locality,
          price_range: listing.price,
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        setBrokers(data.brokers || [])
      }
    } catch (err) {
      console.error('[BrokerMatcher] Error:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleConnect = async (brokerId) => {
    try {
      await fetch(`${API_URL}/api/brokers/${brokerId}/connect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          listing_id: listing.id,
        })
      })
      setConnected(prev => ({ ...prev, [brokerId]: true }))
    } catch (err) {
      console.error('[BrokerMatcher] Error connecting:', err)
    }
  }

  const handleShareAll = async () => {
    try {
      await fetch(`${API_URL}/api/brokers/share-listing`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          listing_id: listing.id,
          broker_ids: brokers.map(b => b.id),
        })
      })
      alert('Listing shared with all matched brokers!')
    } catch (err) {
      console.error('[BrokerMatcher] Error sharing:', err)
    }
  }

  return (
    <div className="bg-dark-800/50 rounded-xl p-4 border border-primary-700/30">
      <div className="flex items-center justify-between mb-3">
        <h4 className="font-medium text-white flex items-center gap-2">
          <Users className="w-4 h-4 text-primary-400" />
          Find Best Brokers
        </h4>
        <button
          onClick={findBrokers}
          disabled={loading}
          className="text-xs text-primary-400 hover:text-white"
        >
          {loading ? 'Finding...' : 'Match'}
        </button>
      </div>

      {brokers.length > 0 ? (
        <div className="space-y-3">
          {brokers.map((broker, i) => (
            <div key={broker.id || i} className="bg-dark-700/50 rounded-lg p-3">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-medium text-white">{broker.name}</span>
                    {broker.match_score > 0 && (
                      <span className="px-2 py-0.5 bg-primary-500/20 text-primary-300 rounded-full text-xs">
                        {broker.match_score}% match
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 text-sm text-primary-400">
                    {broker.locality && (
                      <span className="flex items-center gap-1">
                        <MapPin className="w-3 h-3" />
                        {broker.locality}
                      </span>
                    )}
                    {broker.deals_count > 0 && (
                      <span>{broker.deals_count} deals</span>
                    )}
                    {broker.rating > 0 && (
                      <span className="flex items-center gap-1">
                        <Star className="w-3 h-3 text-yellow-400" />
                        {broker.rating}
                      </span>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => handleConnect(broker.id)}
                  disabled={connected[broker.id]}
                  className={`px-3 py-1.5 rounded-lg text-sm flex items-center gap-1 ${
                    connected[broker.id]
                      ? 'bg-green-500/20 text-green-300'
                      : 'bg-primary-500 hover:bg-primary-400 text-white'
                  }`}
                >
                  {connected[broker.id] ? (
                    <>
                      <Check className="w-4 h-4" />
                      Connected
                    </>
                  ) : (
                    <>
                      <Phone className="w-4 h-4" />
                      Connect
                    </>
                  )}
                </button>
              </div>
            </div>
          ))}

          {/* Share All Button */}
          {brokers.length > 1 && (
            <button
              onClick={handleShareAll}
              className="w-full mt-2 px-4 py-2 bg-primary-500/20 hover:bg-primary-500/30 text-primary-300 rounded-lg text-sm flex items-center justify-center gap-2"
            >
              <Share2 className="w-4 h-4" />
              Share listing with all matched brokers
            </button>
          )}
        </div>
      ) : (
        <p className="text-sm text-primary-400 text-center py-4">
          Click "Match" to find brokers for your property
        </p>
      )}
    </div>
  )
}