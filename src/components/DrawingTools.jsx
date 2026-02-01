import { useState } from 'react'
import { Pentagon, Circle, Trash2, Check, X, ChevronDown, Ruler, Square, MapPin, Move } from 'lucide-react'

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
  const [isExpanded, setIsExpanded] = useState(false)

  const handleBufferStart = () => {
    setShowBufferInput(true)
  }

  const handleBufferConfirm = () => {
    onBufferRadiusChange(tempRadius)
    onStartBuffer()
    setShowBufferInput(false)
  }

  const tools = [
    { id: 'polygon', icon: Pentagon, label: 'Polygon', desc: 'Draw custom area', action: onStartPolygon },
    { id: 'rectangle', icon: Square, label: 'Rectangle', desc: 'Quick rectangular area', action: onStartPolygon },
    { id: 'buffer', icon: Circle, label: 'Buffer', desc: 'Radius around point', action: handleBufferStart },
    { id: 'measure', icon: Ruler, label: 'Measure', desc: 'Distance & area', action: onStartPolygon },
    { id: 'marker', icon: MapPin, label: 'Marker', desc: 'Add point of interest', action: onStartPolygon }
  ]

  return (
    <div className="relative">
      {/* Ultra-compact toggle */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className={`flex items-center gap-1.5 px-2 py-0.5 text-slate-300 hover:text-white hover:bg-slate-800 transition ${
          isDrawing ? 'text-blue-400' : ''
        }`}
      >
        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
        </svg>
        <span className="text-[10px] font-medium">Draw</span>
        <ChevronDown className={`w-3 h-3 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
      </button>

      {/* Modern tools panel */}
      {isExpanded && (
        <div className="absolute bottom-full mb-1 left-0 bg-slate-900 border border-slate-700 shadow-2xl overflow-hidden min-w-[240px] z-50">
          
          {/* Tool grid */}
          <div className="p-2">
            <div className="grid grid-cols-2 gap-1">
              {tools.map(tool => (
                <button
                  key={tool.id}
                  onClick={() => { tool.action(); if (tool.id !== 'buffer') setIsExpanded(false); }}
                  disabled={isDrawing && drawMode !== tool.id}
                  className={`flex flex-col items-center gap-1 p-2 transition group ${
                    drawMode === tool.id 
                      ? 'bg-blue-600/20 border border-blue-500' 
                      : 'hover:bg-slate-800 border border-transparent'
                  } disabled:opacity-40`}
                  title={tool.desc}
                >
                  <tool.icon className={`w-4 h-4 ${drawMode === tool.id ? 'text-blue-400' : 'text-slate-400 group-hover:text-white'}`} />
                  <span className={`text-[9px] font-medium ${drawMode === tool.id ? 'text-blue-300' : 'text-slate-400 group-hover:text-white'}`}>
                    {tool.label}
                  </span>
                </button>
              ))}
              
              {/* Clear button */}
              <button
                onClick={onClearDrawing}
                className="flex flex-col items-center gap-1 p-2 hover:bg-red-600/20 border border-transparent hover:border-red-500/30 transition group"
                title="Clear all drawings"
              >
                <Trash2 className="w-4 h-4 text-red-400 group-hover:text-red-300" />
                <span className="text-[9px] font-medium text-red-400 group-hover:text-red-300">Clear</span>
              </button>
            </div>
          </div>

          {/* Buffer radius config */}
          {showBufferInput && (
            <div className="p-2 border-t border-slate-700/50 bg-slate-950/50">
              <div className="text-[9px] text-slate-400 mb-1.5">Radius (meters)</div>
              <div className="flex gap-1 mb-1.5">
                <input
                  type="number"
                  value={tempRadius}
                  onChange={(e) => setTempRadius(parseInt(e.target.value) || 500)}
                  min={100}
                  max={10000}
                  step={100}
                  className="flex-1 px-2 py-1 text-xs bg-slate-800 text-white border border-slate-600 focus:outline-none focus:border-blue-500"
                />
                <button
                  onClick={handleBufferConfirm}
                  className="px-2 bg-blue-600 text-white hover:bg-blue-700 transition"
                >
                  <Check className="w-3 h-3" />
                </button>
                <button
                  onClick={() => setShowBufferInput(false)}
                  className="px-2 bg-slate-700 text-slate-300 hover:bg-slate-600 transition"
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
              <div className="flex gap-1">
                {[500, 1000, 2000, 5000].map(r => (
                  <button
                    key={r}
                    onClick={() => setTempRadius(r)}
                    className={`flex-1 px-1.5 py-0.5 text-[9px] transition ${
                      tempRadius === r 
                        ? 'bg-blue-600 text-white' 
                        : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
                    }`}
                  >
                    {r >= 1000 ? `${r/1000}km` : `${r}m`}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Active drawing status */}
          {isDrawing && (
            <div className="p-2 border-t border-slate-700/50 bg-blue-950/20">
              <div className="flex items-center gap-2 mb-1.5">
                <div className="w-1.5 h-1.5 bg-blue-400 rounded-full animate-pulse"></div>
                <span className="text-[9px] text-blue-300 font-medium">
                  {drawMode === 'polygon' && 'Click to add points • Right-click to finish'}
                  {drawMode === 'buffer' && 'Click to place buffer center'}
                  {drawMode === 'measure' && 'Click points to measure'}
                  {drawMode === 'marker' && 'Click to place marker'}
                </span>
              </div>
              {polygonPoints > 0 && (
                <div className="text-[9px] text-slate-400 mb-1.5">
                  {polygonPoints} point{polygonPoints !== 1 ? 's' : ''}
                </div>
              )}
              <div className="flex gap-1">
                <button
                  onClick={onFinishDrawing}
                  disabled={drawMode === 'polygon' && polygonPoints < 3}
                  className="flex-1 px-2 py-1 bg-green-600 text-white text-[9px] font-medium hover:bg-green-700 transition disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  Finish
                </button>
                <button
                  onClick={onCancelDrawing}
                  className="flex-1 px-2 py-1 bg-slate-700 text-white text-[9px] font-medium hover:bg-slate-600 transition"
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
