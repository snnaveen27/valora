/**
 * MyListings - Seller dashboard section
 * 
 * Shows:
 * - User's property listings
 * - Listing status
 * - Add/edit/delete functionality
 * - Seller intelligence insights
 * 
 * Only visible if user intent includes 'sell' or 'both'
 */

import { useState, useEffect } from 'react'
import { Plus, Home, MapPin, IndianRupee, Eye, Edit2, Trash2 } from 'lucide-react'
import { API_URL } from '../apiConfig'

const PROPERTY_TYPES = [
  { id: 'apartment', label: 'Apartment', icon: '🏢' },
  { id: 'villa', label: 'Villa', icon: '🏠' },
  { id: 'plot', label: 'Plot', icon: '🏞️' },
  { id: 'commercial', label: 'Commercial', icon: '🏬' },
]

const BEDROOM_OPTIONS = ['1 BHK', '2 BHK', '3 BHK', '4 BHK', '5+ BHK']

export default function MyListings({ intent, user }) {
  const [listings, setListings] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [editingListing, setEditingListing] = useState(null)
  const [loading, setLoading] = useState(false)
  const [formData, setFormData] = useState({
    property_type: '',
    bedrooms: '',
    area_sqft: '',
    price: '',
    locality: '',
    description: '',
    images: [],
  })

  // Only show if user has seller intent
  if (!intent || (intent !== 'sell' && intent !== 'both')) {
    return null
  }

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    try {
      const endpoint = editingListing 
        ? `${API_URL}/api/listings/${editingListing.id}`
        : `${API_URL}/api/listings`
      
      const method = editingListing ? 'PUT' : 'POST'
      
      const response = await fetch(endpoint, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: user.id,
          ...formData,
        })
      })
      
      if (response.ok) {
        const saved = await response.json()
        if (editingListing) {
          setListings(prev => prev.map(l => l.id === saved.id ? saved : l))
        } else {
          setListings(prev => [...prev, saved])
        }
        setShowForm(false)
        setEditingListing(null)
        setFormData({
          property_type: '',
          bedrooms: '',
          area_sqft: '',
          price: '',
          locality: '',
          description: '',
          images: [],
        })
      }
    } catch (err) {
      console.error('[MyListings] Error saving listing:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleEdit = (listing) => {
    setEditingListing(listing)
    setFormData({
      property_type: listing.property_type || '',
      bedrooms: listing.bedrooms || '',
      area_sqft: listing.area_sqft || '',
      price: listing.price || '',
      locality: listing.locality || '',
      description: listing.description || '',
      images: listing.images || [],
    })
    setShowForm(true)
  }

  const handleDelete = async (listingId) => {
    if (!confirm('Are you sure you want to delete this listing?')) return
    try {
      await fetch(`${API_URL}/api/listings/${listingId}`, { method: 'DELETE' })
      setListings(prev => prev.filter(l => l.id !== listingId))
    } catch (err) {
      console.error('[MyListings] Error deleting listing:', err)
    }
  }

  // Format price in lakhs/crores
  const formatPrice = (price) => {
    if (!price) return 'Not set'
    const num = parseFloat(price)
    if (num >= 10000000) return `₹${(num / 10000000).toFixed(2)} Cr`
    if (num >= 100000) return `₹${(num / 100000).toFixed(2)} L`
    return `₹${num.toLocaleString()}`
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold text-white flex items-center gap-2">
          <Home className="w-5 h-5 text-primary-400" />
          My Listings
        </h2>
        <button
          onClick={() => {
            setShowForm(true)
            setEditingListing(null)
            setFormData({
              property_type: '',
              bedrooms: '',
              area_sqft: '',
              price: '',
              locality: '',
              description: '',
              images: [],
            })
          }}
          className="flex items-center gap-2 px-4 py-2 bg-primary-500 hover:bg-primary-400 text-white rounded-lg text-sm"
        >
          <Plus className="w-4 h-4" />
          Add Property
        </button>
      </div>

      {/* Listing Form */}
      {showForm && (
        <div className="bg-dark-800 rounded-xl p-6 border border-primary-700/30">
          <h3 className="text-lg font-medium text-white mb-4">
            {editingListing ? 'Edit Listing' : 'Add New Listing'}
          </h3>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              {/* Property Type */}
              <div>
                <label className="block text-sm text-primary-300 mb-2">Property Type</label>
                <select
                  value={formData.property_type}
                  onChange={(e) => handleInputChange('property_type', e.target.value)}
                  className="w-full px-4 py-3 bg-dark-700 border border-primary-700/50 rounded-lg text-white"
                  required
                >
                  <option value="">Select type</option>
                  {PROPERTY_TYPES.map(pt => (
                    <option key={pt.id} value={pt.id}>{pt.icon} {pt.label}</option>
                  ))}
                </select>
              </div>

              {/* Bedrooms */}
              <div>
                <label className="block text-sm text-primary-300 mb-2">Bedrooms</label>
                <select
                  value={formData.bedrooms}
                  onChange={(e) => handleInputChange('bedrooms', e.target.value)}
                  className="w-full px-4 py-3 bg-dark-700 border border-primary-700/50 rounded-lg text-white"
                >
                  <option value="">Select</option>
                  {BEDROOM_OPTIONS.map(bhk => (
                    <option key={bhk} value={bhk}>{bhk}</option>
                  ))}
                </select>
              </div>

              {/* Area */}
              <div>
                <label className="block text-sm text-primary-300 mb-2">Area (sqft)</label>
                <input
                  type="number"
                  value={formData.area_sqft}
                  onChange={(e) => handleInputChange('area_sqft', e.target.value)}
                  placeholder="e.g., 1200"
                  className="w-full px-4 py-3 bg-dark-700 border border-primary-700/50 rounded-lg text-white"
                />
              </div>

              {/* Price */}
              <div>
                <label className="block text-sm text-primary-300 mb-2">Price (₹)</label>
                <input
                  type="number"
                  value={formData.price}
                  onChange={(e) => handleInputChange('price', e.target.value)}
                  placeholder="e.g., 8500000"
                  className="w-full px-4 py-3 bg-dark-700 border border-primary-700/50 rounded-lg text-white"
                  required
                />
              </div>
            </div>

            {/* Locality */}
            <div>
              <label className="block text-sm text-primary-300 mb-2">Locality</label>
              <input
                type="text"
                value={formData.locality}
                onChange={(e) => handleInputChange('locality', e.target.value)}
                placeholder="e.g., Whitefield"
                className="w-full px-4 py-3 bg-dark-700 border border-primary-700/50 rounded-lg text-white"
                required
              />
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm text-primary-300 mb-2">Description</label>
              <textarea
                value={formData.description}
                onChange={(e) => handleInputChange('description', e.target.value)}
                placeholder="Describe your property..."
                rows={3}
                className="w-full px-4 py-3 bg-dark-700 border border-primary-700/50 rounded-lg text-white resize-none"
              />
            </div>

            {/* Actions */}
            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={() => {
                  setShowForm(false)
                  setEditingListing(null)
                }}
                className="px-4 py-2 text-primary-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-6 py-2 bg-primary-500 hover:bg-primary-400 text-white rounded-lg disabled:opacity-50"
              >
                {loading ? 'Saving...' : (editingListing ? 'Update' : 'Create Listing')}
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Listings Grid */}
      {listings.length === 0 && !showForm ? (
        <div className="text-center py-8 bg-dark-800/50 rounded-xl border border-primary-700/20">
          <Home className="w-12 h-12 text-primary-400 mx-auto mb-3" />
          <p className="text-primary-300 mb-2">No listings yet</p>
          <p className="text-sm text-primary-400">Click "Add Property" to create your first listing</p>
        </div>
      ) : (
        <div className="grid gap-4">
          {listings.map(listing => (
            <div key={listing.id} className="bg-dark-800 rounded-xl p-4 border border-primary-700/30">
              <div className="flex justify-between items-start">
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-2xl">
                      {PROPERTY_TYPES.find(pt => pt.id === listing.property_type)?.icon || '🏠'}
                    </span>
                    <div>
                      <h4 className="font-medium text-white">
                        {listing.bedrooms ? `${listing.bedrooms} ` : ''}{PROPERTY_TYPES.find(pt => pt.id === listing.property_type)?.label || 'Property'}
                      </h4>
                      <div className="flex items-center gap-1 text-sm text-primary-400">
                        <MapPin className="w-3 h-3" />
                        {listing.locality || 'Location not set'}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-4 mt-2">
                    <div className="flex items-center gap-1 text-primary-200">
                      <IndianRupee className="w-4 h-4 text-primary-400" />
                      <span className="font-semibold">{formatPrice(listing.price)}</span>
                    </div>
                    {listing.area_sqft && (
                      <span className="text-sm text-primary-400">{listing.area_sqft} sqft</span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleEdit(listing)}
                    className="p-2 text-primary-400 hover:text-white transition-colors"
                  >
                    <Edit2 className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => handleDelete(listing.id)}
                    className="p-2 text-red-400 hover:text-red-300 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
              
              {/* Status Badge */}
              <div className="mt-3 flex items-center gap-2">
                <span className={`px-2 py-1 rounded-full text-xs ${
                  listing.status === 'active' 
                    ? 'bg-green-500/20 text-green-300' 
                    : 'bg-yellow-500/20 text-yellow-300'
                }`}>
                  {listing.status || 'Draft'}
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}