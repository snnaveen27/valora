import { useState } from 'react'
import { Pentagon, Circle, Trash2, Check, X } from 'lucide-react'

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

  return (
    <div className="absolute top-4 left-4 z-40">
      <div className="bg-white/95 backdrop-blur-sm rounded-lg shadow-lg border border-gray-200/50 overflow-hidden">
        {/* Drawing tools header */}
        <div className="px-3 py-2 bg-slate-50 border-b border-gray-200">
          <span className="text-xs font-semibold text-slate-600 uppercase tracking-wide">
            Drawing Tools
          </span>
        </div>

        <div className="p-2 flex flex-col gap-1">
          {/* Polygon tool */}
          <button
            onClick={onStartPolygon}
            disabled={isDrawing}
            className={`flex items-center gap-2 px-3 py-2 rounded-md text-sm transition-colors ${
              drawMode === 'polygon' 
                ? 'bg-blue-500 text-white' 
                : 'hover:bg-gray-100 text-gray-700'
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
                ? 'bg-blue-500 text-white' 
                : 'hover:bg-gray-100 text-gray-700'
            } disabled:opacity-50 disabled:cursor-not-allowed`}
            title="Draw buffer radius"
          >
            <Circle className="w-4 h-4" />
            <span>Buffer Zone</span>
          </button>

          {/* Clear drawing */}
          <button
            onClick={onClearDrawing}
            className="flex items-center gap-2 px-3 py-2 rounded-md text-sm hover:bg-red-50 text-red-600 transition-colors"
            title="Clear drawings"
          >
            <Trash2 className="w-4 h-4" />
            <span>Clear</span>
          </button>
        </div>

        {/* Buffer radius input */}
        {showBufferInput && (
          <div className="p-3 border-t border-gray-200 bg-slate-50">
            <label className="text-xs font-medium text-slate-600 block mb-2">
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
                className="w-24 px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                onClick={handleBufferConfirm}
                className="px-2 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
              >
                <Check className="w-4 h-4" />
              </button>
              <button
                onClick={() => setShowBufferInput(false)}
                className="px-2 py-1 bg-gray-200 text-gray-600 rounded hover:bg-gray-300 transition-colors"
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
                      ? 'bg-blue-500 text-white' 
                      : 'bg-gray-200 text-gray-600 hover:bg-gray-300'
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
          <div className="p-3 border-t border-gray-200 bg-blue-50">
            <div className="text-xs text-blue-800 mb-2">
              {drawMode === 'polygon' && (
                <>Click to add points. Right-click or press Enter to finish.</>
              )}
              {drawMode === 'buffer' && (
                <>Click to place buffer center.</>
              )}
            </div>
            {polygonPoints > 0 && (
              <div className="text-xs text-blue-600 mb-2">
                Points: {polygonPoints}
              </div>
            )}
            <div className="flex gap-2">
              <button
                onClick={onFinishDrawing}
                disabled={drawMode === 'polygon' && polygonPoints < 3}
                className="flex-1 px-2 py-1 bg-green-500 text-white text-xs rounded hover:bg-green-600 transition-colors disabled:opacity-50"
              >
                Finish
              </button>
              <button
                onClick={onCancelDrawing}
                className="flex-1 px-2 py-1 bg-gray-500 text-white text-xs rounded hover:bg-gray-600 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
