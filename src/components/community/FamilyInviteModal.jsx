/**
 * FamilyInviteModal - Member invitation modal for Family Hub
 * 
 * Features:
 * - Input fields: name, email, phone, role
 * - Invite link generation and copy functionality
 * - WhatsApp share button (deep link integration)
 * - Member list display
 * - Responsive layout
 * 
 * Props:
 * @param {boolean} isOpen - Whether the modal is open
 * @param {function} onClose - Callback to close the modal
 * @param {string} sessionId - Current session ID
 * @param {string} sessionName - Current session name for display
 */

import { useState, useEffect } from 'react';
import {
  XCircle,
  UserPlus,
  Mail,
  Phone,
  Shield,
  Copy,
  Check,
  Loader2,
  AlertCircle,
  Users,
  Trash2,
  MessageCircle,
  Share2,
  Clock,
} from 'lucide-react';

import { 
  inviteMember, 
  getMembers, 
  removeMember,
  generateShareLink,
} from '../../services/familyApi';

// Role options
const ROLE_OPTIONS = [
  { id: 'admin', label: 'Admin', description: 'Can manage members and settings' },
  { id: 'member', label: 'Member', description: 'Can add properties and vote' },
  { id: 'viewer', label: 'Viewer', description: 'Can only view, not edit' },
];

// Role badge colors
const ROLE_COLORS = {
  owner: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  admin: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  member: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  viewer: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
};

// Invite status colors
const STATUS_COLORS = {
  pending: 'bg-orange-500/20 text-orange-400',
  accepted: 'bg-green-500/20 text-green-400',
  declined: 'bg-red-500/20 text-red-400',
};

// Initial form state
const INITIAL_FORM = {
  name: '',
  email: '',
  phone: '',
  role: 'member',
};

export default function FamilyInviteModal({ isOpen, onClose, sessionId, sessionName }) {
  // Form state
  const [form, setForm] = useState(INITIAL_FORM);
  const [errors, setErrors] = useState({});
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  const [submitSuccess, setSubmitSuccess] = useState(null);
  
  // Members state
  const [members, setMembers] = useState([]);
  const [isLoadingMembers, setIsLoadingMembers] = useState(false);
  
  // Share link state
  const [shareLink, setShareLink] = useState(null);
  const [isGeneratingLink, setIsGeneratingLink] = useState(false);
  const [copiedLink, setCopiedLink] = useState(false);
  const [copiedInvite, setCopiedInvite] = useState(false);

  // Reset form when modal opens
  useEffect(() => {
    if (isOpen && sessionId) {
      setForm(INITIAL_FORM);
      setErrors({});
      setSubmitError(null);
      setSubmitSuccess(null);
      setCopiedLink(false);
      setCopiedInvite(false);
      loadMembers();
      generateNewShareLink();
    }
  }, [isOpen, sessionId]);

  /**
   * Load members for the current session
   */
  const loadMembers = async () => {
    setIsLoadingMembers(true);
    try {
      const data = await getMembers(sessionId);
      setMembers(data || []);
    } catch (err) {
      console.error('[FamilyInviteModal] Failed to load members:', err);
    } finally {
      setIsLoadingMembers(false);
    }
  };

  /**
   * Generate a new share link
   */
  const generateNewShareLink = async () => {
    setIsGeneratingLink(true);
    try {
      const data = await generateShareLink(sessionId, { expiry_hours: 72 });
      setShareLink(data);
    } catch (err) {
      console.error('[FamilyInviteModal] Failed to generate share link:', err);
    } finally {
      setIsGeneratingLink(false);
    }
  };

  /**
   * Validate form fields
   */
  const validateForm = () => {
    const newErrors = {};
    
    if (!form.name.trim()) {
      newErrors.name = 'Name is required';
    } else if (form.name.length > 100) {
      newErrors.name = 'Name must be 100 characters or less';
    }
    
    // At least one contact method required
    if (!form.email.trim() && !form.phone.trim()) {
      newErrors.contact = 'Email or phone is required';
    }
    
    if (form.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
      newErrors.email = 'Invalid email format';
    }
    
    if (form.phone && !/^[0-9]{10}$/.test(form.phone.replace(/\D/g, ''))) {
      newErrors.phone = 'Phone must be 10 digits';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  /**
   * Handle input change
   */
  const handleChange = (field, value) => {
    setForm(prev => ({ ...prev, [field]: value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: null }));
    }
    if (errors.contact) {
      setErrors(prev => ({ ...prev, contact: null }));
    }
  };

  /**
   * Handle form submission
   */
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!validateForm()) return;
    
    setIsSubmitting(true);
    setSubmitError(null);
    setSubmitSuccess(null);
    
    try {
      const inviteData = {
        name: form.name.trim(),
        email: form.email.trim() || null,
        phone: form.phone.trim() || null,
        role: form.role,
      };
      
      const result = await inviteMember(sessionId, inviteData);
      
      setSubmitSuccess(`Invitation sent to ${form.email || form.phone}!`);
      setForm(INITIAL_FORM);
      loadMembers(); // Refresh member list
    } catch (err) {
      console.error('[FamilyInviteModal] Failed to send invite:', err);
      setSubmitError(err.message || 'Failed to send invitation. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  /**
   * Handle member removal
   */
  const handleRemoveMember = async (memberId) => {
    try {
      await removeMember(sessionId, memberId);
      setMembers(prev => prev.filter(m => m.id !== memberId));
    } catch (err) {
      console.error('[FamilyInviteModal] Failed to remove member:', err);
      setSubmitError('Failed to remove member.');
    }
  };

  /**
   * Copy text to clipboard
   */
  const copyToClipboard = async (text, type) => {
    try {
      await navigator.clipboard.writeText(text);
      if (type === 'link') {
        setCopiedLink(true);
        setTimeout(() => setCopiedLink(false), 2000);
      } else {
        setCopiedInvite(true);
        setTimeout(() => setCopiedInvite(false), 2000);
      }
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  /**
   * Generate WhatsApp share URL
   */
  const getWhatsAppUrl = () => {
    if (!shareLink) return '#';
    
    const message = encodeURIComponent(
      `🏠 Join our family property search on Valora!\n\n` +
      `Family: ${sessionName}\n` +
      `Click to join: ${shareLink.share_url}\n\n` +
      `Valora - Smart Property Decisions`
    );
    
    return `https://wa.me/?text=${message}`;
  };

  /**
   * Format date for display
   */
  const formatDate = (dateStr) => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('en-IN', {
      day: 'numeric',
      month: 'short',
      year: 'numeric',
    });
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="relative w-full max-w-2xl max-h-[90vh] bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 rounded-2xl shadow-2xl border border-slate-700/50 overflow-hidden">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-700/50 bg-slate-800/50">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-500/20 rounded-lg">
              <UserPlus className="w-5 h-5 text-purple-400" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-white">Invite Family Members</h3>
              <p className="text-sm text-slate-400">{sessionName}</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 hover:bg-slate-700/50 rounded-lg transition-colors"
          >
            <XCircle className="w-5 h-5 text-slate-400" />
          </button>
        </div>

        <div className="overflow-y-auto max-h-[calc(90vh-80px)]">
          {/* Share Link Section */}
          <div className="px-6 py-4 border-b border-slate-700/50 bg-slate-800/30">
            <h4 className="text-sm font-medium text-slate-300 mb-3 flex items-center gap-2">
              <Share2 className="w-4 h-4" />
              Share Invite Link
            </h4>
            
            <div className="flex gap-2">
              <div className="flex-1 relative">
                <input
                  type="text"
                  value={shareLink?.share_url || 'Generating...'}
                  readOnly
                  className="w-full px-4 py-2.5 bg-slate-700/50 border border-slate-600/50 rounded-lg text-slate-300 text-sm"
                />
                {shareLink?.expires_at && (
                  <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1 text-xs text-slate-500">
                    <Clock className="w-3 h-3" />
                    <span>Expires in 72h</span>
                  </div>
                )}
              </div>
              <button
                onClick={() => copyToClipboard(shareLink?.share_url, 'link')}
                disabled={!shareLink}
                className="flex items-center gap-2 px-4 py-2.5 bg-slate-700/50 hover:bg-slate-700 border border-slate-600/50 rounded-lg text-slate-300 transition-colors disabled:opacity-50"
              >
                {copiedLink ? (
                  <>
                    <Check className="w-4 h-4 text-green-400" />
                    <span className="hidden sm:inline">Copied!</span>
                  </>
                ) : (
                  <>
                    <Copy className="w-4 h-4" />
                    <span className="hidden sm:inline">Copy</span>
                  </>
                )}
              </button>
              <a
                href={getWhatsAppUrl()}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-2 px-4 py-2.5 bg-green-500/20 hover:bg-green-500/30 border border-green-500/30 rounded-lg text-green-400 transition-colors"
              >
                <MessageCircle className="w-4 h-4" />
                <span className="hidden sm:inline">WhatsApp</span>
              </a>
            </div>
          </div>

          {/* Invite Form */}
          <form onSubmit={handleSubmit} className="px-6 py-4 space-y-4 border-b border-slate-700/50">
            <h4 className="text-sm font-medium text-slate-300 flex items-center gap-2">
              <Mail className="w-4 h-4" />
              Send Personal Invitation
            </h4>
            
            {/* Success Message */}
            {submitSuccess && (
              <div className="p-3 bg-green-500/20 border border-green-500/30 rounded-lg flex items-center gap-2">
                <Check className="w-4 h-4 text-green-400" />
                <p className="text-sm text-green-400">{submitSuccess}</p>
              </div>
            )}
            
            {/* Error Message */}
            {submitError && (
              <div className="p-3 bg-red-500/20 border border-red-500/30 rounded-lg flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-red-400" />
                <p className="text-sm text-red-400">{submitError}</p>
              </div>
            )}
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {/* Name */}
              <div>
                <label className="block text-sm text-slate-400 mb-1">
                  Name <span className="text-red-400">*</span>
                </label>
                <input
                  type="text"
                  value={form.name}
                  onChange={(e) => handleChange('name', e.target.value)}
                  placeholder="Enter name"
                  className={`w-full px-4 py-2.5 bg-slate-700/50 border rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50 ${
                    errors.name ? 'border-red-500/50' : 'border-slate-600/50'
                  }`}
                />
                {errors.name && (
                  <p className="mt-1 text-xs text-red-400">{errors.name}</p>
                )}
              </div>
              
              {/* Role */}
              <div>
                <label className="block text-sm text-slate-400 mb-1">
                  Role
                </label>
                <select
                  value={form.role}
                  onChange={(e) => handleChange('role', e.target.value)}
                  className="w-full px-4 py-2.5 bg-slate-700/50 border border-slate-600/50 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                >
                  {ROLE_OPTIONS.map(role => (
                    <option key={role.id} value={role.id}>
                      {role.label}
                    </option>
                  ))}
                </select>
              </div>
              
              {/* Email */}
              <div>
                <label className="block text-sm text-slate-400 mb-1">
                  Email
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <input
                    type="email"
                    value={form.email}
                    onChange={(e) => handleChange('email', e.target.value)}
                    placeholder="email@example.com"
                    className={`w-full pl-10 pr-4 py-2.5 bg-slate-700/50 border rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50 ${
                      errors.email ? 'border-red-500/50' : 'border-slate-600/50'
                    }`}
                  />
                </div>
                {errors.email && (
                  <p className="mt-1 text-xs text-red-400">{errors.email}</p>
                )}
              </div>
              
              {/* Phone */}
              <div>
                <label className="block text-sm text-slate-400 mb-1">
                  Phone
                </label>
                <div className="relative">
                  <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <input
                    type="tel"
                    value={form.phone}
                    onChange={(e) => handleChange('phone', e.target.value)}
                    placeholder="10-digit number"
                    className={`w-full pl-10 pr-4 py-2.5 bg-slate-700/50 border rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50 ${
                      errors.phone ? 'border-red-500/50' : 'border-slate-600/50'
                    }`}
                  />
                </div>
                {errors.phone && (
                  <p className="mt-1 text-xs text-red-400">{errors.phone}</p>
                )}
              </div>
            </div>
            
            {errors.contact && (
              <p className="text-xs text-red-400">{errors.contact}</p>
            )}
            
            {/* Submit Button */}
            <button
              type="submit"
              disabled={isSubmitting}
              className={`w-full flex items-center justify-center gap-2 px-6 py-3 rounded-lg font-medium transition-colors ${
                isSubmitting
                  ? 'bg-purple-500/50 text-purple-200 cursor-not-allowed'
                  : 'bg-purple-500 hover:bg-purple-600 text-white'
              }`}
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="w-5 h-5 animate-spin" />
                  <span>Sending...</span>
                </>
              ) : (
                <>
                  <UserPlus className="w-5 h-5" />
                  <span>Send Invitation</span>
                </>
              )}
            </button>
          </form>

          {/* Members List */}
          <div className="px-6 py-4">
            <h4 className="text-sm font-medium text-slate-300 mb-3 flex items-center gap-2">
              <Users className="w-4 h-4" />
              Current Members ({members.length})
            </h4>
            
            {isLoadingMembers ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-6 h-6 text-purple-400 animate-spin" />
              </div>
            ) : members.length === 0 ? (
              <p className="text-center text-slate-500 py-4">No members yet</p>
            ) : (
              <div className="space-y-2">
                {members.map(member => (
                  <div
                    key={member.id}
                    className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg border border-slate-700/50"
                  >
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-purple-500/20 flex items-center justify-center">
                        <span className="text-purple-400 font-medium">
                          {member.name?.charAt(0)?.toUpperCase() || '?'}
                        </span>
                      </div>
                      <div>
                        <p className="font-medium text-white">{member.name}</p>
                        <div className="flex items-center gap-2 text-sm text-slate-400">
                          <span className={`px-2 py-0.5 text-xs rounded-full border ${ROLE_COLORS[member.role] || ROLE_COLORS.member}`}>
                            {member.role}
                          </span>
                          {member.invite_status !== 'accepted' && (
                            <span className={`px-2 py-0.5 text-xs rounded-full ${STATUS_COLORS[member.invite_status] || STATUS_COLORS.pending}`}>
                              {member.invite_status}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                    
                    {/* Remove Button (not for owners) */}
                    {member.role !== 'owner' && (
                      <button
                        onClick={() => handleRemoveMember(member.id)}
                        className="p-2 hover:bg-red-500/20 rounded-lg transition-colors group"
                        title="Remove member"
                      >
                        <Trash2 className="w-4 h-4 text-slate-400 group-hover:text-red-400" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
