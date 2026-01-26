import React, { useState, useEffect } from 'react';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://localhost:8000';

// Archetype icons and colors
const ARCHETYPE_CONFIG = {
  tech_hub: { icon: '💻', color: 'bg-blue-500', label: 'Tech Hub' },
  commercial: { icon: '🏢', color: 'bg-purple-500', label: 'Commercial' },
  residential_family: { icon: '👨‍👩‍👧‍👦', color: 'bg-green-500', label: 'Family Residential' },
  residential_premium: { icon: '🏠', color: 'bg-yellow-500', label: 'Premium Residential' },
  mixed_use: { icon: '🌆', color: 'bg-indigo-500', label: 'Mixed Use' },
  industrial: { icon: '🏭', color: 'bg-gray-500', label: 'Industrial' },
  institutional: { icon: '🏛️', color: 'bg-red-500', label: 'Institutional' },
  heritage: { icon: '🏰', color: 'bg-amber-500', label: 'Heritage' },
  emerging: { icon: '🚀', color: 'bg-cyan-500', label: 'Emerging' },
  transit_oriented: { icon: '🚇', color: 'bg-teal-500', label: 'Transit Oriented' },
};

const GROWTH_STAGE_CONFIG = {
  nascent: { color: 'text-gray-400', label: 'Nascent' },
  emerging: { color: 'text-cyan-400', label: 'Emerging' },
  growing: { color: 'text-green-400', label: 'Growing' },
  maturing: { color: 'text-yellow-400', label: 'Maturing' },
  mature: { color: 'text-blue-400', label: 'Mature' },
  declining: { color: 'text-red-400', label: 'Declining' },
  regenerating: { color: 'text-purple-400', label: 'Regenerating' },
};

const RiskMeter = ({ score, label, size = 'md' }) => {
  const getColor = (score) => {
    if (score < 30) return 'bg-green-500';
    if (score < 50) return 'bg-yellow-500';
    if (score < 70) return 'bg-orange-500';
    return 'bg-red-500';
  };

  const sizes = {
    sm: 'h-2',
    md: 'h-3',
    lg: 'h-4',
  };

  return (
    <div className="w-full">
      {label && <div className="text-xs text-gray-400 mb-1">{label}</div>}
      <div className={`w-full bg-gray-700 rounded-full ${sizes[size]}`}>
        <div
          className={`${getColor(score)} ${sizes[size]} rounded-full transition-all duration-500`}
          style={{ width: `${Math.min(score, 100)}%` }}
        />
      </div>
      <div className="text-xs text-right text-gray-400 mt-0.5">{score.toFixed(0)}/100</div>
    </div>
  );
};

const LocalityCard = ({ locality, onClick, isSelected }) => {
  const config = ARCHETYPE_CONFIG[locality.archetype] || ARCHETYPE_CONFIG.mixed_use;
  const growth = GROWTH_STAGE_CONFIG[locality.growth_stage] || GROWTH_STAGE_CONFIG.growing;

  return (
    <div
      onClick={() => onClick(locality)}
      className={`p-3 rounded-lg cursor-pointer transition-all ${
        isSelected
          ? 'bg-blue-600 border-2 border-blue-400'
          : 'bg-gray-800 hover:bg-gray-700 border border-gray-700'
      }`}
    >
      <div className="flex items-center gap-2">
        <span className="text-2xl">{config.icon}</span>
        <div className="flex-1">
          <div className="font-medium text-white">{locality.name}</div>
          <div className="text-xs text-gray-400">{locality.tagline}</div>
        </div>
      </div>
      <div className="flex items-center gap-2 mt-2">
        <span className={`px-2 py-0.5 rounded text-xs ${config.color} text-white`}>
          {config.label}
        </span>
        <span className={`text-xs ${growth.color}`}>{growth.label}</span>
      </div>
    </div>
  );
};

const TimelineView = ({ timeline }) => {
  if (!timeline) return null;

  return (
    <div className="space-y-4">
      <div className="bg-gray-800 rounded-lg p-4">
        <h4 className="text-sm font-medium text-gray-300 mb-2">Development Phases</h4>
        <div className="relative">
          {timeline.phases?.map((phase, idx) => (
            <div key={idx} className="flex items-center gap-3 mb-2">
              <div className="w-20 text-xs text-gray-400">
                {phase.start}-{phase.end || 'now'}
              </div>
              <div className="w-3 h-3 rounded-full bg-blue-500" />
              <div className="text-sm text-white capitalize">
                {phase.phase.replace(/_/g, ' ')}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-gray-800 rounded-lg p-4">
        <h4 className="text-sm font-medium text-gray-300 mb-2">Key Milestones</h4>
        <div className="space-y-2 max-h-48 overflow-y-auto">
          {timeline.milestones?.slice(0, 10).map((m, idx) => (
            <div key={idx} className="flex gap-3 text-sm">
              <span className="text-blue-400 font-mono w-12">{m.year}</span>
              <span className="text-white flex-1">{m.event}</span>
              <span className={`text-xs px-1.5 py-0.5 rounded ${
                m.impact === 'transformative' ? 'bg-purple-500' :
                m.impact === 'major' ? 'bg-blue-500' : 'bg-gray-600'
              }`}>
                {m.impact}
              </span>
            </div>
          ))}
        </div>
      </div>

      {timeline.projections?.length > 0 && (
        <div className="bg-gray-800 rounded-lg p-4">
          <h4 className="text-sm font-medium text-gray-300 mb-2">Projected Developments</h4>
          <div className="space-y-2">
            {timeline.projections.map((p, idx) => (
              <div key={idx} className="flex gap-3 text-sm">
                <span className="text-cyan-400 font-mono w-12">{p.year}</span>
                <span className="text-white flex-1">{p.event}</span>
                <span className="text-xs text-gray-400">
                  {(p.probability * 100).toFixed(0)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const RiskPanel = ({ risk }) => {
  if (!risk) return null;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-gray-800 rounded-lg p-4">
          <div className="text-sm text-gray-400">Overall Risk</div>
          <div className="text-2xl font-bold text-white">
            {risk.overall_risk?.score?.toFixed(0) || 0}
          </div>
          <div className={`text-sm capitalize ${
            risk.overall_risk?.level === 'low' ? 'text-green-400' :
            risk.overall_risk?.level === 'moderate' ? 'text-yellow-400' :
            'text-red-400'
          }`}>
            {risk.overall_risk?.level || 'unknown'}
          </div>
        </div>
        <div className="bg-gray-800 rounded-lg p-4">
          <div className="text-sm text-gray-400">Investment Risk</div>
          <div className="text-2xl font-bold text-white">
            {risk.investment_risk?.score?.toFixed(0) || 0}
          </div>
          <div className={`text-sm capitalize ${
            risk.investment_risk?.level === 'low' ? 'text-green-400' :
            risk.investment_risk?.level === 'moderate' ? 'text-yellow-400' :
            'text-red-400'
          }`}>
            {risk.investment_risk?.level || 'unknown'}
          </div>
        </div>
      </div>

      <div className="bg-gray-800 rounded-lg p-4">
        <h4 className="text-sm font-medium text-gray-300 mb-3">Risk Components</h4>
        <div className="space-y-3">
          <RiskMeter score={risk.components?.hazard || 0} label="Hazard Risk" />
          <RiskMeter score={risk.components?.infrastructure || 0} label="Infrastructure Stress" />
          <RiskMeter score={risk.components?.speculation || 0} label="Speculation Index" />
          <RiskMeter score={risk.components?.policy || 0} label="Policy Risk" />
        </div>
      </div>

      {risk.bubble_probability > 0.3 && (
        <div className="bg-yellow-900/50 border border-yellow-600 rounded-lg p-3">
          <div className="flex items-center gap-2">
            <span className="text-yellow-400">⚠️</span>
            <span className="text-yellow-300 text-sm">
              Bubble Probability: {(risk.bubble_probability * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      )}

      {risk.warnings?.length > 0 && (
        <div className="bg-gray-800 rounded-lg p-4">
          <h4 className="text-sm font-medium text-gray-300 mb-2">Warnings</h4>
          <div className="space-y-2">
            {risk.warnings.map((warning, idx) => (
              <div key={idx} className="text-sm text-red-400">
                {warning}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

const CausalReasoningPanel = ({ onReason }) => {
  const [scenario, setScenario] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleReason = async () => {
    if (!scenario.trim()) return;
    setLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/city-intelligence/reason`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ scenario }),
      });
      const data = await res.json();
      setResult(data);
    } catch (err) {
      console.error('Reasoning error:', err);
    }
    setLoading(false);
  };

  return (
    <div className="space-y-4">
      <div className="bg-gray-800 rounded-lg p-4">
        <h4 className="text-sm font-medium text-gray-300 mb-2">Ask "What If?"</h4>
        <div className="flex gap-2">
          <input
            type="text"
            value={scenario}
            onChange={(e) => setScenario(e.target.value)}
            placeholder="e.g., New metro station opens in Sarjapur"
            className="flex-1 bg-gray-700 border border-gray-600 rounded px-3 py-2 text-white text-sm"
            onKeyDown={(e) => e.key === 'Enter' && handleReason()}
          />
          <button
            onClick={handleReason}
            disabled={loading}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded text-white text-sm disabled:opacity-50"
          >
            {loading ? '...' : 'Analyze'}
          </button>
        </div>
      </div>

      {result?.success && (
        <div className="bg-gray-800 rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-medium text-gray-300">Causal Analysis</h4>
            <span className="text-xs px-2 py-1 bg-blue-600 rounded">
              {(result.confidence * 100).toFixed(0)}% confidence
            </span>
          </div>

          <div className="space-y-2 mb-4">
            {result.steps?.slice(0, 6).map((step, idx) => (
              <div key={idx} className="flex items-start gap-2 text-sm">
                <span className="text-blue-400 font-mono w-6">{step.step}.</span>
                <div className="flex-1">
                  <div className="text-white">{step.description}</div>
                  {step.effect && step.effect !== '(analyzing effects)' && (
                    <div className="text-gray-400 text-xs mt-0.5">{step.effect}</div>
                  )}
                </div>
              </div>
            ))}
          </div>

          <div className="border-t border-gray-700 pt-3">
            <div className="text-sm font-medium text-green-400">Conclusion:</div>
            <div className="text-sm text-white mt-1">{result.conclusion}</div>
          </div>

          {result.caveats?.length > 0 && (
            <div className="mt-3 text-xs text-gray-400">
              {result.caveats.map((c, i) => (
                <div key={i}>• {c}</div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const CityIntelligencePanel = ({ onLocalitySelect, selectedLocality }) => {
  const [localities, setLocalities] = useState([]);
  const [activeTab, setActiveTab] = useState('localities');
  const [profile, setProfile] = useState(null);
  const [timeline, setTimeline] = useState(null);
  const [risk, setRisk] = useState(null);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState(null);

  useEffect(() => {
    fetchStatus();
    fetchLocalities();
  }, []);

  useEffect(() => {
    if (selectedLocality) {
      fetchLocalityDetails(selectedLocality);
    }
  }, [selectedLocality]);

  const fetchStatus = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/city-intelligence/status`);
      const data = await res.json();
      setStatus(data);
    } catch (err) {
      console.error('Status fetch error:', err);
    }
  };

  const fetchLocalities = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/city-intelligence/localities`);
      const data = await res.json();
      if (data.success) {
        setLocalities(data.localities);
      }
    } catch (err) {
      console.error('Localities fetch error:', err);
    }
  };

  const fetchLocalityDetails = async (localityName) => {
    setLoading(true);
    try {
      const [profileRes, timelineRes, riskRes] = await Promise.all([
        fetch(`${BACKEND_URL}/api/city-intelligence/locality/${localityName}`),
        fetch(`${BACKEND_URL}/api/city-intelligence/timeline/${localityName}`),
        fetch(`${BACKEND_URL}/api/city-intelligence/risk/${localityName}`),
      ]);

      const [profileData, timelineData, riskData] = await Promise.all([
        profileRes.json(),
        timelineRes.json(),
        riskRes.json(),
      ]);

      if (profileData.success) setProfile(profileData.profile);
      if (timelineData.success) setTimeline(timelineData);
      if (riskData.success) setRisk(riskData);
    } catch (err) {
      console.error('Details fetch error:', err);
    }
    setLoading(false);
  };

  const handleLocalityClick = (locality) => {
    onLocalitySelect?.(locality.name);
    fetchLocalityDetails(locality.name);
  };

  const tabs = [
    { id: 'localities', label: 'Localities' },
    { id: 'timeline', label: 'Timeline' },
    { id: 'risk', label: 'Risk' },
    { id: 'reasoning', label: 'What-If' },
  ];

  return (
    <div className="h-full flex flex-col bg-gray-900 text-white">
      {/* Header */}
      <div className="p-4 border-b border-gray-700">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold">City Intelligence</h2>
            <p className="text-xs text-gray-400">Bangalore Urban Analytics</p>
          </div>
          {status?.available && (
            <span className="px-2 py-1 bg-green-600 rounded text-xs">Active</span>
          )}
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-gray-700">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-1 px-4 py-2 text-sm ${
              activeTab === tab.id
                ? 'text-blue-400 border-b-2 border-blue-400'
                : 'text-gray-400 hover:text-white'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'localities' && (
          <div className="space-y-3">
            {localities.map((locality) => (
              <LocalityCard
                key={locality.name}
                locality={locality}
                onClick={handleLocalityClick}
                isSelected={selectedLocality === locality.name}
              />
            ))}
          </div>
        )}

        {activeTab === 'timeline' && (
          loading ? (
            <div className="text-center text-gray-400 py-8">Loading...</div>
          ) : timeline ? (
            <TimelineView timeline={timeline} />
          ) : (
            <div className="text-center text-gray-400 py-8">
              Select a locality to view its timeline
            </div>
          )
        )}

        {activeTab === 'risk' && (
          loading ? (
            <div className="text-center text-gray-400 py-8">Loading...</div>
          ) : risk ? (
            <RiskPanel risk={risk} />
          ) : (
            <div className="text-center text-gray-400 py-8">
              Select a locality to view risk analysis
            </div>
          )
        )}

        {activeTab === 'reasoning' && (
          <CausalReasoningPanel />
        )}
      </div>

      {/* Selected locality info bar */}
      {selectedLocality && profile && (
        <div className="p-3 border-t border-gray-700 bg-gray-800">
          <div className="flex items-center justify-between">
            <div>
              <span className="font-medium">{profile.name}</span>
              <span className="text-xs text-gray-400 ml-2">
                {ARCHETYPE_CONFIG[profile.archetype]?.label || profile.archetype}
              </span>
            </div>
            <div className="text-xs">
              <span className="text-gray-400">Tech: </span>
              <span className="text-blue-400">{profile.tech_orientation}</span>
              <span className="text-gray-400 ml-2">Family: </span>
              <span className="text-green-400">{profile.family_friendliness}</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CityIntelligencePanel;
