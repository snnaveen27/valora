/**
 * ReviewForm - Review submission form component
 * 
 * Features:
 * - Conditional fields based on review type (locality/builder)
 * - Star rating inputs (1-5) for various aspects
 * - Text areas for pros/cons
 * - Verification type selector (resident/visitor/owner)
 * - Form validation
 * 
 * Props:
 * @param {string} [localityId] - Locality ID (for locality reviews)
 * @param {string} [localityName] - Locality name (for locality reviews)
 * @param {string} [builderId] - Builder ID (for builder reviews)
 * @param {string} [builderName] - Builder name (for builder reviews)
 * @param {function} onClose - Callback to close the form
 * @param {function} onSuccess - Callback on successful submission
 */

import { useState } from 'react';
import {
  Star,
  X,
  Loader2,
  AlertCircle,
  CheckCircle,
  Plus,
  Trash2,
} from 'lucide-react';

import {
  submitLocalityReview,
  submitBuilderReview,
} from '../../services/reviewApi';

import VastuRating from './VastuRating';

// Star rating input component
function StarRatingInput({ value, onChange, label, required = false }) {
  const [hover, setHover] = useState(0);

  return (
    <div className="flex flex-col gap-1">
      <label className="text-sm text-gray-300">
        {label}
        {required && <span className="text-red-400 ml-1">*</span>}
      </label>
      <div className="flex items-center gap-1">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            onClick={() => onChange(star)}
            onMouseEnter={() => setHover(star)}
            onMouseLeave={() => setHover(0)}
            className="p-0.5 transition-transform hover:scale-110"
          >
            <Star
              size={24}
              className={`${
                star <= (hover || value)
                  ? 'fill-yellow-400 text-yellow-400'
                  : 'fill-gray-600 text-gray-600'
              }`}
            />
          </button>
        ))}
        {value > 0 && (
          <span className="ml-2 text-sm text-gray-400">{value}/5</span>
        )}
      </div>
    </div>
  );
}

// Pros/Cons input component
function ProsConsInput({ pros, cons, onChange }) {
  const [newPro, setNewPro] = useState('');
  const [newCon, setNewCon] = useState('');

  const addPro = () => {
    if (newPro.trim()) {
      onChange('pros', [...pros, newPro.trim()]);
      setNewPro('');
    }
  };

  const addCon = () => {
    if (newCon.trim()) {
      onChange('cons', [...cons, newCon.trim()]);
      setNewCon('');
    }
  };

  const removePro = (index) => {
    onChange('pros', pros.filter((_, i) => i !== index));
  };

  const removeCon = (index) => {
    onChange('cons', cons.filter((_, i) => i !== index));
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* Pros */}
      <div>
        <label className="text-sm text-green-400 font-medium mb-2 block">Pros</label>
        <div className="flex gap-2 mb-2">
          <input
            type="text"
            value={newPro}
            onChange={(e) => setNewPro(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && addPro()}
            placeholder="Add a positive point..."
            className="flex-1 bg-gray-800 border border-gray-600 text-white text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-green-500"
          />
          <button
            type="button"
            onClick={addPro}
            className="p-2 bg-green-600/20 hover:bg-green-600/30 text-green-400 rounded-lg transition-colors"
          >
            <Plus size={18} />
          </button>
        </div>
        <ul className="space-y-1">
          {pros.map((pro, index) => (
            <li
              key={index}
              className="flex items-center justify-between bg-green-900/20 text-green-300 text-sm px-3 py-1.5 rounded"
            >
              <span className="flex items-center gap-2">
                <CheckCircle size={14} className="text-green-400" />
                {pro}
              </span>
              <button
                type="button"
                onClick={() => removePro(index)}
                className="text-green-500 hover:text-green-300"
              >
                <Trash2 size={14} />
              </button>
            </li>
          ))}
        </ul>
      </div>

      {/* Cons */}
      <div>
        <label className="text-sm text-red-400 font-medium mb-2 block">Cons</label>
        <div className="flex gap-2 mb-2">
          <input
            type="text"
            value={newCon}
            onChange={(e) => setNewCon(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && addCon()}
            placeholder="Add a negative point..."
            className="flex-1 bg-gray-800 border border-gray-600 text-white text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-red-500"
          />
          <button
            type="button"
            onClick={addCon}
            className="p-2 bg-red-600/20 hover:bg-red-600/30 text-red-400 rounded-lg transition-colors"
          >
            <Plus size={18} />
          </button>
        </div>
        <ul className="space-y-1">
          {cons.map((con, index) => (
            <li
              key={index}
              className="flex items-center justify-between bg-red-900/20 text-red-300 text-sm px-3 py-1.5 rounded"
            >
              <span className="flex items-center gap-2">
                <AlertCircle size={14} className="text-red-400" />
                {con}
              </span>
              <button
                type="button"
                onClick={() => removeCon(index)}
                className="text-red-500 hover:text-red-300"
              >
                <Trash2 size={14} />
              </button>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

// Locality-specific form fields
function LocalityFields({ formData, onChange }) {
  return (
    <div className="space-y-4">
      {/* Overall Rating */}
      <StarRatingInput
        label="Overall Rating"
        value={formData.overall_rating}
        onChange={(value) => onChange('overall_rating', value)}
        required
      />

      {/* Vastu Rating */}
      <div className="p-4 bg-gray-800/50 rounded-lg border border-gray-700/50">
        <h4 className="text-sm font-medium text-gray-300 mb-3">Vastu Compliance</h4>
        <VastuRating
          rating={formData.vastu_rating}
          notes={formData.vastu_notes}
          onChange={(rating, notes) => {
            onChange('vastu_rating', rating);
            onChange('vastu_notes', notes);
          }}
        />
      </div>

      {/* Other Aspect Ratings */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <StarRatingInput
          label="School Proximity"
          value={formData.school_rating}
          onChange={(value) => onChange('school_rating', value)}
        />
        <div className="flex flex-col gap-1">
          <label className="text-sm text-gray-300">School Notes</label>
          <textarea
            value={formData.school_notes || ''}
            onChange={(e) => onChange('school_notes', e.target.value)}
            placeholder="Notes about nearby schools..."
            rows={2}
            className="bg-gray-800 border border-gray-600 text-white text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500 resize-none"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <StarRatingInput
          label="Transport Connectivity"
          value={formData.transport_rating}
          onChange={(value) => onChange('transport_rating', value)}
        />
        <div className="flex flex-col gap-1">
          <label className="text-sm text-gray-300">Transport Notes</label>
          <textarea
            value={formData.transport_notes || ''}
            onChange={(e) => onChange('transport_notes', e.target.value)}
            placeholder="Notes about public transport..."
            rows={2}
            className="bg-gray-800 border border-gray-600 text-white text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500 resize-none"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <StarRatingInput
          label="Safety"
          value={formData.safety_rating}
          onChange={(value) => onChange('safety_rating', value)}
        />
        <div className="flex flex-col gap-1">
          <label className="text-sm text-gray-300">Safety Notes</label>
          <textarea
            value={formData.safety_notes || ''}
            onChange={(e) => onChange('safety_notes', e.target.value)}
            placeholder="Notes about neighborhood safety..."
            rows={2}
            className="bg-gray-800 border border-gray-600 text-white text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500 resize-none"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <StarRatingInput
          label="Amenities"
          value={formData.amenities_rating}
          onChange={(value) => onChange('amenities_rating', value)}
        />
        <div className="flex flex-col gap-1">
          <label className="text-sm text-gray-300">Amenities Notes</label>
          <textarea
            value={formData.amenities_notes || ''}
            onChange={(e) => onChange('amenities_notes', e.target.value)}
            placeholder="Notes about nearby amenities..."
            rows={2}
            className="bg-gray-800 border border-gray-600 text-white text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500 resize-none"
          />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <StarRatingInput
          label="Water Supply"
          value={formData.water_supply_rating}
          onChange={(value) => onChange('water_supply_rating', value)}
        />
        <StarRatingInput
          label="Power Supply"
          value={formData.power_supply_rating}
          onChange={(value) => onChange('power_supply_rating', value)}
        />
      </div>
    </div>
  );
}

// Builder-specific form fields
function BuilderFields({ formData, onChange }) {
  return (
    <div className="space-y-4">
      {/* Project Details */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="flex flex-col gap-1">
          <label className="text-sm text-gray-300">Project Name</label>
          <input
            type="text"
            value={formData.project_name || ''}
            onChange={(e) => onChange('project_name', e.target.value)}
            placeholder="Name of the project..."
            className="bg-gray-800 border border-gray-600 text-white text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500"
          />
        </div>
        <div className="flex flex-col gap-1">
          <label className="text-sm text-gray-300">Project Location</label>
          <input
            type="text"
            value={formData.project_location || ''}
            onChange={(e) => onChange('project_location', e.target.value)}
            placeholder="Location of the project..."
            className="bg-gray-800 border border-gray-600 text-white text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500"
          />
        </div>
      </div>

      {/* Overall Rating */}
      <StarRatingInput
        label="Overall Rating"
        value={formData.overall_rating}
        onChange={(value) => onChange('overall_rating', value)}
        required
      />

      {/* Aspect Ratings */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <StarRatingInput
          label="Construction Quality"
          value={formData.construction_quality}
          onChange={(value) => onChange('construction_quality', value)}
        />
        <StarRatingInput
          label="Timely Delivery"
          value={formData.timely_delivery}
          onChange={(value) => onChange('timely_delivery', value)}
        />
        <StarRatingInput
          label="After-Sales Service"
          value={formData.after_sales_service}
          onChange={(value) => onChange('after_sales_service', value)}
        />
        <StarRatingInput
          label="Value for Money"
          value={formData.value_for_money}
          onChange={(value) => onChange('value_for_money', value)}
        />
        <StarRatingInput
          label="Transparency"
          value={formData.transparency}
          onChange={(value) => onChange('transparency', value)}
        />
      </div>

      {/* Verified Buyer */}
      <div className="flex items-center gap-3">
        <input
          type="checkbox"
          id="is_verified_buyer"
          checked={formData.is_verified_buyer || false}
          onChange={(e) => onChange('is_verified_buyer', e.target.checked)}
          className="w-4 h-4 rounded bg-gray-800 border-gray-600 text-blue-600 focus:ring-blue-500"
        />
        <label htmlFor="is_verified_buyer" className="text-sm text-gray-300">
          I am a verified buyer/owner of this property
        </label>
      </div>

      {/* Purchase Date */}
      <div className="flex flex-col gap-1">
        <label className="text-sm text-gray-300">Purchase Date (if applicable)</label>
        <input
          type="date"
          value={formData.purchase_date || ''}
          onChange={(e) => onChange('purchase_date', e.target.value)}
          className="bg-gray-800 border border-gray-600 text-white text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500"
        />
      </div>
    </div>
  );
}

export default function ReviewForm({
  localityId,
  localityName,
  builderId,
  builderName,
  onClose,
  onSuccess,
}) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  // Determine review type
  const isLocalityReview = !!localityId;
  const isBuilderReview = !!builderId;

  // Form state
  const [formData, setFormData] = useState({
    // Common
    overall_rating: 0,
    pros: [],
    cons: [],
    review_text: '',
    verification_type: '',

    // Locality specific
    locality_id: localityId,
    locality_name: localityName,
    vastu_rating: 0,
    vastu_notes: '',
    school_rating: 0,
    school_notes: '',
    religious_proximity: {},
    transport_rating: 0,
    transport_notes: '',
    safety_rating: 0,
    safety_notes: '',
    amenities_rating: 0,
    amenities_notes: '',
    water_supply_rating: 0,
    power_supply_rating: 0,

    // Builder specific
    builder_id: builderId,
    project_name: '',
    project_location: '',
    construction_quality: 0,
    timely_delivery: 0,
    after_sales_service: 0,
    value_for_money: 0,
    transparency: 0,
    is_verified_buyer: false,
    purchase_date: '',
  });

  const updateField = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const validateForm = () => {
    if (!formData.overall_rating) {
      setError('Please provide an overall rating');
      return false;
    }

    if (isLocalityReview && !localityId) {
      setError('Locality ID is required');
      return false;
    }

    if (isBuilderReview && !builderId) {
      setError('Builder ID is required');
      return false;
    }

    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!validateForm()) return;

    setIsSubmitting(true);

    try {
      // Prepare the data based on review type
      const submitData = {
        ...formData,
        // Filter out undefined/null values
        ...Object.fromEntries(
          Object.entries(formData).filter(
            ([_, value]) => value !== '' && value !== null && value !== undefined
          )
        ),
      };

      if (isLocalityReview) {
        await submitLocalityReview(submitData);
      } else if (isBuilderReview) {
        await submitBuilderReview(builderId, submitData);
      }

      setSuccess(true);
      setTimeout(() => {
        onSuccess?.();
      }, 1500);
    } catch (err) {
      setError(err.message || 'Failed to submit review. Please try again.');
      console.error('Failed to submit review:', err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const title = isLocalityReview
    ? `Review ${localityName || 'Locality'}`
    : `Review ${builderName || 'Builder'}`;

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-semibold text-white">{title}</h2>
        <button
          onClick={onClose}
          className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
        >
          <X size={20} className="text-gray-400" />
        </button>
      </div>

      {/* Success Message */}
      {success && (
        <div className="flex items-center gap-2 p-4 mb-4 bg-green-500/10 border border-green-500/30 rounded-lg text-green-400">
          <CheckCircle size={20} />
          <span>Review submitted successfully! Redirecting...</span>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="flex items-center gap-2 p-4 mb-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400">
          <AlertCircle size={20} />
          <span>{error}</span>
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Review Type Specific Fields */}
        {isLocalityReview && (
          <LocalityFields formData={formData} onChange={updateField} />
        )}
        {isBuilderReview && (
          <BuilderFields formData={formData} onChange={updateField} />
        )}

        {/* Pros and Cons */}
        <ProsConsInput
          pros={formData.pros}
          cons={formData.cons}
          onChange={(field, value) => updateField(field, value)}
        />

        {/* Verification Type (for locality reviews) */}
        {isLocalityReview && (
          <div className="flex flex-col gap-2">
            <label className="text-sm text-gray-300">Your Connection to this Locality</label>
            <div className="flex flex-wrap gap-2">
              {['owner', 'resident', 'visitor'].map((type) => (
                <button
                  key={type}
                  type="button"
                  onClick={() => updateField('verification_type', type)}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    formData.verification_type === type
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
                  }`}
                >
                  {type.charAt(0).toUpperCase() + type.slice(1)}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Review Text */}
        <div className="flex flex-col gap-2">
          <label className="text-sm text-gray-300">
            Your Review {isLocalityReview && '(Optional)'}
          </label>
          <textarea
            value={formData.review_text}
            onChange={(e) => updateField('review_text', e.target.value)}
            placeholder="Share your experience..."
            rows={4}
            className="bg-gray-800 border border-gray-600 text-white text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-blue-500 resize-none"
          />
          <span className="text-xs text-gray-500">
            {formData.review_text.length}/2000 characters
          </span>
        </div>

        {/* Submit Button */}
        <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-700">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSubmitting || !formData.overall_rating}
            className="flex items-center gap-2 px-6 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors"
          >
            {isSubmitting ? (
              <>
                <Loader2 size={18} className="animate-spin" />
                <span>Submitting...</span>
              </>
            ) : (
              <span>Submit Review</span>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}
