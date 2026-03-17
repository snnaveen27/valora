import { useEffect, useMemo, useState } from 'react';
import {
  BarChart3,
  CreditCard,
  MapPin,
  MessageSquare,
  ShieldCheck,
  Sparkles,
  Users,
  TrendingUp,
} from 'lucide-react';

import { getSessions } from '../../services/familyApi';
import { getLocalityStats } from '../../services/reviewApi';
import { checkCredits } from '../../services/sentimentApi';

// Import centralized dummy data
import { 
  DUMMY_SESSIONS, 
  DUMMY_REVIEWS,
  DUMMY_REVIEW_STATS, 
  DUMMY_SENTIMENTS,
  DUMMY_INVESTMENTS,
  DUMMY_PRICE_DATA,
  LOCALITY_DISPLAY_NAMES,
  getLocalityInfo,
  isDummyData
} from '../../data/dummyCommunityData';

const normalizeLocalityId = (value) =>
  (value || '')
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\s-]/g, '')
    .replace(/[\s-]+/g, '_');

// Get display name for locality from centralized data
const getLocalizedName = (localityId) => {
  const normalized = normalizeLocalityId(localityId);
  return LOCALITY_DISPLAY_NAMES[normalized] || localityId || 'Unknown';
};

const formatCompactNumber = (value) => {
  if (value === null || value === undefined || value === '') return '--';
  return new Intl.NumberFormat('en-IN', {
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(Number(value));
};

const formatCredits = (credits) => {
  if (typeof credits === 'number') return credits;
  return credits?.credits_available ?? credits?.remaining ?? credits?.total ?? 0;
};

function StatTile({ icon: Icon, label, value }) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-slate-700/50 bg-slate-800/30 p-2">
      <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-slate-700/50">
        <Icon className="h-2.5 w-2.5 text-slate-400" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-[8px] uppercase tracking-wider text-slate-500">{label}</div>
        <div className="truncate text-xs font-semibold text-white">{value}</div>
      </div>
    </div>
  );
}

export default function CommunityPulseWorkspace({ agentData, viewportAnalysis, locality, lat, lng }) {
  const [summary, setSummary] = useState({
    loading: true,
    sessions: [],
    reviewStats: null,
    credits: 0,
  });

  // Derive localityName from multiple fallback sources (like EnhancedChatPanel)
  const derivedLocalityName = 
    agentData?.buildingAnalysis?.building?.name ||
    viewportAnalysis?.area_name ||
    agentData?.viewportAnalysis?.area_name ||
    agentData?.explainability?.locality?.name ||
    agentData?.explainability?.area ||
    locality ||
    '';
  
  const localityName = derivedLocalityName;
  const localityId = useMemo(() => normalizeLocalityId(localityName) || 'whitefield', [localityName]);
  
  // Use whitefield as fallback for display when no locality is specified
  const displayLocalityName = localityName || 'Whitefield';

  useEffect(() => {
    let mounted = true;

    const loadSummary = async () => {
      try {
        const [sessions, reviewStats, credits] = await Promise.all([
          getSessions({ status: 'active', limit: 50 }).catch(() => []),
          localityId ? getLocalityStats(localityId).catch(() => null) : Promise.resolve(null),
          checkCredits().catch(() => 0),
        ]);

        if (!mounted) return;

        // Use dummy data when API returns empty (for demonstration)
        let sessionsData = Array.isArray(sessions) && sessions.length > 0 ? sessions : DUMMY_SESSIONS;
        
        // Filter sessions by locality if a locality is selected
        if (localityId) {
          const filteredSessions = sessionsData.filter(
            s => s.target_locality === localityId || s.target_locality === normalizeLocalityId(localityId)
          );
          if (filteredSessions.length > 0) {
            sessionsData = filteredSessions;
          }
        }

        // Get locality-specific review stats from centralized dummy data
        const normalizedLocality = normalizeLocalityId(localityId);
        const localitySpecificStats = DUMMY_REVIEW_STATS[normalizedLocality];
        
        // Use API data only if it has real data (more than 0 reviews), otherwise fallback to dummy
        const hasRealData = reviewStats && reviewStats.total_reviews > 0;
        const reviewStatsData = hasRealData ? reviewStats : (localitySpecificStats || DUMMY_REVIEW_STATS.whitefield);

        setSummary({
          loading: false,
          sessions: sessionsData,
          reviewStats: reviewStatsData,
          credits: formatCredits(credits),
        });
      } catch (error) {
        if (!mounted) return;
        // Fallback to localized dummy data (only use if has real data)
        const normalizedLocality = normalizeLocalityId(localityId);
        const localitySpecificStats = DUMMY_REVIEW_STATS[normalizedLocality];
        const hasRealData = localitySpecificStats && localitySpecificStats.tr > 0;
        setSummary({ 
          loading: false, 
          sessions: DUMMY_SESSIONS, 
          reviewStats: hasRealData ? localitySpecificStats : DUMMY_REVIEW_STATS.whitefield, 
          credits: 0 
        });
      }
    };

    loadSummary();
    return () => { mounted = false; };
  }, [localityId]);

  const reviewCount = summary.reviewStats?.total_reviews || summary.reviewStats?.tr || 0;
  const verifiedCount = summary.reviewStats?.verified_count || summary.reviewStats?.vr || 0;
  const averageRating = summary.reviewStats?.avg_overall_rating || summary.reviewStats?.or || summary.reviewStats?.avg_overall_rating || 4.0;

  // Helper to get compact reviews for inline display
  const getCompactReviews = (locId) => {
    const normalized = normalizeLocalityId(locId) || 'whitefield';
    const localityData = DUMMY_REVIEWS[normalized] || DUMMY_REVIEWS.whitefield;
    return localityData?.reviews || [];
  };

  // Helper to get latest review title
  const getLatestReviewTitle = (locId) => {
    const reviews = getCompactReviews(locId);
    return reviews[0]?.title?.slice(0, 8) || '--';
  };

  // Helper to get sentiment label
  const getSentimentLabel = (locId) => {
    const normalized = normalizeLocalityId(locId) || 'whitefield';
    const data = DUMMY_SENTIMENTS[normalized] || DUMMY_SENTIMENTS.whitefield;
    return data?.sentiment_label || data?.sl || 'Neutral';
  };

  // Helper to get investment score
  const getInvestmentScore = (locId) => {
    const normalized = normalizeLocalityId(locId) || 'whitefield';
    const data = DUMMY_INVESTMENTS[normalized] || DUMMY_INVESTMENTS.whitefield;
    return data?.investment_score || data?.is?.toString() || 'Medium';
  };

  // Helper to get price per sqft
  const getPricePerSqft = (locId) => {
    const normalized = normalizeLocalityId(locId) || 'whitefield';
    const data = DUMMY_PRICE_DATA[normalized] || DUMMY_PRICE_DATA.whitefield;
    const price = data?.current_price_sqft || data?.cps || 0;
    return price > 0 ? `₹${(price / 1000).toFixed(1)}k` : 'N/A';
  };

  return (
    <div className="space-y-1 p-1">
      {/* Header: Context */}
      <div className="flex items-center justify-between rounded border border-slate-700/50 bg-slate-800/30 p-1">
        <div className="flex items-center gap-1">
          <MapPin className="h-2 w-2 text-cyan-400" />
          <span className="text-[8px] uppercase tracking-wider text-slate-500">Context</span>
        </div>
        <span className="text-[9px] font-medium text-white">
          {localityName || 'No locality'}
        </span>
      </div>

      {/* Hero */}
      <div className="rounded border border-slate-700/50 bg-slate-800/40 p-1">
        <div className="flex items-center gap-1 mb-0.5">
          <Sparkles className="h-2 w-2 text-cyan-400" />
          <span className="text-[9px] font-semibold text-white">Community</span>
        </div>
        <p className="text-[8px] text-slate-400">
          Decision rooms, resident proof & market pulse
        </p>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-4 gap-0.5">
        <StatTile icon={Users} label="Rooms" value={summary.loading ? '...' : formatCompactNumber(summary.sessions.length)} />
        <StatTile icon={MessageSquare} label="Rating" value={summary.loading ? '...' : (averageRating?.toFixed(1) || '--')} />
        <StatTile icon={ShieldCheck} label="Verified" value={summary.loading ? '...' : formatCompactNumber(verifiedCount)} />
        <StatTile icon={CreditCard} label="Credits" value={summary.loading ? '...' : summary.credits} />
      </div>

      {/* Decision Rooms */}
      <div className="rounded border border-blue-500/30 bg-blue-500/5 p-1">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-1">
            <Users className="h-2 w-2 text-blue-400" />
            <span className="text-[9px] font-medium text-white">Decision Rooms</span>
          </div>
          <span className="text-[8px] text-slate-500">{summary.sessions.length} active</span>
        </div>
        
        {summary.sessions.length > 0 ? (
          <div className="space-y-0.5">
            {summary.sessions.slice(0, 2).map((session) => (
              <div key={session.id} className="flex items-center justify-between rounded bg-slate-800/50 p-0.5">
                <span className="text-[8px] text-white truncate max-w-[100px]">{session.family_name}</span>
                <span className="text-[7px] text-slate-500 truncate max-w-[60px]">{session.target_locality_display || session.target_locality || '--'}</span>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-[8px] text-slate-500 py-0.5">
            Use chat to create
          </div>
        )}
      </div>

      {/* Resident Proof - Simple stats */}
      <div className="rounded border border-emerald-500/30 bg-emerald-500/5 p-1">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-1">
            <ShieldCheck className="h-2 w-2 text-emerald-400" />
            <span className="text-[9px] font-medium text-white">Resident Proof</span>
          </div>
          <span className="text-[8px] text-slate-500">{reviewCount} reviews</span>
        </div>
        
        {/* Simple stats row */}
        <div className="grid grid-cols-3 gap-0.5 text-center">
          <div className="rounded bg-slate-800/50 p-0.5">
            <div className="text-[7px] text-slate-500">Rating</div>
            <div className="text-[8px] text-yellow-400">{(averageRating || 0).toFixed(1)}</div>
          </div>
          <div className="rounded bg-slate-800/50 p-0.5">
            <div className="text-[7px] text-slate-500">Verified</div>
            <div className="text-[8px] text-green-400">{verifiedCount}</div>
          </div>
          <div className="rounded bg-slate-800/50 p-0.5">
            <div className="text-[7px] text-slate-500">Latest</div>
            <div className="text-[8px] text-white truncate">{getLatestReviewTitle(localityId)}</div>
          </div>
        </div>
      </div>

      {/* Market Pulse - Simple stats */}
      <div className="rounded border border-amber-500/30 bg-amber-500/5 p-1">
        <div className="flex items-center justify-between mb-1">
          <div className="flex items-center gap-1">
            <TrendingUp className="h-2 w-2 text-amber-400" />
            <span className="text-[9px] font-medium text-white">Market Pulse</span>
          </div>
        </div>
        
        {/* Simple stats row */}
        <div className="grid grid-cols-3 gap-0.5">
          <div className="rounded bg-slate-800/50 p-0.5 text-center">
            <div className="text-[7px] text-slate-500">Sentiment</div>
            <div className="text-[8px] text-green-400">{getSentimentLabel(localityId)}</div>
          </div>
          <div className="rounded bg-slate-800/50 p-0.5 text-center">
            <div className="text-[7px] text-slate-500">Invest</div>
            <div className="text-[8px] text-cyan-400">{getInvestmentScore(localityId)}</div>
          </div>
          <div className="rounded bg-slate-800/50 p-0.5 text-center">
            <div className="text-[7px] text-slate-500">₹/sqft</div>
            <div className="text-[8px] text-amber-400">{getPricePerSqft(localityId)}</div>
          </div>
        </div>
      </div>
    </div>
  );
}
