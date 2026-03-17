/**
 * Community Components - FOCUSED VERSION
 * 
 * This module exports components aligned with Valora's product thesis:
 * - Broker productivity and explainable decision intelligence
 * - Client-ready outputs
 * 
 * KEPT (Aligned with Product Thesis):
 * ================================
 * 1. Decision-Room (Family Hub) - Multi-stakeholder workflow
 * 2. Locality Reviews with Verified Resident Proof
 * 3. Market Sentiment as Supporting Intelligence
 * 
 * REMOVED (Not aligned with product thesis):
 * ==========================================
 * - BuilderProfile - Generic builder directory
 * - RERAVerification - Not core to broker workflow
 * 
 * These changes ensure Valora stays niche: broker workflow,
 * explainable reasoning, and client-ready intelligence outputs.
 */

// Decision-Room (Family Hub) - Multi-stakeholder workflow
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

// Locality Reviews with Verified Resident Proof
export { default as LocalityReviews } from './LocalityReviews';
export { default as ReviewForm } from './ReviewForm';
export { default as VastuRating } from './VastuRating';

// Market Sentiment - Supporting Intelligence (Secondary)
export { default as SentimentDashboard } from './SentimentDashboard';
export { default as SentimentGauge } from './SentimentGauge';
export { default as ActivityFeed, generateMockActivities } from './ActivityFeed';
export { default as InvestmentScore } from './InvestmentScore';
export { default as PriceTrendChart, generateMockPriceData } from './PriceTrendChart';
