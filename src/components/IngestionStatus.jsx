import React, { useState, useEffect } from 'react';

const IngestionStatus = () => {
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchStatus = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/ingestion/status');
      if (!response.ok) throw new Error('Failed to fetch status');
      const data = await response.json();
      setStatus(data);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 5000);
    return () => clearInterval(interval);
  }, []);

  const getStatusColor = (statusValue) => {
    switch (statusValue) {
      case 'running':
        return 'bg-blue-500';
      case 'completed':
        return 'bg-green-500';
      case 'completed_with_errors':
        return 'bg-yellow-500';
      case 'failed':
        return 'bg-red-500';
      case 'idle':
      default:
        return 'bg-gray-500';
    }
  };

  const getStatusIcon = (statusValue) => {
    switch (statusValue) {
      case 'running':
        return (
          <svg className="animate-spin h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
        );
      case 'completed':
        return (
          <svg className="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        );
      case 'failed':
        return (
          <svg className="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        );
      default:
        return (
          <svg className="h-5 w-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
          </svg>
        );
    }
  };

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return 'N/A';
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-3/4 mb-4"></div>
          <div className="h-4 bg-gray-200 rounded w-1/2"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="flex items-center text-red-600">
          <svg className="h-5 w-5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>Error: {error}</span>
        </div>
      </div>
    );
  }

  if (!status) return null;

  const totalItems = Object.values(status.counts || {}).reduce((sum, count) => sum + count, 0);

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold text-gray-800">Data Ingestion Status</h2>
        <button
          onClick={fetchStatus}
          className="px-3 py-1 text-sm bg-gray-100 hover:bg-gray-200 rounded-md transition-colors"
        >
          Refresh
        </button>
      </div>

      <div className="space-y-4">
        <div className="flex items-center space-x-3">
          <div className={`${getStatusColor(status.status)} rounded-full p-2`}>
            {getStatusIcon(status.status)}
          </div>
          <div>
            <div className="font-semibold text-gray-800 capitalize">
              {status.status.replace('_', ' ')}
            </div>
            <div className="text-sm text-gray-600">{status.message}</div>
          </div>
        </div>

        {status.timestamp && (
          <div className="text-sm text-gray-600">
            <span className="font-medium">Last Updated:</span> {formatTimestamp(status.timestamp)}
          </div>
        )}

        {status.category && (
          <div className="text-sm text-gray-600">
            <span className="font-medium">Current Category:</span> {status.category}
          </div>
        )}

        {status.progress && Object.keys(status.progress).length > 0 && (
          <div className="bg-gray-50 rounded-md p-3">
            <div className="text-sm font-medium text-gray-700 mb-2">Progress Details:</div>
            <div className="space-y-1 text-sm text-gray-600">
              {status.progress.run_id && (
                <div>Run ID: <span className="font-mono text-xs">{status.progress.run_id}</span></div>
              )}
              {status.progress.elapsed_seconds !== undefined && (
                <div>Elapsed: {status.progress.elapsed_seconds}s</div>
              )}
              {status.progress.items_downloaded !== undefined && (
                <div>Items Downloaded: {status.progress.items_downloaded}</div>
              )}
              {status.progress.errors && status.progress.errors.length > 0 && (
                <div className="text-red-600">
                  Errors: {status.progress.errors.length}
                  <ul className="ml-4 mt-1 list-disc">
                    {status.progress.errors.map((err, idx) => (
                      <li key={idx} className="text-xs">{err}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        )}

        {status.counts && Object.keys(status.counts).length > 0 && (
          <div className="bg-gray-50 rounded-md p-3">
            <div className="text-sm font-medium text-gray-700 mb-2">
              Items by Category (Total: {totalItems})
            </div>
            <div className="grid grid-cols-2 gap-2">
              {Object.entries(status.counts).map(([category, count]) => (
                <div key={category} className="flex justify-between text-sm">
                  <span className="text-gray-600">{category}:</span>
                  <span className="font-semibold text-gray-800">{count}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {status.status === 'idle' && (
          <div className="bg-blue-50 border border-blue-200 rounded-md p-4 mt-4">
            <div className="flex items-start">
              <svg className="h-5 w-5 text-blue-500 mt-0.5 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <div className="text-sm text-blue-800">
                <div className="font-medium mb-1">Ready to ingest data</div>
                <div>Run the ingestion script to start scraping property data from Apify.</div>
                <code className="block mt-2 bg-blue-100 px-2 py-1 rounded text-xs">
                  cd scripts/ingest && python apify_to_json.py
                </code>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default IngestionStatus;
