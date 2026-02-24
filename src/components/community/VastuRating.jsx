/**
 * VastuRating - Vastu-specific ratings component
 * 
 * Features:
 * - Direction facing selector (North, South, East, West, NE, NW, SE, SW)
 * - Room placement rating
 * - Vastu compliance score visualization
 * - Vastu-specific notes field
 * 
 * Props:
 * @param {number} [rating] - Vastu compliance rating (1-5)
 * @param {string} [notes] - Vastu notes
 * @param {string} [direction] - Direction facing
 * @param {Object} [roomPlacements] - Room placement ratings
 * @param {function} onChange - Callback when rating or notes changes
 */

import { useState, useMemo } from 'react';
import { Compass, Home, CheckCircle, AlertCircle, Info } from 'lucide-react';

// Direction options with Vastu significance
const DIRECTIONS = [
  { value: 'N', label: 'North', vastu: 'Kuber (wealth)', color: 'bg-blue-500' },
  { value: 'NE', label: 'North-East', vastu: 'Ishanya (knowledge)', color: 'bg-cyan-500' },
  { value: 'E', label: 'East', vastu: 'Indra (direction)', color: 'bg-yellow-500' },
  { value: 'SE', label: 'South-East', vastu: 'Agni (fire)', color: 'bg-orange-500' },
  { value: 'S', label: 'South', vastu: 'Yama (death)', color: 'bg-red-500' },
  { value: 'SW', label: 'South-West', vastu: 'Nairitya (stability)', color: 'bg-brown-500' },
  { value: 'W', label: 'West', vastu: 'Varuna (water)', color: 'bg-teal-500' },
  { value: 'NW', label: 'North-West', vastu: 'Vayu (air)', color: 'bg-purple-500' },
];

// Room types with ideal Vastu positions
const ROOM_TYPES = [
  { id: 'main_door', label: 'Main Door', ideal: ['NE', 'E', 'N'] },
  { id: 'master_bedroom', label: 'Master Bedroom', ideal: ['SW', 'S', 'W'] },
  { id: 'kitchen', label: 'Kitchen', ideal: ['SE', 'NE', 'E'] },
  { id: 'living_room', label: 'Living Room', ideal: ['N', 'E', 'NE'] },
  { id: 'bathroom', label: 'Bathroom', ideal: ['NW', 'W', 'SW'] },
  { id: 'pooja_room', label: 'Pooja Room', ideal: ['NE', 'E'] },
  { id: 'study', label: 'Study Room', ideal: ['E', 'NE', 'N'] },
  { id: 'balcony', label: 'Balcony', ideal: ['N', 'E', 'NE'] },
];

// Star rating input
function StarRatingInput({ value, onChange, label, size = 20 }) {
  const [hover, setHover] = useState(0);

  return (
    <div className="flex flex-col gap-1">
      <label className="text-sm text-gray-300">{label}</label>
      <div className="flex items-center gap-1">
        {[1, 2, 3, 4, 5].map((star) => (
          <button
            key={star}
            type="button"
            onClick={() => onChange(star)}
            onMouseEnter={() => setHover(star)}
            onMouseLeave={() => setHover(0)}
            className="p-0.5 transition-transform hover:scale-110"
          >
            <Compass
              size={size}
              className={`${
                star <= (hover || value)
                  ? 'fill-yellow-400 text-yellow-400'
                  : 'fill-gray-600 text-gray-600'
              }`}
            />
          </button>
        ))}
        {value > 0 && <span className="ml-2 text-sm text-gray-400">{value}/5</span>}
      </div>
    </div>
  );
}

// Direction selector with compass visualization
function DirectionSelector({ selected, onChange }) {
  return (
    <div className="flex flex-col gap-2">
      <label className="text-sm text-gray-300">Direction Facing</label>
      <div className="grid grid-cols-4 gap-2">
        {DIRECTIONS.map((dir) => (
          <button
            key={dir.value}
            type="button"
            onClick={() => onChange(dir.value)}
            className={`p-2 rounded-lg text-center transition-all ${
              selected === dir.value
                ? `${dir.color} text-white`
                : 'bg-gray-700/50 text-gray-400 hover:bg-gray-600/50'
            }`}
          >
            <div className="text-xs font-medium">{dir.label}</div>
            <div className="text-[10px] opacity-75 truncate">{dir.vastu}</div>
          </button>
        ))}
      </div>
    </div>
  );
}

// Room placement rating
function RoomPlacementRating({ roomPlacements, onChange }) {
  return (
    <div className="space-y-3">
      <label className="text-sm text-gray-300 block">Room Placement Assessment</label>
      <div className="space-y-2">
        {ROOM_TYPES.map((room) => {
          const currentDirection = roomPlacements?.[room.id] || '';
          const isIdeal = room.ideal.includes(currentDirection);

          return (
            <div
              key={room.id}
              className="flex items-center gap-3 p-2 bg-gray-800/30 rounded-lg"
            >
              <div className="flex-1">
                <div className="text-sm text-gray-300">{room.label}</div>
                <div className="text-xs text-gray-500">
                  Ideal: {room.ideal.join(', ')}
                </div>
              </div>
              <select
                value={currentDirection}
                onChange={(e) =>
                  onChange({
                    ...roomPlacements,
                    [room.id]: e.target.value,
                  })
                }
                className="bg-gray-700 border border-gray-600 text-white text-sm rounded px-2 py-1 focus:outline-none focus:border-blue-500"
              >
                <option value="">Select direction</option>
                {DIRECTIONS.map((dir) => (
                  <option key={dir.value} value={dir.value}>
                    {dir.label}
                  </option>
                ))}
              </select>
              {currentDirection && (
                isIdeal ? (
                  <CheckCircle size={16} className="text-green-400" />
                ) : (
                  <AlertCircle size={16} className="text-yellow-400" />
                )
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// Vastu compliance score visualization
function VastuScoreDisplay({ score, showDetails = false }) {
  const scoreColor = useMemo(() => {
    if (score >= 4.5) return 'text-green-400';
    if (score >= 3.5) return 'text-yellow-400';
    if (score >= 2.5) return 'text-orange-400';
    return 'text-red-400';
  }, [score]);

  const scoreLabel = useMemo(() => {
    if (score >= 4.5) return 'Excellent';
    if (score >= 3.5) return 'Good';
    if (score >= 2.5) return 'Fair';
    return 'Poor';
  }, [score]);

  return (
    <div className="flex flex-col items-center p-4 bg-gray-800/50 rounded-lg">
      <div className="text-4xl font-bold mb-1" style={{ color: scoreColor }}>
        {score.toFixed(1)}
      </div>
      <div className="text-sm text-gray-400 mb-3">out of 5.0</div>
      
      {/* Progress bar */}
      <div className="w-full h-3 bg-gray-700 rounded-full overflow-hidden mb-2">
        <div
          className="h-full transition-all duration-500 rounded-full"
          style={{
            width: `${(score / 5) * 100}%`,
            backgroundColor:
              score >= 4.5
                ? '#4ade80'
                : score >= 3.5
                ? '#facc15'
                : score >= 2.5
                ? '#fb923c'
                : '#f87171',
          }}
        />
      </div>
      
      <div className={`text-sm font-medium ${scoreColor}`}>{scoreLabel} Vastu Compliance</div>

      {showDetails && (
        <div className="mt-4 w-full text-xs text-gray-500 space-y-1">
          <div className="flex justify-between">
            <span>Direction facing</span>
            <span>25%</span>
          </div>
          <div className="flex justify-between">
            <span>Room placements</span>
            <span>50%</span>
          </div>
          <div className="flex justify-between">
            <span>Overall assessment</span>
            <span>25%</span>
          </div>
        </div>
      )}
    </div>
  );
}

export default function VastuRating({
  rating = 0,
  notes = '',
  direction = '',
  roomPlacements = {},
  onChange,
}) {
  const [localRating, setLocalRating] = useState(rating);
  const [localDirection, setLocalDirection] = useState(direction);
  const [localRoomPlacements, setLocalRoomPlacements] = useState(roomPlacements);
  const [localNotes, setLocalNotes] = useState(notes);

  // Calculate Vastu compliance score
  const vastuScore = useMemo(() => {
    let totalWeight = 0;
    let weightedSum = 0;

    // Direction facing weight (25%)
    if (localDirection) {
      const dir = DIRECTIONS.find((d) => d.value === localDirection);
      if (dir) {
        const isIdeal = ['NE', 'N', 'E'].includes(localDirection);
        weightedSum += isIdeal ? 5 : localRating > 0 ? 3 : 2.5;
        totalWeight += 1;
      }
    }

    // Room placements weight (50%)
    const placedRooms = Object.values(localRoomPlacements).filter(Boolean).length;
    if (placedRooms > 0) {
      let correctPlacements = 0;
      ROOM_TYPES.forEach((room) => {
        const dir = localRoomPlacements[room.id];
        if (dir && room.ideal.includes(dir)) {
          correctPlacements++;
        }
      });
      const placementScore = (correctPlacements / ROOM_TYPES.length) * 5;
      weightedSum += placementScore;
      totalWeight += 1;
    }

    // User rating weight (25%)
    if (localRating > 0) {
      weightedSum += localRating;
      totalWeight += 1;
    }

    return totalWeight > 0 ? weightedSum / totalWeight : 0;
  }, [localDirection, localRating, localRoomPlacements]);

  // Handle changes and propagate to parent
  const handleRatingChange = (value) => {
    setLocalRating(value);
    onChange?.(value, localNotes);
  };

  const handleNotesChange = (value) => {
    setLocalNotes(value);
    onChange?.(localRating, value);
  };

  const handleDirectionChange = (value) => {
    setLocalDirection(value);
  };

  const handleRoomPlacementsChange = (value) => {
    setLocalRoomPlacements(value);
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center gap-2 mb-2">
        <Home size={18} className="text-purple-400" />
        <h4 className="text-sm font-medium text-gray-300">Vastu Compliance Assessment</h4>
      </div>

      {/* Score Display */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="md:col-span-1">
          <VastuScoreDisplay score={vastuScore} showDetails />
        </div>

        <div className="md:col-span-2 space-y-4">
          {/* Overall Rating */}
          <StarRatingInput
            label="Your Vastu Assessment"
            value={localRating}
            onChange={handleRatingChange}
          />

          {/* Direction Selector */}
          <DirectionSelector selected={localDirection} onChange={handleDirectionChange} />
        </div>
      </div>

      {/* Room Placement Rating */}
      <RoomPlacementRating
        roomPlacements={localRoomPlacements}
        onChange={handleRoomPlacementsChange}
      />

      {/* Notes */}
      <div className="flex flex-col gap-2">
        <label className="text-sm text-gray-300">Vastu Notes</label>
        <textarea
          value={localNotes}
          onChange={(e) => handleNotesChange(e.target.value)}
          placeholder="Share your Vastu observations (e.g., positive aspects, concerns, recommendations)..."
          rows={3}
          className="bg-gray-800 border border-gray-600 text-white text-sm rounded-lg px-3 py-2 focus:outline-none focus:border-purple-500 resize-none"
        />
        <div className="flex items-center gap-1 text-xs text-gray-500">
          <Info size={12} />
          <span>
            Include details about direction, room placements, and any Vastu-related observations.
          </span>
        </div>
      </div>

      {/* Vastu Tips */}
      <div className="p-3 bg-purple-900/20 border border-purple-500/30 rounded-lg">
        <div className="flex items-start gap-2">
          <Info size={16} className="text-purple-400 mt-0.5 flex-shrink-0" />
          <div className="text-xs text-gray-400">
            <span className="text-purple-300 font-medium">Vastu Tips: </span>
            North-East (Ishanya) is considered the most auspicious direction for spiritual activities
            and main entrances. South-West is ideal for bedrooms as it provides stability. The kitchen
            (Agni) should be in South-East for positive energy flow.
          </div>
        </div>
      </div>
    </div>
  );
}
