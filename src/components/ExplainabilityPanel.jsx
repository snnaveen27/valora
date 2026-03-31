import { useState, useEffect } from 'react';
import { Brain, TrendingUp, TrendingDown, AlertTriangle, CheckCircle, Info, ChevronDown, ChevronUp } from 'lucide-react';

/**
 * SHAP-style Explainability Panel
 * Shows WHY the AI made certain predictions/recommendations
 */

const FeatureBar = ({ feature, value, impact, maxImpact, isPositive }) => {
  const barWidth = Math.min(Math.abs(impact / maxImpact) * 100, 100);
  
  return (
    <div className="flex items-center gap-2 py-1.5">
      <div className="w-28 text-xs text-slate-400 truncate" title={feature}>
        {feature}
      </div>
      <div className="flex-1 flex items-center">
        <div className="w-1/2 flex justify-end pr-1">
          {!isPositive && (
            <div 
              className="h-4 bg-red-500/70 rounded-l"
              style={{ width: `${barWidth}%` }}
            />
          )}
        </div>
        <div className="w-px h-6 bg-slate-600" />
        <div className="w-1/2 pl-1">
          {isPositive && (
            <div 
              className="h-4 bg-green-500/70 rounded-r"
              style={{ width: `${barWidth}%` }}
            />
          )}
        </div>
      </div>
      <div className={`w-12 text-xs font-mono text-right ${isPositive ? 'text-green-400' : 'text-red-400'}`}>
        {isPositive ? '+' : ''}{(impact * 100).toFixed(0)}%
      </div>
    </div>
  );
};

const ConfidenceGauge = ({ confidence, label }) => {
  const getColor = (conf) => {
    if (conf >= 80) return 'text-green-400';
    if (conf >= 60) return 'text-yellow-400';
    if (conf >= 40) return 'text-orange-400';
    return 'text-red-400';
  };

  const getBgColor = (conf) => {
    if (conf >= 80) return 'bg-green-500';
    if (conf >= 60) return 'bg-yellow-500';
    if (conf >= 40) return 'bg-orange-500';
    return 'bg-red-500';
  };

  return (
    <div className="bg-slate-800 rounded-lg p-3">
      <div className="flex items-center justify-between mb-2">
        <span className="text-xs text-slate-400">{label}</span>
        <span className={`text-lg font-bold ${getColor(confidence)}`}>
          {confidence}%
        </span>
      </div>
      <div className="h-2 bg-slate-700 rounded-full overflow-hidden">
        <div 
          className={`h-full ${getBgColor(confidence)} transition-all duration-500`}
          style={{ width: `${confidence}%` }}
        />
      </div>
    </div>
  );
};

const ReasoningStep = ({ step, index, isLast }) => {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="relative">
      {!isLast && (
        <div className="absolute left-3 top-8 bottom-0 w-px bg-slate-700" />
      )}
      <div className="flex gap-3">
        <div className="w-6 h-6 rounded-full bg-blue-600 flex items-center justify-center text-xs font-bold text-white shrink-0">
          {index + 1}
        </div>
        <div className="flex-1 pb-4">
          <div 
            className="cursor-pointer"
            onClick={() => setExpanded(!expanded)}
          >
            <div className="flex items-center gap-2">
              <span className="text-sm text-white font-medium">{step.title}</span>
              {expanded ? (
                <ChevronUp className="w-3 h-3 text-slate-400" />
              ) : (
                <ChevronDown className="w-3 h-3 text-slate-400" />
              )}
            </div>
            <div className="text-xs text-slate-400 mt-0.5">{step.summary}</div>
          </div>
          {expanded && step.details && (
            <div className="mt-2 p-2 bg-slate-800 rounded text-xs text-slate-300">
              {step.details}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

const CausalChain = ({ chain }) => {
  if (!chain || !chain.steps) return null;

  return (
    <div className="bg-slate-800 rounded-lg p-4">
      <h4 className="text-sm font-medium text-white mb-3 flex items-center gap-2">
        <Brain className="w-4 h-4 text-purple-400" />
        Causal Reasoning Chain
      </h4>
      <div className="space-y-1">
        {chain.steps.map((step, idx) => (
          <div key={idx} className="flex items-center gap-2 text-xs">
            <span className="text-slate-400">{step.cause}</span>
            <span className="text-blue-400">→</span>
            <span className="text-white">{step.effect}</span>
            <span className="text-slate-500">({(step.confidence * 100).toFixed(0)}%)</span>
          </div>
        ))}
      </div>
      {chain.conclusion && (
        <div className="mt-3 pt-3 border-t border-slate-700">
          <div className="text-xs text-green-400 font-medium">Conclusion:</div>
          <div className="text-xs text-slate-300 mt-1">{chain.conclusion}</div>
        </div>
      )}
    </div>
  );
};

const RiskExplanation = ({ riskProfile }) => {
  if (!riskProfile) return null;

  const risks = [
    { name: 'Hazard', value: riskProfile.hazard, icon: AlertTriangle },
    { name: 'Infrastructure', value: riskProfile.infrastructure, icon: TrendingDown },
    { name: 'Speculation', value: riskProfile.speculation, icon: TrendingUp },
  ].filter(r => r.value !== undefined);

  return (
    <div className="bg-slate-800 rounded-lg p-4">
      <h4 className="text-sm font-medium text-white mb-3">Risk Breakdown</h4>
      <div className="space-y-3">
        {risks.map((risk, idx) => (
          <div key={idx}>
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-2">
                <risk.icon className="w-3 h-3 text-slate-400" />
                <span className="text-xs text-slate-300">{risk.name}</span>
              </div>
              <span className={`text-xs font-bold ${
                risk.value < 30 ? 'text-green-400' :
                risk.value < 60 ? 'text-yellow-400' : 'text-red-400'
              }`}>
                {risk.value.toFixed(0)}/100
              </span>
            </div>
            <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
              <div 
                className={`h-full transition-all ${
                  risk.value < 30 ? 'bg-green-500' :
                  risk.value < 60 ? 'bg-yellow-500' : 'bg-red-500'
                }`}
                style={{ width: `${risk.value}%` }}
              />
            </div>
          </div>
        ))}
      </div>
      {riskProfile.bubble_probability > 0.3 && (
        <div className="mt-3 p-2 bg-yellow-900/30 rounded border border-yellow-700/50">
          <div className="flex items-center gap-2 text-xs text-yellow-400">
            <AlertTriangle className="w-3 h-3" />
            Bubble Probability: {(riskProfile.bubble_probability * 100).toFixed(0)}%
          </div>
        </div>
      )}
    </div>
  );
};

const ExplainabilityPanel = ({ analysis, fontSize = 100 }) => {
  const [activeSection, setActiveSection] = useState('features');

  // Extract explainability data from analysis
  const features = analysis?.keyDrivers || analysis?.features || [];
  const confidence = analysis?.confidence || analysis?.overallConfidence || 75;
  const reasoningSteps = analysis?.reasoningSteps || analysis?.reasoning_chain || [];
  const causalChain = analysis?.causalAnalysis || analysis?.causal_analysis;
  const riskProfile = analysis?.riskProfile || analysis?.risk_profile;
  const prediction = analysis?.prediction;
  const warnings = analysis?.warnings || analysis?.risk_warnings || [];

  // Calculate max impact for bar scaling
  const maxImpact = features.length > 0 
    ? Math.max(...features.map(f => Math.abs(f.impact || f.value || 0)))
    : 1;

  const sections = [
    { id: 'features', label: 'Key Factors' },
    { id: 'reasoning', label: 'Reasoning' },
    { id: 'risk', label: 'Risk' },
  ];

  if (!analysis) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-slate-400 p-4">
        <Brain className="w-12 h-12 mb-3 opacity-50" />
        <div className="text-center">
          <div className="font-medium">No Analysis Yet</div>
          <div className="text-xs mt-1">
            Ask me about a location or property to see why I make my recommendations
          </div>
        </div>
      </div>
    );
  }

  return (
    <div 
      className="h-full flex flex-col bg-slate-900 overflow-hidden"
      style={{ fontSize: `${fontSize}%` }}
    >
      {/* Header */}
      <div className="p-3 border-b border-slate-700">
        <div className="flex items-center gap-2 mb-2">
          <Brain className="w-4 h-4 text-purple-400" />
          <span className="text-sm font-medium text-white">Why This Recommendation?</span>
        </div>
        
        {/* Section Tabs */}
        <div className="flex gap-1">
          {sections.map(section => (
            <button
              key={section.id}
              onClick={() => setActiveSection(section.id)}
              className={`px-2 py-1 text-xs rounded transition ${
                activeSection === section.id
                  ? 'bg-purple-600 text-white'
                  : 'bg-slate-800 text-slate-400 hover:text-white'
              }`}
            >
              {section.label}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3 space-y-4">
        {/* Confidence */}
        <ConfidenceGauge confidence={confidence} label="Analysis Confidence" />

        {/* Key Factors (SHAP-style) */}
        {activeSection === 'features' && (
          <div className="bg-slate-800 rounded-lg p-4">
            <h4 className="text-sm font-medium text-white mb-3">Impact on Recommendation</h4>
            <div className="mb-2 flex justify-between text-xs text-slate-500">
              <span>← Negative</span>
              <span>Positive →</span>
            </div>
            {features.length > 0 ? (
              features.slice(0, 8).map((feature, idx) => (
                <FeatureBar
                  key={idx}
                  feature={feature.name || feature.feature}
                  value={feature.value}
                  impact={feature.impact || feature.value}
                  maxImpact={maxImpact}
                  isPositive={(feature.impact || feature.value) > 0}
                />
              ))
            ) : (
              <div className="text-xs text-slate-400 text-center py-4">
                Feature analysis not available for this query
              </div>
            )}
          </div>
        )}

        {/* Reasoning Steps */}
        {activeSection === 'reasoning' && (
          <div className="bg-slate-800 rounded-lg p-4">
            <h4 className="text-sm font-medium text-white mb-3">How I Reached This Conclusion</h4>
            {reasoningSteps.length > 0 ? (
              <div className="space-y-1">
                {reasoningSteps.map((step, idx) => (
                  <ReasoningStep
                    key={idx}
                    step={typeof step === 'string' ? { title: step, summary: '' } : step}
                    index={idx}
                    isLast={idx === reasoningSteps.length - 1}
                  />
                ))}
              </div>
            ) : (
              <div className="text-xs text-slate-400 text-center py-4">
                Detailed reasoning steps not available
              </div>
            )}
          </div>
        )}

        {/* Causal Chain */}
        {activeSection === 'reasoning' && causalChain && (
          <CausalChain chain={causalChain} />
        )}

        {/* Risk Explanation */}
        {activeSection === 'risk' && (
          <>
            <RiskExplanation riskProfile={riskProfile} />
            
            {warnings.length > 0 && (
              <div className="bg-slate-800 rounded-lg p-4">
                <h4 className="text-sm font-medium text-white mb-2 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-yellow-400" />
                  Warnings
                </h4>
                <div className="space-y-2">
                  {warnings.map((warning, idx) => (
                    <div key={idx} className="text-xs text-yellow-300 flex items-start gap-2">
                      <span>•</span>
                      <span>{warning}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}

        {/* Prediction Details */}
        {prediction && (
          <div className="bg-slate-800 rounded-lg p-4">
            <h4 className="text-sm font-medium text-white mb-2">Prediction Details</h4>
            <div className="grid grid-cols-2 gap-3">
              {prediction.point_estimate && (
                <div>
                  <div className="text-xs text-slate-400">Estimate</div>
                  <div className="text-lg font-bold text-white">
                    ₹{prediction.point_estimate.toLocaleString()}
                  </div>
                </div>
              )}
              {prediction.change_percentage && (
                <div>
                  <div className="text-xs text-slate-400">Change</div>
                  <div className={`text-lg font-bold ${
                    prediction.change_percentage > 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {prediction.change_percentage > 0 ? '+' : ''}{prediction.change_percentage.toFixed(1)}%
                  </div>
                </div>
              )}
            </div>
            {prediction.confidence_interval && (
              <div className="mt-2 text-xs text-slate-400">
                95% CI: ₹{prediction.confidence_interval.lower?.toLocaleString()} - 
                ₹{prediction.confidence_interval.upper?.toLocaleString()}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-2 border-t border-slate-700 bg-slate-800/50">
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <Info className="w-3 h-3" />
          <span>Analysis based on {analysis?.dataPoints || 'available'} data points</span>
        </div>
      </div>
    </div>
  );
};

export default ExplainabilityPanel;
