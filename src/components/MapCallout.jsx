import { useEffect, useState } from 'react'

const TYPE_COLORS = {
  area: '#8b5cf6',
  property: '#10b981',
  location: '#f59e0b',
  building: '#f43f5e'
}

const TYPE_LABELS = {
  area: 'Area',
  property: 'Property',
  location: 'Location',
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
  buildingCount = 0,
  pricePerSqft = null,
  investmentScore = null,
  connectivityScore = null,
  status = 'Live',
  isLoading = false,
  propertyData = null,
  buildingData = null,
  onClose,
  onPropertyClick,
  onBuildingClick,
  // New props for grouped properties
  hasMultipleProperties = false,
  tabs = [],
  activeTabIndex = 0,
  onTabChange,
  allProperties = [],
  onLocateMe
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

  const activeProperty = hasMultipleProperties && tabs.length > 0 ? tabs[currentTab] : null

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
    return `${Number(sqft).toLocaleString()} sqft`
  }

  const formatScore = (score) => {
    if (score === null || score === undefined) return '--'
    return `${score}%`
  }

  const getScoreColor = (score) => {
    if (score === null || score === undefined) return '#64748b'
    if (score >= 80) return '#34d399'
    if (score >= 60) return '#fbbf24'
    return '#f87171'
  }

  const getStatusBadge = () => {
    if (isLoading) {
      return (
        <span style={styles.statusBadge}>
          <span style={styles.statusDotLoading} />
          Analyzing
        </span>
      )
    }
    if (status === 'Live') {
      return (
        <span style={styles.statusBadgeLive}>
          <span style={{ ...styles.statusDot, backgroundColor: themeColor }} />
          Live
        </span>
      )
    }
    return null
  }

  const handlePropertyClick = () => {
    if (onPropertyClick && propertyData) {
      onPropertyClick(propertyData)
    }
  }

  const handleBuildingClick = () => {
    if (onBuildingClick && buildingData) {
      onBuildingClick(buildingData)
    }
  }

  const renderContent = () => {
    // For properties with tabs (multiple properties at same location)
    if (hasMultipleProperties && tabs.length > 0) {
      const currentProp = tabs[currentTab]
      return (
        <div style={styles.contentSection}>
          {/* Tabs for multiple properties */}
          <div style={styles.tabsContainer}>
            {tabs.map((tab, idx) => (
              <button
                key={idx}
                onClick={() => handleTabClick(idx)}
                style={{
                  ...styles.tab,
                  ...(idx === currentTab ? styles.tabActive : {}),
                  ...(idx === currentTab ? { borderBottomColor: themeColor } : {})
                }}
              >
                {idx + 1}
              </button>
            ))}
            {allProperties.length > 1 && (
              <button onClick={handleLocateMe} style={styles.locateBtn} title="Fit all properties in view">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <circle cx="12" cy="12" r="3" />
                  <path d="M12 2v4M12 18v4M2 12h4M18 12h4" />
                </svg>
              </button>
            )}
          </div>
          
          <div style={styles.header}>
            <div style={styles.headerText}>
              <div style={styles.locality}>{currentProp?.name || 'Property'}</div>
              <div style={styles.place}>{currentProp?.locality || locality || 'Bangalore'}</div>
            </div>
            <span style={styles.statusBadgeLive}>
              <span style={{ ...styles.statusDot, backgroundColor: '#10b981' }} />
              {tabs.length} {tabs.length === 1 ? 'property' : 'properties'} here
            </span>
          </div>
          
          <div style={styles.propertyMainInfo}>
            <div style={styles.propertyPriceRow}>
              <span style={styles.propertyPrice}>{formatPrice(currentProp?.price)}</span>
              {currentProp?.pricePerSqft && (
                <span style={styles.propertyPriceSqft}>₹{currentProp.pricePerSqft}/sqft</span>
              )}
            </div>
          </div>
          
          <div style={styles.propertyDetails}>
            {currentProp?.bhk && <span style={styles.propertyTag}>{currentProp.bhk}BHK</span>}
            {currentProp?.propertyType && <span style={styles.propertyTag}>{currentProp.propertyType}</span>}
            {currentProp?.sqft && <span style={styles.propertyTag}>{formatSqft(currentProp.sqft)}</span>}
            {currentProp?.furnishing && <span style={styles.propertyTag}>{currentProp.furnishing}</span>}
            {currentProp?.propertyAge && <span style={styles.propertyTag}>{currentProp.propertyAge}</span>}
            {currentProp?.parking && <span style={styles.propertyTag}>Parking</span>}
          </div>
        </div>
      )
    }
    
    // Original single property rendering
    switch (type) {
      case 'property':
        return propertyData ? (
          <div style={styles.contentSection}>
            <div style={styles.header}>
              <div style={styles.headerText}>
                <div style={styles.locality}>{propertyData.name || 'Property'}</div>
                <div style={styles.place}>{propertyData.locality || 'Bangalore'}</div>
              </div>
              <span style={styles.statusBadgeLive}>
                <span style={{ ...styles.statusDot, backgroundColor: '#10b981' }} />
                {propertyData.totalProperties ? `${propertyData.totalProperties} found` : 'Available'}
              </span>
            </div>
            
            <div style={styles.propertyMainInfo}>
              <div style={styles.propertyPriceRow}>
                <span style={styles.propertyPrice}>{formatPrice(propertyData.price)}</span>
                {propertyData.pricePerSqft && (
                  <span style={styles.propertyPriceSqft}>₹{propertyData.pricePerSqft}/sqft</span>
                )}
              </div>
            </div>
            
            <div style={styles.propertyDetails}>
              {propertyData.bhk && <span style={styles.propertyTag}>{propertyData.bhk}BHK</span>}
              {propertyData.propertyType && <span style={styles.propertyTag}>{propertyData.propertyType}</span>}
              {propertyData.sqft && <span style={styles.propertyTag}>{formatSqft(propertyData.sqft)}</span>}
              {propertyData.furnishing && <span style={styles.propertyTag}>{propertyData.furnishing}</span>}
              {propertyData.propertyAge && <span style={styles.propertyTag}>{propertyData.propertyAge}</span>}
              {propertyData.parking && <span style={styles.propertyTag}>Parking</span>}
            </div>
          </div>
        ) : null

      case 'building':
        return buildingData ? (
          <div style={styles.contentSection}>
            <div style={styles.buildingHeader}>
              <span style={{ ...styles.typeBadge, backgroundColor: themeColor }}>
                Building
              </span>
              {onLocateMe && (
                <button onClick={handleLocateMe} style={styles.locateBtnSmall} title="Center on map">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <circle cx="12" cy="12" r="3" />
                    <path d="M12 2v4M12 18v4M2 12h4M18 12h4" />
                  </svg>
                </button>
              )}
            </div>
            <div style={styles.buildingName}>{buildingData.name || 'Building'}</div>
            <div style={styles.buildingDetails}>
              {buildingData.levels && <span>{buildingData.levels} floors</span>}
              {buildingData.height && <span>· {buildingData.height}m</span>}
              {buildingData.area && <span>· {formatSqft(buildingData.area)}</span>}
            </div>
          </div>
        ) : null

      case 'location':
        return (
          <div style={styles.contentSection}>
            <div style={styles.locationHeader}>
              <span style={{ ...styles.typeBadge, backgroundColor: themeColor }}>
                {TYPE_LABELS[type]}
              </span>
            </div>
            <div style={styles.localityName}>{locality}</div>
            <div style={styles.placeName}>{place}</div>
          </div>
        )

      case 'area':
      default:
        return (
          <>
            <div style={styles.header}>
              <div style={styles.headerText}>
                <div style={styles.locality}>{locality}</div>
                <div style={styles.place}>{place}</div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {getStatusBadge()}
                {onLocateMe && (
                  <button onClick={handleLocateMe} style={styles.locateBtnSmall} title="Center on map">
                    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="12" cy="12" r="3" />
                      <path d="M12 2v4M12 18v4M2 12h4M18 12h4" />
                    </svg>
                  </button>
                )}
              </div>
            </div>

            <div style={styles.metricsGrid}>
              {buildingCount > 0 && (
                <div style={styles.metricBox}>
                  <div style={styles.metricValue}>{isLoading ? '...' : buildingCount.toLocaleString()}</div>
                  <div style={styles.metricLabel}>Bldgs</div>
                </div>
              )}
              {pricePerSqft && (
                <div style={styles.metricBox}>
                  <div style={styles.metricValue}>
                    {isLoading ? '...' : `₹${pricePerSqft >= 10000 ? (pricePerSqft / 1000).toFixed(0) + 'k' : pricePerSqft}`}
                  </div>
                  <div style={styles.metricLabel}>sqft</div>
                </div>
              )}
              {investmentScore != null && (
                <div style={{ ...styles.metricBox }}>
                  <div style={{ ...styles.metricValue, color: getScoreColor(investmentScore) }}>
                    {isLoading ? '...' : formatScore(investmentScore)}
                  </div>
                  <div style={styles.metricLabel}>Inv</div>
                </div>
              )}
              {connectivityScore != null && (
                <div style={{ ...styles.metricBox }}>
                  <div style={{ ...styles.metricValue, color: getScoreColor(connectivityScore) }}>
                    {isLoading ? '...' : formatScore(connectivityScore)}
                  </div>
                  <div style={styles.metricLabel}>Conn</div>
                </div>
              )}
            </div>
          </>
        )
    }
  }

  return (
    <div style={{ ...styles.container, left: x, top: y }}>
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
            <div style={{ ...styles.cardGlow, backgroundColor: themeColor }} />
            {renderContent()}

            <div style={styles.footer}>
              <div style={styles.coords}>{lat?.toFixed(4)}°N, {lng?.toFixed(4)}°E</div>
              {onClose && (
                <button onClick={onClose} style={styles.closeBtn} title="Close">
                  <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="2">
                    <path d="M18 6L6 18M6 6l12 12" />
                  </svg>
                </button>
              )}
            </div>
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
    transition: 'left 0.05s linear, top 0.05s linear',
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
    backgroundColor: '#8b5cf6',
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
  orbContainer: {
    display: 'none'
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
    backgroundColor: 'rgba(15, 23, 42, 0.95)',
    backdropFilter: 'blur(12px)',
    borderRadius: '12px',
    borderTop: '3px solid #8b5cf6',
    padding: '14px 16px',
    minWidth: '200px',
    maxWidth: '280px',
    boxShadow: '0 8px 32px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(255, 255, 255, 0.05)'
  },
  cardGlow: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    height: '80px',
    backgroundColor: '#8b5cf6',
    opacity: 0.05,
    borderRadius: '12px 12px 0 0',
    pointerEvents: 'none'
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '12px'
  },
  headerText: {
    flex: 1
  },
  locality: {
    fontSize: '15px',
    fontWeight: '700',
    color: '#f1f5f9',
    marginBottom: '2px'
  },
  place: {
    fontSize: '12px',
    color: '#94a3b8'
  },
  statusBadge: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    padding: '3px 8px',
    borderRadius: '4px',
    backgroundColor: 'rgba(245, 158, 11, 0.15)',
    fontSize: '10px',
    fontWeight: '600',
    color: '#fbbf24',
    textTransform: 'uppercase',
    letterSpacing: '0.5px'
  },
  statusBadgeLive: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    padding: '3px 8px',
    borderRadius: '4px',
    backgroundColor: 'rgba(16, 185, 129, 0.15)',
    fontSize: '10px',
    fontWeight: '600',
    color: '#34d399',
    textTransform: 'uppercase',
    letterSpacing: '0.5px'
  },
  statusDot: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    backgroundColor: '#34d399'
  },
  statusDotLoading: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    backgroundColor: '#fbbf24',
    animation: 'pulse 1s infinite'
  },
  metricsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(4, 1fr)',
    gap: '8px',
    marginBottom: '10px'
  },
  metricBox: {
    textAlign: 'center',
    padding: '6px 4px',
    backgroundColor: 'rgba(255, 255, 255, 0.03)',
    borderRadius: '6px'
  },
  metricValue: {
    fontSize: '13px',
    fontWeight: '700',
    color: '#e2e8f0'
  },
  metricLabel: {
    fontSize: '9px',
    color: '#64748b',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    marginTop: '2px'
  },
  tabsContainer: {
    display: 'flex',
    gap: '4px',
    marginBottom: '10px',
    alignItems: 'center'
  },
  tab: {
    padding: '4px 10px',
    borderRadius: '4px 4px 0 0',
    border: 'none',
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    color: '#94a3b8',
    fontSize: '11px',
    fontWeight: '600',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    borderBottom: '2px solid transparent'
  },
  tabActive: {
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    color: '#fff'
  },
  locateBtn: {
    marginLeft: 'auto',
    padding: '4px 8px',
    borderRadius: '4px',
    border: 'none',
    backgroundColor: 'rgba(16, 185, 129, 0.2)',
    color: '#10b981',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'all 0.2s ease'
  },
  locateBtnSmall: {
    padding: '4px',
    borderRadius: '4px',
    border: 'none',
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    color: '#94a3b8',
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'all 0.2s ease'
  },
  contentSection: {
    marginBottom: '8px'
  },
  propertyHeader: {
    marginBottom: '6px'
  },
  typeBadge: {
    display: 'inline-block',
    padding: '3px 8px',
    borderRadius: '4px',
    fontSize: '11px',
    fontWeight: '600',
    color: '#fff',
    textTransform: 'uppercase',
    letterSpacing: '0.3px'
  },
  propertyPrice: {
    fontSize: '20px',
    fontWeight: '700',
    color: '#10b981'
  },
  propertyPriceRow: {
    display: 'flex',
    alignItems: 'baseline',
    gap: '10px'
  },
  propertyPriceSqft: {
    fontSize: '12px',
    color: '#94a3b8'
  },
  propertyMainInfo: {
    marginBottom: '10px'
  },
  propertyDetails: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '6px'
  },
  propertyTag: {
    display: 'inline-block',
    padding: '3px 8px',
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderRadius: '4px',
    fontSize: '11px',
    fontWeight: '500',
    color: '#e2e8f0'
  },
  locationHeader: {
    marginBottom: '8px'
  },
  localityName: {
    fontSize: '15px',
    fontWeight: '700',
    color: '#f1f5f9',
    marginBottom: '2px'
  },
  placeName: {
    fontSize: '12px',
    color: '#94a3b8'
  },
  buildingHeader: {
    marginBottom: '6px'
  },
  buildingName: {
    fontSize: '14px',
    fontWeight: '700',
    color: '#f1f5f9',
    marginBottom: '4px'
  },
  buildingDetails: {
    fontSize: '12px',
    color: '#94a3b8'
  },
  actionBtn: {
    marginTop: '10px',
    padding: '6px 12px',
    border: 'none',
    borderRadius: '6px',
    fontSize: '12px',
    fontWeight: '600',
    color: '#fff',
    cursor: 'pointer',
    width: '100%',
    pointerEvents: 'auto'
  },
  footer: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: '10px',
    borderTop: '1px solid rgba(255, 255, 255, 0.08)'
  },
  coords: {
    fontSize: '10px',
    color: '#64748b',
    fontFamily: 'monospace'
  },
  closeBtn: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    width: '20px',
    height: '20px',
    padding: 0,
    border: 'none',
    borderRadius: '4px',
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
    cursor: 'pointer',
    pointerEvents: 'auto'
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
  }
}
