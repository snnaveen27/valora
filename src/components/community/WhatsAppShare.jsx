/**
 * WhatsAppShare - WhatsApp sharing component for Family Hub
 * 
 * Features:
 * - Generate share link for properties
 * - WhatsApp deep link integration
 * - Property summary card preview
 * - Copy link functionality
 * - Share to specific contacts
 * 
 * Props:
 * @param {Object} property - Property data to share
 * @param {string} [property.id] - Property ID
 * @param {string} [property.property_title] - Property title
 * @param {string} [property.locality] - Property locality
 * @param {number} [property.price] - Property price
 * @param {string} [property.notes] - Property notes
 * @param {string} [property.status] - Property status
 * @param {string} [property.priority] - Property priority
 * @param {string} [sessionName] - Family session name
 * @param {string} [shareUrl] - Pre-generated share URL
 * @param {function} [onShare] - Callback when share is triggered
 * @param {string} [variant] - Display variant ('button', 'card', 'inline')
 */

import { useState, useCallback } from 'react';
import {
  MessageCircle,
  Copy,
  Check,
  Share2,
  MapPin,
  Wallet,
  Building2,
  Star,
  Eye,
  ExternalLink,
} from 'lucide-react';

// Status display config
const STATUS_CONFIG = {
  considering: { label: 'Considering', color: 'bg-blue-500/20 text-blue-400' },
  shortlisted: { label: 'Shortlisted', color: 'bg-yellow-500/20 text-yellow-400' },
  visited: { label: 'Visited', color: 'bg-green-500/20 text-green-400' },
  rejected: { label: 'Rejected', color: 'bg-red-500/20 text-red-400' },
};

// Priority display config
const PRIORITY_CONFIG = {
  high: { label: 'High', color: 'bg-red-500 text-white' },
  medium: { label: 'Medium', color: 'bg-yellow-500 text-white' },
  low: { label: 'Low', color: 'bg-slate-500 text-white' },
};

export default function WhatsAppShare({
  property,
  sessionName = 'Family Property Search',
  shareUrl,
  onShare,
  variant = 'button',
}) {
  const [copied, setCopied] = useState(false);
  const [showPreview, setShowPreview] = useState(false);

  /**
   * Format price for display
   */
  const formatPrice = (price) => {
    if (!price) return 'Price not specified';
    if (price >= 10000000) return `₹${(price / 10000000).toFixed(2)} Cr`;
    if (price >= 100000) return `₹${(price / 100000).toFixed(2)} L`;
    return `₹${price.toLocaleString('en-IN')}`;
  };

  /**
   * Generate WhatsApp share URL
   */
  const generateWhatsAppUrl = useCallback(() => {
    const lines = [
      `🏠 *${property?.property_title || 'Property'}*`,
      '',
      property?.locality && `📍 Location: ${property.locality}`,
      property?.price && `💰 Price: ${formatPrice(property.price)}`,
      property?.status && `📊 Status: ${STATUS_CONFIG[property.status]?.label || property.status}`,
      property?.priority && `⭐ Priority: ${PRIORITY_CONFIG[property.priority]?.label || property.priority}`,
      '',
      `👨‍👩‍👧‍👦 ${sessionName}`,
      '',
      shareUrl && `🔗 View Details: ${shareUrl}`,
      '',
      '_Shared via Valora - Smart Property Decisions_',
    ].filter(Boolean);

    const message = encodeURIComponent(lines.join('\n'));
    return `https://wa.me/?text=${message}`;
  }, [property, sessionName, shareUrl]);

  /**
   * Generate WhatsApp URL for specific phone number
   */
  const generateWhatsAppUrlForPhone = (phone) => {
    // Clean phone number (remove non-digits, ensure it starts with country code)
    let cleanPhone = phone.replace(/\D/g, '');
    if (cleanPhone.length === 10) {
      cleanPhone = '91' + cleanPhone; // Default to India country code
    }
    
    const message = encodeURIComponent(
      `🏠 *${property?.property_title || 'Property'}*\n\n` +
      (property?.locality ? `📍 ${property.locality}\n` : '') +
      (property?.price ? `💰 ${formatPrice(property.price)}\n` : '') +
      `\n👨‍👩‍👧‍👦 ${sessionName}\n` +
      (shareUrl ? `\n🔗 ${shareUrl}` : '') +
      '\n\n_Shared via Valora_'
    );
    
    return `https://wa.me/${cleanPhone}?text=${message}`;
  };

  /**
   * Copy link to clipboard
   */
  const copyToClipboard = async () => {
    if (!shareUrl) return;
    
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  /**
   * Handle share click
   */
  const handleShare = () => {
    onShare?.();
    
    // Open WhatsApp
    const whatsappUrl = generateWhatsAppUrl();
    window.open(whatsappUrl, '_blank');
  };

  /**
   * Get status config
   */
  const getStatusConfig = (status) => {
    return STATUS_CONFIG[status] || STATUS_CONFIG.considering;
  };

  /**
   * Get priority config
   */
  const getPriorityConfig = (priority) => {
    return PRIORITY_CONFIG[priority] || PRIORITY_CONFIG.medium;
  };

  // Button variant
  if (variant === 'button') {
    return (
      <button
        onClick={handleShare}
        className="flex items-center gap-2 px-3 py-2 bg-green-500/20 hover:bg-green-500/30 text-green-400 rounded-lg transition-colors"
      >
        <MessageCircle className="w-4 h-4" />
        <span className="text-sm font-medium">Share on WhatsApp</span>
      </button>
    );
  }

  // Inline variant (icon only)
  if (variant === 'inline') {
    return (
      <button
        onClick={handleShare}
        className="p-2 hover:bg-green-500/20 rounded-lg transition-colors group"
        title="Share on WhatsApp"
      >
        <MessageCircle className="w-4 h-4 text-slate-400 group-hover:text-green-400" />
      </button>
    );
  }

  // Card variant (full preview card)
  return (
    <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 overflow-hidden">
      {/* Property Preview */}
      <div className="p-4 border-b border-slate-700/50">
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1">
            <h4 className="font-medium text-white">
              {property?.property_title || 'Property'}
            </h4>
            {property?.locality && (
              <div className="flex items-center gap-1 text-sm text-slate-400 mt-1">
                <MapPin className="w-3 h-3" />
                <span>{property.locality}</span>
              </div>
            )}
          </div>
          
          {property?.priority && (
            <span className={`px-2 py-0.5 text-xs font-medium rounded ${getPriorityConfig(property.priority).color}`}>
              {getPriorityConfig(property.priority).label}
            </span>
          )}
        </div>
        
        <div className="flex items-center gap-4 text-sm">
          {property?.price && (
            <div className="flex items-center gap-1 text-white">
              <Wallet className="w-4 h-4 text-slate-400" />
              <span className="font-medium">{formatPrice(property.price)}</span>
            </div>
          )}
          
          {property?.status && (
            <span className={`px-2 py-0.5 text-xs rounded-full ${getStatusConfig(property.status).color}`}>
              {getStatusConfig(property.status).label}
            </span>
          )}
        </div>
        
        {property?.notes && (
          <p className="mt-3 text-sm text-slate-400 line-clamp-2">{property.notes}</p>
        )}
      </div>
      
      {/* Share Actions */}
      <div className="p-4 bg-slate-800/30">
        <div className="flex items-center gap-2 mb-3">
          <Share2 className="w-4 h-4 text-slate-400" />
          <span className="text-sm text-slate-300">Share this property</span>
        </div>
        
        {/* Share Link */}
        {shareUrl && (
          <div className="flex gap-2 mb-3">
            <input
              type="text"
              value={shareUrl}
              readOnly
              className="flex-1 px-3 py-2 bg-slate-700/50 border border-slate-600/50 rounded-lg text-sm text-slate-300 truncate"
            />
            <button
              onClick={copyToClipboard}
              className={`flex items-center gap-1 px-3 py-2 rounded-lg transition-colors ${
                copied
                  ? 'bg-green-500/20 text-green-400'
                  : 'bg-slate-700/50 text-slate-300 hover:bg-slate-700'
              }`}
            >
              {copied ? (
                <>
                  <Check className="w-4 h-4" />
                  <span className="text-sm">Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="w-4 h-4" />
                  <span className="text-sm">Copy</span>
                </>
              )}
            </button>
          </div>
        )}
        
        {/* WhatsApp Button */}
        <button
          onClick={handleShare}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-green-500 hover:bg-green-600 text-white rounded-lg transition-colors"
        >
          <MessageCircle className="w-5 h-5" />
          <span className="font-medium">Share on WhatsApp</span>
        </button>
        
        {/* Quick Share to Family */}
        <div className="mt-3 pt-3 border-t border-slate-700/50">
          <p className="text-xs text-slate-500 mb-2">Quick share to:</p>
          <div className="flex gap-2">
            <a
              href={generateWhatsAppUrl()}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-1 flex items-center justify-center gap-1 px-3 py-2 bg-slate-700/50 hover:bg-slate-700 rounded-lg text-sm text-slate-300 transition-colors"
            >
              <MessageCircle className="w-4 h-4" />
              <span>All Contacts</span>
            </a>
            <button
              onClick={copyToClipboard}
              className="flex-1 flex items-center justify-center gap-1 px-3 py-2 bg-slate-700/50 hover:bg-slate-700 rounded-lg text-sm text-slate-300 transition-colors"
            >
              <Copy className="w-4 h-4" />
              <span>Copy Link</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * WhatsAppShareButton - Simplified button component
 */
export function WhatsAppShareButton({ property, sessionName, shareUrl, onShare }) {
  return (
    <WhatsAppShare
      property={property}
      sessionName={sessionName}
      shareUrl={shareUrl}
      onShare={onShare}
      variant="button"
    />
  );
}

/**
 * WhatsAppShareCard - Full card component with preview
 */
export function WhatsAppShareCard({ property, sessionName, shareUrl, onShare }) {
  return (
    <WhatsAppShare
      property={property}
      sessionName={sessionName}
      shareUrl={shareUrl}
      onShare={onShare}
      variant="card"
    />
  );
}

/**
 * WhatsAppShareInline - Inline icon button
 */
export function WhatsAppShareInline({ property, sessionName, shareUrl, onShare }) {
  return (
    <WhatsAppShare
      property={property}
      sessionName={sessionName}
      shareUrl={shareUrl}
      onShare={onShare}
      variant="inline"
    />
  );
}

/**
 * generateWhatsAppMessage - Utility function to generate WhatsApp message
 */
export function generateWhatsAppMessage(property, sessionName, shareUrl) {
  const lines = [
    `🏠 *${property?.property_title || 'Property'}*`,
    '',
    property?.locality && `📍 Location: ${property.locality}`,
    property?.price && `💰 Price: ${formatPrice(property.price)}`,
    property?.status && `📊 Status: ${STATUS_CONFIG[property.status]?.label || property.status}`,
    '',
    `👨‍👩‍👧‍👦 ${sessionName}`,
    '',
    shareUrl && `🔗 View Details: ${shareUrl}`,
    '',
    '_Shared via Valora - Smart Property Decisions_',
  ].filter(Boolean);

  return lines.join('\n');
}

/**
 * formatPrice - Utility function to format price
 */
function formatPriceExport(price) {
  if (!price) return 'Price not specified';
  if (price >= 10000000) return `₹${(price / 10000000).toFixed(2)} Cr`;
  if (price >= 100000) return `₹${(price / 100000).toFixed(2)} L`;
  return `₹${price.toLocaleString('en-IN')}`;
}

export { formatPriceExport as formatPrice };
