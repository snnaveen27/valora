/**
 * SentimentGauge - Visual gauge component for sentiment score
 * 
 * Features:
 * - Animated gauge showing sentiment score (0-100)
 * - Color coding: green (positive), yellow (neutral), red (negative)
 * - Score breakdown display
 * - Animated transitions
 * 
 * Props:
 * @param {number} score - Sentiment score (0-100)
 * @param {Object} [components] - Score components breakdown
 * @param {string} [size] - Size variant (sm, md, lg)
 * @param {boolean} [showBreakdown] - Whether to show score breakdown
 * @param {boolean} [animated] - Whether to animate the gauge
 * @param {string} [label] - Custom label
 * @param {function} [onClick] - Click handler
 */

import { useState, useEffect, useMemo } from 'react';
import { TrendingUp, TrendingDown, Minus, Info } from 'lucide-react';

// Score thresholds
const SCORE_THRESHOLDS = {
  positive: 60,
  neutral: 40,
};

/**
 * Get color based on score
 * @param {number} score - Score value
 * @returns {Object} Color values
 */
const getScoreColors = (score) => {
  if (score >= SCORE_THRESHOLDS.positive) {
    return {
      bg: 'bg-emerald-500',
      bgLight: 'bg-emerald-500/20',
      text: 'text-emerald-400',
      border: 'border-emerald-500/50',
      gradient: 'from-emerald-500/80 to-emerald-600',
      glow: 'shadow-emerald-500/30',
    };
  } else if (score >= SCORE_THRESHOLDS.neutral) {
    return {
      bg: 'bg-yellow-500',
      bgLight: 'bg-yellow-500/20',
      text: 'text-yellow-400',
      border: 'border-yellow-500/50',
      gradient: 'from-yellow-500/80 to-yellow-600',
      glow: 'shadow-yellow-500/30',
    };
  } else {
    return {
      bg: 'bg-red-500',
      bgLight: 'bg-red-500/20',
      text: 'text-red-400',
      border: 'border-red-500/50',
      gradient: 'from-red-500/80 to-red-600',
      glow: 'shadow-red-500/30',
    };
  }
};

/**
 * Get sentiment label based on score
 * @param {number} score - Score value
 * @returns {string} Label
 */
const getScoreLabel = (score) => {
  if (score >= SCORE_THRESHOLDS.positive) return 'Positive';
  if (score >= SCORE_THRESHOLDS.neutral) return 'Neutral';
  return 'Negative';
};

/**
 * Get trend icon based on score change
 * @param {number} change - Score change
 * @returns {React.ReactNode} Trend icon
 */
const TrendIcon = ({ change }) => {
  if (change > 0) {
    return <TrendingUp size={14} className="text-emerald-400" />;
  }
  if (change < 0) {
    return <TrendingDown size={14} className="text-red-400" />;
  }
  return <Minus size={14} className="text-gray-400" />;
};

// SVG Gauge Component
function GaugeSVG({ score, size, animated, colors }) {
  const [animatedScore, setAnimatedScore] = useState(0);
  
  // Calculate the angle (180 degrees total, from -90 to 90)
  const angle = useMemo(() => {
    const normalizedScore = Math.min(100, Math.max(0, score));
    return -90 + (normalizedScore / 100) * 180;
  }, [score]);
  
  // Animate the score
  useEffect(() => {
    if (animated) {
      const duration = 1000;
      const startTime = Date.now();
      const startValue = 0;
      
      const animate = () => {
        const elapsed = Date.now() - startTime;
        const progress = Math.min(elapsed / duration, 1);
        // Easing function (ease-out)
        const eased = 1 - Math.pow(1 - progress, 3);
        const currentValue = startValue + (score - startValue) * eased;
        
        setAnimatedScore(currentValue);
        
        if (progress < 1) {
          requestAnimationFrame(animate);
        }
      };
      
      requestAnimationFrame(animate);
    } else {
      setAnimatedScore(score);
    }
  }, [score, animated]);
  
  const sizeConfig = {
    sm: { width: 120, strokeWidth: 10, fontSize: '1.5rem' },
    md: { width: 180, strokeWidth: 14, fontSize: '2.5rem' },
    lg: { width: 240, strokeWidth: 18, fontSize: '3.5rem' },
  };
  
  const config = sizeConfig[size] || sizeConfig.md;
  const radius = (config.width - config.strokeWidth) / 2;
  const circumference = Math.PI * radius;
  const offset = circumference - (animatedScore / 100) * circumference;
  const animatedAngle = -90 + (animatedScore / 100) * 180;
  
  return (
    <svg
      width={config.width}
      height={config.width * 0.6}
      viewBox={`0 0 ${config.width} ${config.width * 0.6}`}
      className="overflow-visible"
    >
      {/* Background arc */}
      <path
        d={`M ${config.strokeWidth / 2} ${config.width * 0.6 - config.strokeWidth / 2} A ${radius} ${radius} 0 0 1 ${config.width - config.strokeWidth / 2} ${config.width * 0.6 - config.strokeWidth / 2}`}
        fill="none"
        stroke="currentColor"
        strokeWidth={config.strokeWidth}
        strokeLinecap="round"
        className="text-gray-700"
      />
      
      {/* Colored arc */}
      <path
        d={`M ${config.strokeWidth / 2} ${config.width * 0.6 - config.strokeWidth / 2} A ${radius} ${radius} 0 0 1 ${config.width - config.strokeWidth / 2} ${config.width * 0.6 - config.strokeWidth / 2}`}
        fill="none"
        stroke="currentColor"
        strokeWidth={config.strokeWidth}
        strokeLinecap="round"
        strokeDasharray={circumference}
        strokeDashoffset={offset}
        className={`transition-all duration-1000 ease-out ${colors.bg}`}
        style={{ filter: `drop-shadow(0 0 8px var(--tw-${colors.glow}))` }}
      />
      
      {/* Needle */}
      <g transform={`translate(${config.width / 2}, ${config.width * 0.6 - config.strokeWidth / 2})`}>
        <line
          x1="0"
          y1="0"
          x2={Math.cos((animatedAngle * Math.PI) / 180) * (radius - config.strokeWidth)}
          y2={Math.sin((animatedAngle * Math.PI) / 180) * (radius - config.strokeWidth)}
          stroke="white"
          strokeWidth={2}
          strokeLinecap="round"
          className="transition-all duration-1000 ease-out"
        />
        <circle
          r={config.strokeWidth / 2.5}
          fill="white"
        />
      </g>
      
      {/* Score text */}
      <text
        x={config.width / 2}
        y={config.width * 0.45}
        textAnchor="middle"
        fill="white"
        fontSize={config.fontSize}
        fontWeight="bold"
        className="transition-all duration-300"
      >
        {Math.round(animatedScore)}
      </text>
    </svg>
  );
}

// Score Breakdown Component
function ScoreBreakdown({ components, colors }) {
  if (!components || Object.keys(components).length === 0) return null;
  
  const componentLabels = {
    demand_score: 'Demand',
    supply_score: 'Supply',
    price_momentum: 'Price Momentum',
    activity_level: 'Activity',
    sentiment_trend: 'Trend',
  };
  
  return (
    <div className="mt-4 space-y-2">
      <h4 className="text-sm text-gray-400 font-medium">Score Breakdown</h4>
      <div className="grid grid-cols-2 gap-2">
        {Object.entries(components).map(([key, value]) => (
          <div key={key} className="flex items-center justify-between text-sm">
            <span className="text-gray-400">
              {componentLabels[key] || key.replace(/_/g, ' ')}
            </span>
            <span className={`font-medium ${colors.text}`}>{value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// Main Component
export default function SentimentGauge({
  score = 0,
  components,
  size = 'md',
  showBreakdown = false,
  animated = true,
  label = 'Market Sentiment',
  change,
  onClick,
}) {
  const colors = useMemo(() => getScoreColors(score), [score]);
  
  return (
    <div
      className={`
        relative flex flex-col items-center p-4 
        bg-gray-800/50 rounded-xl border ${colors.border}
        backdrop-blur-sm transition-all duration-300
        ${onClick ? 'cursor-pointer hover:bg-gray-800/70 hover:scale-[1.02]' : ''}
        ${colors.glow} shadow-lg
      `}
      onClick={onClick}
    >
      {/* Header */}
      <div className="flex items-center justify-between w-full mb-2">
        <span className="text-sm text-gray-300 font-medium">{label}</span>
        <div className={`flex items-center gap-1 px-2 py-0.5 rounded-full ${colors.bgLight}`}>
          <TrendIcon change={change} />
          {change !== undefined && (
            <span className={`text-xs font-medium ${colors.text}`}>
              {change > 0 ? '+' : ''}{change}%
            </span>
          )}
        </div>
      </div>
      
      {/* Gauge */}
      <GaugeSVG
        score={score}
        size={size}
        animated={animated}
        colors={colors}
      />
      
      {/* Label */}
      <div className={`mt-2 px-3 py-1 rounded-full ${colors.bgLight} ${colors.text}`}>
        <span className="text-sm font-medium">{getScoreLabel(score)}</span>
      </div>
      
      {/* Breakdown */}
      {showBreakdown && (
        <ScoreBreakdown components={components} colors={colors} />
      )}
      
      {/* Info tooltip hint */}
      <div className="absolute top-2 right-2 opacity-50 hover:opacity-100 transition-opacity">
        <Info size={14} className="text-gray-400" />
      </div>
    </div>
  );
}

// Export completed - component ready for use
