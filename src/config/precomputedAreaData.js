/**
 * PRECOMPUTED AREA DATA
 * =====================
 * This file contains precomputed market data for map callouts.
 * 
 * UPDATE FREQUENCY: Weekly (market sentiment) + Monthly (reviews)
 * LAST UPDATED: 2026-03-18
 * NEXT UPDATE: 2026-03-25
 * 
 * Source: Bangalore real estate market data + Community Pulse
 * 
 * Data includes:
 * - Market sentiment scores (demand, supply, sentiment)
 * - Rental yield averages
 * - Price momentum indicators
 * - Locality review ratings (Vastu, School, Transport, Safety)
 * 
 * To update:
 * 1. Refresh market data from API/database (market_sentiment table)
 * 2. Refresh reviews from locality_reviews table
 * 3. Update values below
 * 4. Update LAST_UPDATED to current date
 * 5. Update NEXT_UPDATE based on refresh frequency
 */

export const AREA_PRECOMPUTED_DATA = {
  indiranagar: {
    pricePerSqft: 12500,
    investmentScore: 82,
    connectivityScore: 91,
    sentimentScore: 78,
    demandScore: 82,
    supplyScore: 65,
    rentalYieldAvg: 4.2,
    priceMomentum: 'rising',
    daysOnMarket: 45,
    overallRating: 4.3,
    vastuScore: 3.8,
    schoolScore: 4.5,
    transportScore: 4.2,
    safetyScore: 4.4,
    verifiedReviews: 32
  },
  hebbal: {
    pricePerSqft: 9800,
    investmentScore: 78,
    connectivityScore: 85,
    sentimentScore: 72,
    demandScore: 75,
    supplyScore: 70,
    rentalYieldAvg: 4.8,
    priceMomentum: 'stable',
    daysOnMarket: 52,
    overallRating: 4.1,
    vastuScore: 4.0,
    schoolScore: 4.3,
    transportScore: 3.9,
    safetyScore: 4.2,
    verifiedReviews: 24
  },
  whitefield: {
    pricePerSqft: 11000,
    investmentScore: 88,
    connectivityScore: 79,
    sentimentScore: 85,
    demandScore: 88,
    supplyScore: 55,
    rentalYieldAvg: 4.5,
    priceMomentum: 'rising',
    daysOnMarket: 38,
    overallRating: 4.4,
    vastuScore: 4.2,
    schoolScore: 4.6,
    transportScore: 3.8,
    safetyScore: 4.0,
    verifiedReviews: 48
  },
  koramangala: {
    pricePerSqft: 14500,
    investmentScore: 75,
    connectivityScore: 94,
    sentimentScore: 80,
    demandScore: 85,
    supplyScore: 45,
    rentalYieldAvg: 3.8,
    priceMomentum: 'rising',
    daysOnMarket: 35,
    overallRating: 4.5,
    vastuScore: 3.5,
    schoolScore: 4.7,
    transportScore: 4.5,
    safetyScore: 4.3,
    verifiedReviews: 56
  },
  jayanagar: {
    pricePerSqft: 9200,
    investmentScore: 72,
    connectivityScore: 81,
    sentimentScore: 68,
    demandScore: 70,
    supplyScore: 75,
    rentalYieldAvg: 4.1,
    priceMomentum: 'stable',
    daysOnMarket: 55,
    overallRating: 4.2,
    vastuScore: 4.3,
    schoolScore: 4.4,
    transportScore: 3.7,
    safetyScore: 4.5,
    verifiedReviews: 28
  },
  mgroad: {
    pricePerSqft: 16800,
    investmentScore: 68,
    connectivityScore: 96,
    sentimentScore: 74,
    demandScore: 78,
    supplyScore: 40,
    rentalYieldAvg: 3.5,
    priceMomentum: 'stable',
    daysOnMarket: 42,
    overallRating: 4.0,
    vastuScore: 3.2,
    schoolScore: 4.1,
    transportScore: 4.8,
    safetyScore: 4.1,
    verifiedReviews: 22
  },
  electroniccity: {
    pricePerSqft: 7500,
    investmentScore: 91,
    connectivityScore: 72,
    sentimentScore: 88,
    demandScore: 90,
    supplyScore: 60,
    rentalYieldAvg: 5.2,
    priceMomentum: 'rising',
    daysOnMarket: 32,
    overallRating: 4.1,
    vastuScore: 4.5,
    schoolScore: 3.9,
    transportScore: 3.5,
    safetyScore: 4.2,
    verifiedReviews: 35
  },
  malleshwaram: {
    pricePerSqft: 10500,
    investmentScore: 74,
    connectivityScore: 83,
    sentimentScore: 70,
    demandScore: 72,
    supplyScore: 68,
    rentalYieldAvg: 4.3,
    priceMomentum: 'stable',
    daysOnMarket: 50,
    overallRating: 4.3,
    vastuScore: 4.6,
    schoolScore: 4.5,
    transportScore: 3.8,
    safetyScore: 4.4,
    verifiedReviews: 26
  },
  hennur: {
    pricePerSqft: 8800,
    investmentScore: 76,
    connectivityScore: 78,
    sentimentScore: 74,
    demandScore: 76,
    supplyScore: 62,
    rentalYieldAvg: 4.6,
    priceMomentum: 'rising',
    daysOnMarket: 40,
    overallRating: 4.0,
    vastuScore: 4.1,
    schoolScore: 3.8,
    transportScore: 3.6,
    safetyScore: 3.9,
    verifiedReviews: 18
  },
  bellandur: {
    pricePerSqft: 10200,
    investmentScore: 84,
    connectivityScore: 82,
    sentimentScore: 82,
    demandScore: 85,
    supplyScore: 58,
    rentalYieldAvg: 4.4,
    priceMomentum: 'rising',
    daysOnMarket: 36,
    overallRating: 4.2,
    vastuScore: 3.9,
    schoolScore: 4.3,
    transportScore: 4.0,
    safetyScore: 3.8,
    verifiedReviews: 42
  },
  marathahalli: {
    pricePerSqft: 9500,
    investmentScore: 79,
    connectivityScore: 88,
    sentimentScore: 76,
    demandScore: 80,
    supplyScore: 55,
    rentalYieldAvg: 4.3,
    priceMomentum: 'stable',
    daysOnMarket: 44,
    overallRating: 4.1,
    vastuScore: 3.7,
    schoolScore: 4.0,
    transportScore: 4.3,
    safetyScore: 3.9,
    verifiedReviews: 30
  },
  hsrlayout: {
    pricePerSqft: 11500,
    investmentScore: 86,
    connectivityScore: 90,
    sentimentScore: 84,
    demandScore: 86,
    supplyScore: 52,
    rentalYieldAvg: 4.7,
    priceMomentum: 'rising',
    daysOnMarket: 34,
    overallRating: 4.5,
    vastuScore: 4.0,
    schoolScore: 4.6,
    transportScore: 4.4,
    safetyScore: 4.3,
    verifiedReviews: 52
  },
  sarjapurroad: {
    pricePerSqft: 9200,
    investmentScore: 87,
    connectivityScore: 75,
    sentimentScore: 86,
    demandScore: 89,
    supplyScore: 58,
    rentalYieldAvg: 5.0,
    priceMomentum: 'rising',
    daysOnMarket: 30,
    overallRating: 4.3,
    vastuScore: 4.4,
    schoolScore: 4.2,
    transportScore: 3.6,
    safetyScore: 4.1,
    verifiedReviews: 38
  },
  jp_nagar: {
    pricePerSqft: 10200,
    investmentScore: 77,
    connectivityScore: 84,
    sentimentScore: 72,
    demandScore: 74,
    supplyScore: 65,
    rentalYieldAvg: 4.2,
    priceMomentum: 'stable',
    daysOnMarket: 48,
    overallRating: 4.2,
    vastuScore: 4.3,
    schoolScore: 4.5,
    transportScore: 3.9,
    safetyScore: 4.4,
    verifiedReviews: 34
  },
  banashankari: {
    pricePerSqft: 9400,
    investmentScore: 73,
    connectivityScore: 80,
    sentimentScore: 67,
    demandScore: 68,
    supplyScore: 72,
    rentalYieldAvg: 4.0,
    priceMomentum: 'stable',
    daysOnMarket: 56,
    overallRating: 4.1,
    vastuScore: 4.4,
    schoolScore: 4.3,
    transportScore: 3.6,
    safetyScore: 4.5,
    verifiedReviews: 25
  },
  yelahanka: {
    pricePerSqft: 7800,
    investmentScore: 71,
    connectivityScore: 70,
    sentimentScore: 65,
    demandScore: 65,
    supplyScore: 78,
    rentalYieldAvg: 5.1,
    priceMomentum: 'stable',
    daysOnMarket: 58,
    overallRating: 3.9,
    vastuScore: 4.5,
    schoolScore: 3.7,
    transportScore: 3.4,
    safetyScore: 4.3,
    verifiedReviews: 15
  }
};

export const DATA_VERSION = {
  lastUpdated: '2026-03-18',
  nextUpdate: '2026-03-25',
  updateFrequencyDays: 7,
  dataSources: ['market_sentiment', 'locality_reviews']
};

export default AREA_PRECOMPUTED_DATA;
