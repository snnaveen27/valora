import React, { useState } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'

export default function ComponentErrorBoundary({ children, fallback, name = 'Component' }) {
  const [hasError, setHasError] = useState(false)
  const [error, setError] = useState(null)

  if (hasError) {
    if (fallback) {
      return fallback(error, () => {
        setHasError(false)
        setError(null)
      })
    }

    return (
      <div className="flex flex-col items-center justify-center h-full min-h-[200px] bg-slate-900/50 border border-red-500/30 rounded-lg p-6">
        <AlertTriangle className="w-8 h-8 text-red-500 mb-3" />
        <h3 className="text-sm font-semibold text-red-400 mb-1">{name} Error</h3>
        <p className="text-xs text-gray-400 text-center max-w-xs mb-3">
          {error?.message || 'Something went wrong. Please try again.'}
        </p>
        <button
          onClick={() => {
            setHasError(false)
            setError(null)
          }}
          className="flex items-center gap-2 px-3 py-1.5 text-xs bg-blue-500/20 text-blue-400 rounded hover:bg-blue-500/30 transition-colors"
        >
          <RefreshCw className="w-3 h-3" />
          Retry
        </button>
      </div>
    )
  }

  return (
    <ErrorCatcher
      onError={(err) => {
        setHasError(true)
        setError(err)
      }}
    >
      {children}
    </ErrorCatcher>
  )
}

class ErrorCatcher extends React.Component {
  componentDidCatch(error) {
    this.props.onError(error)
  }

  render() {
    return this.props.children
  }
}
