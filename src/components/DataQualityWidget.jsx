import { useState } from 'react'
import { 
  Database, Clock, AlertTriangle, CheckCircle, Info, 
  ChevronDown, ChevronUp, Server, Layers, FileText
} from 'lucide-react'

// Quality indicator bar
function QualityBar({ quality, label }) {
  const getColor = (q) => {
    if (q >= 80) return 'bg-green-500'
    if (q >= 60) return 'bg-yellow-500'
    return 'bg-red-500'
  }
  
  return (
    <div className="flex items-center gap-2">
      <span className="text-[9px] text-slate-400 w-20">{label}</span>
      <div className="flex-1 h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div 
          className={`h-full ${getColor(quality)} transition-all duration-500`}
          style={{ width: `${quality}%` }}
        />
      </div>
      <span className={`text-[9px] font-medium w-8 text-right ${
        quality >= 80 ? 'text-green-400' : quality >= 60 ? 'text-yellow-400' : 'text-red-400'
      }`}>{quality}%</span>
    </div>
  )
}

// Missing features list
function MissingFeatures({ features, expanded }) {
  if (!expanded || !features || features.length === 0) return null
  
  return (
    <div className="mt-2 p-2 bg-red-500/10 rounded border border-red-500/20">
      <div className="text-[9px] text-red-400 mb-1 flex items-center gap-1">
        <AlertTriangle className="w-2.5 h-2.5" />
        Missing/Low-Confidence Features:
      </div>
      <div className="flex flex-wrap gap-1">
        {features.map((f, i) => (
          <span key={i} className="text-[8px] bg-red-500/20 text-red-300 px-1.5 py-0.5 rounded">
            {f}
          </span>
        ))}
      </div>
    </div>
  )
}

export default function DataQualityWidget({ 
  dataStats = {},
  vectorBackend = 'FAISS',
  lastUpdated = new Date().toISOString()
}) {
  const [expanded, setExpanded] = useState(false)
  
  // Default stats
  const stats = {
    properties: dataStats.properties || 12450,
    pois: dataStats.pois || 8920,
    transactions: dataStats.transactions || 45600,
    buildings: dataStats.buildings || 156000,
    terrainCells: dataStats.terrainCells || 25000,
    ...dataStats
  }
  
  // Data freshness calculation
  const lastUpdate = new Date(lastUpdated)
  const hoursSinceUpdate = Math.floor((Date.now() - lastUpdate.getTime()) / (1000 * 60 * 60))
  const freshnessLabel = hoursSinceUpdate < 1 ? 'Just now' : 
                         hoursSinceUpdate < 24 ? `${hoursSinceUpdate}h ago` :
                         `${Math.floor(hoursSinceUpdate / 24)}d ago`
  
  // Quality scores
  const overallQuality = dataStats.overallQuality || 82
  const spatialCoverage = dataStats.spatialCoverage || 88
  const temporalCoverage = dataStats.temporalCoverage || 75
  const attributeCompleteness = dataStats.attributeCompleteness || 79
  
  // Missing features
  const missingFeatures = dataStats.missingFeatures || [
    'rental_history',
    'crime_index',
    'noise_levels',
    'air_quality'
  ]
  
  return (
    <div className="bg-slate-800/40 rounded-xl p-3 border border-slate-700/50 max-w-2xl mx-auto">
      {/* Header */}
      <div 
        className="flex items-center justify-between cursor-pointer flex-wrap gap-2"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2">
          <Database className="w-3.5 h-3.5 text-slate-400" />
          <span className="text-slate-400 font-medium text-[9px] uppercase">Data Quality</span>
          <span className={`flex items-center gap-0.5 text-[9px] px-1.5 py-0.5 rounded ${
            overallQuality >= 80 ? 'bg-green-500/20 text-green-400' :
            overallQuality >= 60 ? 'bg-yellow-500/20 text-yellow-400' :
            'bg-red-500/20 text-red-400'
          }`}>
            {overallQuality >= 80 ? <CheckCircle className="w-2.5 h-2.5" /> : <AlertTriangle className="w-2.5 h-2.5" />}
            {overallQuality}%
          </span>
        </div>
        
        <div className="flex items-center gap-2">
          <span className="text-[9px] text-slate-500 flex items-center gap-1">
            <Clock className="w-2.5 h-2.5" />
            {freshnessLabel}
          </span>
          {expanded ? <ChevronUp className="w-3 h-3 text-slate-500" /> : <ChevronDown className="w-3 h-3 text-slate-500" />}
        </div>
      </div>
      
      {expanded && (
        <div className="mt-3 space-y-3">
          {/* Data counts */}
          <div className="grid grid-cols-3 gap-2">
            <div className="bg-slate-900/50 rounded p-1.5 text-center">
              <div className="text-white font-bold text-sm">{(stats.properties / 1000).toFixed(1)}k</div>
              <div className="text-[8px] text-slate-500">Properties</div>
            </div>
            <div className="bg-slate-900/50 rounded p-1.5 text-center">
              <div className="text-white font-bold text-sm">{(stats.pois / 1000).toFixed(1)}k</div>
              <div className="text-[8px] text-slate-500">POIs</div>
            </div>
            <div className="bg-slate-900/50 rounded p-1.5 text-center">
              <div className="text-white font-bold text-sm">{(stats.buildings / 1000).toFixed(0)}k</div>
              <div className="text-[8px] text-slate-500">Buildings</div>
            </div>
          </div>
          
          {/* Quality breakdown */}
          <div className="space-y-1.5">
            <QualityBar quality={spatialCoverage} label="Spatial" />
            <QualityBar quality={temporalCoverage} label="Temporal" />
            <QualityBar quality={attributeCompleteness} label="Attributes" />
          </div>
          
          {/* Backend info */}
          <div className="flex items-center justify-between text-[9px] py-2 border-t border-slate-700/50">
            <div className="flex items-center gap-1 text-slate-400">
              <Server className="w-2.5 h-2.5" />
              Vector Backend:
              <span className="text-slate-300 font-medium">{vectorBackend}</span>
            </div>
            <div className="flex items-center gap-1 text-slate-400">
              <Layers className="w-2.5 h-2.5" />
              Embeddings:
              <span className="text-slate-300 font-medium">384-dim</span>
            </div>
          </div>
          
          {/* Missing features */}
          <MissingFeatures features={missingFeatures} expanded={true} />
          
          {/* Provenance note */}
          <div className="text-[8px] text-slate-500 flex items-start gap-1">
            <Info className="w-2.5 h-2.5 mt-0.5 flex-shrink-0" />
            <span>
              Data sources: OSM extracts, property portals (Magic Bricks, 99acres), 
              government registrations. Last full sync: {lastUpdate.toLocaleDateString()}.
            </span>
          </div>
        </div>
      )}
    </div>
  )
}
