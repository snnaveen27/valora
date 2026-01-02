import React, { useState, useEffect } from 'react';
import { Calendar, TrendingUp, Clock, ChevronLeft, ChevronRight } from 'lucide-react';

const TimeSlider = ({ onTimeChange, onAnalyze }) => {
  const [currentTime, setCurrentTime] = useState(0); // 0 = present
  const [isPlaying, setIsPlaying] = useState(false);
  const [analysisMode, setAnalysisMode] = useState('current'); // current, forecast, trend
  
  // Time periods: -24 to +60 months (-2 years to +5 years)
  const minTime = -24;
  const maxTime = 60;
  
  const timeLabels = {
    '-24': '2 Years Ago',
    '-12': '1 Year Ago',
    '-6': '6 Months Ago',
    '0': 'Present',
    '6': '6 Months',
    '12': '1 Year',
    '24': '2 Years',
    '36': '3 Years',
    '48': '4 Years',
    '60': '5 Years'
  };
  
  useEffect(() => {
    if (isPlaying) {
      const interval = setInterval(() => {
        setCurrentTime((prev) => {
          if (prev >= maxTime) {
            setIsPlaying(false);
            return maxTime;
          }
          return prev + 1;
        });
      }, 500);
      return () => clearInterval(interval);
    }
  }, [isPlaying]);
  
  useEffect(() => {
    // Notify parent component of time change
    onTimeChange({
      monthsFromNow: currentTime,
      mode: analysisMode,
      label: getTimeLabel(currentTime)
    });
  }, [currentTime, analysisMode]);
  
  const getTimeLabel = (value) => {
    if (value === 0) return 'Present';
    if (value < 0) return `${Math.abs(value)} months ago`;
    return `In ${value} months`;
  };
  
  const getSliderColor = () => {
    if (currentTime < 0) return 'bg-blue-500'; // Past
    if (currentTime === 0) return 'bg-green-500'; // Present
    return 'bg-purple-500'; // Future
  };
  
  const handleQuickJump = (months) => {
    setCurrentTime(months);
    if (months > 0) {
      setAnalysisMode('forecast');
    } else if (months < 0) {
      setAnalysisMode('trend');
    } else {
      setAnalysisMode('current');
    }
  };
  
  const handleAnalyzePoint = () => {
    onAnalyze({
      time: currentTime,
      mode: analysisMode
    });
  };

  return (
    <div className="w-full bg-slate-800/95 border-b border-slate-700">
      <div className="flex items-center gap-2 px-3 py-1 text-[10px]">
        {/* Label */}
        <div className="flex items-center gap-1 shrink-0 text-purple-300">
          <Calendar className="w-3 h-3" />
          <span className="font-medium uppercase tracking-wide">Time</span>
        </div>

        {/* Current time badge */}
        <div className={`px-1.5 py-0.5 rounded text-[9px] font-medium shrink-0 ${
          currentTime < 0 ? 'bg-blue-500/20 text-blue-300' :
          currentTime === 0 ? 'bg-green-500/20 text-green-300' :
          'bg-purple-500/20 text-purple-300'
        }`}>
          {getTimeLabel(currentTime)}
        </div>

        {/* Slider */}
        <input
          type="range"
          min={minTime}
          max={maxTime}
          value={currentTime}
          onChange={(e) => setCurrentTime(parseInt(e.target.value))}
          className="flex-1 h-1 appearance-none cursor-pointer rounded-full min-w-[100px]"
          style={{
            background: `linear-gradient(to right, #8b5cf6 0%, #8b5cf6 ${((currentTime - minTime) / (maxTime - minTime)) * 100}%, #334155 ${((currentTime - minTime) / (maxTime - minTime)) * 100}%, #334155 100%)`
          }}
        />

        {/* Quick buttons */}
        <div className="flex items-center gap-0.5 shrink-0">
          {[
            { months: -12, label: '-1Y' },
            { months: 0, label: 'Now' },
            { months: 12, label: '+1Y' },
            { months: 24, label: '+2Y' }
          ].map(({ months, label }) => (
            <button
              key={months}
              onClick={() => handleQuickJump(months)}
              className={`px-1.5 py-0.5 text-[9px] rounded ${
                months === currentTime 
                  ? 'bg-purple-500 text-white' 
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              {label}
            </button>
          ))}
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className={`px-1.5 py-0.5 text-[9px] rounded ${isPlaying ? 'bg-red-500 text-white' : 'bg-blue-500 text-white'}`}
          >
            {isPlaying ? '⏹' : '▶'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default TimeSlider;
