/**
 * LocalityReviews - Reviews container component for locality reviews
 * 
 * Features:
 * - Display list of locality reviews
 * - Filter by rating, verification type
 * - Sort by recent/helpful/rating
 * - Show aggregate ratings
 * - Link to submit new review
 * 
 * Props:
 * @param {string} localityId - Locality ID
 * @param {string} localityName - Locality name
 * @param {boolean} [isOpen] - Whether the component is open
 * @param {function} [onClose] - Callback to close the component
 * @param {function} [onSubmitReview] - Callback to open review submission form
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Star,
  ThumbsUp,
  Filter,
  SortAsc,
  Plus,
  Loader2,
  AlertCircle,
  MapPin,
  Shield,
  CheckCircle,
  Clock,
  ChevronDown,
  X,
} from 'lucide-react';

import {
  getLocalityReviews,
  getLocalityStats,
  markHelpful,
  unmarkHelpful,
} from '../../services/reviewApi';

import ReviewForm from './ReviewForm';

// Filter and sort options
const RATING_FILTERS = [
  { value: '', label: 'All Ratings' },
  { value: '5', label: '5 Stars' },
  { value: '4', label: '4+ Stars' },
  { value: '3', label: '3+ Stars' },
  { value: '2', label: '2+ Stars' },
];

const VERIFICATION_FILTERS = [
  { value: '', label: 'All Types' },
  { value: 'owner', label: 'Owners' },
  { value: 'resident', label: 'Residents' },
  { value: 'visitor', label: 'Visitors' },
];

const SORT_OPTIONS = [
  { value: 'created_at-desc', label: 'Most Recent' },
  { value: 'helpful_count-desc', label: 'Most Helpful' },
  { value: 'overall_rating-desc', label: 'Highest Rated' },
  { value: 'overall_rating-asc', label: 'Lowest Rated' },
];

// Star rating display component
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
        await onToggleHelpful(review.id, 'locality', false);
        setIsHelpful(false);
        setHelpfulCount((prev) => prev - 1);
      } else {
        await onToggleHelpful(review.id, 'locality', true);
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

  const verificationBadge = (type) => {
    const badges = {
      owner: { label: 'Owner', color: 'bg-green-500/20 text-green-400 border-green-500/30' },
      resident: { label: 'Resident', color: 'bg-blue-500/20 text-blue-400 border-blue-500/30' },
      visitor: { label: 'Visitor', color: 'bg-gray-500/20 text-gray-400 border-gray-500/30' },
    };
    const badge = badges[type] || badges.visitor;
    return (
      <span className={`px-2 py-0.5 text-xs rounded-full border ${badge.color}`}>
        {badge.label}
      </span>
    );
  };

  const renderAspectRating = (label, rating, notes) => {
    if (!rating && !notes) return null;
    return (
      <div className="flex items-center justify-between py-1">
        <span className="text-sm text-gray-400">{label}</span>
        <div className="flex items-center gap-2">
          {rating && <StarRating rating={rating} size={12} />}
          {notes && (
            <span className="text-xs text-gray-500 truncate max-w-[150px]" title={notes}>
              {notes}
            </span>
          )}
        </div>
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
            {review.is_verified === 1 && (
              <Shield size={14} className="text-green-400" />
            )}
            {review.verification_type && verificationBadge(review.verification_type)}
          </div>
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
      <div className="border-t border-gray-700/50 pt-3 mb-3">
        {renderAspectRating('Vastu', review.vastu_rating, review.vastu_notes)}
        {renderAspectRating('Schools', review.school_rating, review.school_notes)}
        {renderAspectRating('Transport', review.transport_rating, review.transport_notes)}
        {renderAspectRating('Safety', review.safety_rating, review.safety_notes)}
        {renderAspectRating('Amenities', review.amenities_rating, review.amenities_notes)}
        {renderAspectRating('Water Supply', review.water_supply_rating)}
        {renderAspectRating('Power Supply', review.power_supply_rating)}
      </div>

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

// Aggregate ratings display
function AggregateRatings({ stats }) {
  if (!stats) return null;

  const ratingBars = [
    { label: '5 Star', count: stats.rating_distribution?.['5'] || 0, percentage: 0 },
    { label: '4 Star', count: stats.rating_distribution?.['4'] || 0, percentage: 0 },
    { label: '3 Star', count: stats.rating_distribution?.['3'] || 0, percentage: 0 },
    { label: '2 Star', count: stats.rating_distribution?.['2'] || 0, percentage: 0 },
    { label: '1 Star', count: stats.rating_distribution?.['1'] || 0, percentage: 0 },
  ];

  const total = Object.values(stats.rating_distribution || {}).reduce((a, b) => a + b, 0);
  ratingBars.forEach((bar) => {
    bar.percentage = total > 0 ? (bar.count / total) * 100 : 0;
  });

  return (
    <div className="bg-gray-800/50 rounded-lg border border-gray-700/50 p-4">
      <div className="flex items-start gap-4">
        {/* Overall Rating */}
        <div className="text-center min-w-[80px]">
          <div className="text-4xl font-bold text-white mb-1">
            {stats.avg_overall_rating?.toFixed(1) || '-'}
          </div>
          <StarRating rating={Math.round(stats.avg_overall_rating || 0)} size={16} />
          <div className="text-xs text-gray-500 mt-1">
            {stats.total_reviews} reviews
          </div>
        </div>

        {/* Rating Distribution */}
        <div className="flex-1 space-y-1">
          {ratingBars.map((bar) => (
            <div key={bar.label} className="flex items-center gap-2">
              <span className="text-xs text-gray-500 w-16">{bar.label}</span>
              <div className="flex-1 h-2 bg-gray-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-yellow-400 rounded-full transition-all"
                  style={{ width: `${bar.percentage}%` }}
                />
              </div>
              <span className="text-xs text-gray-500 w-8 text-right">{bar.count}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Category Ratings */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4 pt-4 border-t border-gray-700/50">
        {[
          { label: 'Vastu', value: stats.avg_vastu_rating },
          { label: 'Schools', value: stats.avg_school_rating },
          { label: 'Transport', value: stats.avg_transport_rating },
          { label: 'Safety', value: stats.avg_safety_rating },
          { label: 'Amenities', value: stats.avg_amenities_rating },
          { label: 'Water Supply', value: stats.avg_water_supply_rating },
          { label: 'Power Supply', value: stats.avg_power_supply_rating },
        ].map(
          (item) =>
            item.value && (
              <div key={item.label} className="text-center">
                <div className="text-sm font-medium text-gray-300">{item.label}</div>
                <div className="flex items-center justify-center gap-1 mt-1">
                  <StarRating rating={item.value} size={12} />
                  <span className="text-sm text-gray-400">{item.value.toFixed(1)}</span>
                </div>
              </div>
            )
        )}
      </div>

      {/* Verified Badge */}
      {stats.verified_count > 0 && (
        <div className="flex items-center gap-2 mt-4 pt-3 border-t border-gray-700/50">
          <Shield size={14} className="text-green-400" />
          <span className="text-sm text-gray-400">
            <span className="text-green-400 font-medium">{stats.verified_count}</span> verified{' '}
            {stats.verified_count === 1 ? 'review' : 'reviews'}
          </span>
        </div>
      )}
    </div>
  );
}

export default function LocalityReviews({
  localityId,
  localityName,
  isOpen = true,
  onClose,
  onSubmitReview,
}) {
  const [reviews, setReviews] = useState([]);
  const [stats, setStats] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Filter and sort state
  const [ratingFilter, setRatingFilter] = useState('');
  const [verificationFilter, setVerificationFilter] = useState('');
  const [sortOption, setSortOption] = useState('created_at-desc');

  // Form state
  const [showReviewForm, setShowReviewForm] = useState(false);

  // Load reviews
  const loadReviews = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [sortBy, sortOrder] = sortOption.split('-');
      const reviewsData = await getLocalityReviews(localityId, {
        rating: ratingFilter || undefined,
        verification_type: verificationFilter || undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
        limit: 20,
      });
      setReviews(reviewsData);
    } catch (err) {
      setError(err.message);
      console.error('Failed to load reviews:', err);
    } finally {
      setIsLoading(false);
    }
  }, [localityId, ratingFilter, verificationFilter, sortOption]);

  // Load stats
  const loadStats = useCallback(async () => {
    try {
      const statsData = await getLocalityStats(localityId);
      setStats(statsData);
    } catch (err) {
      console.error('Failed to load stats:', err);
    }
  }, [localityId]);

  // Initial load
  useEffect(() => {
    if (isOpen && localityId) {
      loadReviews();
      loadStats();
    }
  }, [isOpen, localityId, loadReviews, loadStats]);

  // Handle filter changes
  useEffect(() => {
    if (isOpen && localityId) {
      loadReviews();
    }
  }, [ratingFilter, verificationFilter, sortOption]);

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
    loadStats();
  };

  if (!isOpen) return null;

  return (
    <div className="h-full flex flex-col bg-gray-900">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-700/50 bg-gray-800/50">
        <div>
          <h2 className="text-xl font-semibold text-white flex items-center gap-2">
            <MapPin size={20} className="text-blue-400" />
            {localityName || 'Locality Reviews'}
          </h2>
          {stats && (
            <p className="text-sm text-gray-400 mt-1">
              {stats.total_reviews} reviews · {stats.verified_count} verified
            </p>
          )}
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

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3 p-4 bg-gray-800/30 border-b border-gray-700/50">
        {/* Rating Filter */}
        <div className="flex items-center gap-2">
          <Filter size={16} className="text-gray-400" />
          <select
            value={ratingFilter}
            onChange={(e) => setRatingFilter(e.target.value)}
            className="bg-gray-800 border border-gray-600 text-white text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:border-blue-500"
          >
            {RATING_FILTERS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        {/* Verification Filter */}
        <select
          value={verificationFilter}
          onChange={(e) => setVerificationFilter(e.target.value)}
          className="bg-gray-800 border border-gray-600 text-white text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:border-blue-500"
        >
          {VERIFICATION_FILTERS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>

        {/* Sort */}
        <div className="flex items-center gap-2 ml-auto">
          <SortAsc size={16} className="text-gray-400" />
          <select
            value={sortOption}
            onChange={(e) => setSortOption(e.target.value)}
            className="bg-gray-800 border border-gray-600 text-white text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:border-blue-500"
          >
            {SORT_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
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

        {/* Stats */}
        {!isLoading && stats && <AggregateRatings stats={stats} />}

        {/* Reviews List */}
        {!isLoading && !error && (
          <>
            {reviews.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-gray-400 mb-4">No reviews yet for this locality.</p>
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
              localityId={localityId}
              localityName={localityName}
              onClose={() => setShowReviewForm(false)}
              onSuccess={handleReviewSubmitted}
            />
          </div>
        </div>
      )}
    </div>
  );
}
