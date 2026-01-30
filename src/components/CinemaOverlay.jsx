import { useState, useEffect } from 'react'
import { Play, Pause, Square, Volume2, VolumeX } from 'lucide-react'

export default function CinemaOverlay({ isActive, narration, onStop, onPause, isPaused }) {
  const [progress, setProgress] = useState(0)
  const [isMuted, setIsMuted] = useState(false)

  useEffect(() => {
    if (!isActive) {
      setProgress(0)
      return
    }

    const interval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) return 0
        return prev + 0.5
      })
    }, 50)

    return () => clearInterval(interval)
  }, [isActive, isPaused])

  if (!isActive) return null

  return (
    <div className="fixed inset-0 z-[100] pointer-events-none">
      {/* Letterbox bars - cinematic effect */}
      <div className="absolute top-0 left-0 right-0 h-16 bg-gradient-to-b from-black/90 to-transparent" />
      <div className="absolute bottom-0 left-0 right-0 h-32 bg-gradient-to-t from-black/95 to-transparent" />
      
      {/* Side vignette */}
      <div className="absolute inset-0 pointer-events-none" 
        style={{
          background: 'radial-gradient(ellipse at center, transparent 50%, rgba(0,0,0,0.3) 100%)'
        }} 
      />

      {/* Narration panel - bottom center */}
      <div className="absolute bottom-8 left-1/2 -translate-x-1/2 max-w-3xl w-full px-4 pointer-events-auto">
        <div className="bg-slate-900/95 backdrop-blur-md rounded-2xl border border-white/10 shadow-2xl overflow-hidden">
          {/* Progress bar */}
          <div className="h-1 bg-slate-800">
            <div 
              className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-100"
              style={{ width: `${progress}%` }}
            />
          </div>

          <div className="p-5">
            {/* Header */}
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center">
                <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </div>
              <div>
                <div className="text-white font-semibold text-sm">Valora City Intelligence</div>
                <div className="text-slate-400 text-xs">Simulation Playback</div>
              </div>
            </div>

            {/* Narration text */}
            <p className="text-white text-base leading-relaxed mb-4 min-h-[60px]">
              {narration || "Analyzing spatial impact..."}
            </p>

            {/* Controls */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <button
                  onClick={onPause}
                  className="w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center text-white transition-colors"
                  title={isPaused ? "Resume" : "Pause"}
                >
                  {isPaused ? <Play className="w-5 h-5" /> : <Pause className="w-5 h-5" />}
                </button>
                <button
                  onClick={onStop}
                  className="w-10 h-10 rounded-full bg-white/10 hover:bg-red-500/50 flex items-center justify-center text-white transition-colors"
                  title="Stop"
                >
                  <Square className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setIsMuted(!isMuted)}
                  className="w-10 h-10 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center text-white transition-colors"
                  title={isMuted ? "Unmute" : "Mute"}
                >
                  {isMuted ? <VolumeX className="w-5 h-5" /> : <Volume2 className="w-5 h-5" />}
                </button>
              </div>

              <div className="text-slate-400 text-xs">
                Press <kbd className="px-1.5 py-0.5 bg-slate-700 rounded text-slate-300">ESC</kbd> to exit
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Cinema mode indicator - top left */}
      <div className="absolute top-4 left-4 pointer-events-auto">
        <div className="flex items-center gap-2 bg-red-500/90 backdrop-blur-sm px-3 py-1.5 rounded-full">
          <div className="w-2 h-2 bg-white rounded-full animate-pulse" />
          <span className="text-white text-xs font-medium">CINEMA MODE</span>
        </div>
      </div>
    </div>
  )
}
