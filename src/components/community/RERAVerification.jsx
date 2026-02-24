/**
 * RERAVerification - RERA status badge component
 * 
 * Features:
 * - RERA ID input for verification
 * - Status display (verified/not_found/pending)
 * - Project details if verified
 * - Last verified timestamp
 * - Refresh button
 * 
 * Props:
 * @param {string[]} [reraIds] - Array of RERA IDs (for builder profiles)
 * @param {string} [builderName] - Builder name (for builder profiles)
 * @param {string} [singleReraId] - Single RERA ID (for standalone verification)
 * @param {boolean} [compact] - Compact display mode
 * @param {boolean} [showInput] - Show RERA ID input field
 * @param {function} [onVerified] - Callback when RERA is verified
 */

import { useState, useEffect, useCallback } from 'react';
import {
  Shield,
  Search,
  RefreshCw,
  CheckCircle,
  XCircle,
  Clock,
  AlertCircle,
  Loader2,
  MapPin,
  Calendar,
  Building2,
  Info,
} from 'lucide-react';

import { verifyRera, refreshRera } from '../../services/reviewApi';

// Status configurations
const STATUS_CONFIG = {
  verified: {
    icon: CheckCircle,
    color: 'text-green-400',
    bgColor: 'bg-green-500/10',
    borderColor: 'border-green-500/30',
    label: 'Verified',
  },
  not_found: {
    icon: XCircle,
    color: 'text-red-400',
    bgColor: 'bg-red-500/10',
    borderColor: 'border-red-500/30',
    label: 'Not Found',
  },
  pending: {
    icon: Clock,
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-500/10',
    borderColor: 'border-yellow-500/30',
    label: 'Pending',
  },
  error: {
    icon: AlertCircle,
    color: 'text-gray-400',
    bgColor: 'bg-gray-500/10',
    borderColor: 'border-gray-500/30',
    label: 'Error',
  },
};

// Single RERA verification result
function RERACard({ verification, onRefresh, isRefreshing }) {
  const status = STATUS_CONFIG[verification.verification_status] || STATUS_CONFIG.error;
  const StatusIcon = status.icon;

  const formatDate = (dateString) => {
    if (!dateString) return null;
    const date = new Date(dateString);
    return date.toLocaleDateString('en-IN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className={`p-4 rounded-lg border ${status.bgColor} ${status.borderColor}`}>
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <StatusIcon size={20} className={status.color} />
          <span className={`font-medium ${status.color}`}>{status.label}</span>
        </div>
        <button
          onClick={() => onRefresh(verification.rera_id)}
          disabled={isRefreshing}
          className="p-1.5 hover:bg-gray-700/50 rounded-lg transition-colors disabled:opacity-50"
        >
          {isRefreshing ? (
            <Loader2 size={16} className="text-gray-400 animate-spin" />
          ) : (
            <RefreshCw size={16} className="text-gray-400" />
          )}
        </button>
      </div>

      {/* RERA ID */}
      <div className="text-sm font-mono text-gray-300 mb-3">
        RERA ID: {verification.rera_id}
      </div>

      {/* Verified Details */}
      {verification.verification_status === 'verified' && (
        <div className="space-y-2 text-sm">
          {verification.project_name && (
            <div className="flex items-start gap-2">
              <Building2 size={14} className="text-gray-500 mt-0.5 flex-shrink-0" />
              <div>
                <span className="text-gray-400">Project: </span>
                <span className="text-white">{verification.project_name}</span>
              </div>
            </div>
          )}
          
          {verification.builder_name && (
            <div className="flex items-start gap-2">
              <Shield size={14} className="text-gray-500 mt-0.5 flex-shrink-0" />
              <div>
                <span className="text-gray-400">Builder: </span>
                <span className="text-white">{verification.builder_name}</span>
              </div>
            </div>
          )}

          {verification.state && (
            <div className="flex items-start gap-2">
              <MapPin size={14} className="text-gray-500 mt-0.5 flex-shrink-0" />
              <div>
                <span className="text-gray-400">State: </span>
                <span className="text-white">{verification.state}</span>
              </div>
            </div>
          )}

          {verification.project_status && (
            <div className="flex items-start gap-2">
              <Clock size={14} className="text-gray-500 mt-0.5 flex-shrink-0" />
              <div>
                <span className="text-gray-400">Status: </span>
                <span className="text-white">{verification.project_status}</span>
              </div>
            </div>
          )}

          {verification.registration_date && (
            <div className="flex items-start gap-2">
              <Calendar size={14} className="text-gray-500 mt-0.5 flex-shrink-0" />
              <div>
                <span className="text-gray-400">Registered: </span>
                <span className="text-white">{formatDate(verification.registration_date)}</span>
              </div>
            </div>
          )}

          {verification.expiry_date && (
            <div className="flex items-start gap-2">
              <Calendar size={14} className="text-gray-500 mt-0.5 flex-shrink-0" />
              <div>
                <span className="text-gray-400">Valid Until: </span>
                <span className="text-white">{formatDate(verification.expiry_date)}</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Last Verified */}
      {verification.last_verified_at && (
        <div className="mt-3 pt-3 border-t border-gray-700/50 text-xs text-gray-500">
          Last verified: {formatDate(verification.last_verified_at)}
        </div>
      )}
    </div>
  );
}

// Compact badge version
function RERACompactBadge({ verification }) {
  const status = STATUS_CONFIG[verification.verification_status] || STATUS_CONFIG.error;
  const StatusIcon = status.icon;

  return (
    <div className="flex items-center gap-2">
      <StatusIcon size={16} className={status.color} />
      <span className={`text-sm font-medium ${status.color}`}>{status.label}</span>
      {verification.verification_status === 'verified' && verification.project_name && (
        <span className="text-sm text-gray-400">- {verification.project_name}</span>
      )}
    </div>
  );
}

export default function RERAVerification({
  reraIds,
  builderName,
  singleReraId,
  compact = false,
  showInput = false,
  onVerified,
}) {
  const [inputReraId, setInputReraId] = useState(singleReraId || '');
  const [verifications, setVerifications] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState(null);

  // Verify a single RERA ID
  const verifyReraId = useCallback(async (reraId) => {
    if (!reraId) return;
    
    setIsLoading(true);
    setError(null);
    
    try {
      const result = await verifyRera(reraId);
      
      // Update verifications state
      setVerifications((prev) => {
        const existing = prev.findIndex((v) => v.rera_id === reraId);
        if (existing >= 0) {
          const updated = [...prev];
          updated[existing] = result;
          return updated;
        }
        return [...prev, result];
      });
      
      onVerified?.(result);
    } catch (err) {
      setError(err.message);
      console.error('RERA verification failed:', err);
    } finally {
      setIsLoading(false);
    }
  }, [onVerified]);

  // Initial verification of provided RERA IDs
  useEffect(() => {
    if (reraIds?.length > 0) {
      // Verify all RERA IDs
      reraIds.forEach((id) => verifyReraId(id));
    } else if (singleReraId) {
      verifyReraId(singleReraId);
    }
  }, [reraIds, singleReraId]);

  // Handle refresh
  const handleRefresh = async (reraId) => {
    setIsRefreshing(true);
    try {
      const result = await refreshRera(reraId);
      setVerifications((prev) =>
        prev.map((v) => (v.rera_id === reraId ? result : v))
      );
    } catch (err) {
      console.error('RERA refresh failed:', err);
    } finally {
      setIsRefreshing(false);
    }
  };

  // Handle form submission
  const handleSubmit = (e) => {
    e.preventDefault();
    if (inputReraId.trim()) {
      verifyReraId(inputReraId.trim().toUpperCase());
      setInputReraId('');
    }
  };

  // Compact mode - show badges for each RERA
  if (compact) {
    return (
      <div className="space-y-2">
        {verifications.length > 0 ? (
          verifications.map((verification) => (
            <RERACompactBadge key={verification.rera_id} verification={verification} />
          ))
        ) : reraIds?.length > 0 ? (
          <div className="flex items-center gap-2">
            <Loader2 size={16} className="text-gray-400 animate-spin" />
            <span className="text-sm text-gray-400">Verifying RERA IDs...</span>
          </div>
        ) : null}
      </div>
    );
  }

  // Full mode
  return (
    <div className="space-y-4">
      {/* Input Form */}
      {showInput && (
        <form onSubmit={handleSubmit} className="flex gap-2">
          <div className="flex-1 relative">
            <Search
              size={18}
              className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
            />
            <input
              type="text"
              value={inputReraId}
              onChange={(e) => setInputReraId(e.target.value)}
              placeholder="Enter RERA ID (e.g., PRM/KA/RERA/2023/1234)"
              className="w-full bg-gray-800 border border-gray-600 text-white text-sm rounded-lg pl-10 pr-3 py-2 focus:outline-none focus:border-blue-500"
            />
          </div>
          <button
            type="submit"
            disabled={isLoading || !inputReraId.trim()}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed text-white rounded-lg transition-colors flex items-center gap-2"
          >
            {isLoading ? (
              <Loader2 size={18} className="animate-spin" />
            ) : (
              <Shield size={18} />
            )}
            <span>Verify</span>
          </button>
        </form>
      )}

      {/* Error Message */}
      {error && (
        <div className="flex items-center gap-2 p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Verification Results */}
      {verifications.length > 0 && (
        <div className="space-y-3">
          {verifications.map((verification) => (
            <RERACard
              key={verification.rera_id}
              verification={verification}
              onRefresh={handleRefresh}
              isRefreshing={isRefreshing}
            />
          ))}
        </div>
      )}

      {/* Empty State */}
      {!showInput && verifications.length === 0 && reraIds?.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          <Shield size={32} className="mx-auto mb-2 opacity-50" />
          <p>No RERA information available</p>
        </div>
      )}

      {/* Info Box */}
      {showInput && verifications.length === 0 && !isLoading && (
        <div className="flex items-start gap-2 p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg">
          <Info size={16} className="text-blue-400 mt-0.5 flex-shrink-0" />
          <div className="text-xs text-gray-400">
            <span className="text-blue-300 font-medium">RERA Verification: </span>
            Enter a RERA registration ID to verify the project and builder registration status.
            RERA (Real Estate Regulatory Authority) registration ensures legal compliance of real estate projects.
          </div>
        </div>
      )}
    </div>
  );
}
