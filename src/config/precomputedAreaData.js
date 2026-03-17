/**
 * PRECOMPUTED AREA DATA
 * =====================
 * This file contains precomputed market data for map callouts.
 * 
 * UPDATE FREQUENCY: Monthly (every 30 days)
 * LAST UPDATED: 2026-03-17
 * NEXT UPDATE: 2026-04-17
 * 
 * Source: Bangalore real estate market data
 * 
 * To update:
 * 1. Refresh market data from API/database
 * 2. Update values below
 * 3. Update LASTPDATED to current date
 * 4. Update NEXT UPDATE to +30 days
 */

export const AREA_PRECOMPUTED_DATA = {
  indiranagar: {
    buildingCount: 245,
    pricePerSqft: 12500,
    investmentScore: 82,
    connectivityScore: 91
  },
  hebbal: {
    buildingCount: 180,
    pricePerSqft: 9800,
    investmentScore: 78,
    connectivityScore: 85
  },
  whitefield: {
    buildingCount: 320,
    pricePerSqft: 11000,
    investmentScore: 88,
    connectivityScore: 79
  },
  koramangala: {
    buildingCount: 280,
    pricePerSqft: 14500,
    investmentScore: 75,
    connectivityScore: 94
  },
  jayanagar: {
    buildingCount: 195,
    pricePerSqft: 9200,
    investmentScore: 72,
    connectivityScore: 81
  },
  mgroad: {
    buildingCount: 156,
    pricePerSqft: 16800,
    investmentScore: 68,
    connectivityScore: 96
  },
  electroniccity: {
    buildingCount: 410,
    pricePerSqft: 7500,
    investmentScore: 91,
    connectivityScore: 72
  },
  malleshwaram: {
    buildingCount: 165,
    pricePerSqft: 10500,
    investmentScore: 74,
    connectivityScore: 83
  },
  hennur: {
    buildingCount: 210,
    pricePerSqft: 8800,
    investmentScore: 76,
    connectivityScore: 78
  },
  bellandur: {
    buildingCount: 290,
    pricePerSqft: 10200,
    investmentScore: 84,
    connectivityScore: 82
  },
  marathahalli: {
    buildingCount: 235,
    pricePerSqft: 9500,
    investmentScore: 79,
    connectivityScore: 88
  }
};

export const DATA_VERSION = {
  lastUpdated: '2026-03-17',
  nextUpdate: '2026-04-17',
  updateFrequencyDays: 30
};

export default AREA_PRECOMPUTED_DATA;
