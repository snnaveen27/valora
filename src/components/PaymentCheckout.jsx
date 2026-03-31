import { useState, useEffect } from 'react'
import { CreditCard, Zap, Shield, Check, X, Loader2 } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { API_URL } from '../apiConfig'

export default function PaymentCheckout({ isOpen, onClose, type = 'subscription', planId = null, packId = null }) {
  const { user, token } = useAuth()
  const [config, setConfig] = useState(null)
  const [selectedGateway, setSelectedGateway] = useState('stripe')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [plans, setPlans] = useState({})
  const [packs, setPacks] = useState({})
  const [promo, setPromo] = useState(null)

  useEffect(() => {
    if (isOpen) {
      fetchConfig()
      fetchPlans()
      fetchPacks()
    }
  }, [isOpen])

  const fetchConfig = async () => {
    try {
      const res = await fetch(`${API_URL}/api/payments/config`)
      const data = await res.json()
      setConfig(data)
      setSelectedGateway(data.default_gateway || 'stripe')
    } catch (err) {
      console.error('Failed to fetch payment config:', err)
    }
  }

  const fetchPlans = async () => {
    try {
      const res = await fetch(`${API_URL}/api/payments/plans`)
      const data = await res.json()
      setPlans(data.plans || {})
      setPromo(data.promo)
    } catch (err) {
      console.error('Failed to fetch plans:', err)
    }
  }

  const fetchPacks = async () => {
    try {
      const res = await fetch(`${API_URL}/api/payments/topup-packs`)
      const data = await res.json()
      setPacks(data.packs || {})
    } catch (err) {
      console.error('Failed to fetch packs:', err)
    }
  }

  const handleSubscribe = async (selectedPlanId) => {
    setLoading(true)
    setError(null)

    try {
      const res = await fetch(`${API_URL}/api/payments/subscribe`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          plan_id: selectedPlanId,
          gateway: selectedGateway,
          phone: user?.phone || '9999999999',
        }),
      })

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.detail || 'Failed to create subscription')
      }

      // Handle gateway-specific checkout
      if (selectedGateway === 'stripe' && data.subscription?.url) {
        // Redirect to Stripe Checkout
        window.location.href = data.subscription.url
      } else if (selectedGateway === 'razorpay' && data.subscription) {
        // Open Razorpay checkout
        openRazorpayCheckout(data.subscription, 'subscription')
      } else if (selectedGateway === 'cashfree' && data.subscription) {
        // Open Cashfree checkout
        openCashfreeCheckout(data.subscription)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleTopup = async (selectedPackId) => {
    setLoading(true)
    setError(null)

    try {
      const res = await fetch(`${API_URL}/api/payments/topup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          pack_id: selectedPackId,
          gateway: selectedGateway,
        }),
      })

      const data = await res.json()

      if (!res.ok) {
        throw new Error(data.detail || 'Failed to create top-up order')
      }

      // Handle gateway-specific checkout
      if (selectedGateway === 'stripe' && data.order?.client_secret) {
        // Open Stripe Elements for PaymentIntent
        openStripePayment(data.order)
      } else if (selectedGateway === 'razorpay' && data.order) {
        // Open Razorpay checkout
        openRazorpayCheckout(data.order, 'payment')
      } else if (selectedGateway === 'cashfree' && data.order) {
        // Open Cashfree checkout
        openCashfreeCheckout(data.order)
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const openRazorpayCheckout = (orderData, type) => {
    if (!window.Razorpay) {
      // Load Razorpay script dynamically
      const script = document.createElement('script')
      script.src = 'https://checkout.razorpay.com/v1/checkout.js'
      script.onload = () => initiateRazorpay(orderData, type)
      document.body.appendChild(script)
    } else {
      initiateRazorpay(orderData, type)
    }
  }

  const initiateRazorpay = (orderData, type) => {
    const options = {
      key: config?.razorpay?.key_id,
      amount: orderData.amount,
      currency: 'INR',
      name: 'Valora AI',
      description: type === 'subscription' ? 'Subscription Payment' : 'Top-up Units',
      order_id: orderData.id,
      handler: async (response) => {
        // Verify payment
        await verifyPayment('razorpay', response.razorpay_order_id, response.razorpay_payment_id, response.razorpay_signature)
      },
      prefill: {
        name: user?.name,
        email: user?.email,
      },
      theme: {
        color: '#3B82F6',
      },
    }

    const rzp = new window.Razorpay(options)
    rzp.open()
  }

  const openCashfreeCheckout = (orderData) => {
    // Cashfree checkout redirect
    if (orderData.payment_session_id) {
      const cashfree = window.Cashfree({ mode: config?.cashfree?.environment === 'TEST' ? 'sandbox' : 'production' })
      cashfree.checkout({
        paymentSessionId: orderData.payment_session_id,
        redirectTarget: '_self',
      })
    }
  }

  const openStripePayment = async (orderData) => {
    // For Stripe PaymentIntent, we'd typically use Stripe Elements
    // For now, show a message that Stripe checkout will be opened
    alert('Stripe payment integration requires Stripe.js Elements. Redirecting...')
    // In production, integrate @stripe/stripe-js and @stripe/react-stripe-js
  }

  const verifyPayment = async (gateway, orderId, paymentId, signature) => {
    try {
      const res = await fetch(`${API_URL}/api/payments/verify`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          gateway,
          order_id: orderId,
          payment_id: paymentId,
          signature,
        }),
      })

      const data = await res.json()

      if (data.success) {
        alert('Payment successful! Your account has been updated.')
        onClose()
        window.location.reload()
      } else {
        setError('Payment verification failed')
      }
    } catch (err) {
      setError('Payment verification error: ' + err.message)
    }
  }

  if (!isOpen) return null

  const gatewayIcons = {
    stripe: '💳',
    razorpay: '🔵',
    cashfree: '🟢',
  }

  const gatewayDescriptions = {
    stripe: 'Best for AI usage tracking • Cards, UPI',
    razorpay: 'Popular in India • Cards, UPI, NetBanking',
    cashfree: 'Fast settlements • UPI AutoPay',
  }

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
      <div className="bg-slate-800 rounded-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto border border-slate-700 shadow-2xl">
        {/* Header */}
        <div className="p-6 border-b border-slate-700">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl flex items-center justify-center">
                <CreditCard className="w-5 h-5 text-white" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white">
                  {type === 'subscription' ? 'Subscribe to Valora AI' : 'Top-up Compute Units'}
                </h2>
                <p className="text-slate-400 text-sm">Choose your payment method</p>
              </div>
            </div>
            <button onClick={onClose} className="p-2 hover:bg-slate-700 rounded-lg transition">
              <X className="w-5 h-5 text-slate-400" />
            </button>
          </div>
        </div>

        {/* Promo Banner */}
        {promo?.active && (
          <div className="mx-6 mt-4 p-3 bg-gradient-to-r from-amber-500/20 to-orange-500/20 border border-amber-500/50 rounded-xl">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-xl">🎉</span>
                <span className="text-amber-400 font-semibold">{promo.discount_percent}% OFF - {promo.promo_code}</span>
              </div>
              <span className="text-amber-200/70 text-sm">{promo.days_left} days left</span>
            </div>
          </div>
        )}

        {/* Gateway Selection */}
        <div className="p-6 border-b border-slate-700">
          <h3 className="text-white font-semibold mb-3">Payment Gateway</h3>
          <div className="grid grid-cols-3 gap-3">
            {config?.supported_gateways?.map((gateway) => (
              <button
                key={gateway}
                onClick={() => setSelectedGateway(gateway)}
                className={`p-4 rounded-xl border transition text-left ${
                  selectedGateway === gateway
                    ? 'bg-blue-500/20 border-blue-500'
                    : 'bg-slate-700/50 border-slate-600 hover:border-slate-500'
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-lg">{gatewayIcons[gateway]}</span>
                  <span className="text-white font-medium capitalize">{gateway}</span>
                  {gateway === 'stripe' && (
                    <span className="bg-green-500/20 text-green-400 text-[10px] px-1.5 py-0.5 rounded font-medium">AI</span>
                  )}
                </div>
                <p className="text-slate-400 text-xs">{gatewayDescriptions[gateway]}</p>
              </button>
            ))}
          </div>
        </div>

        {/* Error Display */}
        {error && (
          <div className="mx-6 mt-4 p-3 bg-red-500/20 border border-red-500/50 rounded-xl text-red-400 text-sm">
            {error}
          </div>
        )}

        {/* Plans or Packs */}
        <div className="p-6">
          {type === 'subscription' ? (
            <>
              <h3 className="text-white font-semibold mb-4">Select a Plan</h3>
              <div className="grid grid-cols-2 gap-4">
                {Object.entries(plans).map(([id, plan]) => (
                  <div
                    key={id}
                    className="p-4 bg-slate-700/50 border border-slate-600 rounded-xl hover:border-blue-500/50 transition"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-white font-bold">{plan.name}</h4>
                      {plan.is_promo_price && (
                        <span className="bg-amber-500 text-black text-[10px] font-bold px-2 py-0.5 rounded">
                          {plan.discount_percent}% OFF
                        </span>
                      )}
                    </div>
                    <p className="text-3xl font-bold text-white mb-1">
                      ₹{plan.current_price_inr}
                      <span className="text-sm text-slate-400 font-normal">/{plan.billing_period === 'monthly' ? 'mo' : 'yr'}</span>
                    </p>
                    {plan.is_promo_price && (
                      <p className="text-slate-500 line-through text-sm">₹{plan.base_price_inr}</p>
                    )}
                    <p className="text-blue-400 text-sm mt-2">{plan.units_per_month.toLocaleString()} units/month</p>
                    <ul className="mt-3 space-y-1">
                      {plan.features?.slice(0, 3).map((feature, i) => (
                        <li key={i} className="flex items-center gap-2 text-slate-300 text-xs">
                          <Check className="w-3 h-3 text-green-400" />
                          {feature.replace(/_/g, ' ')}
                        </li>
                      ))}
                    </ul>
                    <button
                      onClick={() => handleSubscribe(id)}
                      disabled={loading}
                      className="w-full mt-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 text-white font-semibold rounded-lg transition flex items-center justify-center gap-2"
                    >
                      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Zap className="w-4 h-4" />}
                      Subscribe
                    </button>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <>
              <h3 className="text-white font-semibold mb-4">Select a Top-up Pack</h3>
              <div className="grid grid-cols-3 gap-4">
                {Object.entries(packs).map(([id, pack]) => (
                  <div
                    key={id}
                    className="p-4 bg-slate-700/50 border border-slate-600 rounded-xl hover:border-blue-500/50 transition text-center"
                  >
                    {pack.is_promo_price && (
                      <span className="bg-amber-500 text-black text-[10px] font-bold px-2 py-0.5 rounded">
                        {pack.discount_percent}% OFF
                      </span>
                    )}
                    <p className="text-3xl font-bold text-white mt-2">{pack.units.toLocaleString()}</p>
                    <p className="text-slate-400 text-sm">units</p>
                    <p className="text-2xl font-bold text-amber-400 mt-2">₹{pack.current_price_inr}</p>
                    {pack.is_promo_price && (
                      <p className="text-slate-500 line-through text-sm">₹{pack.base_price_inr}</p>
                    )}
                    <button
                      onClick={() => handleTopup(id)}
                      disabled={loading}
                      className="w-full mt-4 py-2 bg-green-600 hover:bg-green-700 disabled:bg-slate-600 text-white font-semibold rounded-lg transition flex items-center justify-center gap-2"
                    >
                      {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <CreditCard className="w-4 h-4" />}
                      Buy Now
                    </button>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>

        {/* Security Footer */}
        <div className="p-4 border-t border-slate-700 bg-slate-800/50 rounded-b-2xl">
          <div className="flex items-center justify-center gap-4 text-slate-400 text-xs">
            <div className="flex items-center gap-1">
              <Shield className="w-3 h-3" />
              <span>256-bit SSL Encryption</span>
            </div>
            <span>•</span>
            <span>PCI DSS Compliant</span>
            <span>•</span>
            <span>Secure Payments</span>
          </div>
        </div>
      </div>
    </div>
  )
}
