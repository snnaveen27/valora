import React, { useState, useEffect } from 'react';
import { Database, Table, Search, Download, RefreshCw, ChevronDown, ChevronRight, Eye } from 'lucide-react';

import { API_URL } from '../apiConfig'

const DatabasePanel = () => {
  const [tables, setTables] = useState([]);
  const [selectedTable, setSelectedTable] = useState(null);
  const [tableData, setTableData] = useState([]);
  const [tableSchema, setTableSchema] = useState([]);
  const [query, setQuery] = useState('');
  const [queryResult, setQueryResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState({});
  const [limit, setLimit] = useState(50);
  const [offset, setOffset] = useState(0);
  const [expandedRows, setExpandedRows] = useState({});

  useEffect(() => {
    fetchTables();
    fetchStats();
  }, []);

  const fetchTables = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/database/tables`);
      const data = await res.json();
      if (data.success) {
        setTables(data.tables);
      }
    } catch (err) {
      console.error('Error fetching tables:', err);
    }
  };

  const fetchStats = async () => {
    try {
      const res = await fetch(`${API_BASE}/api/database/stats`);
      const data = await res.json();
      if (data.success) {
        setStats(data.stats);
      }
    } catch (err) {
      console.error('Error fetching stats:', err);
    }
  };

  const fetchTableData = async (tableName, newOffset = 0) => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(
        `${API_BASE}/api/database/table/${tableName}?limit=${limit}&offset=${newOffset}`
      );
      const data = await res.json();
      if (data.success) {
        setSelectedTable(tableName);
        setTableData(data.rows);
        setTableSchema(data.columns);
        setOffset(newOffset);
      } else {
        setError(data.error);
      }
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  };

  const executeQuery = async () => {
    if (!query.trim()) return;
    
    setLoading(true);
    setError(null);
    setQueryResult(null);
    
    try {
      const res = await fetch(`${API_BASE}/api/database/query`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query, limit: limit })
      });
      const data = await res.json();
      
      if (data.success) {
        setQueryResult(data);
      } else {
        setError(data.error);
      }
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  };

  const exportCSV = (data, columns, filename) => {
    const header = columns.join(',');
    const rows = data.map(row => 
      columns.map(col => {
        const val = row[col];
        if (val === null) return '';
        if (typeof val === 'string' && (val.includes(',') || val.includes('"'))) {
          return `"${val.replace(/"/g, '""')}"`;
        }
        return val;
      }).join(',')
    );
    const csv = [header, ...rows].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${filename}.csv`;
    a.click();
  };

  const toggleRow = (idx) => {
    setExpandedRows(prev => ({ ...prev, [idx]: !prev[idx] }));
  };

  const formatValue = (val, col) => {
    if (val === null) return <span className="text-gray-400 italic">null</span>;
    if (typeof val === 'boolean') return val ? '✓' : '✗';
    if (col.includes('data') || col.includes('json')) {
      try {
        const parsed = typeof val === 'string' ? JSON.parse(val) : val;
        return (
          <pre className="text-xs bg-gray-100 p-1 rounded max-h-32 overflow-auto">
            {JSON.stringify(parsed, null, 2).slice(0, 500)}
          </pre>
        );
      } catch {
        return String(val).slice(0, 100);
      }
    }
    if (typeof val === 'string' && val.length > 100) {
      return val.slice(0, 100) + '...';
    }
    return String(val);
  };

  const quickQueries = [
    { label: 'Properties by locality', query: "SELECT locality, COUNT(*) as count, AVG(price) as avg_price FROM properties GROUP BY locality ORDER BY count DESC LIMIT 20" },
    { label: 'Top agents', query: "SELECT name, rating, reviews_count, phone FROM real_estate_agents WHERE rating IS NOT NULL ORDER BY rating DESC LIMIT 20" },
    { label: 'POI categories', query: "SELECT category, COUNT(*) as count FROM pois GROUP BY category ORDER BY count DESC" },
    { label: 'Price history', query: "SELECT locality, snapshot_date, COUNT(*) as records, AVG(price) as avg_price FROM price_history GROUP BY locality, snapshot_date ORDER BY snapshot_date DESC LIMIT 50" },
    { label: 'Recent ingestion', query: "SELECT * FROM ingestion_log ORDER BY started_at DESC LIMIT 10" },
  ];

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <Database className="w-8 h-8 text-indigo-600" />
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Database Panel</h1>
              <p className="text-gray-500 text-sm">Explore and query Valora database</p>
            </div>
          </div>
          <button 
            onClick={() => { fetchTables(); fetchStats(); }}
            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
          {Object.entries(stats).slice(0, 8).map(([key, value]) => (
            <div key={key} className="bg-white rounded-lg shadow p-4">
              <div className="text-sm text-gray-500 capitalize">{key.replace(/_/g, ' ')}</div>
              <div className="text-2xl font-bold text-indigo-600">
                {typeof value === 'number' ? value.toLocaleString() : value}
              </div>
            </div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
          {/* Tables Sidebar */}
          <div className="bg-white rounded-lg shadow p-4">
            <h2 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
              <Table className="w-4 h-4" />
              Tables ({tables.length})
            </h2>
            <div className="space-y-1">
              {tables.map(t => (
                <button
                  key={t.name}
                  onClick={() => fetchTableData(t.name)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-sm flex justify-between items-center
                    ${selectedTable === t.name ? 'bg-indigo-100 text-indigo-700' : 'hover:bg-gray-100'}`}
                >
                  <span>{t.name}</span>
                  <span className="text-xs text-gray-500">{t.count?.toLocaleString()}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Main Content */}
          <div className="lg:col-span-3 space-y-6">
            {/* Query Box */}
            <div className="bg-white rounded-lg shadow p-4">
              <h2 className="font-semibold text-gray-800 mb-3 flex items-center gap-2">
                <Search className="w-4 h-4" />
                SQL Query
              </h2>
              
              {/* Quick Queries */}
              <div className="flex flex-wrap gap-2 mb-3">
                {quickQueries.map((q, i) => (
                  <button
                    key={i}
                    onClick={() => setQuery(q.query)}
                    className="px-2 py-1 text-xs bg-gray-100 hover:bg-gray-200 rounded"
                  >
                    {q.label}
                  </button>
                ))}
              </div>
              
              <textarea
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Enter SQL query (SELECT only)..."
                className="w-full h-24 p-3 border rounded-lg font-mono text-sm focus:ring-2 focus:ring-indigo-500"
              />
              <div className="flex items-center gap-4 mt-3">
                <button
                  onClick={executeQuery}
                  disabled={loading || !query.trim()}
                  className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50"
                >
                  {loading ? 'Running...' : 'Execute Query'}
                </button>
                <label className="flex items-center gap-2 text-sm">
                  Limit:
                  <select 
                    value={limit} 
                    onChange={(e) => setLimit(Number(e.target.value))}
                    className="border rounded px-2 py-1"
                  >
                    <option value={20}>20</option>
                    <option value={50}>50</option>
                    <option value={100}>100</option>
                    <option value={500}>500</option>
                  </select>
                </label>
              </div>
            </div>

            {/* Error Display */}
            {error && (
              <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
                {error}
              </div>
            )}

            {/* Query Results */}
            {queryResult && (
              <div className="bg-white rounded-lg shadow p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold">
                    Query Results ({queryResult.row_count} rows)
                  </h3>
                  <button
                    onClick={() => exportCSV(queryResult.rows, queryResult.columns, 'query_result')}
                    className="flex items-center gap-1 px-3 py-1 text-sm bg-green-100 text-green-700 rounded hover:bg-green-200"
                  >
                    <Download className="w-4 h-4" />
                    Export CSV
                  </button>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-gray-50">
                        {queryResult.columns.map(col => (
                          <th key={col} className="px-3 py-2 text-left font-medium text-gray-600">
                            {col}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {queryResult.rows.map((row, i) => (
                        <tr key={i} className="border-t hover:bg-gray-50">
                          {queryResult.columns.map(col => (
                            <td key={col} className="px-3 py-2">
                              {formatValue(row[col], col)}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Table Data */}
            {selectedTable && tableData.length > 0 && !queryResult && (
              <div className="bg-white rounded-lg shadow p-4">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="font-semibold">
                    {selectedTable} ({stats[selectedTable] || tableData.length} total)
                  </h3>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => fetchTableData(selectedTable, Math.max(0, offset - limit))}
                      disabled={offset === 0}
                      className="px-3 py-1 text-sm bg-gray-100 rounded disabled:opacity-50"
                    >
                      Previous
                    </button>
                    <span className="text-sm text-gray-500">
                      {offset + 1} - {offset + tableData.length}
                    </span>
                    <button
                      onClick={() => fetchTableData(selectedTable, offset + limit)}
                      disabled={tableData.length < limit}
                      className="px-3 py-1 text-sm bg-gray-100 rounded disabled:opacity-50"
                    >
                      Next
                    </button>
                    <button
                      onClick={() => exportCSV(tableData, tableSchema, selectedTable)}
                      className="flex items-center gap-1 px-3 py-1 text-sm bg-green-100 text-green-700 rounded hover:bg-green-200"
                    >
                      <Download className="w-4 h-4" />
                      CSV
                    </button>
                  </div>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-gray-50">
                        <th className="px-2 py-2 w-8"></th>
                        {tableSchema.slice(0, 8).map(col => (
                          <th key={col} className="px-3 py-2 text-left font-medium text-gray-600">
                            {col}
                          </th>
                        ))}
                        {tableSchema.length > 8 && (
                          <th className="px-3 py-2 text-gray-400">+{tableSchema.length - 8} more</th>
                        )}
                      </tr>
                    </thead>
                    <tbody>
                      {tableData.map((row, i) => (
                        <React.Fragment key={i}>
                          <tr className="border-t hover:bg-gray-50">
                            <td className="px-2 py-2">
                              <button onClick={() => toggleRow(i)}>
                                {expandedRows[i] ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                              </button>
                            </td>
                            {tableSchema.slice(0, 8).map(col => (
                              <td key={col} className="px-3 py-2 max-w-xs truncate">
                                {formatValue(row[col], col)}
                              </td>
                            ))}
                            {tableSchema.length > 8 && <td></td>}
                          </tr>
                          {expandedRows[i] && (
                            <tr className="bg-gray-50">
                              <td colSpan={tableSchema.length + 1} className="px-4 py-3">
                                <div className="grid grid-cols-2 gap-2 text-xs">
                                  {tableSchema.map(col => (
                                    <div key={col} className="flex">
                                      <span className="font-medium text-gray-600 w-32">{col}:</span>
                                      <span className="flex-1">{formatValue(row[col], col)}</span>
                                    </div>
                                  ))}
                                </div>
                              </td>
                            </tr>
                          )}
                        </React.Fragment>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DatabasePanel;
