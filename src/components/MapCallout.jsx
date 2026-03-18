import { useEffect, useState } from 'react'

const TYPE_COLORS = {
  area: '#8b5cf6',
  property: '#10b981',
  building: '#f43f5e'
}

const TYPE_LABELS = {
  area: 'Area',
  property: 'Property',
  building: 'Building'
}

export default function MapCallout({
  visible = false,
  lat,
  lng,
  x = 0,
  y = 0,
  type = 'area',
  color = null,
  locality = 'Unknown Area',
  place = 'Unknown Location',
  pricePerSqft = null,
  investmentScore = null,
  connectivityScore = null,
  sentimentScore = null,
  rentalYieldAvg = null,
  priceMomentum = null,
  overallRating = null,
  vastuScore = null,
  schoolScore = null,
  transportScore = null,
  safetyScore = null,
  verifiedReviews = null,
  status = 'Live',
  isLoading = false,
  propertyData = null,
  buildingData = null,
  onClose,
  onPropertyClick,
  onBuildingClick,
  hasMultipleProperties = false,
  tabs = [],
  activeTabIndex = 0,
  onTabChange,
  allProperties = [],
  onLocateMe,
  cartesian = null,
  zIndex = 50,
  onFocus
}) {
  const [isVisible, setIsVisible] = useState(false)
  const [showLabel, setShowLabel] = useState(false)
  const [currentTab, setCurrentTab] = useState(0)

  const themeColor = color || TYPE_COLORS[type] || TYPE_COLORS.area

  useEffect(() => {
    if (visible) {
      setIsVisible(true)
      const timer = setTimeout(() => setShowLabel(true), 300)
      return () => clearTimeout(timer)
    } else {
      setShowLabel(false)
      const timer = setTimeout(() => setIsVisible(false), 200)
      return () => clearTimeout(timer)
    }
  }, [visible])

  useEffect(() => {
    setCurrentTab(activeTabIndex)
  }, [activeTabIndex])

  useEffect(() => {
    const handleEsc = (e) => {
      if (e.key === 'Escape' && visible && onClose) {
        onClose()
      }
    }
    window.addEventListener('keydown', handleEsc)
    return () => window.removeEventListener('keydown', handleEsc)
  }, [visible, onClose])

  const handleTabClick = (tabIndex) => {
    setCurrentTab(tabIndex)
    if (onTabChange) {
      onTabChange(tabIndex)
    }
  }

  const handleLocateMe = () => {
    if (onLocateMe) {
      onLocateMe()
    }
  }

  if (!isVisible) return null
  if (!x || !y || x <= 0 || y <= 0) return null

  const formatPrice = (price) => {
    if (price === null || price === undefined) return '--'
    if (price >= 10000000) return `₹${(price / 10000000).toFixed(1)}Cr`
    if (price >= 100000) return `₹${(price / 100000).toFixed(0)}L`
    if (price >= 10000) return `₹${(price / 1000).toFixed(0)}k`
    return `₹${price}`
  }

  const formatSqft = (sqft) => {
    if (!sqft) return '--'
    return `${Number(sqft).toLocaleString()} ft²`
  }

  const formatScore = (score) => {
    if (score === null || score === undefined) return '--'
    return `${score}%`
  }

  const formatRating = (rating) => {
    if (rating === null || rating === undefined) return '--'
    return rating.toFixed(1)
  }

  const formatRentalYield = (yieldVal) => {
    if (yieldVal === null || yieldVal === undefined) return '--'
    return `${yieldVal.toFixed(1)}%`
  }

  const getMomentumIcon = (momentum) => {
    if (!momentum) return null
    switch (momentum) {
      case 'rising': return <span style={styles.momentumIconRising}>↗</span>
      case 'falling': return <span style={styles.momentumIconFalling}>↘</span>
      case 'stable': return <span style={styles.momentumIconStable}>➡</span>
      default: return null
    }
  }

  const getScoreColor = (score) => {
    if (score === null || score === undefined) return '#64748b'
    if (score >= 80) return '#34d399'
    if (score >= 60) return '#fbbf24'
    return '#f87171'
  }

  const getRatingColor = (rating) => {
    if (rating === null || rating === undefined) return '#64748b'
    if (rating >= 4.0) return '#34d399'
    if (rating >= 3.0) return '#fbbf24'
    return '#f87171'
  }

  const renderAreaContent = () => (
    <>
      <div style={styles.areaHeader}>
        <span style={styles.areaName}>{locality}</span>
        <span style={styles.areaPlace}>{place}</span>
      </div>
      
      {/* Ratings Row - Only show if we have review data */}
      {(overallRating || vastuScore || schoolScore || transportScore || safetyScore) && (
        <div style={styles.ratingsRow}>
          {overallRating && (
            <div style={styles.ratingBadge} title="Overall Rating">
              <span style={{ ...styles.ratingVal, color: getRatingColor(overallRating) }}>★ {formatRating(overallRating)}</span>
            </div>
          )}
          {verifiedReviews && verifiedReviews > 0 && (
            <span style={styles.reviewCount}>{verifiedReviews} reviews</span>
          )}
        </div>
      )}

      {/* Category Ratings */}
      {(vastuScore || schoolScore || transportScore || safetyScore) && (
        <div style={styles.categoryRatings}>
          {vastuScore && <span style={styles.categoryPill} title="Vastu">🧭 {formatRating(vastuScore)}</span>}
          {schoolScore && <span style={styles.categoryPill} title="Schools">🏫 {formatRating(schoolScore)}</span>}
          {transportScore && <span style={styles.categoryPill} title="Transport">🚌 {formatRating(transportScore)}</span>}
          {safetyScore && <span style={styles.categoryPill} title="Safety">🛡️ {formatRating(safetyScore)}</span>}
        </div>
      )}
      
      {/* Metrics Row */}
      <div style={styles.metricsRow}>
        {pricePerSqft && (
          <div style={styles.metric}>
            <span style={styles.metricVal}>
              {isLoading ? '...' : `₹${pricePerSqft >= 10000 ? (pricePerSqft / 1000).toFixed(0) + 'k' : pricePerSqft}`}
            </span>
            <span style={styles.metricLbl}>ft²</span>
          </div>
        )}
        {sentimentScore != null && (
          <div style={styles.metric}>
            <span style={{ ...styles.metricVal, color: getScoreColor(sentimentScore) }}>
              {isLoading ? '...' : formatScore(sentimentScore)}
            </span>
            <span style={styles.metricLbl}>Sentiment</span>
          </div>
        )}
        {investmentScore != null && (
          <div style={styles.metric}>
            <span style={{ ...styles.metricVal, color: getScoreColor(investmentScore) }}>
              {isLoading ? '...' : formatScore(investmentScore)}
            </span>
            <span style={styles.metricLbl}>Inv</span>
          </div>
        )}
      </div>

      {/* Secondary Metrics Row */}
      <div style={styles.metricsRow}>
        {rentalYieldAvg && (
          <div style={styles.metric}>
            <span style={{ ...styles.metricVal, color: '#10b981' }}>
              {isLoading ? '...' : formatRentalYield(rentalYieldAvg)}
            </span>
            <span style={styles.metricLbl}>Yield</span>
          </div>
        )}
        {connectivityScore != null && (
          <div style={styles.metric}>
            <span style={{ ...styles.metricVal, color: getScoreColor(connectivityScore) }}>
              {isLoading ? '...' : formatScore(connectivityScore)}
            </span>
            <span style={styles.metricLbl}>Conn</span>
          </div>
        )}
        {priceMomentum && (
          <div style={styles.metric}>
            <span style={{ ...styles.metricVal, display: 'flex', alignItems: 'center', gap: '2px' }}>
              {isLoading ? '...' : getMomentumIcon(priceMomentum)}
              {!isLoading && <span style={{ fontSize: '10px', textTransform: 'capitalize' }}>{priceMomentum}</span>}
            </span>
            <span style={styles.metricLbl}>Trend</span>
          </div>
        )}
      </div>
    </>
  )

  const renderPropertyContent = () => {
    const prop = hasMultipleProperties && tabs.length > 0 ? tabs[currentTab] : propertyData
    
    if (!prop) return null

    return (
      <>
        {prop.name && !/^Property\s*\d+$/i.test(prop.name) && (
          <div style={styles.propName}>{prop.name}</div>
        )}
        <div style={styles.propRow}>
          {prop.bhk && <span style={styles.propTag}>{prop.bhk}BHK</span>}
          <span style={styles.propPrice}>{formatPrice(prop.price)}</span>
        </div>
        <div style={styles.propTags}>
          {prop.propertyType && <span style={styles.propTag}>{prop.propertyType}</span>}
          {prop.sqft && <span style={styles.propTag}>{formatSqft(prop.sqft)}</span>}
          {prop.furnishing && <span style={styles.propTag}>{prop.furnishing}</span>}
        </div>
      </>
    )
  }

  const renderBuildingContent = () => {
    if (!buildingData) return null

    return (
      <>
        <span style={{ ...styles.typeBadge, backgroundColor: themeColor + '20', color: themeColor }}>
          Building
        </span>
        <div style={styles.buildingName}>{buildingData.name || 'Building'}</div>
        <div style={styles.buildingMeta}>
          {[buildingData.levels && `${buildingData.levels} floors`, buildingData.height && `${buildingData.height}m`, buildingData.area && formatSqft(buildingData.area)].filter(Boolean).join(' · ')}
        </div>
      </>
    )
  }

  const renderContent = () => {
    switch (type) {
      case 'property': return renderPropertyContent()
      case 'building': return renderBuildingContent()
      case 'area':
      default: return renderAreaContent()
    }
  }

  return (
    <div 
      style={{ ...styles.container, left: x, top: y, zIndex }}
      onClick={onFocus}
    >
      <div style={styles.wrapper}>
        <div style={styles.anchorContainer}>
          {isLoading ? (
            <div style={styles.anchorLoading} />
          ) : (
            <div style={{ ...styles.anchor, backgroundColor: themeColor, boxShadow: `0 0 12px ${themeColor}, 0 0 24px ${themeColor}80` }}>
              <div style={styles.anchorInner} />
            </div>
          )}
        </div>

        <div style={styles.beamContainer}>
          <div style={{ ...styles.beamGlow, backgroundColor: themeColor }} />
          <div style={{ ...styles.beam, backgroundColor: themeColor }} />
        </div>

        {!isLoading && (
          <div style={styles.particlesContainer}>
            <div style={{ ...styles.particle, backgroundColor: themeColor, animationDelay: '0s' }} />
            <div style={{ ...styles.particle, backgroundColor: themeColor, animationDelay: '0.5s' }} />
            <div style={{ ...styles.particle, backgroundColor: themeColor, animationDelay: '1s' }} />
          </div>
        )}

        <div style={{
          ...styles.labelContainer,
          opacity: showLabel ? 1 : 0,
          transform: showLabel ? 'translateX(-50%) translateY(0)' : 'translateX(-50%) translateY(10px)'
        }}>
          <div style={{ ...styles.labelCard, borderTopColor: themeColor }}>
            <div style={styles.cardHeader}>
              <div style={styles.cardHeaderLeft}>
                {onLocateMe && (
                  <button onClick={handleLocateMe} style={styles.headerBtn} title="Center">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="12" cy="12" r="3" />
                      <path d="M12 2v4M12 18v4M2 12h4M18 12h4" />
                    </svg>
                  </button>
                )}
              </div>
              <div style={styles.cardHeaderRight}>
                {onClose && (
                  <button onClick={onClose} style={styles.headerBtn} title="Close">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <path d="M18 6L6 18M6 6l12 12" />
                    </svg>
                  </button>
                )}
              </div>
            </div>
            {isLoading ? (
              <div style={styles.loadingRow}>
                <span style={styles.loadingDot} />
                <span style={styles.loadingText}>Analyzing...</span>
              </div>
            ) : (
              <div style={styles.content}>
                {renderContent()}
              </div>
            )}
          </div>
          <div style={{ ...styles.pointer, borderTopColor: themeColor }} />
        </div>
      </div>

      <style>{`
        @keyframes beamGrow {
          0% { height: 0px; opacity: 0; }
          50% { opacity: 0.6; height: 120px; }
          100% { height: 0px; opacity: 0; }
        }
        @keyframes float {
          0%, 100% { transform: translateX(-50%) translateY(0px); }
          50% { transform: translateX(-50%) translateY(-3px); }
        }
        @keyframes particleFloat {
          0% { transform: translateY(0); opacity: 0; }
          20% { opacity: 1; }
          100% { transform: translateY(-120px); opacity: 0; }
        }
        @keyframes anchorPulse {
          0%, 100% { transform: translateX(-50%) scale(1); }
          50% { transform: translateX(-50%) scale(1.2); }
        }
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
      `}</style>
    </div>
  )
}

const styles = {
  container: {
    position: 'absolute',
    transform: 'translate(-50%, 0%)',
    zIndex: 50,
    pointerEvents: 'auto'
  },
  wrapper: {
    position: 'relative',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center'
  },
  anchorContainer: {
    position: 'absolute',
    left: '50%',
    transform: 'translateX(-50%)',
    bottom: 0,
    zIndex: 30
  },
  anchor: {
    width: '12px',
    height: '12px',
    borderRadius: '50%',
    boxShadow: `0 0 12px #8b5cf6, 0 0 24px #8b5cf680`,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center'
  },
  anchorInner: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    backgroundColor: '#fff'
  },
  anchorLoading: {
    width: '12px',
    height: '12px',
    borderRadius: '50%',
    backgroundColor: '#f59e0b',
    animation: 'pulse 1s infinite'
  },
  beamContainer: {
    position: 'absolute',
    left: '50%',
    transform: 'translateX(-50%)',
    bottom: '6px',
    width: '3px',
    height: '120px',
    overflow: 'hidden',
    zIndex: 20
  },
  beamGlow: {
    position: 'absolute',
    top: 0,
    left: '-4px',
    width: '10px',
    height: '100%',
    opacity: 0.3,
    filter: 'blur(8px)'
  },
  beam: {
    width: '100%',
    height: '100%',
    opacity: 0.4,
    animation: 'beamGrow 2s ease-in-out infinite'
  },
  particlesContainer: {
    position: 'absolute',
    left: '50%',
    transform: 'translateX(-50%)',
    bottom: '10px',
    width: '4px',
    height: '120px',
    overflow: 'hidden',
    zIndex: 25
  },
  particle: {
    position: 'absolute',
    bottom: 0,
    left: '50%',
    width: '4px',
    height: '4px',
    borderRadius: '50%',
    animation: 'particleFloat 2s ease-out infinite'
  },
  labelContainer: {
    position: 'absolute',
    left: '50%',
    transform: 'translateX(-50%)',
    bottom: '145px',
    zIndex: 40,
    transition: 'all 0.3s ease',
    animation: 'float 3s ease-in-out infinite'
  },
  labelCard: {
    position: 'relative',
    backgroundColor: 'rgba(15, 23, 42, 0.98)',
    backdropFilter: 'blur(16px)',
    borderRadius: '8px',
    borderTop: '2px solid #8b5cf6',
    minWidth: '180px',
    maxWidth: '220px',
    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.5), 0 0 0 1px rgba(255, 255, 255, 0.05)',
    overflow: 'hidden'
  },
  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '6px 8px',
    borderBottom: '1px solid rgba(255, 255, 255, 0.06)'
  },
  cardHeaderLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px'
  },
  cardHeaderRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px'
  },
  headerBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '20px',
    height: '20px',
    padding: 0,
    border: 'none',
    borderRadius: '4px',
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    color: '#94a3b8',
    cursor: 'pointer'
  },
  content: {
    padding: '6px 8px'
  },
  areaHeader: {
    marginBottom: '8px'
  },
  areaName: {
    fontSize: '13px',
    fontWeight: '600',
    color: '#f1f5f9',
    display: 'block',
    marginBottom: '3px'
  },
  areaPlace: {
    fontSize: '11px',
    color: '#64748b'
  },
  ratingsRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '6px',
    paddingBottom: '6px',
    borderBottom: '1px solid rgba(255, 255, 255, 0.06)'
  },
  ratingBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px'
  },
  ratingVal: {
    fontSize: '12px',
    fontWeight: '700'
  },
  reviewCount: {
    fontSize: '9px',
    color: '#64748b'
  },
  categoryRatings: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '4px',
    marginBottom: '8px'
  },
  categoryPill: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '2px',
    padding: '2px 6px',
    backgroundColor: 'rgba(255, 255, 255, 0.06)',
    borderRadius: '10px',
    fontSize: '9px',
    color: '#94a3b8'
  },
  momentumIconRising: {
    color: '#34d399',
    fontSize: '12px',
    fontWeight: '700'
  },
  momentumIconFalling: {
    color: '#f87171',
    fontSize: '12px',
    fontWeight: '700'
  },
  momentumIconStable: {
    color: '#fbbf24',
    fontSize: '12px',
    fontWeight: '700'
  },
  metricsRow: {
    display: 'flex',
    gap: '8px',
    paddingTop: '8px',
    borderTop: '1px solid rgba(255, 255, 255, 0.06)'
  },
  metric: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    flex: 1
  },
  metricVal: {
    fontSize: '12px',
    fontWeight: '700',
    color: '#e2e8f0'
  },
  metricLbl: {
    fontSize: '9px',
    color: '#64748b',
    textTransform: 'uppercase',
    letterSpacing: '0.3px',
    marginTop: '2px'
  },
  tabsRow: {
    display: 'flex',
    gap: '6px',
    marginBottom: '10px',
    alignItems: 'center'
  },
  tab: {
    padding: '4px 10px',
    borderRadius: '4px',
    border: 'none',
    fontSize: '11px',
    fontWeight: '600',
    cursor: 'pointer'
  },
  propRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    marginBottom: '8px'
  },
  propName: {
    fontSize: '12px',
    fontWeight: '600',
    color: '#f1f5f9',
    marginBottom: '8px',
    wordBreak: 'break-word'
  },
  propTags: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '6px',
    flex: 1
  },
  propPrice: {
    fontSize: '16px',
    fontWeight: '700',
    color: '#10b981',
    whiteSpace: 'nowrap'
  },
  propMetaRow: {
    display: 'flex',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: '6px'
  },
  propTag: {
    display: 'inline-block',
    padding: '3px 8px',
    backgroundColor: 'rgba(255, 255, 255, 0.06)',
    borderRadius: '4px',
    fontSize: '9px',
    color: '#94a3b8'
  },
  propPriceSub: {
    fontSize: '9px',
    color: '#64748b',
    marginTop: '4px'
  },
  typeBadge: {
    display: 'inline-block',
    padding: '2px 6px',
    borderRadius: '4px',
    fontSize: '9px',
    fontWeight: '600',
    textTransform: 'uppercase',
    letterSpacing: '0.3px',
    marginBottom: '4px'
  },
  buildingName: {
    fontSize: '11px',
    fontWeight: '600',
    color: '#f1f5f9',
    marginBottom: '2px'
  },
  buildingMeta: {
    fontSize: '10px',
    color: '#64748b'
  },
  locationName: {
    fontSize: '11px',
    fontWeight: '600',
    color: '#f1f5f9',
    marginBottom: '2px'
  },
  locationPlace: {
    fontSize: '10px',
    color: '#64748b'
  },
  pointer: {
    position: 'absolute',
    bottom: '-6px',
    left: '50%',
    transform: 'translateX(-50%)',
    width: 0,
    height: 0,
    borderLeft: '6px solid transparent',
    borderRight: '6px solid transparent',
    borderTop: '6px solid #8b5cf6'
  },
  loadingRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '8px 0'
  },
  loadingDot: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    backgroundColor: '#f59e0b',
    animation: 'pulse 1s infinite'
  },
  loadingText: {
    fontSize: '11px',
    color: '#94a3b8'
  }
}
