/**
 * FamilySessionCreate - Session creation form for Family Hub
 * 
 * Features:
 * - Form fields: family_name, description, target_locality, budget range, property_types
 * - Form validation with error messages
 * - API integration for session creation
 * - Responsive layout
 * 
 * Props:
 * @param {boolean} isOpen - Whether the modal is open
 * @param {function} onClose - Callback to close the modal
 * @param {function} onCreated - Callback when session is created successfully
 */

import { useState, useEffect } from 'react';
import {
  XCircle,
  Users,
  MapPin,
  Wallet,
  Building2,
  FileText,
  Loader2,
  AlertCircle,
  CheckCircle,
  ChevronDown,
} from 'lucide-react';

import { createSession } from '../../services/familyApi';

// Property type options
const PROPERTY_TYPES = [
  { id: 'apartment', label: 'Apartment' },
  { id: 'villa', label: 'Villa' },
  { id: 'independent_house', label: 'Independent House' },
  { id: 'plot', label: 'Plot' },
  { id: 'commercial', label: 'Commercial' },
  { id: 'row_house', label: 'Row House' },
];

// Budget presets (in INR)
const BUDGET_PRESETS = [
  { label: 'Under ₹50 Lakhs', min: 0, max: 5000000 },
  { label: '₹50L - ₹1 Crore', min: 5000000, max: 10000000 },
  { label: '₹1Cr - ₹2 Crore', min: 10000000, max: 20000000 },
  { label: '₹2Cr - ₹5 Crore', min: 20000000, max: 50000000 },
  { label: 'Above ₹5 Crore', min: 50000000, max: null },
  { label: 'Custom', min: null, max: null },
];

// Popular localities in Bangalore (can be made dynamic)
const POPULAR_LOCALITIES = [
  'Whitefield', 'Electronic City', 'Koramangala', 'Indiranagar', 'HSR Layout',
  'JP Nagar', 'Jayanagar', 'BTM Layout', 'Marathahalli', 'Bellandur',
  'Sarjapur', 'Hebbal', 'Yelahanka', 'Kengeri', 'Banashankari',
  'Malleshwaram', 'Rajajinagar', 'Vijayanagar', 'RT Nagar', 'HBR Layout',
];

// Initial form state
const INITIAL_FORM = {
  family_name: '',
  description: '',
  target_locality: '',
  budget_min: '',
  budget_max: '',
  property_types: [],
};

export default function FamilySessionCreate({ isOpen, onClose, onCreated }) {
  // Form state
  const [form, setForm] = useState(INITIAL_FORM);
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  
  // UI state
  const [showLocalityDropdown, setShowLocalityDropdown] = useState(false);
  const [showBudgetDropdown, setShowBudgetDropdown] = useState(false);
  const [selectedBudgetPreset, setSelectedBudgetPreset] = useState(null);
  const [localitySearch, setLocalitySearch] = useState('');

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen) {
      setForm(INITIAL_FORM);
      setErrors({});
      setSubmitError(null);
      setSelectedBudgetPreset(null);
      setLocalitySearch('');
    }
  }, [isOpen]);

  // Close dropdowns when clicking outside
  useEffect(() => {
    const handleClickOutside = () => {
      setShowLocalityDropdown(false);
      setShowBudgetDropdown(false);
    };
    
    if (showLocalityDropdown || showBudgetDropdown) {
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  }, [showLocalityDropdown, showBudgetDropdown]);

  /**
   * Validate form fields
   */
  const validateForm = () => {
    const newErrors = {};
    
    if (!form.family_name.trim()) {
      newErrors.family_name = 'Family name is required';
    } else if (form.family_name.length > 100) {
      newErrors.family_name = 'Family name must be 100 characters or less';
    }
    
    if (form.description && form.description.length > 500) {
      newErrors.description = 'Description must be 500 characters or less';
    }
    
    if (form.budget_min && form.budget_max) {
      const min = parseFloat(form.budget_min);
      const max = parseFloat(form.budget_max);
      if (min > max) {
        newErrors.budget = 'Minimum budget cannot exceed maximum budget';
      }
    }
    
    if (form.budget_min && parseFloat(form.budget_min) < 0) {
      newErrors.budget_min = 'Budget cannot be negative';
    }
    
    if (form.budget_max && parseFloat(form.budget_max) < 0) {
      newErrors.budget_max = 'Budget cannot be negative';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  /**
   * Handle input change
   */
  const handleChange = (field, value) => {
    setForm(prev => ({ ...prev, [field]: value }));
    // Clear error when user types
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: null }));
    }
  };

  /**
   * Handle property type toggle
   */
  const handlePropertyTypeToggle = (typeId) => {
    setForm(prev => ({
      ...prev,
      property_types: prev.property_types.includes(typeId)
        ? prev.property_types.filter(t => t !== typeId)
        : [...prev.property_types, typeId],
    }));
  };

  /**
   * Handle budget preset selection
   */
  const handleBudgetPreset = (preset) => {
    setSelectedBudgetPreset(preset.label);
    
    if (preset.label === 'Custom') {
      setForm(prev => ({
        ...prev,
        budget_min: prev.budget_min || '',
        budget_max: prev.budget_max || '',
      }));
    } else {
      setForm(prev => ({
        ...prev,
        budget_min: preset.min ? preset.min.toString() : '',
        budget_max: preset.max ? preset.max.toString() : '',
      }));
    }
    
    setShowBudgetDropdown(false);
    if (errors.budget) {
      setErrors(prev => ({ ...prev, budget: null }));
    }
  };

  /**
   * Handle locality selection
   */
  const handleLocalitySelect = (locality) => {
    setForm(prev => ({ ...prev, target_locality: locality }));
    setLocalitySearch(locality);
    setShowLocalityDropdown(false);
  };

  /**
   * Format number to Indian currency format
   */
  const formatCurrencyInput = (value) => {
    // Remove non-numeric characters
    const num = value.replace(/[^0-9]/g, '');
    if (!num) return '';
    return parseInt(num, 10).toLocaleString('en-IN');
  };

  /**
   * Parse currency input to number
   */
  const parseCurrencyInput = (value) => {
    return value.replace(/[^0-9]/g, '');
  };

  /**
   * Handle form submission
   */
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) return;
    
    setIsSubmitting(true);
    setSubmitError(null);
    
    try {
      // Prepare data for API
      const sessionData = {
        family_name: form.family_name.trim(),
        description: form.description.trim() || null,
        target_locality: form.target_locality.trim() || null,
        budget_min: form.budget_min ? parseFloat(form.budget_min) : null,
        budget_max: form.budget_max ? parseFloat(form.budget_max) : null,
        property_types: form.property_types.length > 0 ? form.property_types : null,
      };
      
      const newSession = await createSession(sessionData);
      
      // Notify parent
      onCreated(newSession);
    } catch (err) {
      console.error('[FamilySessionCreate] Failed to create session:', err);
      setSubmitError(err.message || 'Failed to create session. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Filter localities based on search
  const filteredLocalities = POPULAR_LOCALITIES.filter(loc =>
    loc.toLowerCase().includes(localitySearch.toLowerCase())
  );

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="relative w-full max-w-lg bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 rounded-2xl shadow-2xl border border-slate-700/50 overflow-hidden">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700/50 bg-slate-800/50">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-500/20 rounded-lg">
              <Users className="w-5 h-5 text-purple-400" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white">Create Family Session</h3>
              <p className="text-sm text-slate-400">Start collaborating on property decisions</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-700/50 rounded-lg transition-colors"
          >
            <XCircle className="w-5 h-5 text-slate-400" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="p-6 space-y-5 max-h-[70vh] overflow-y-auto">
          {/* Submit Error */}
          {submitError && (
            <div className="p-3 bg-red-500/20 border border-red-500/30 rounded-lg flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-red-400" />
              <p className="text-sm text-red-400">{submitError}</p>
            </div>
          )}

          {/* Family Name */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Family Name <span className="text-red-400">*</span>
            </label>
            <div className="relative">
              <Users className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                value={form.family_name}
                onChange={(e) => handleChange('family_name', e.target.value)}
                placeholder="e.g., Sharma Family Home Search"
                className={`w-full pl-10 pr-4 py-2.5 bg-slate-700/50 border rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50 ${
                  errors.family_name ? 'border-red-500/50' : 'border-slate-600/50'
                }`}
                maxLength={100}
              />
            </div>
            {errors.family_name && (
              <p className="mt-1 text-sm text-red-400">{errors.family_name}</p>
            )}
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Description
            </label>
            <div className="relative">
              <FileText className="absolute left-3 top-3 w-4 h-4 text-slate-400" />
              <textarea
                value={form.description}
                onChange={(e) => handleChange('description', e.target.value)}
                placeholder="What are you looking for?"
                rows={3}
                className={`w-full pl-10 pr-4 py-2.5 bg-slate-700/50 border rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50 resize-none ${
                  errors.description ? 'border-red-500/50' : 'border-slate-600/50'
                }`}
                maxLength={500}
              />
            </div>
            <p className="mt-1 text-xs text-slate-500">
              {form.description.length}/500 characters
            </p>
            {errors.description && (
              <p className="mt-1 text-sm text-red-400">{errors.description}</p>
            )}
          </div>

          {/* Target Locality */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Target Locality
            </label>
            <div className="relative">
              <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
              <input
                type="text"
                value={localitySearch}
                onChange={(e) => {
                  setLocalitySearch(e.target.value);
                  setForm(prev => ({ ...prev, target_locality: e.target.value }));
                  setShowLocalityDropdown(true);
                }}
                onFocus={() => setShowLocalityDropdown(true)}
                onClick={(e) => e.stopPropagation()}
                placeholder="Search for a locality..."
                className="w-full pl-10 pr-4 py-2.5 bg-slate-700/50 border border-slate-600/50 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50"
              />
              
              {/* Locality Dropdown */}
              {showLocalityDropdown && filteredLocalities.length > 0 && (
                <div 
                  className="absolute top-full left-0 right-0 mt-1 bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-10 max-h-48 overflow-y-auto"
                  onClick={(e) => e.stopPropagation()}
                >
                  {filteredLocalities.map(locality => (
                    <button
                      key={locality}
                      type="button"
                      onClick={() => handleLocalitySelect(locality)}
                      className="w-full px-4 py-2 text-left text-slate-300 hover:bg-slate-700/50 transition-colors"
                    >
                      {locality}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* Budget Range */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Budget Range
            </label>
            
            {/* Budget Presets */}
            <div className="relative mb-3">
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  setShowBudgetDropdown(!showBudgetDropdown);
                }}
                className="w-full flex items-center justify-between px-4 py-2.5 bg-slate-700/50 border border-slate-600/50 rounded-lg text-slate-300 hover:bg-slate-700 transition-colors"
              >
                <span>{selectedBudgetPreset || 'Select budget range'}</span>
                <ChevronDown className={`w-4 h-4 transition-transform ${showBudgetDropdown ? 'rotate-180' : ''}`} />
              </button>
              
              {showBudgetDropdown && (
                <div 
                  className="absolute top-full left-0 right-0 mt-1 bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-10"
                  onClick={(e) => e.stopPropagation()}
                >
                  {BUDGET_PRESETS.map(preset => (
                    <button
                      key={preset.label}
                      type="button"
                      onClick={() => handleBudgetPreset(preset)}
                      className={`w-full px-4 py-2 text-left transition-colors ${
                        selectedBudgetPreset === preset.label
                          ? 'bg-purple-500/20 text-purple-400'
                          : 'text-slate-300 hover:bg-slate-700/50'
                      }`}
                    >
                      {preset.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
            
            {/* Custom Budget Inputs */}
            {selectedBudgetPreset === 'Custom' && (
              <div className="grid grid-cols-2 gap-3">
                <div className="relative">
                  <Wallet className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <input
                    type="text"
                    value={form.budget_min ? formatCurrencyInput(form.budget_min) : ''}
                    onChange={(e) => handleChange('budget_min', parseCurrencyInput(e.target.value))}
                    placeholder="Min (₹)"
                    className={`w-full pl-10 pr-4 py-2.5 bg-slate-700/50 border rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50 ${
                      errors.budget_min ? 'border-red-500/50' : 'border-slate-600/50'
                    }`}
                  />
                </div>
                <div className="relative">
                  <Wallet className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <input
                    type="text"
                    value={form.budget_max ? formatCurrencyInput(form.budget_max) : ''}
                    onChange={(e) => handleChange('budget_max', parseCurrencyInput(e.target.value))}
                    placeholder="Max (₹)"
                    className={`w-full pl-10 pr-4 py-2.5 bg-slate-700/50 border rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50 ${
                      errors.budget_max ? 'border-red-500/50' : 'border-slate-600/50'
                    }`}
                  />
                </div>
              </div>
            )}
            
            {errors.budget && (
              <p className="mt-1 text-sm text-red-400">{errors.budget}</p>
            )}
          </div>

          {/* Property Types */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-2">
              Property Types
            </label>
            <div className="flex flex-wrap gap-2">
              {PROPERTY_TYPES.map(type => (
                <button
                  key={type.id}
                  type="button"
                  onClick={() => handlePropertyTypeToggle(type.id)}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                    form.property_types.includes(type.id)
                      ? 'bg-purple-500/30 text-purple-300 border border-purple-500/50'
                      : 'bg-slate-700/50 text-slate-400 border border-slate-600/50 hover:border-slate-500'
                  }`}
                >
                  {type.label}
                </button>
              ))}
            </div>
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
                  <span>Creating...</span>
                </>
              ) : (
                <>
                  <CheckCircle className="w-5 h-5" />
                  <span>Create Session</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
