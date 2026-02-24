/**
 * FamilyWatchlist - Shared property list for Family Hub
 * 
 * Features:
 * - Property cards with key details
 * - Add property form/modal
 * - Status indicators (considering/shortlisted/rejected/visited)
 * - Priority badges
 * - Notes display
 * - Responsive grid layout
 * 
 * Props:
 * @param {string} sessionId - Current session ID
 * @param {function} onUpdate - Callback when watchlist is updated
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Heart,
  Plus,
  MapPin,
  Wallet,
  Building2,
  Clock,
  MoreVertical,
  Trash2,
  Edit3,
  CheckCircle,
  XCircle,
  Eye,
  Star,
  AlertCircle,
  Loader2,
  Filter,
  ChevronDown,
  FileText,
  X,
} from 'lucide-react';

import {
  getWatchlist,
  addToWatchlist,
  updateWatchlistItem,
  removeFromWatchlist,
} from '../../services/familyApi';

// Status options
const STATUS_OPTIONS = [
  { id: 'considering', label: 'Considering', icon: Eye, color: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
  { id: 'shortlisted', label: 'Shortlisted', icon: Star, color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30' },
  { id: 'visited', label: 'Visited', icon: CheckCircle, color: 'bg-green-500/20 text-green-400 border-green-500/30' },
  { id: 'rejected', label: 'Rejected', icon: XCircle, color: 'bg-red-500/20 text-red-400 border-red-500/30' },
];

// Priority options
const PRIORITY_OPTIONS = [
  { id: 'high', label: 'High', color: 'bg-red-500 text-white' },
  { id: 'medium', label: 'Medium', color: 'bg-yellow-500 text-white' },
  { id: 'low', label: 'Low', color: 'bg-slate-500 text-white' },
];

// Initial form state
const INITIAL_FORM = {
  property_id: '',
  property_title: '',
  locality: '',
  latitude: '',
  longitude: '',
  price: '',
  notes: '',
  priority: 'medium',
};

export default function FamilyWatchlist({ sessionId, onUpdate }) {
  // Watchlist state
  const [watchlist, setWatchlist] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // Filter state
  const [statusFilter, setStatusFilter] = useState('all');
  const [showFilters, setShowFilters] = useState(false);
  
  // Add/Edit modal state
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingItem, setEditingItem] = useState(null);
  const [form, setForm] = useState(INITIAL_FORM);
  const [formErrors, setFormErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  // Item menu state
  const [openMenuId, setOpenMenuId] = useState(null);

  // Load watchlist on mount
  useEffect(() => {
    if (sessionId) {
      loadWatchlist();
    }
  }, [sessionId, statusFilter]);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = () => setOpenMenuId(null);
    if (openMenuId) {
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  }, [openMenuId]);

  /**
   * Load watchlist from API
   */
  const loadWatchlist = async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const params = statusFilter !== 'all' ? { status: statusFilter } : {};
      const data = await getWatchlist(sessionId, params);
      setWatchlist(data || []);
    } catch (err) {
      console.error('[FamilyWatchlist] Failed to load watchlist:', err);
      setError('Failed to load properties. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Validate form
   */
  const validateForm = () => {
    const errors = {};
    
    if (!form.property_title?.trim()) {
      errors.property_title = 'Property title is required';
    }
    
    if (form.price && parseFloat(form.price) < 0) {
      errors.price = 'Price cannot be negative';
    }
    
    if (form.latitude && (parseFloat(form.latitude) < -90 || parseFloat(form.latitude) > 90)) {
      errors.latitude = 'Invalid latitude (-90 to 90)';
    }
    
    if (form.longitude && (parseFloat(form.longitude) < -180 || parseFloat(form.longitude) > 180)) {
      errors.longitude = 'Invalid longitude (-180 to 180)';
    }
    
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  /**
   * Handle form submission
   */
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) return;
    
    setIsSubmitting(true);
    
    try {
      const propertyData = {
        property_id: form.property_id?.trim() || null,
        property_title: form.property_title?.trim(),
        locality: form.locality?.trim() || null,
        latitude: form.latitude ? parseFloat(form.latitude) : null,
        longitude: form.longitude ? parseFloat(form.longitude) : null,
        price: form.price ? parseFloat(form.price) : null,
        notes: form.notes?.trim() || null,
        priority: form.priority,
      };
      
      if (editingItem) {
        await updateWatchlistItem(sessionId, editingItem.id, propertyData);
      } else {
        await addToWatchlist(sessionId, propertyData);
      }
      
      setShowAddModal(false);
      setEditingItem(null);
      setForm(INITIAL_FORM);
      loadWatchlist();
      onUpdate?.();
    } catch (err) {
      console.error('[FamilyWatchlist] Failed to save property:', err);
      setFormErrors({ submit: err.message || 'Failed to save property' });
    } finally {
      setIsSubmitting(false);
    }
  };

  /**
   * Handle status change
   */
  const handleStatusChange = async (item, newStatus) => {
    try {
      await updateWatchlistItem(sessionId, item.id, { status: newStatus });
      loadWatchlist();
      onUpdate?.();
    } catch (err) {
      console.error('[FamilyWatchlist] Failed to update status:', err);
      setError('Failed to update status');
    }
    setOpenMenuId(null);
  };

  /**
   * Handle priority change
   */
  const handlePriorityChange = async (item, newPriority) => {
    try {
      await updateWatchlistItem(sessionId, item.id, { priority: newPriority });
      loadWatchlist();
    } catch (err) {
      console.error('[FamilyWatchlist] Failed to update priority:', err);
      setError('Failed to update priority');
    }
    setOpenMenuId(null);
  };

  /**
   * Handle remove item
   */
  const handleRemove = async (itemId) => {
    try {
      await removeFromWatchlist(sessionId, itemId);
      loadWatchlist();
      onUpdate?.();
    } catch (err) {
      console.error('[FamilyWatchlist] Failed to remove property:', err);
      setError('Failed to remove property');
    }
    setOpenMenuId(null);
  };

  /**
   * Open edit modal
   */
  const openEditModal = (item) => {
    setEditingItem(item);
    setForm({
      property_id: item.property_id || '',
      property_title: item.property_title || '',
      locality: item.locality || '',
      latitude: item.latitude?.toString() || '',
      longitude: item.longitude?.toString() || '',
      price: item.price?.toString() || '',
      notes: item.notes || '',
      priority: item.priority || 'medium',
    });
    setShowAddModal(true);
    setOpenMenuId(null);
  };

  /**
   * Format price for display
   */
  const formatPrice = (price) => {
    if (!price) return 'Price not specified';
    
    if (price >= 10000000) {
      return `₹${(price / 10000000).toFixed(2)} Cr`;
    } else if (price >= 100000) {
      return `₹${(price / 100000).toFixed(2)} L`;
    }
    return `₹${price.toLocaleString('en-IN')}`;
  };

  /**
   * Format date for display
   */
  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
    });
  };

  /**
   * Get status config
   */
  const getStatusConfig = (status) => {
    return STATUS_OPTIONS.find(s => s.id === status) || STATUS_OPTIONS[0];
  };

  /**
   * Get priority config
   */
  const getPriorityConfig = (priority) => {
    return PRIORITY_OPTIONS.find(p => p.id === priority) || PRIORITY_OPTIONS[1];
  };

  return (
    <div className="p-4 sm:p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-semibold text-white">Property Watchlist</h3>
          <span className="px-2 py-0.5 bg-slate-700/50 rounded-full text-sm text-slate-400">
            {watchlist.length} properties
          </span>
        </div>
        
        <div className="flex items-center gap-2">
          {/* Filter Button */}
          <div className="relative">
            <button
              onClick={(e) => {
                e.stopPropagation();
                setShowFilters(!showFilters);
              }}
              className={`flex items-center gap-2 px-3 py-2 rounded-lg transition-colors ${
                statusFilter !== 'all'
                  ? 'bg-purple-500/20 text-purple-400'
                  : 'bg-slate-700/50 text-slate-400 hover:bg-slate-700'
              }`}
            >
              <Filter className="w-4 h-4" />
              <span className="hidden sm:inline text-sm">
                {statusFilter === 'all' ? 'Filter' : STATUS_OPTIONS.find(s => s.id === statusFilter)?.label}
              </span>
              <ChevronDown className="w-3 h-3" />
            </button>
            
            {showFilters && (
              <div 
                className="absolute right-0 top-full mt-1 bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-10 min-w-[150px]"
                onClick={(e) => e.stopPropagation()}
              >
                <button
                  onClick={() => {
                    setStatusFilter('all');
                    setShowFilters(false);
                  }}
                  className={`w-full px-4 py-2 text-left text-sm hover:bg-slate-700/50 ${
                    statusFilter === 'all' ? 'text-purple-400' : 'text-slate-300'
                  }`}
                >
                  All Properties
                </button>
                {STATUS_OPTIONS.map(status => (
                  <button
                    key={status.id}
                    onClick={() => {
                      setStatusFilter(status.id);
                      setShowFilters(false);
                    }}
                    className={`w-full px-4 py-2 text-left text-sm hover:bg-slate-700/50 flex items-center gap-2 ${
                      statusFilter === status.id ? 'text-purple-400' : 'text-slate-300'
                    }`}
                  >
                    <status.icon className="w-3 h-3" />
                    {status.label}
                  </button>
                ))}
              </div>
            )}
          </div>
          
          {/* Add Button */}
          <button
            onClick={() => {
              setEditingItem(null);
              setForm(INITIAL_FORM);
              setShowAddModal(true);
            }}
            className="flex items-center gap-2 px-3 py-2 bg-purple-500/20 hover:bg-purple-500/30 text-purple-400 rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            <span className="hidden sm:inline text-sm">Add Property</span>
          </button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-4 p-3 bg-red-500/20 border border-red-500/30 rounded-lg flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-400" />
          <p className="text-sm text-red-400">{error}</p>
          <button onClick={() => setError(null)} className="ml-auto">
            <X className="w-4 h-4 text-red-400" />
          </button>
        </div>
      )}

      {/* Loading State */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
        </div>
      )}

      {/* Empty State */}
      {!isLoading && watchlist.length === 0 && (
        <div className="text-center py-12">
          <Heart className="w-12 h-12 text-slate-600 mx-auto mb-3" />
          <h4 className="text-lg font-medium text-slate-400 mb-2">No Properties Yet</h4>
          <p className="text-sm text-slate-500 mb-4">
            {statusFilter !== 'all'
              ? `No ${STATUS_OPTIONS.find(s => s.id === statusFilter)?.label?.toLowerCase()} properties`
              : 'Start adding properties to your family watchlist'}
          </p>
          <button
            onClick={() => setShowAddModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-purple-500 hover:bg-purple-600 text-white rounded-lg transition-colors"
          >
            <Plus className="w-4 h-4" />
            Add First Property
          </button>
        </div>
      )}

      {/* Property Grid */}
      {!isLoading && watchlist.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {watchlist.map(item => {
            const statusConfig = getStatusConfig(item.status);
            const priorityConfig = getPriorityConfig(item.priority);
            
            return (
              <div
                key={item.id}
                className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden hover:border-slate-600 transition-colors"
              >
                {/* Card Header */}
                <div className="p-4 border-b border-slate-700/50">
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <h4 className="font-medium text-white truncate">
                        {item.property_title || 'Untitled Property'}
                      </h4>
                      {item.locality && (
                        <div className="flex items-center gap-1 text-sm text-slate-400 mt-1">
                          <MapPin className="w-3 h-3" />
                          <span className="truncate">{item.locality}</span>
                        </div>
                      )}
                    </div>
                    
                    {/* Priority Badge */}
                    <span className={`px-2 py-0.5 text-xs font-medium rounded ${priorityConfig.color}`}>
                      {priorityConfig.label}
                    </span>
                  </div>
                </div>
                
                {/* Card Body */}
                <div className="p-4 space-y-3">
                  {/* Price */}
                  <div className="flex items-center gap-2">
                    <Wallet className="w-4 h-4 text-slate-400" />
                    <span className="text-white font-medium">{formatPrice(item.price)}</span>
                  </div>
                  
                  {/* Status */}
                  <div className="flex items-center gap-2">
                    <statusConfig.icon className="w-4 h-4 text-slate-400" />
                    <span className={`px-2 py-0.5 text-xs rounded-full border ${statusConfig.color}`}>
                      {statusConfig.label}
                    </span>
                  </div>
                  
                  {/* Notes */}
                  {item.notes && (
                    <div className="flex items-start gap-2">
                      <FileText className="w-4 h-4 text-slate-400 mt-0.5" />
                      <p className="text-sm text-slate-400 line-clamp-2">{item.notes}</p>
                    </div>
                  )}
                  
                  {/* Added Date */}
                  <div className="flex items-center gap-2 text-xs text-slate-500">
                    <Clock className="w-3 h-3" />
                    <span>Added {formatDate(item.created_at)}</span>
                  </div>
                </div>
                
                {/* Card Footer */}
                <div className="px-4 py-3 bg-slate-800/30 border-t border-slate-700/50 flex items-center justify-between">
                  <div className="text-xs text-slate-500">
                    by {item.added_by_name || 'Family member'}
                  </div>
                  
                  {/* Actions Menu */}
                  <div className="relative">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setOpenMenuId(openMenuId === item.id ? null : item.id);
                      }}
                      className="p-1.5 hover:bg-slate-700/50 rounded-lg transition-colors"
                    >
                      <MoreVertical className="w-4 h-4 text-slate-400" />
                    </button>
                    
                    {openMenuId === item.id && (
                      <div 
                        className="absolute right-0 bottom-full mb-1 bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-10 min-w-[160px]"
                        onClick={(e) => e.stopPropagation()}
                      >
                        {/* Status Options */}
                        <div className="px-3 py-2 text-xs text-slate-500 border-b border-slate-700">
                          Change Status
                        </div>
                        {STATUS_OPTIONS.map(status => (
                          <button
                            key={status.id}
                            onClick={() => handleStatusChange(item, status.id)}
                            className={`w-full px-3 py-2 text-left text-sm hover:bg-slate-700/50 flex items-center gap-2 ${
                              item.status === status.id ? 'text-purple-400' : 'text-slate-300'
                            }`}
                          >
                            <status.icon className="w-3 h-3" />
                            {status.label}
                          </button>
                        ))}
                        
                        {/* Priority Options */}
                        <div className="px-3 py-2 text-xs text-slate-500 border-t border-b border-slate-700">
                          Priority
                        </div>
                        {PRIORITY_OPTIONS.map(priority => (
                          <button
                            key={priority.id}
                            onClick={() => handlePriorityChange(item, priority.id)}
                            className={`w-full px-3 py-2 text-left text-sm hover:bg-slate-700/50 ${
                              item.priority === priority.id ? 'text-purple-400' : 'text-slate-300'
                            }`}
                          >
                            {priority.label}
                          </button>
                        ))}
                        
                        {/* Edit & Delete */}
                        <div className="border-t border-slate-700">
                          <button
                            onClick={() => openEditModal(item)}
                            className="w-full px-3 py-2 text-left text-sm hover:bg-slate-700/50 flex items-center gap-2 text-slate-300"
                          >
                            <Edit3 className="w-3 h-3" />
                            Edit Details
                          </button>
                          <button
                            onClick={() => handleRemove(item.id)}
                            className="w-full px-3 py-2 text-left text-sm hover:bg-red-500/20 flex items-center gap-2 text-red-400"
                          >
                            <Trash2 className="w-3 h-3" />
                            Remove
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Add/Edit Modal */}
      {showAddModal && (
        <AddPropertyModal
          isOpen={showAddModal}
          onClose={() => {
            setShowAddModal(false);
            setEditingItem(null);
            setForm(INITIAL_FORM);
          }}
          onSubmit={handleSubmit}
          form={form}
          setForm={setForm}
          errors={formErrors}
          isSubmitting={isSubmitting}
          isEditing={!!editingItem}
        />
      )}
    </div>
  );
}

/**
 * Add Property Modal Component
 */
function AddPropertyModal({ isOpen, onClose, onSubmit, form, setForm, errors, isSubmitting, isEditing }) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="relative w-full max-w-md bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 rounded-2xl shadow-2xl border border-slate-700/50 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700/50 bg-slate-800/50">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-pink-500/20 rounded-lg">
              <Heart className="w-5 h-5 text-pink-400" />
            </div>
            <h3 className="text-lg font-semibold text-white">
              {isEditing ? 'Edit Property' : 'Add Property'}
            </h3>
          </div>
          <button onClick={onClose} className="p-2 hover:bg-slate-700/50 rounded-lg transition-colors">
            <X className="w-5 h-5 text-slate-400" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={onSubmit} className="p-6 space-y-4 max-h-[70vh] overflow-y-auto">
          {errors.submit && (
            <div className="p-3 bg-red-500/20 border border-red-500/30 rounded-lg flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-400" />
              <p className="text-sm text-red-400">{errors.submit}</p>
            </div>
          )}

          {/* Property Title */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">
              Property Title <span className="text-red-400">*</span>
            </label>
            <input
              type="text"
              value={form.property_title}
              onChange={(e) => setForm(prev => ({ ...prev, property_title: e.target.value }))}
              placeholder="e.g., 3BHK Apartment in Whitefield"
              className={`w-full px-4 py-2.5 bg-slate-700/50 border rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50 ${
                errors.property_title ? 'border-red-500/50' : 'border-slate-600/50'
              }`}
            />
            {errors.property_title && (
              <p className="mt-1 text-xs text-red-400">{errors.property_title}</p>
            )}
          </div>

          {/* Locality */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">
              Locality
            </label>
            <div className="relative">
              <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                value={form.locality}
                onChange={(e) => setForm(prev => ({ ...prev, locality: e.target.value }))}
                placeholder="e.g., Whitefield, Bangalore"
                className="w-full pl-10 pr-4 py-2.5 bg-slate-700/50 border border-slate-600/50 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50"
              />
            </div>
          </div>

          {/* Price */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">
              Price (₹)
            </label>
            <div className="relative">
              <Wallet className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="number"
                value={form.price}
                onChange={(e) => setForm(prev => ({ ...prev, price: e.target.value }))}
                placeholder="Enter price"
                className={`w-full pl-10 pr-4 py-2.5 bg-slate-700/50 border rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50 ${
                  errors.price ? 'border-red-500/50' : 'border-slate-600/50'
                }`}
              />
            </div>
            {errors.price && <p className="mt-1 text-xs text-red-400">{errors.price}</p>}
          </div>

          {/* Coordinates (Optional) */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                Latitude
              </label>
              <input
                type="number"
                step="any"
                value={form.latitude}
                onChange={(e) => setForm(prev => ({ ...prev, latitude: e.target.value }))}
                placeholder="e.g., 12.9716"
                className={`w-full px-4 py-2.5 bg-slate-700/50 border rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50 ${
                  errors.latitude ? 'border-red-500/50' : 'border-slate-600/50'
                }`}
              />
              {errors.latitude && <p className="mt-1 text-xs text-red-400">{errors.latitude}</p>}
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1">
                Longitude
              </label>
              <input
                type="number"
                step="any"
                value={form.longitude}
                onChange={(e) => setForm(prev => ({ ...prev, longitude: e.target.value }))}
                placeholder="e.g., 77.5946"
                className={`w-full px-4 py-2.5 bg-slate-700/50 border rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50 ${
                  errors.longitude ? 'border-red-500/50' : 'border-slate-600/50'
                }`}
              />
              {errors.longitude && <p className="mt-1 text-xs text-red-400">{errors.longitude}</p>}
            </div>
          </div>

          {/* Priority */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Priority
            </label>
            <div className="flex gap-2">
              {PRIORITY_OPTIONS.map(priority => (
                <button
                  key={priority.id}
                  type="button"
                  onClick={() => setForm(prev => ({ ...prev, priority: priority.id }))}
                  className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${
                    form.priority === priority.id
                      ? `${priority.color}`
                      : 'bg-slate-700/50 text-slate-400 border border-slate-600/50'
                  }`}
                >
                  {priority.label}
                </button>
              ))}
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">
              Notes
            </label>
            <textarea
              value={form.notes}
              onChange={(e) => setForm(prev => ({ ...prev, notes: e.target.value }))}
              placeholder="Add any notes about this property..."
              rows={3}
              className="w-full px-4 py-2.5 bg-slate-700/50 border border-slate-600/50 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50 resize-none"
            />
          </div>

          {/* Submit Button */}
          <div className="pt-4 border-t border-slate-700/50">
            <button
              type="submit"
              disabled={isSubmitting}
              className={`w-full flex items-center justify-center gap-2 px-6 py-3 rounded-lg font-medium transition-colors ${
                isSubmitting
                  ? 'bg-purple-500/50 text-purple-200 cursor-not-allowed'
                  : 'bg-purple-500 hover:bg-purple-600 text-white'
              }`}
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>{isEditing ? 'Updating...' : 'Adding...'}</span>
                </>
              ) : (
                <>
                  <Heart className="w-5 h-5" />
                  <span>{isEditing ? 'Update Property' : 'Add to Watchlist'}</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
