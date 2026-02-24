/**
 * Community Pulse Components - Phases 1, 2 & 3
 * 
 * This module exports all components for the Community Pulse feature,
 * which includes collaborative property decision-making (Phase 1),
 * locality/builder reviews (Phase 2), and sentiment dashboard (Phase 3).
 * 
 * Phase 1 - Family Hub:
 * - FamilyHub: Main container with tab navigation
 * - FamilySessionCreate: Form to create new family sessions
 * - FamilyInviteModal: Modal for inviting family members
 * - FamilyWatchlist: Shared property watchlist
 * - FamilyVotingPanel: Voting interface for properties
 * - FamilyTimeline: Activity timeline visualization
 * - WhatsAppShare: WhatsApp sharing component
 * 
 * Phase 2 - Reviews:
 * - LocalityReviews: Locality reviews container
 * - ReviewForm: Review submission form
 * - VastuRating: Vastu-specific ratings
 * - BuilderProfile: Builder profiles component
 * - RERAVerification: RERA verification badge
 * 
 * Phase 3 - Sentiment Dashboard:
 * - SentimentDashboard: Main sentiment dashboard
 * - SentimentGauge: Visual gauge for sentiment score
 * - ActivityFeed: Activity stream component
 * - InvestmentScore: Investment score card
 * - PriceTrendChart: Price trend visualization
 */

// Phase 1 - Family Hub (existing)
export { default as FamilyHub } from './FamilyHub';
export { default as FamilySessionCreate } from './FamilySessionCreate';
export { default as FamilyInviteModal } from './FamilyInviteModal';
export { default as FamilyWatchlist } from './FamilyWatchlist';
export { default as FamilyVotingPanel } from './FamilyVotingPanel';
export { default as FamilyTimeline } from './FamilyTimeline';
export { 
  default as WhatsAppShare,
  WhatsAppShareButton,
  WhatsAppShareCard,
  WhatsAppShareInline,
  generateWhatsAppMessage,
  formatPrice,
} from './WhatsAppShare';

// Phase 2 - Reviews (existing)
export { default as LocalityReviews } from './LocalityReviews';
export { default as ReviewForm } from './ReviewForm';
export { default as VastuRating } from './VastuRating';
export { default as BuilderProfile } from './BuilderProfile';
export { default as RERAVerification } from './RERAVerification';

// Phase 3 - Sentiment Dashboard (new)
export { default as SentimentDashboard } from './SentimentDashboard';
export { default as SentimentGauge } from './SentimentGauge';
export { default as ActivityFeed, generateMockActivities } from './ActivityFeed';
export { default as InvestmentScore } from './InvestmentScore';
export { default as PriceTrendChart, generateMockPriceData } from './PriceTrendChart';
