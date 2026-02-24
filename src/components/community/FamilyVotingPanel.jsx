/**
 * FamilyVotingPanel - Voting interface for Family Hub
 * 
 * Features:
 * - Property selector from watchlist
 * - Vote buttons (thumbs up/down/maybe)
 * - Aspect-based ratings (location, price, vastu, amenities)
 * - Comment input
 * - Vote summary display
 * - Responsive layout
 * 
 * Props:
 * @param {string} sessionId - Current session ID
 * @param {Array} watchlist - Optional watchlist items (loaded internally if not provided)
 */

import { useState, useEffect } from 'react';
import {
  ThumbsUp,
  ThumbsDown,
  HelpCircle,
  MapPin,
  Wallet,
  Building2,
  Sun,
  Trees,
  MessageSquare,
  Loader2,
  AlertCircle,
  CheckCircle,
  ChevronDown,
  Users,
  BarChart3,
  Send,
} from 'lucide-react';

import {
  getWatchlist,
  getVotes,
  getPropertyVotes,
  getVoteSummary,
  castVote,
} from '../../services/familyApi';

// Vote types
const VOTE_TYPES = [
  { id: 'up', label: 'Like', icon: ThumbsUp, color: 'text-green-400', bg: 'bg-green-500/20', border: 'border-green-500/30' },
  { id: 'down', label: 'Dislike', icon: ThumbsDown, color: 'text-red-400', bg: 'bg-red-500/20', border: 'border-red-500/30' },
  { id: 'maybe', label: 'Maybe', icon: HelpCircle, color: 'text-yellow-400', bg: 'bg-yellow-500/20', border: 'border-yellow-500/30' },
];

// Aspect options for detailed voting
const ASPECTS = [
  { id: 'location', label: 'Location', icon: MapPin },
  { id: 'price', label: 'Price', icon: Wallet },
  { id: 'vastu', label: 'Vastu', icon: Sun },
  { id: 'amenities', label: 'Amenities', icon: Trees },
];

export default function FamilyVotingPanel({ sessionId, watchlist: propWatchlist }) {
  // Data state
  const [watchlist, setWatchlist] = useState(propWatchlist || []);
  const [selectedProperty, setSelectedProperty] = useState(null);
  const [propertyVotes, setPropertyVotes] = useState([]);
  const [voteSummary, setVoteSummary] = useState(null);
  const [allVotes, setAllVotes] = useState([]);
  
  // UI state
  const [isLoading, setIsLoading] = useState(false);
  const [isLoadingVotes, setIsLoadingVotes] = useState(false);
  const [error, setError] = useState(null);
  const [showPropertyDropdown, setShowPropertyDropdown] = useState(false);
  
  // Vote form state
  const [currentVote, setCurrentVote] = useState(null);
  const [aspectVotes, setAspectVotes] = useState({});
  const [comment, setComment] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitSuccess, setSubmitSuccess] = useState(false);

  // Load watchlist on mount
  useEffect(() => {
    if (sessionId && !propWatchlist) {
      loadWatchlist();
    } else if (propWatchlist) {
      setWatchlist(propWatchlist);
    }
  }, [sessionId, propWatchlist]);

  // Load votes when property is selected
  useEffect(() => {
    if (selectedProperty) {
      loadPropertyVotes();
      loadVoteSummary();
    }
  }, [selectedProperty]);

  // Reset vote form when property changes
  useEffect(() => {
    setCurrentVote(null);
    setAspectVotes({});
    setComment('');
    setSubmitSuccess(false);
  }, [selectedProperty?.id]);

  /**
   * Load watchlist from API
   */
  const loadWatchlist = async () => {
    setIsLoading(true);
    try {
      const data = await getWatchlist(sessionId);
      setWatchlist(data || []);
      
      // Auto-select first property if available
      if (data && data.length > 0 && !selectedProperty) {
        setSelectedProperty(data[0]);
      }
    } catch (err) {
      console.error('[FamilyVotingPanel] Failed to load watchlist:', err);
      setError('Failed to load properties');
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Load votes for selected property
   */
  const loadPropertyVotes = async () => {
    if (!selectedProperty) return;
    
    setIsLoadingVotes(true);
    try {
      const votes = await getPropertyVotes(sessionId, selectedProperty.id);
      setPropertyVotes(votes || []);
    } catch (err) {
      console.error('[FamilyVotingPanel] Failed to load votes:', err);
    } finally {
      setIsLoadingVotes(false);
    }
  };

  /**
   * Load vote summary
   */
  const loadVoteSummary = async () => {
    if (!selectedProperty) return;
    
    try {
      const summary = await getVoteSummary(sessionId);
      // Find summary for selected property
      const propertySummary = summary?.find(s => s.property_id === selectedProperty.id);
      setVoteSummary(propertySummary || null);
    } catch (err) {
      console.error('[FamilyVotingPanel] Failed to load vote summary:', err);
    }
  };

  /**
   * Handle property selection
   */
  const handlePropertySelect = (property) => {
    setSelectedProperty(property);
    setShowPropertyDropdown(false);
  };

  /**
   * Handle main vote selection
   */
  const handleVoteSelect = (voteType) => {
    setCurrentVote(voteType);
    setSubmitSuccess(false);
  };

  /**
   * Handle aspect vote
   */
  const handleAspectVote = (aspectId, voteType) => {
    setAspectVotes(prev => ({
      ...prev,
      [aspectId]: voteType,
    }));
    setSubmitSuccess(false);
  };

  /**
   * Submit vote
   */
  const handleSubmitVote = async () => {
    if (!selectedProperty || !currentVote) return;
    
    setIsSubmitting(true);
    setError(null);
    
    try {
      await castVote(sessionId, {
        property_id: selectedProperty.id,
        vote: currentVote,
        aspects: Object.keys(aspectVotes).length > 0 ? aspectVotes : null,
        comment: comment.trim() || null,
      });
      
      setSubmitSuccess(true);
      loadPropertyVotes();
      loadVoteSummary();
      
      // Reset form after delay
      setTimeout(() => {
        setSubmitSuccess(false);
      }, 2000);
    } catch (err) {
      console.error('[FamilyVotingPanel] Failed to submit vote:', err);
      setError(err.message || 'Failed to submit vote');
    } finally {
      setIsSubmitting(false);
    }
  };

  /**
   * Format price
   */
  const formatPrice = (price) => {
    if (!price) return 'Price not specified';
    if (price >= 10000000) return `₹${(price / 10000000).toFixed(2)} Cr`;
    if (price >= 100000) return `₹${(price / 100000).toFixed(2)} L`;
    return `₹${price.toLocaleString('en-IN')}`;
  };

  /**
   * Get vote type config
   */
  const getVoteTypeConfig = (voteId) => {
    return VOTE_TYPES.find(v => v.id === voteId) || VOTE_TYPES[2];
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
      </div>
    );
  }

  // Empty state
  if (!isLoading && watchlist.length === 0) {
    return (
      <div className="text-center py-12 px-6">
        <ThumbsUp className="w-12 h-12 text-slate-600 mx-auto mb-3" />
        <h4 className="text-lg font-medium text-slate-400 mb-2">No Properties to Vote</h4>
        <p className="text-sm text-slate-500">
          Add properties to your watchlist first to start voting.
        </p>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6">
      {/* Property Selector */}
      <div className="mb-6">
        <label className="block text-sm font-medium text-slate-300 mb-2">
          Select Property
        </label>
        <div className="relative">
          <button
            onClick={(e) => {
              e.stopPropagation();
              setShowPropertyDropdown(!showPropertyDropdown);
            }}
            className="w-full flex items-center justify-between px-4 py-3 bg-slate-800/50 border border-slate-700/50 rounded-lg hover:border-slate-600 transition-colors"
          >
            {selectedProperty ? (
              <div className="flex items-center gap-3">
                <Building2 className="w-5 h-5 text-purple-400" />
                <div className="text-left">
                  <p className="font-medium text-white">{selectedProperty.property_title}</p>
                  {selectedProperty.locality && (
                    <p className="text-sm text-slate-400">{selectedProperty.locality}</p>
                  )}
                </div>
              </div>
            ) : (
              <span className="text-slate-400">Choose a property to vote</span>
            )}
            <ChevronDown className={`w-5 h-5 text-slate-400 transition-transform ${showPropertyDropdown ? 'rotate-180' : ''}`} />
          </button>
          
          {showPropertyDropdown && (
            <div 
              className="absolute top-full left-0 right-0 mt-1 bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-10 max-h-64 overflow-y-auto"
              onClick={(e) => e.stopPropagation()}
            >
              {watchlist.map(property => (
                <button
                  key={property.id}
                  onClick={() => handlePropertySelect(property)}
                  className={`w-full px-4 py-3 text-left hover:bg-slate-700/50 transition-colors ${
                    selectedProperty?.id === property.id ? 'bg-purple-500/20' : ''
                  }`}
                >
                  <p className="font-medium text-white">{property.property_title}</p>
                  <div className="flex items-center gap-3 text-sm text-slate-400 mt-1">
                    {property.locality && (
                      <span className="flex items-center gap-1">
                        <MapPin className="w-3 h-3" />
                        {property.locality}
                      </span>
                    )}
                    {property.price && (
                      <span>{formatPrice(property.price)}</span>
                    )}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-4 p-3 bg-red-500/20 border border-red-500/30 rounded-lg flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-400" />
          <p className="text-sm text-red-400">{error}</p>
        </div>
      )}

      {/* Success Message */}
      {submitSuccess && (
        <div className="mb-4 p-3 bg-green-500/20 border border-green-500/30 rounded-lg flex items-center gap-2">
          <CheckCircle className="w-4 h-4 text-green-400" />
          <p className="text-sm text-green-400">Vote submitted successfully!</p>
        </div>
      )}

      {selectedProperty && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Voting Section */}
          <div className="space-y-6">
            {/* Main Vote */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4">
              <h4 className="text-sm font-medium text-slate-300 mb-3">Your Vote</h4>
              <div className="flex gap-3">
                {VOTE_TYPES.map(voteType => (
                  <button
                    key={voteType.id}
                    onClick={() => handleVoteSelect(voteType.id)}
                    className={`flex-1 flex flex-col items-center gap-2 p-3 rounded-lg border transition-all ${
                      currentVote === voteType.id
                        ? `${voteType.bg} ${voteType.border}`
                        : 'bg-slate-700/30 border-slate-600/30 hover:border-slate-500'
                    }`}
                  >
                    <voteType.icon className={`w-6 h-6 ${currentVote === voteType.id ? voteType.color : 'text-slate-400'}`} />
                    <span className={`text-sm font-medium ${currentVote === voteType.id ? voteType.color : 'text-slate-400'}`}>
                      {voteType.label}
                    </span>
                  </button>
                ))}
              </div>
            </div>

            {/* Aspect Ratings */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4">
              <h4 className="text-sm font-medium text-slate-300 mb-3">Rate Aspects (Optional)</h4>
              <div className="space-y-3">
                {ASPECTS.map(aspect => (
                  <div key={aspect.id} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <aspect.icon className="w-4 h-4 text-slate-400" />
                      <span className="text-sm text-slate-300">{aspect.label}</span>
                    </div>
                    <div className="flex gap-1">
                      {VOTE_TYPES.map(voteType => (
                        <button
                          key={voteType.id}
                          onClick={() => handleAspectVote(aspect.id, voteType.id)}
                          className={`p-1.5 rounded-lg transition-all ${
                            aspectVotes[aspect.id] === voteType.id
                              ? `${voteType.bg} ${voteType.border} border`
                              : 'hover:bg-slate-700/50'
                          }`}
                          title={voteType.label}
                        >
                          <voteType.icon className={`w-4 h-4 ${
                            aspectVotes[aspect.id] === voteType.id ? voteType.color : 'text-slate-500'
                          }`} />
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Comment */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4">
              <h4 className="text-sm font-medium text-slate-300 mb-3">Add Comment (Optional)</h4>
              <textarea
                value={comment}
                onChange={(e) => setComment(e.target.value)}
                placeholder="Share your thoughts about this property..."
                rows={3}
                className="w-full px-4 py-2.5 bg-slate-700/50 border border-slate-600/50 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50 resize-none"
                maxLength={500}
              />
              <p className="mt-1 text-xs text-slate-500 text-right">
                {comment.length}/500
              </p>
            </div>

            {/* Submit Button */}
            <button
              onClick={handleSubmitVote}
              disabled={!currentVote || isSubmitting}
              className={`w-full flex items-center justify-center gap-2 px-6 py-3 rounded-lg font-medium transition-colors ${
                !currentVote || isSubmitting
                  ? 'bg-slate-700/50 text-slate-400 cursor-not-allowed'
                  : 'bg-purple-500 hover:bg-purple-600 text-white'
              }`}
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Submitting...</span>
                </>
              ) : (
                <>
                  <Send className="w-5 h-5" />
                  <span>Submit Vote</span>
                </>
              )}
            </button>
          </div>

          {/* Vote Summary Section */}
          <div className="space-y-6">
            {/* Summary Stats */}
            {voteSummary && (
              <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4">
                <h4 className="text-sm font-medium text-slate-300 mb-3 flex items-center gap-2">
                  <BarChart3 className="w-4 h-4" />
                  Vote Summary
                </h4>
                
                <div className="grid grid-cols-3 gap-3 mb-4">
                  <div className="text-center p-3 bg-green-500/10 rounded-lg">
                    <p className="text-2xl font-bold text-green-400">{voteSummary.up || 0}</p>
                    <p className="text-xs text-slate-400">Likes</p>
                  </div>
                  <div className="text-center p-3 bg-yellow-500/10 rounded-lg">
                    <p className="text-2xl font-bold text-yellow-400">{voteSummary.maybe || 0}</p>
                    <p className="text-xs text-slate-400">Maybes</p>
                  </div>
                  <div className="text-center p-3 bg-red-500/10 rounded-lg">
                    <p className="text-2xl font-bold text-red-400">{voteSummary.down || 0}</p>
                    <p className="text-xs text-slate-400">Dislikes</p>
                  </div>
                </div>

                {/* Aspect Summary */}
                {voteSummary.aspects_summary && Object.keys(voteSummary.aspects_summary).length > 0 && (
                  <div className="border-t border-slate-700/50 pt-3">
                    <p className="text-xs text-slate-500 mb-2">Aspect Ratings</p>
                    <div className="space-y-2">
                      {Object.entries(voteSummary.aspects_summary).map(([aspect, counts]) => (
                        <div key={aspect} className="flex items-center justify-between text-sm">
                          <span className="text-slate-400 capitalize">{aspect}</span>
                          <div className="flex items-center gap-2">
                            <span className="text-green-400">↑{counts.up || 0}</span>
                            <span className="text-yellow-400">?{counts.maybe || 0}</span>
                            <span className="text-red-400">↓{counts.down || 0}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Comments Section */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4">
              <h4 className="text-sm font-medium text-slate-300 mb-3 flex items-center gap-2">
                <MessageSquare className="w-4 h-4" />
                Comments ({propertyVotes.filter(v => v.comment).length})
              </h4>
              
              {isLoadingVotes ? (
                <div className="flex items-center justify-center py-4">
                  <Loader2 className="w-5 h-5 text-purple-400 animate-spin" />
                </div>
              ) : propertyVotes.filter(v => v.comment).length === 0 ? (
                <p className="text-sm text-slate-500 text-center py-4">No comments yet</p>
              ) : (
                <div className="space-y-3 max-h-64 overflow-y-auto">
                  {propertyVotes.filter(v => v.comment).map(vote => {
                    const voteConfig = getVoteTypeConfig(vote.vote);
                    return (
                      <div key={vote.id} className="p-3 bg-slate-700/30 rounded-lg">
                        <div className="flex items-center gap-2 mb-1">
                          <voteConfig.icon className={`w-4 h-4 ${voteConfig.color}`} />
                          <span className="text-sm font-medium text-white">
                            {vote.user_name || 'Family Member'}
                          </span>
                        </div>
                        <p className="text-sm text-slate-300">{vote.comment}</p>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* All Votes */}
            <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-4">
              <h4 className="text-sm font-medium text-slate-300 mb-3 flex items-center gap-2">
                <Users className="w-4 h-4" />
                All Votes ({propertyVotes.length})
              </h4>
              
              {isLoadingVotes ? (
                <div className="flex items-center justify-center py-4">
                  <Loader2 className="w-5 h-5 text-purple-400 animate-spin" />
                </div>
              ) : propertyVotes.length === 0 ? (
                <p className="text-sm text-slate-500 text-center py-4">No votes yet. Be the first!</p>
              ) : (
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {propertyVotes.map(vote => {
                    const voteConfig = getVoteTypeConfig(vote.vote);
                    return (
                      <div key={vote.id} className="flex items-center justify-between p-2 bg-slate-700/30 rounded-lg">
                        <span className="text-sm text-white">{vote.user_name || 'Family Member'}</span>
                        <div className={`flex items-center gap-1 px-2 py-1 rounded-full ${voteConfig.bg}`}>
                          <voteConfig.icon className={`w-3 h-3 ${voteConfig.color}`} />
                          <span className={`text-xs ${voteConfig.color}`}>{voteConfig.label}</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
