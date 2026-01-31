import { useState } from 'react'
import { Pentagon, Circle, Trash2, Check, X, ChevronDown } from 'lucide-react'

export default function DrawingTools({ 
  isDrawing, 
  drawMode, 
  onStartPolygon, 
  onStartBuffer, 
  onClearDrawing, 
  onFinishDrawing,
  onCancelDrawing,
  bufferRadius,
  onBufferRadiusChange,
  polygonPoints
}) {
  const [showBufferInput, setShowBufferInput] = useState(false)
  const [tempRadius, setTempRadius] = useState(bufferRadius || 500)

  const handleBufferStart = () => {
    setShowBufferInput(true)
  }

  const handleBufferConfirm = () => {
    onBufferRadiusChange(tempRadius)
    onStartBuffer()
    setShowBufferInput(false)
  }

  const [isExpanded, setIsExpanded] = useState(false)

  return (
    <div className="relative">
      {/* Compact toggle button */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 px-3 py-2 bg-slate-800/95 backdrop-blur-sm text-white rounded-lg shadow-lg border border-slate-700 hover:bg-slate-700 transition-colors"
      >
        <Pentagon className="w-4 h-4" />
        <span className="text-sm font-medium">Drawing Tools</span>
        <ChevronDown className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
      </button>

      {/* Expanded tools panel */}
      {isExpanded && (
        <div className="absolute bottom-full mb-2 left-0 bg-slate-800/95 backdrop-blur-sm rounded-lg shadow-lg border border-slate-700 overflow-hidden min-w-[200px]">

          <div className="p-2 flex flex-col gap-1">
            {/* Polygon tool */}
            <button
              onClick={() => { onStartPolygon(); setIsExpanded(false); }}
              disabled={isDrawing}
              className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors ${
                drawMode === 'polygon' 
                  ? 'bg-blue-600 text-white' 
                  : 'hover:bg-slate-700 text-slate-200'
              } disabled:opacity-50 disabled:cursor-not-allowed`}
              title="Draw polygon area"
            >
              <Pentagon className="w-4 h-4" />
              <span>Draw Polygon</span>
            </button>

            {/* Buffer/Radius tool */}
            <button
              onClick={handleBufferStart}
              disabled={isDrawing}
              className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors ${
                drawMode === 'buffer' 
                  ? 'bg-blue-600 text-white' 
                  : 'hover:bg-slate-700 text-slate-200'
              } disabled:opacity-50 disabled:cursor-not-allowed`}
              title="Draw buffer radius"
            >
              <Circle className="w-4 h-4" />
              <span>Buffer Zone</span>
            </button>

            {/* Clear drawing */}
            <button
              onClick={onClearDrawing}
              className="flex items-center gap-2 px-3 py-2 rounded-md text-sm hover:bg-red-600 text-red-400 hover:text-white transition-colors"
              title="Clear drawings"
            >
              <Trash2 className="w-4 h-4" />
              <span>Clear</span>
            </button>
          </div>

          {/* Buffer radius input */}
          {showBufferInput && (
            <div className="p-3 border-t border-slate-700 bg-slate-900">
              <label className="text-xs font-medium text-slate-300 block mb-2">
                Buffer Radius (meters)
              </label>
              <div className="flex gap-2">
                <input
                  type="number"
                  value={tempRadius}
                  onChange={(e) => setTempRadius(parseInt(e.target.value) || 500)}
                  min={100}
                  max={10000}
                  step={100}
                  className="w-24 px-2 py-1 text-sm bg-slate-700 text-white border border-slate-600 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <button
                  onClick={handleBufferConfirm}
                  className="px-2 py-1 bg-blue-600 text-white rounded hover:bg-blue-700 transition-colors"
                >
                  <Check className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setShowBufferInput(false)}
                  className="px-2 py-1 bg-slate-700 text-slate-300 rounded hover:bg-slate-600 transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>
              <div className="mt-2 flex gap-1 flex-wrap">
                {[500, 1000, 2000, 5000].map(r => (
                  <button
                    key={r}
                    onClick={() => setTempRadius(r)}
                    className={`px-2 py-0.5 text-xs rounded ${
                      tempRadius === r 
                        ? 'bg-blue-600 text-white' 
                        : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                    }`}
                  >
                    {r >= 1000 ? `${r/1000}km` : `${r}m`}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Drawing instructions */}
          {isDrawing && (
            <div className="p-3 border-t border-slate-700 bg-slate-900">
              <div className="text-xs text-blue-300 mb-2">
                {drawMode === 'polygon' && (
                  <>Click to add points. Right-click to finish.</>
                )}
                {drawMode === 'buffer' && (
                  <>Click to place buffer center.</>
                )}
              </div>
              {polygonPoints > 0 && (
                <div className="text-xs text-blue-400 mb-2">
                  Points: {polygonPoints}
                </div>
              )}
              <div className="flex gap-2">
                <button
                  onClick={onFinishDrawing}
                  disabled={drawMode === 'polygon' && polygonPoints < 3}
                  className="flex-1 px-2 py-1 bg-green-600 text-white text-xs rounded hover:bg-green-700 transition-colors disabled:opacity-50"
                >
                  Finish
                </button>
                <button
                  onClick={onCancelDrawing}
                  className="flex-1 px-2 py-1 bg-slate-700 text-white text-xs rounded hover:bg-slate-600 transition-colors"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
