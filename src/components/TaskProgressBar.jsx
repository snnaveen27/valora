/**
 * TaskProgressBar - Shows progress of report generation task
 * Displays circular progress, current tab, completed tabs, and download buttons
 */

import React, { useState, useEffect, useCallback } from 'react';
import { API_URL } from '../apiConfig';
import {
  Loader2, CheckCircle, XCircle, Download, FileText,
  FileDown, X, Clock, AlertTriangle, ChevronDown, ChevronUp
} from 'lucide-react';

// Tab display names
const TAB_NAMES = {
  'decision_verdict': 'Decision Verdict',
  'market_snapshot': 'Market Snapshot',
  'spatial_intelligence': 'Spatial Intelligence',
  'risk_analysis': 'Risk Analysis',
  'roi_projection': 'ROI Projection',
  'comparables': 'Comparables',
  'strategy': 'Strategy',
  'data_transparency': 'Data Transparency',
  'client_pitch': 'Client Pitch'
};

export default function TaskProgressBar({
  taskId,
  onComplete,
  onCancel,
  autoClose = false,
  showDetails = true
}) {
  const [task, setTask] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expanded, setExpanded] = useState(true);
  const [downloading, setDownloading] = useState(null);

  // Poll task status
  const fetchTaskStatus = useCallback(async () => {
    if (!taskId) return;

    try {
      const response = await fetch(`${API_URL}/api/smart-report/task/${taskId}`);
      
      if (!response.ok) {
        throw new Error('Task not found');
      }
      
      const data = await response.json();
      setTask(data);
      setLoading(false);
      
      // Check if completed
      if (data.status === 'completed' && onComplete) {
        onComplete(data);
      }
      
      // Check if failed
      if (data.status === 'failed') {
        setError(data.error || 'Task failed');
      }
      
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  }, [taskId, onComplete]);

  // Poll every 2 seconds while processing
  useEffect(() => {
    if (!taskId) return;
    
    fetchTaskStatus();
    
    const interval = setInterval(() => {
      if (task?.status === 'processing' || task?.status === 'pending') {
        fetchTaskStatus();
      }
    }, 2000);
    
    return () => clearInterval(interval);
  }, [taskId, task?.status, fetchTaskStatus]);

  // Handle cancel
  const handleCancel = async () => {
    if (!taskId || task?.status !== 'processing') return;
    
    try {
      const response = await fetch(`${API_URL}/api/smart-report/cancel/${taskId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      
      if (response.ok) {
        const data = await response.json();
        setTask(prev => ({ ...prev, status: 'cancelled', ...data }));
        if (onCancel) onCancel(data);
      }
    } catch (err) {
      console.error('Failed to cancel task:', err);
    }
  };

  // Handle download
  const handleDownload = async (type) => {
    if (!taskId) return;
    
    setDownloading(type);
    try {
      const response = await fetch(`${API_URL}/api/smart-report/download/${type}/${taskId}`);
      
      if (!response.ok) {
        throw new Error('Download failed');
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      
      // Get filename from Content-Disposition header or use default
      const contentDisposition = response.headers.get('Content-Disposition');
      let filename = `Valora_Report.${type === 'pdf' ? 'pdf' : 'md'}`;
      if (contentDisposition) {
        const match = contentDisposition.match(/filename="?(.+)"?/);
        if (match) filename = match[1];
      }
      
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      
    } catch (err) {
      console.error('Download failed:', err);
      alert('Download failed. Please try again.');
    } finally {
      setDownloading(null);
    }
  };

  // Calculate progress
  const progress = task?.progress || {};
  const percentage = progress.percentage || 0;
  const currentTab = progress.current_tab || '';
  const completedTabs = progress.completed_tabs || [];
  const totalTabs = progress.total || 9;
  const currentStep = progress.current || 0;
  const estimatedTime = progress.estimated_remaining_seconds;

  // Status colors and icons
  const getStatusDisplay = () => {
    switch (task?.status) {
      case 'pending':
        return { color: 'text-yellow-400', bg: 'bg-yellow-500/20', icon: Clock, text: 'Starting...' };
      case 'processing':
        return { color: 'text-blue-400', bg: 'bg-blue-500/20', icon: Loader2, text: 'Processing' };
      case 'completed':
        return { color: 'text-green-400', bg: 'bg-green-500/20', icon: CheckCircle, text: 'Complete' };
      case 'failed':
        return { color: 'text-red-400', bg: 'bg-red-500/20', icon: XCircle, text: 'Failed' };
      case 'cancelled':
        return { color: 'text-orange-400', bg: 'bg-orange-500/20', icon: X, text: 'Cancelled' };
      default:
        return { color: 'text-slate-400', bg: 'bg-slate-500/20', icon: Clock, text: 'Unknown' };
    }
  };

  const statusDisplay = getStatusDisplay();
  const StatusIcon = statusDisplay.icon;

  if (loading) {
    return (
      <div className="bg-slate-800/50 rounded-lg p-3 border border-slate-700">
        <div className="flex items-center gap-2 text-slate-400">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span className="text-sm">Loading task status...</span>
        </div>
      </div>
    );
  }

  if (error && !task) {
    return (
      <div className="bg-red-500/10 rounded-lg p-3 border border-red-500/30">
        <div className="flex items-center gap-2 text-red-400">
          <AlertTriangle className="w-4 h-4" />
          <span className="text-sm">{error}</span>
        </div>
      </div>
    );
  }

  return (
    <div className={`rounded-lg border transition-all ${
      task?.status === 'completed' ? 'bg-green-500/10 border-green-500/30' :
      task?.status === 'failed' ? 'bg-red-500/10 border-red-500/30' :
      task?.status === 'cancelled' ? 'bg-orange-500/10 border-orange-500/30' :
      'bg-blue-500/10 border-blue-500/30'
    }`}>
      {/* Header */}
      <div className="p-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          {/* Circular Progress */}
          <div className="relative w-10 h-10">
            <svg className="w-10 h-10 transform -rotate-90">
              {/* Background circle */}
              <circle
                cx="20"
                cy="20"
                r="16"
                stroke="currentColor"
                strokeWidth="3"
                fill="none"
                className="text-slate-700"
              />
              {/* Progress circle */}
              <circle
                cx="20"
                cy="20"
                r="16"
                stroke="currentColor"
                strokeWidth="3"
                fill="none"
                strokeDasharray={`${percentage} 100`}
                className={
                  task?.status === 'completed' ? 'text-green-400' :
                  task?.status === 'failed' ? 'text-red-400' :
                  'text-blue-400'
                }
              />
            </svg>
            {/* Percentage or icon in center */}
            <div className="absolute inset-0 flex items-center justify-center">
              {task?.status === 'completed' ? (
                <CheckCircle className="w-5 h-5 text-green-400" />
              ) : task?.status === 'failed' ? (
                <XCircle className="w-5 h-5 text-red-400" />
              ) : (
                <span className="text-xs font-bold text-white">{Math.round(percentage)}%</span>
              )}
            </div>
          </div>

          {/* Status text */}
          <div>
            <div className={`flex items-center gap-1.5 ${statusDisplay.color}`}>
              <StatusIcon className={`w-4 h-4 ${task?.status === 'processing' ? 'animate-spin' : ''}`} />
              <span className="font-medium text-sm">{statusDisplay.text}</span>
            </div>
            {task?.status === 'processing' && currentTab && (
              <p className="text-xs text-slate-400 mt-0.5">
                Processing: {TAB_NAMES[currentTab] || currentTab}
              </p>
            )}
            {task?.status === 'completed' && (
              <p className="text-xs text-green-300 mt-0.5">
                Report ready for download
              </p>
            )}
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2">
          {/* Cancel button (only while processing) */}
          {task?.status === 'processing' && (
            <button
              onClick={handleCancel}
              className="px-2 py-1 text-xs bg-red-500/20 hover:bg-red-500/30 text-red-400 rounded transition"
            >
              Cancel
            </button>
          )}

          {/* Download buttons (only when completed) */}
          {task?.status === 'completed' && (
            <div className="flex gap-1">
              <button
                onClick={() => handleDownload('md')}
                disabled={downloading !== null}
                className="flex items-center gap-1 px-2 py-1 text-xs bg-slate-600 hover:bg-slate-500 text-white rounded transition disabled:opacity-50"
              >
                {downloading === 'md' ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <FileText className="w-3 h-3" />
                )}
                MD
              </button>
              <button
                onClick={() => handleDownload('pdf')}
                disabled={downloading !== null}
                className="flex items-center gap-1 px-2 py-1 text-xs bg-blue-600 hover:bg-blue-500 text-white rounded transition disabled:opacity-50"
              >
                {downloading === 'pdf' ? (
                  <Loader2 className="w-3 h-3 animate-spin" />
                ) : (
                  <FileDown className="w-3 h-3" />
                )}
                PDF
              </button>
            </div>
          )}

          {/* Expand/collapse */}
          {showDetails && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="p-1 hover:bg-slate-700/50 rounded transition"
            >
              {expanded ? (
                <ChevronUp className="w-4 h-4 text-slate-400" />
              ) : (
                <ChevronDown className="w-4 h-4 text-slate-400" />
              )}
            </button>
          )}
        </div>
      </div>

      {/* Expanded details */}
      {expanded && showDetails && (
        <div className="px-3 pb-3 border-t border-slate-700/50 pt-2">
          {/* Progress bar */}
          <div className="mb-3">
            <div className="flex justify-between text-xs text-slate-400 mb-1">
              <span>{currentStep} of {totalTabs} tabs</span>
              {estimatedTime && estimatedTime > 0 && task?.status === 'processing' && (
                <span>~{Math.ceil(estimatedTime / 60)} min remaining</span>
              )}
            </div>
            <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-300 ${
                  task?.status === 'completed' ? 'bg-green-500' :
                  task?.status === 'failed' ? 'bg-red-500' :
                  'bg-blue-500'
                }`}
                style={{ width: `${percentage}%` }}
              />
            </div>
          </div>

          {/* Tab checklist */}
          <div className="grid grid-cols-3 gap-1">
            {Object.entries(TAB_NAMES).map(([tabId, tabName]) => {
              const isCompleted = completedTabs.includes(tabId);
              const isCurrent = currentTab === tabId;
              
              return (
                <div
                  key={tabId}
                  className={`flex items-center gap-1 px-2 py-1 rounded text-xs ${
                    isCompleted ? 'bg-green-500/20 text-green-400' :
                    isCurrent ? 'bg-blue-500/20 text-blue-400' :
                    'bg-slate-700/30 text-slate-500'
                  }`}
                >
                  {isCompleted ? (
                    <CheckCircle className="w-3 h-3" />
                  ) : isCurrent ? (
                    <Loader2 className="w-3 h-3 animate-spin" />
                  ) : (
                    <div className="w-3 h-3 rounded-full border border-current opacity-50" />
                  )}
                  <span className="truncate">{tabName}</span>
                </div>
              );
            })}
          </div>

          {/* Error message */}
          {task?.status === 'failed' && task?.error && (
            <div className="mt-2 p-2 bg-red-500/10 rounded text-xs text-red-400">
              {task.error}
            </div>
          )}

          {/* Credits info */}
          {task?.credits_charged > 0 && (
            <div className="mt-2 text-xs text-slate-500">
              Credits charged: {task.credits_charged}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
