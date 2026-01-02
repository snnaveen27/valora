import { useState, useRef, useEffect, Suspense } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import { OrbitControls, PerspectiveCamera, Environment, Html, Text, useGLTF } from '@react-three/drei'
import { 
  Building2, Layers, Eye, EyeOff, RotateCcw, ZoomIn, ZoomOut, 
  Sun, Moon, Maximize2, X, Home, DollarSign, TrendingUp, 
  Thermometer, Droplets, Wind, Info, ChevronDown, ChevronUp
} from 'lucide-react'
import * as THREE from 'three'

// Building Floor Component
function BuildingFloor({ position, size, floorNumber, isSelected, onClick, floorData, showLabels }) {
  const meshRef = useRef()
  const [hovered, setHovered] = useState(false)
  
  const getFloorColor = () => {
    if (isSelected) return '#3b82f6'
    if (hovered) return '#60a5fa'
    
    // Color based on occupancy or price
    if (floorData?.occupancy > 0.9) return '#22c55e'
    if (floorData?.occupancy > 0.7) return '#84cc16'
    if (floorData?.occupancy > 0.5) return '#eab308'
    return '#94a3b8'
  }
  
  return (
    <group position={position}>
      <mesh
        ref={meshRef}
        onClick={(e) => { e.stopPropagation(); onClick(floorNumber) }}
        onPointerOver={(e) => { e.stopPropagation(); setHovered(true) }}
        onPointerOut={() => setHovered(false)}
      >
        <boxGeometry args={[size.width, size.height, size.depth]} />
        <meshStandardMaterial 
          color={getFloorColor()} 
          transparent 
          opacity={isSelected ? 1 : 0.85}
          metalness={0.1}
          roughness={0.6}
        />
      </mesh>
      
      {/* Floor edges */}
      <lineSegments>
        <edgesGeometry args={[new THREE.BoxGeometry(size.width, size.height, size.depth)]} />
        <lineBasicMaterial color="#1e293b" linewidth={1} />
      </lineSegments>
      
      {/* Floor label */}
      {showLabels && (
        <Html position={[size.width / 2 + 0.5, 0, 0]} center>
          <div className="bg-slate-800/90 text-white text-xs px-2 py-1 rounded whitespace-nowrap">
            Floor {floorNumber}
          </div>
        </Html>
      )}
    </group>
  )
}

// Building Component
function Building({ buildingData, selectedFloor, onFloorSelect, showLabels, viewMode }) {
  const groupRef = useRef()
  const { floors = 10, width = 4, depth = 4, floorHeight = 0.4, gap = 0.05 } = buildingData
  
  useFrame((state) => {
    if (viewMode === 'rotate') {
      groupRef.current.rotation.y += 0.002
    }
  })
  
  const floorComponents = []
  for (let i = 0; i < floors; i++) {
    const yPos = i * (floorHeight + gap)
    floorComponents.push(
      <BuildingFloor
        key={i}
        position={[0, yPos, 0]}
        size={{ width, height: floorHeight, depth }}
        floorNumber={i + 1}
        isSelected={selectedFloor === i + 1}
        onClick={onFloorSelect}
        floorData={buildingData.floorData?.[i]}
        showLabels={showLabels}
      />
    )
  }
  
  return (
    <group ref={groupRef} position={[0, -floors * (floorHeight + gap) / 2, 0]}>
      {/* Ground plane */}
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.1, 0]}>
        <planeGeometry args={[20, 20]} />
        <meshStandardMaterial color="#1e3a5f" transparent opacity={0.5} />
      </mesh>
      
      {/* Building base */}
      <mesh position={[0, -0.15, 0]}>
        <boxGeometry args={[width + 0.5, 0.1, depth + 0.5]} />
        <meshStandardMaterial color="#334155" />
      </mesh>
      
      {/* Floors */}
      {floorComponents}
      
      {/* Roof */}
      <mesh position={[0, floors * (floorHeight + gap) + 0.1, 0]}>
        <boxGeometry args={[width + 0.2, 0.1, depth + 0.2]} />
        <meshStandardMaterial color="#475569" />
      </mesh>
      
      {/* Building name label */}
      {showLabels && buildingData.name && (
        <Html position={[0, floors * (floorHeight + gap) + 1, 0]} center>
          <div className="bg-blue-500/90 text-white text-sm font-medium px-3 py-1.5 rounded-lg shadow-lg">
            {buildingData.name}
          </div>
        </Html>
      )}
    </group>
  )
}

// Camera Controls
function CameraController({ resetTrigger }) {
  const { camera } = useThree()
  
  useEffect(() => {
    if (resetTrigger > 0) {
      camera.position.set(8, 6, 8)
      camera.lookAt(0, 0, 0)
    }
  }, [resetTrigger, camera])
  
  return null
}

// Scene lighting based on time of day
function SceneLighting({ timeOfDay }) {
  const lightIntensity = timeOfDay === 'day' ? 1 : 0.3
  const ambientIntensity = timeOfDay === 'day' ? 0.5 : 0.2
  
  return (
    <>
      <ambientLight intensity={ambientIntensity} />
      <directionalLight 
        position={timeOfDay === 'day' ? [10, 10, 5] : [-5, 3, -5]} 
        intensity={lightIntensity} 
        castShadow 
      />
      <pointLight position={[-10, 10, -10]} intensity={0.3} />
      {timeOfDay === 'night' && (
        <>
          <pointLight position={[0, 2, 0]} intensity={0.5} color="#fbbf24" />
          <pointLight position={[3, 1, 3]} intensity={0.3} color="#60a5fa" />
        </>
      )}
    </>
  )
}

// Floor Details Panel
function FloorDetailsPanel({ floorNumber, floorData, onClose }) {
  if (!floorNumber) return null
  
  const data = floorData || {
    units: 4,
    occupancy: 0.75,
    avgPrice: 8500000,
    avgRent: 35000,
    amenities: ['Balcony', 'Parking', 'Gym Access'],
    unitTypes: ['2BHK', '3BHK']
  }
  
  return (
    <div className="absolute top-4 right-4 w-72 bg-slate-800/95 backdrop-blur-sm rounded-xl border border-slate-700 shadow-2xl overflow-hidden z-10">
      <div className="p-4 border-b border-slate-700 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Layers className="w-5 h-5 text-blue-400" />
          <h3 className="text-white font-semibold">Floor {floorNumber}</h3>
        </div>
        <button onClick={onClose} className="p-1 hover:bg-slate-700 rounded">
          <X className="w-4 h-4 text-slate-400" />
        </button>
      </div>
      
      <div className="p-4 space-y-4">
        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-3">
          <div className="bg-slate-700/50 rounded-lg p-3">
            <p className="text-slate-400 text-xs">Units</p>
            <p className="text-white font-bold text-lg">{data.units}</p>
          </div>
          <div className="bg-slate-700/50 rounded-lg p-3">
            <p className="text-slate-400 text-xs">Occupancy</p>
            <p className="text-green-400 font-bold text-lg">{Math.round(data.occupancy * 100)}%</p>
          </div>
          <div className="bg-slate-700/50 rounded-lg p-3">
            <p className="text-slate-400 text-xs">Avg Price</p>
            <p className="text-white font-bold">₹{(data.avgPrice / 100000).toFixed(1)}L</p>
          </div>
          <div className="bg-slate-700/50 rounded-lg p-3">
            <p className="text-slate-400 text-xs">Avg Rent</p>
            <p className="text-white font-bold">₹{(data.avgRent / 1000).toFixed(0)}K</p>
          </div>
        </div>
        
        {/* Unit Types */}
        <div>
          <p className="text-slate-400 text-xs mb-2">Unit Types</p>
          <div className="flex gap-2">
            {data.unitTypes.map((type, i) => (
              <span key={i} className="px-2 py-1 bg-blue-500/20 text-blue-400 text-xs rounded">
                {type}
              </span>
            ))}
          </div>
        </div>
        
        {/* Amenities */}
        <div>
          <p className="text-slate-400 text-xs mb-2">Amenities</p>
          <div className="flex flex-wrap gap-2">
            {data.amenities.map((amenity, i) => (
              <span key={i} className="px-2 py-1 bg-slate-700 text-slate-300 text-xs rounded">
                {amenity}
              </span>
            ))}
          </div>
        </div>
        
        {/* View Unit Button */}
        <button className="w-full py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg text-sm font-medium transition">
          View Available Units
        </button>
      </div>
    </div>
  )
}

// Building Info Panel
function BuildingInfoPanel({ buildingData, isExpanded, onToggle }) {
  return (
    <div className="absolute top-4 left-4 w-64 bg-slate-800/95 backdrop-blur-sm rounded-xl border border-slate-700 shadow-2xl overflow-hidden z-10">
      <div 
        className="p-4 border-b border-slate-700 flex items-center justify-between cursor-pointer"
        onClick={onToggle}
      >
        <div className="flex items-center gap-2">
          <Building2 className="w-5 h-5 text-blue-400" />
          <h3 className="text-white font-semibold">{buildingData.name || 'Building Info'}</h3>
        </div>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-slate-400" />
        ) : (
          <ChevronDown className="w-4 h-4 text-slate-400" />
        )}
      </div>
      
      {isExpanded && (
        <div className="p-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-slate-400 text-sm">Total Floors</span>
            <span className="text-white font-medium">{buildingData.floors}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-400 text-sm">Total Units</span>
            <span className="text-white font-medium">{buildingData.totalUnits || buildingData.floors * 4}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-400 text-sm">Avg Price/sqft</span>
            <span className="text-white font-medium">₹{buildingData.pricePerSqft?.toLocaleString() || '8,500'}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-400 text-sm">Year Built</span>
            <span className="text-white font-medium">{buildingData.yearBuilt || '2022'}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-400 text-sm">Occupancy</span>
            <span className="text-green-400 font-medium">{buildingData.occupancy || '85'}%</span>
          </div>
          
          <div className="pt-2 border-t border-slate-700">
            <p className="text-slate-400 text-xs mb-2">Environmental</p>
            <div className="grid grid-cols-3 gap-2">
              <div className="text-center p-2 bg-slate-700/50 rounded">
                <Thermometer className="w-4 h-4 text-orange-400 mx-auto mb-1" />
                <p className="text-white text-xs">{buildingData.temperature || '26'}°C</p>
              </div>
              <div className="text-center p-2 bg-slate-700/50 rounded">
                <Droplets className="w-4 h-4 text-blue-400 mx-auto mb-1" />
                <p className="text-white text-xs">{buildingData.humidity || '65'}%</p>
              </div>
              <div className="text-center p-2 bg-slate-700/50 rounded">
                <Wind className="w-4 h-4 text-cyan-400 mx-auto mb-1" />
                <p className="text-white text-xs">{buildingData.aqi || '45'} AQI</p>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// Main Digital Twin Viewer Component
export default function DigitalTwinViewer({ 
  property = null, 
  isOpen = false, 
  onClose = () => {},
  embedded = false
}) {
  const [selectedFloor, setSelectedFloor] = useState(null)
  const [showLabels, setShowLabels] = useState(true)
  const [viewMode, setViewMode] = useState('static') // 'static', 'rotate'
  const [timeOfDay, setTimeOfDay] = useState('day')
  const [resetCamera, setResetCamera] = useState(0)
  const [showBuildingInfo, setShowBuildingInfo] = useState(true)
  
  // Default building data (can be overridden by property prop)
  const buildingData = property ? {
    name: property.name || property.title || 'Property',
    floors: property.floors || 12,
    width: 4,
    depth: 4,
    floorHeight: 0.4,
    totalUnits: property.totalUnits || 48,
    pricePerSqft: property.pricePerSqft || 8500,
    yearBuilt: property.yearBuilt || 2022,
    occupancy: property.occupancy || 85,
    floorData: Array.from({ length: property.floors || 12 }, (_, i) => ({
      units: 4,
      occupancy: 0.6 + Math.random() * 0.4,
      avgPrice: 7500000 + i * 250000,
      avgRent: 30000 + i * 2000,
      amenities: i > 8 ? ['Balcony', 'Premium View', 'Parking'] : ['Balcony', 'Parking'],
      unitTypes: i > 6 ? ['3BHK', '4BHK'] : ['2BHK', '3BHK']
    }))
  } : {
    name: 'Prestige Lakeside Habitat',
    floors: 15,
    width: 4,
    depth: 4,
    floorHeight: 0.4,
    totalUnits: 60,
    pricePerSqft: 9200,
    yearBuilt: 2023,
    occupancy: 78,
    temperature: 27,
    humidity: 62,
    aqi: 52,
    floorData: Array.from({ length: 15 }, (_, i) => ({
      units: 4,
      occupancy: 0.5 + Math.random() * 0.5,
      avgPrice: 8500000 + i * 300000,
      avgRent: 35000 + i * 2500,
      amenities: i > 10 ? ['Balcony', 'Premium View', 'Private Terrace'] : ['Balcony', 'Parking'],
      unitTypes: i > 8 ? ['3BHK', '4BHK', 'Penthouse'] : ['2BHK', '3BHK']
    }))
  }
  
  const containerClass = embedded 
    ? "w-full h-full bg-gradient-to-b from-slate-900 to-slate-800 rounded-xl overflow-hidden"
    : "fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center"
  
  const viewerClass = embedded
    ? "w-full h-full relative"
    : "w-[90vw] h-[85vh] bg-gradient-to-b from-slate-900 to-slate-800 rounded-2xl overflow-hidden relative shadow-2xl"
  
  if (!isOpen && !embedded) return null
  
  return (
    <div className={containerClass}>
      <div className={viewerClass}>
        {/* Header */}
        <div className="absolute top-0 left-0 right-0 h-12 bg-slate-900/80 backdrop-blur-sm border-b border-slate-700 flex items-center justify-between px-4 z-20">
          <div className="flex items-center gap-3">
            <Building2 className="w-5 h-5 text-blue-400" />
            <h2 className="text-white font-semibold">Digital Twin Viewer</h2>
            <span className="text-slate-400 text-sm">• {buildingData.name}</span>
          </div>
          
          <div className="flex items-center gap-2">
            {/* View controls */}
            <button
              onClick={() => setShowLabels(!showLabels)}
              className={`p-2 rounded-lg transition ${showLabels ? 'bg-blue-500/20 text-blue-400' : 'text-slate-400 hover:bg-slate-700'}`}
              title="Toggle Labels"
            >
              {showLabels ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
            </button>
            
            <button
              onClick={() => setViewMode(viewMode === 'static' ? 'rotate' : 'static')}
              className={`p-2 rounded-lg transition ${viewMode === 'rotate' ? 'bg-blue-500/20 text-blue-400' : 'text-slate-400 hover:bg-slate-700'}`}
              title="Auto Rotate"
            >
              <RotateCcw className="w-4 h-4" />
            </button>
            
            <button
              onClick={() => setTimeOfDay(timeOfDay === 'day' ? 'night' : 'day')}
              className="p-2 text-slate-400 hover:bg-slate-700 rounded-lg transition"
              title="Toggle Day/Night"
            >
              {timeOfDay === 'day' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>
            
            <button
              onClick={() => setResetCamera(prev => prev + 1)}
              className="p-2 text-slate-400 hover:bg-slate-700 rounded-lg transition"
              title="Reset Camera"
            >
              <Home className="w-4 h-4" />
            </button>
            
            {!embedded && (
              <button
                onClick={onClose}
                className="p-2 text-slate-400 hover:bg-red-500/20 hover:text-red-400 rounded-lg transition ml-2"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
        
        {/* 3D Canvas */}
        <div className="absolute inset-0 pt-12">
          <Canvas shadows>
            <CameraController resetTrigger={resetCamera} />
            <PerspectiveCamera makeDefault position={[8, 6, 8]} fov={50} />
            <OrbitControls 
              enablePan={true}
              enableZoom={true}
              enableRotate={true}
              minDistance={5}
              maxDistance={25}
              maxPolarAngle={Math.PI / 2.1}
            />
            
            <SceneLighting timeOfDay={timeOfDay} />
            
            <Suspense fallback={null}>
              <Building 
                buildingData={buildingData}
                selectedFloor={selectedFloor}
                onFloorSelect={setSelectedFloor}
                showLabels={showLabels}
                viewMode={viewMode}
              />
            </Suspense>
            
            {/* Sky/Environment */}
            <color attach="background" args={[timeOfDay === 'day' ? '#0f172a' : '#020617']} />
            <fog attach="fog" args={[timeOfDay === 'day' ? '#0f172a' : '#020617', 15, 35]} />
          </Canvas>
        </div>
        
        {/* Building Info Panel */}
        <BuildingInfoPanel 
          buildingData={buildingData}
          isExpanded={showBuildingInfo}
          onToggle={() => setShowBuildingInfo(!showBuildingInfo)}
        />
        
        {/* Floor Details Panel */}
        <FloorDetailsPanel 
          floorNumber={selectedFloor}
          floorData={buildingData.floorData?.[selectedFloor - 1]}
          onClose={() => setSelectedFloor(null)}
        />
        
        {/* Floor Legend */}
        <div className="absolute bottom-4 left-4 bg-slate-800/90 backdrop-blur-sm rounded-lg p-3 border border-slate-700 z-10">
          <p className="text-slate-400 text-xs mb-2">Occupancy</p>
          <div className="flex items-center gap-2">
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded bg-green-500"></div>
              <span className="text-slate-300 text-xs">&gt;90%</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded bg-lime-500"></div>
              <span className="text-slate-300 text-xs">&gt;70%</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded bg-yellow-500"></div>
              <span className="text-slate-300 text-xs">&gt;50%</span>
            </div>
            <div className="flex items-center gap-1">
              <div className="w-3 h-3 rounded bg-slate-400"></div>
              <span className="text-slate-300 text-xs">&lt;50%</span>
            </div>
          </div>
        </div>
        
        {/* Instructions */}
        <div className="absolute bottom-4 right-4 bg-slate-800/90 backdrop-blur-sm rounded-lg p-3 border border-slate-700 z-10">
          <p className="text-slate-400 text-xs">
            <span className="text-white">Click</span> floor to view details • 
            <span className="text-white"> Drag</span> to rotate • 
            <span className="text-white"> Scroll</span> to zoom
          </p>
        </div>
      </div>
    </div>
  )
}
