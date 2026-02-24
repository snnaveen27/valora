/**
 * BuilderProfile - Builder profiles component
 * 
 * Features:
 * - Builder header with logo and name
 * - Aggregate ratings display
 * - Project statistics (completed, ongoing)
 * - On-time delivery rate
 * - RERA verification badge
 * - List of reviews with filters
 * 
 * Props:
 * @param {string} builderId - Builder ID
 * @param {boolean} [isOpen] - Whether the component is open
 * @param {function} [onClose] - Callback to close the component
 * @param {function} [onSubmitReview] - Callback to open review submission form
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Star,
  Building2,
  MapPin,
  Phone,
  Mail,
  Globe,
  Calendar,
  Shield,
  CheckCircle,
  ThumbsUp,
  Clock,
  Loader2,
  AlertCircle,
  Filter,
  SortAsc,
  Plus,
  X,
  TrendingUp,
  Users,
} from 'lucide-react';

import {
  getBuilder,
  getBuilderReviews,
  markHelpful,
  unmarkHelpful,
} from '../../services/reviewApi';

import ReviewForm from './ReviewForm';
import RERAVerification from './RERAVerification';

// Star rating display
function StarRating({ rating, size = 16 }) {
  return (
    <div className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((star) => (
        <Star
          key={star}
          size={size}
          className={`${
            star <= rating
              ? 'fill-yellow-400 text-yellow-400'
              : 'fill-gray-600 text-gray-600'
          }`}
        />
      ))}
    </div>
  );
}

// Individual review card
function ReviewCard({ review, onToggleHelpful, userHelpful }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isHelpful, setIsHelpful] = useState(userHelpful || false);
  const [helpfulCount, setHelpfulCount] = useState(review.helpful_count || 0);

  const handleHelpfulClick = async () => {
    try {
      if (isHelpful) {
        await onToggleHelpful(review.id, 'builder', false);
        setIsHelpful(false);
        setHelpfulCount((prev) => prev - 1);
      } else {
        await onToggleHelpful(review.id, 'builder', true);
        setIsHelpful(true);
        setHelpfulCount((prev) => prev + 1);
      }
    } catch (error) {
      console.error('Failed to toggle helpful:', error);
    }
  };

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const renderAspectRating = (label, rating) => {
    if (!rating) return null;
    return (
      <div className="flex items-center justify-between py-1">
        <span className="text-sm text-gray-400">{label}</span>
        <StarRating rating={rating} size={12} />
      </div>
    );
  };

  return (
    <div className="bg-gray-800/50 rounded-lg border border-gray-700/50 p-4 hover:border-gray-600/50 transition-colors">
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <StarRating rating={review.overall_rating} size={18} />
            <span className="text-lg font-semibold text-white">
              {review.overall_rating.toFixed(1)}
            </span>
            {review.is_verified_buyer === 1 && (
              <span className="px-2 py-0.5 text-xs rounded-full bg-green-500/20 text-green-400 border border-green-500/30">
                Verified Buyer
              </span>
            )}
          </div>
          {review.project_name && (
            <p className="text-sm text-gray-400 mb-1">
              {review.project_name}
              {review.project_location && ` - ${review.project_location}`}
            </p>
          )}
          <div className="flex items-center gap-2 text-xs text-gray-500">
            <Clock size={12} />
            <span>{formatDate(review.created_at)}</span>
          </div>
        </div>
      </div>

      {/* Review text */}
      {review.review_text && (
        <p className="text-gray-300 text-sm mb-3">
          {isExpanded || review.review_text.length <= 300
            ? review.review_text
            : `${review.review_text.substring(0, 300)}...`}
          {review.review_text.length > 300 && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-blue-400 text-xs ml-1 hover:underline"
            >
              {isExpanded ? 'Show less' : 'Read more'}
            </button>
          )}
        </p>
      )}

      {/* Pros and Cons */}
      {(review.pros?.length > 0 || review.cons?.length > 0) && (
        <div className="grid grid-cols-2 gap-3 mb-3">
          {review.pros?.length > 0 && (
            <div>
              <span className="text-xs text-green-400 font-medium">Pros</span>
              <ul className="mt-1 space-y-1">
                {review.pros.map((pro, index) => (
                  <li key={index} className="text-xs text-gray-400 flex items-start gap-1">
                    <CheckCircle size={12} className="text-green-400 mt-0.5 flex-shrink-0" />
                    {pro}
                  </li>
                ))}
              </ul>
            </div>
          )}
          {review.cons?.length > 0 && (
            <div>
              <span className="text-xs text-red-400 font-medium">Cons</span>
              <ul className="mt-1 space-y-1">
                {review.cons.map((con, index) => (
                  <li key={index} className="text-xs text-gray-400 flex items-start gap-1">
                    <AlertCircle size={12} className="text-red-400 mt-0.5 flex-shrink-0" />
                    {con}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {/* Aspect Ratings */}
      {review.construction_quality || review.timely_delivery || review.after_sales_service ? (
        <div className="border-t border-gray-700/50 pt-3 mb-3">
          <div className="grid grid-cols-2 gap-2">
            {renderAspectRating('Construction Quality', review.construction_quality)}
            {renderAspectRating('Timely Delivery', review.timely_delivery)}
            {renderAspectRating('After-Sales Service', review.after_sales_service)}
            {renderAspectRating('Value for Money', review.value_for_money)}
            {renderAspectRating('Transparency', review.transparency)}
          </div>
        </div>
      ) : null}

      {/* Footer */}
      <div className="flex items-center justify-between pt-2 border-t border-gray-700/30">
        <button
          onClick={handleHelpfulClick}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-colors ${
            isHelpful
              ? 'bg-blue-500/20 text-blue-400'
              : 'bg-gray-700/50 text-gray-400 hover:bg-gray-600/50'
          }`}
        >
          <ThumbsUp size={14} className={isHelpful ? 'fill-current' : ''} />
          <span>Helpful ({helpfulCount})</span>
        </button>
      </div>
    </div>
  );
}

// Builder stats display
function BuilderStats({ builder }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {/* Total Projects */}
      <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700/50">
        <div className="flex items-center gap-2 text-gray-400 mb-1">
          <Building2 size={16} />
          <span className="text-xs">Total Projects</span>
        </div>
        <div className="text-2xl font-bold text-white">{builder.total_projects || 0}</div>
      </div>

      {/* Completed */}
      <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700/50">
        <div className="flex items-center gap-2 text-gray-400 mb-1">
          <CheckCircle size={16} />
          <span className="text-xs">Completed</span>
        </div>
        <div className="text-2xl font-bold text-green-400">{builder.completed_projects || 0}</div>
      </div>

      {/* Ongoing */}
      <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700/50">
        <div className="flex items-center gap-2 text-gray-400 mb-1">
          <TrendingUp size={16} />
          <span className="text-xs">Ongoing</span>
        </div>
        <div className="text-2xl font-bold text-blue-400">{builder.ongoing_projects || 0}</div>
      </div>

      {/* On-Time Delivery */}
      <div className="bg-gray-800/50 rounded-lg p-4 border border-gray-700/50">
        <div className="flex items-center gap-2 text-gray-400 mb-1">
          <Clock size={16} />
          <span className="text-xs">On-Time Delivery</span>
        </div>
        <div className="text-2xl font-bold text-white">
          {builder.on_time_delivery_rate ? `${builder.on_time_delivery_rate.toFixed(0)}%` : '-'}
        </div>
      </div>
    </div>
  );
}

// Aggregate ratings display
function AggregateRatings({ builder }) {
  return (
    <div className="bg-gray-800/50 rounded-lg border border-gray-700/50 p-4">
      <h4 className="text-sm font-medium text-gray-300 mb-4">Performance Ratings</h4>
      <div className="grid grid-cols-2 gap-4">
        {[
          { label: 'Construction Quality', value: builder.avg_construction_quality_rating },
          { label: 'After-Sales Service', value: builder.avg_after_sales_rating },
        ].map(
          (item) =>
            item.value && (
              <div key={item.label} className="flex items-center justify-between">
                <span className="text-sm text-gray-400">{item.label}</span>
                <div className="flex items-center gap-2">
                  <StarRating rating={item.value} size={14} />
                  <span className="text-sm text-gray-300">{item.value.toFixed(1)}</span>
                </div>
              </div>
            )
        )}
      </div>
    </div>
  );
}

export default function BuilderProfile({
  builderId,
  isOpen = true,
  onClose,
  onSubmitReview,
}) {
  const [builder, setBuilder] = useState(null);
  const [reviews, setReviews] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filter and sort state
  const [ratingFilter, setRatingFilter] = useState('');
  const [sortOption, setSortOption] = useState('created_at-desc');

  // Form state
  const [showReviewForm, setShowReviewForm] = useState(false);

  // Load builder data
  const loadBuilder = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const builderData = await getBuilder(builderId);
      setBuilder(builderData);
    } catch (err) {
      setError(err.message);
      console.error('Failed to load builder:', err);
    } finally {
      setIsLoading(false);
    }
  }, [builderId]);

  // Load reviews
  const loadReviews = useCallback(async () => {
    try {
      const [sortBy, sortOrder] = sortOption.split('-');
      const reviewsData = await getBuilderReviews(builderId, {
        rating: ratingFilter || undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
        limit: 20,
      });
      setReviews(reviewsData);
    } catch (err) {
      console.error('Failed to load reviews:', err);
    }
  }, [builderId, ratingFilter, sortOption]);

  // Initial load
  useEffect(() => {
    if (isOpen && builderId) {
      loadBuilder();
    }
  }, [isOpen, builderId, loadBuilder]);

  // Load reviews when filters change
  useEffect(() => {
    if (isOpen && builderId) {
      loadReviews();
    }
  }, [isOpen, builderId, ratingFilter, sortOption, loadReviews]);

  // Handle helpful toggle
  const handleToggleHelpful = async (reviewId, reviewType, isHelpful) => {
    try {
      if (isHelpful) {
        await markHelpful(reviewType, reviewId);
      } else {
        await unmarkHelpful(reviewType, reviewId);
      }
    } catch (err) {
      console.error('Failed to toggle helpful:', err);
    }
  };

  // Handle new review submission
  const handleReviewSubmitted = () => {
    setShowReviewForm(false);
    loadReviews();
    loadBuilder(); // Refresh builder stats
  };

  const formatDate = (dateString) => {
    if (!dateString) return null;
    const date = new Date(dateString);
    return date.toLocaleDateString('en-IN', {
      year: 'numeric',
      month: 'short',
    });
  };

  if (!isOpen) return null;

  return (
    <div className="h-full flex flex-col bg-gray-900">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-700/50 bg-gray-800/50">
        <div className="flex items-center gap-4">
          {/* Logo */}
          {builder?.logo_url ? (
            <img
              src={builder.logo_url}
              alt={builder.name}
              className="w-12 h-12 rounded-lg object-cover"
            />
          ) : (
            <div className="w-12 h-12 rounded-lg bg-gray-700 flex items-center justify-center">
              <Building2 size={24} className="text-gray-400" />
            </div>
          )}
          <div>
            <h2 className="text-xl font-semibold text-white flex items-center gap-2">
              {builder?.name || 'Builder Profile'}
              {builder?.rera_registered === 1 && (
                <Shield size={18} className="text-green-400" />
              )}
            </h2>
            {builder?.established_year && (
              <p className="text-sm text-gray-400 flex items-center gap-1">
                <Calendar size={12} />
                Est. {builder.established_year}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowReviewForm(true)}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
          >
            <Plus size={18} />
            <span className="hidden sm:inline">Write Review</span>
          </button>
          {onClose && (
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-700 rounded-lg transition-colors"
            >
              <X size={20} className="text-gray-400" />
            </button>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Error State */}
        {error && (
          <div className="flex items-center gap-2 p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400">
            <AlertCircle size={20} />
            <span>{error}</span>
          </div>
        )}

        {/* Loading State */}
        {isLoading && (
          <div className="flex items-center justify-center py-12">
            <Loader2 size={32} className="text-blue-400 animate-spin" />
          </div>
        )}

        {/* Builder Content */}
        {!isLoading && !error && builder && (
          <>
            {/* Contact & Info */}
            <div className="bg-gray-800/50 rounded-lg border border-gray-700/50 p-4">
              <h4 className="text-sm font-medium text-gray-300 mb-3">Contact Information</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {builder.description && (
                  <p className="text-sm text-gray-400 md:col-span-2">{builder.description}</p>
                )}
                {builder.address && (
                  <div className="flex items-start gap-2 text-sm text-gray-400">
                    <MapPin size={16} className="mt-0.5 flex-shrink-0" />
                    <span>{builder.address}</span>
                  </div>
                )}
                {builder.contact_phone && (
                  <div className="flex items-center gap-2 text-sm text-gray-400">
                    <Phone size={16} />
                    <span>{builder.contact_phone}</span>
                  </div>
                )}
                {builder.contact_email && (
                  <div className="flex items-center gap-2 text-sm text-gray-400">
                    <Mail size={16} />
                    <span>{builder.contact_email}</span>
                  </div>
                )}
                {builder.website && (
                  <div className="flex items-center gap-2 text-sm text-gray-400">
                    <Globe size={16} />
                    <a
                      href={builder.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-400 hover:underline"
                    >
                      {builder.website}
                    </a>
                  </div>
                )}
                {builder.cities_operating?.length > 0 && (
                  <div className="flex items-start gap-2 text-sm text-gray-400 md:col-span-2">
                    <Users size={16} className="mt-0.5 flex-shrink-0" />
                    <span>Operating in: {builder.cities_operating.join(', ')}</span>
                  </div>
                )}
              </div>
            </div>

            {/* RERA Verification */}
            {builder.rera_ids?.length > 0 && (
              <div className="bg-gray-800/50 rounded-lg border border-gray-700/50 p-4">
                <h4 className="text-sm font-medium text-gray-300 mb-3">RERA Verification</h4>
                <RERAVerification
                  reraIds={builder.rera_ids}
                  builderName={builder.name}
                  compact
                />
              </div>
            )}

            {/* Stats */}
            <BuilderStats builder={builder} />

            {/* Aggregate Ratings */}
            <AggregateRatings builder={builder} />

            {/* Reviews Header */}
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-semibold text-white">
                Reviews ({reviews.length})
              </h3>
            </div>

            {/* Review Filters */}
            <div className="flex flex-wrap items-center gap-3">
              {/* Rating Filter */}
              <div className="flex items-center gap-2">
                <Filter size={16} className="text-gray-400" />
                <select
                  value={ratingFilter}
                  onChange={(e) => setRatingFilter(e.target.value)}
                  className="bg-gray-800 border border-gray-600 text-white text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:border-blue-500"
                >
                  <option value="">All Ratings</option>
                  <option value="5">5 Stars</option>
                  <option value="4">4+ Stars</option>
                  <option value="3">3+ Stars</option>
                  <option value="2">2+ Stars</option>
                </select>
              </div>

              {/* Sort */}
              <div className="flex items-center gap-2">
                <SortAsc size={16} className="text-gray-400" />
                <select
                  value={sortOption}
                  onChange={(e) => setSortOption(e.target.value)}
                  className="bg-gray-800 border border-gray-600 text-white text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:border-blue-500"
                >
                  <option value="created_at-desc">Most Recent</option>
                  <option value="helpful_count-desc">Most Helpful</option>
                  <option value="overall_rating-desc">Highest Rated</option>
                  <option value="overall_rating-asc">Lowest Rated</option>
                </select>
              </div>
            </div>

            {/* Reviews List */}
            {reviews.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-gray-400 mb-4">No reviews yet for this builder.</p>
                <button
                  onClick={() => setShowReviewForm(true)}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
                >
                  Be the first to write a review!
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                {reviews.map((review) => (
                  <ReviewCard
                    key={review.id}
                    review={review}
                    onToggleHelpful={handleToggleHelpful}
                  />
                ))}
              </div>
            )}
          </>
        )}
      </div>

      {/* Review Form Modal */}
      {showReviewForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-gray-900 rounded-xl border border-gray-700 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <ReviewForm
              builderId={builderId}
              builderName={builder?.name}
              onClose={() => setShowReviewForm(false)}
              onSuccess={handleReviewSubmitted}
            />
          </div>
        </div>
      )}
    </div>
  );
}
