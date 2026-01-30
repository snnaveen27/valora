/**
 * Valora AI - Verification Badge Component
 * 
 * Displays verification status for LLM-generated content.
 * Shows verified/unverified/partial status with appropriate warnings.
 */

import React from 'react';
import { 
  CheckCircle, 
  AlertTriangle, 
  XCircle, 
  HelpCircle,
  Info,
  Shield,
  ShieldCheck,
  ShieldAlert,
  ChevronDown,
  ChevronUp
} from 'lucide-react';

/**
 * Verification status badge
 */
export const VerificationBadge = ({ 
  status, 
  confidence = 0,
  compact = false,
  onClick = null 
}) => {
  const getStatusConfig = () => {
    switch (status) {
      case 'verified':
        return {
          icon: ShieldCheck,
          color: 'text-green-500',
          bg: 'bg-green-500/10',
          border: 'border-green-500/30',
          label: 'Verified',
          description: 'Facts verified against data sources'
        };
      case 'partially_verified':
        return {
          icon: ShieldAlert,
          color: 'text-yellow-500',
          bg: 'bg-yellow-500/10',
          border: 'border-yellow-500/30',
          label: 'Partial',
          description: 'Some claims could not be verified'
        };
      case 'unverified':
        return {
          icon: XCircle,
          color: 'text-red-500',
          bg: 'bg-red-500/10',
          border: 'border-red-500/30',
          label: 'Unverified',
          description: 'Claims do not match data sources'
        };
      case 'unable_to_verify':
        return {
          icon: HelpCircle,
          color: 'text-gray-400',
          bg: 'bg-gray-500/10',
          border: 'border-gray-500/30',
          label: 'Unknown',
          description: 'Unable to verify claims'
        };
      default:
        return {
          icon: Shield,
          color: 'text-gray-400',
          bg: 'bg-gray-500/10',
          border: 'border-gray-500/30',
          label: 'Pending',
          description: 'Verification pending'
        };
    }
  };

  const config = getStatusConfig();
  const Icon = config.icon;

  if (compact) {
    return (
      <span 
        className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium ${config.bg} ${config.color} ${config.border} border cursor-pointer`}
        onClick={onClick}
        title={config.description}
      >
        <Icon className="w-3 h-3" />
        {config.label}
      </span>
    );
  }

  return (
    <div 
      className={`flex items-center gap-2 px-3 py-1.5 rounded-lg ${config.bg} ${config.border} border cursor-pointer hover:opacity-80 transition-opacity`}
      onClick={onClick}
    >
      <Icon className={`w-4 h-4 ${config.color}`} />
      <span className={`text-sm font-medium ${config.color}`}>{config.label}</span>
      {confidence > 0 && (
        <span className="text-xs text-gray-400">({confidence}%)</span>
      )}
    </div>
  );
};

/**
 * Verification warning banner for unverified content
 */
export const VerificationWarning = ({ 
  status, 
  unverifiedCount = 0,
  totalClaims = 0,
  onViewDetails = null 
}) => {
  if (status === 'verified') return null;

  const isUnverified = status === 'unverified';
  const isPartial = status === 'partially_verified';

  return (
    <div className={`rounded-lg p-3 mb-3 ${
      isUnverified ? 'bg-red-500/10 border border-red-500/30' : 
      isPartial ? 'bg-yellow-500/10 border border-yellow-500/30' :
      'bg-gray-500/10 border border-gray-500/30'
    }`}>
      <div className="flex items-start gap-2">
        <AlertTriangle className={`w-5 h-5 mt-0.5 flex-shrink-0 ${
          isUnverified ? 'text-red-500' : 
          isPartial ? 'text-yellow-500' : 
          'text-gray-400'
        }`} />
        <div className="flex-1">
          <p className={`text-sm font-medium ${
            isUnverified ? 'text-red-400' : 
            isPartial ? 'text-yellow-400' : 
            'text-gray-400'
          }`}>
            {isUnverified ? 'Unverified Content' : 
             isPartial ? 'Partially Verified' : 
             'Verification Pending'}
          </p>
          <p className="text-xs text-gray-400 mt-1">
            {isUnverified 
              ? `${unverifiedCount} claim(s) did not match our data sources. Please verify independently.`
              : isPartial
              ? `${unverifiedCount} of ${totalClaims} claims could not be verified.`
              : 'This content has not been verified yet.'}
          </p>
          {onViewDetails && (
            <button 
              onClick={onViewDetails}
              className="text-xs text-blue-400 hover:text-blue-300 mt-2 flex items-center gap-1"
            >
              <Info className="w-3 h-3" />
              View verification details
            </button>
          )}
        </div>
      </div>
    </div>
  );
};

/**
 * Detailed verification results panel
 */
export const VerificationDetails = ({ 
  results = [], 
  isExpanded = false,
  onToggle = null 
}) => {
  const [expanded, setExpanded] = React.useState(isExpanded);

  const handleToggle = () => {
    setExpanded(!expanded);
    if (onToggle) onToggle(!expanded);
  };

  if (!results || results.length === 0) return null;

  const verifiedCount = results.filter(r => r.status === 'verified').length;
  const unverifiedCount = results.filter(r => r.status === 'unverified').length;

  return (
    <div className="bg-gray-800/50 rounded-lg border border-gray-700">
      {/* Header */}
      <button 
        onClick={handleToggle}
        className="w-full flex items-center justify-between p-3 hover:bg-gray-700/30 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Shield className="w-4 h-4 text-gray-400" />
          <span className="text-sm font-medium text-gray-300">Verification Details</span>
          <span className="text-xs text-gray-500">
            ({verifiedCount} verified, {unverifiedCount} unverified)
          </span>
        </div>
        {expanded ? (
          <ChevronUp className="w-4 h-4 text-gray-400" />
        ) : (
          <ChevronDown className="w-4 h-4 text-gray-400" />
        )}
      </button>

      {/* Details */}
      {expanded && (
        <div className="border-t border-gray-700 p-3 space-y-2">
          {results.map((result, index) => (
            <div 
              key={result.claim_id || index}
              className={`p-2 rounded ${
                result.status === 'verified' ? 'bg-green-500/5' :
                result.status === 'unverified' ? 'bg-red-500/5' :
                'bg-gray-500/5'
              }`}
            >
              <div className="flex items-start gap-2">
                {result.status === 'verified' ? (
                  <CheckCircle className="w-4 h-4 text-green-500 mt-0.5 flex-shrink-0" />
                ) : result.status === 'unverified' ? (
                  <XCircle className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
                ) : (
                  <HelpCircle className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
                )}
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-300 break-words">
                    "{result.claim_text}"
                  </p>
                  
                  {/* Evidence */}
                  {result.evidence && result.evidence.length > 0 && (
                    <div className="mt-1 text-xs text-gray-500">
                      {result.evidence.map((e, i) => (
                        <div key={i} className="flex items-center gap-1">
                          <span className="text-gray-400">{e.source}:</span>
                          <span>Expected {e.expected_value}, got {e.actual_value}</span>
                          {e.match && <CheckCircle className="w-3 h-3 text-green-500" />}
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Rewrite suggestion */}
                  {result.rewrite_suggestion && (
                    <p className="mt-1 text-xs text-yellow-400/80 italic">
                      Suggestion: {result.rewrite_suggestion}
                    </p>
                  )}
                </div>

                {/* Confidence */}
                {result.confidence > 0 && (
                  <span className="text-xs text-gray-500 flex-shrink-0">
                    {result.confidence}%
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

/**
 * Wrapper component that gates content based on verification status
 */
export const VerifiedContent = ({ 
  children, 
  verificationStatus,
  verificationResults = [],
  showWarning = true,
  allowUnverified = true,
  unverifiedMessage = "This content has not been verified and may contain inaccuracies."
}) => {
  const [showDetails, setShowDetails] = React.useState(false);

  const isVerified = verificationStatus === 'verified';
  const isPartial = verificationStatus === 'partially_verified';
  const isUnverified = verificationStatus === 'unverified';

  // If content is blocked for unverified
  if (!allowUnverified && isUnverified) {
    return (
      <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-2">
          <XCircle className="w-5 h-5 text-red-500" />
          <span className="text-red-400 font-medium">Content Unavailable</span>
        </div>
        <p className="text-sm text-gray-400">
          {unverifiedMessage}
        </p>
      </div>
    );
  }

  return (
    <div className="relative">
      {/* Verification badge */}
      <div className="absolute top-0 right-0 z-10">
        <VerificationBadge 
          status={verificationStatus}
          compact
          onClick={() => setShowDetails(!showDetails)}
        />
      </div>

      {/* Warning banner */}
      {showWarning && !isVerified && (
        <VerificationWarning
          status={verificationStatus}
          unverifiedCount={verificationResults.filter(r => r.status === 'unverified').length}
          totalClaims={verificationResults.length}
          onViewDetails={() => setShowDetails(true)}
        />
      )}

      {/* Main content */}
      <div className={`${!isVerified && showWarning ? 'pt-2' : ''}`}>
        {children}
      </div>

      {/* Verification details panel */}
      {showDetails && verificationResults.length > 0 && (
        <div className="mt-3">
          <VerificationDetails 
            results={verificationResults}
            isExpanded={true}
            onToggle={(expanded) => setShowDetails(expanded)}
          />
        </div>
      )}
    </div>
  );
};

export default VerificationBadge;
