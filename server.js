import express from 'express'
import cors from 'cors'
import dotenv from 'dotenv'
import OpenAI from 'openai'
import axios from 'axios'

// Load environment variables
dotenv.config()

const app = express()
const PORT = process.env.PORT || 3001
const DMPE_API_URL = process.env.DMPE_API_URL || 'http://localhost:8000'

// Middleware
app.use(cors())
app.use(express.json())

// Initialize OpenRouter (OpenAI-compatible API)
const openai = new OpenAI({
  apiKey: process.env.OPENROUTER_API_KEY,
  baseURL: 'https://openrouter.ai/api/v1',
  defaultHeaders: {
    'HTTP-Referer': 'http://localhost:3000',
    'X-Title': 'Valora AI'
  }
})

app.post('/api/ai/analyze', async (req, res) => {
  try {
    const { query } = req.body
    if (!query) {
      return res.status(400).json({ error: 'Query is required' })
    }

    const q = String(query || '').toLowerCase()
    const knownCities = ['bangalore', 'bengaluru', 'mumbai', 'delhi', 'hyderabad', 'pune', 'chennai']
    let cityParam = null
    for (const c of knownCities) {
      if (q.includes(c)) {
        cityParam = c === 'bengaluru' ? 'Bangalore' : c.charAt(0).toUpperCase() + c.slice(1)
        break
      }
    }

    let propertyType = null
    if (q.includes('apartment') || q.includes('flat')) propertyType = 'residential_apartment'
    else if (q.includes('house') || q.includes('villa')) propertyType = 'residential_house'
    else if (q.includes('plot')) propertyType = 'residential_plot'
    else if (q.includes('office')) propertyType = 'commercial_office'
    else if (q.includes('shop') || q.includes('retail')) propertyType = 'commercial_shop'
    else if (q.includes('warehouse')) propertyType = 'commercial_warehouse'
    else if (q.includes('industrial')) propertyType = 'commercial_industrial'
    else if (q.includes('agricultur')) propertyType = 'agricultural_land'

    let listingType = null
    if (q.includes('rent') || q.includes('lease')) listingType = 'rent'
    if (q.includes('sale') || q.includes('buy') || q.includes('sell')) listingType = 'sale'

    let summary = null
    let hotspots = []
    let priceDistribution = null
    let topProperties = []
    let ragMatches = []
    try {
      const summaryResp = await axios.get(`${DMPE_API_URL}/api/market/summary`)
      summary = summaryResp.data
    } catch (e) {}

    const chosenCity = cityParam || (summary?.cities && summary.cities[0]) || null

    try {
      const hotResp = await axios.get(`${DMPE_API_URL}/api/market/hotspots`, { params: { city: chosenCity || undefined } })
      hotspots = hotResp.data?.hotspots || []
    } catch (e) {}

    try {
      const distResp = await axios.get(`${DMPE_API_URL}/api/analytics/price-distribution`, { params: { city: chosenCity || undefined, property_type: propertyType || undefined } })
      priceDistribution = distResp.data
    } catch (e) {}

    // Desired count from query (e.g., "top 10 properties")
    let desiredCount = 10
    const countMatch = q.match(/top\s+(\d+)/) || q.match(/(\d+)\s+properties/)
    if (countMatch && countMatch[1]) desiredCount = Math.min(50, parseInt(countMatch[1], 10) || 10)

    // Get top properties for city/type
    try {
      const topResp = await axios.get(`${DMPE_API_URL}/api/properties/top`, {
        params: {
          city: chosenCity || undefined,
          property_type: propertyType || undefined,
          limit: desiredCount,
          sort_by: 'investment_score',
          order: 'desc'
        }
      })
      topProperties = topResp.data?.properties || []
    } catch (e) {}

    // Try Pinecone RAG retrieval when configured
    try {
      const ragResp = await axios.post(`${DMPE_API_URL}/api/rag/query`, {
        query,
        top_k: desiredCount,
        city: chosenCity || undefined,
        property_type: propertyType || undefined
      })
      ragMatches = ragResp.data?.matches || []
    } catch (e) {}

    let priceStats = null
    if (summary?.price_analysis && chosenCity && summary.price_analysis[chosenCity]) {
      const typesObj = summary.price_analysis[chosenCity]
      if (propertyType && typesObj[propertyType]) priceStats = typesObj[propertyType]
      else {
        const firstKey = Object.keys(typesObj)[0]
        if (firstKey) priceStats = typesObj[firstKey]
      }
    }

    const topLocalities = Array.isArray(hotspots)
      ? hotspots.slice(0, 5).map(h => `${h.locality} (score ${typeof h.investment_score === 'number' ? h.investment_score.toFixed(2) : h.investment_score || ''})`).join(', ')
      : ''

    const contextLines = []
    if (chosenCity) contextLines.push(`City: ${chosenCity}`)
    if (propertyType) contextLines.push(`Property type: ${propertyType}`)
    if (listingType) contextLines.push(`Listing type: ${listingType}`)
    if (priceStats) {
      contextLines.push(`Avg price: ${Math.round(priceStats.avg_price || 0)}`)
      contextLines.push(`Median price: ${Math.round(priceStats.median_price || 0)}`)
      if (priceStats.avg_price_per_sqft) contextLines.push(`Avg price/sqft: ${Math.round(priceStats.avg_price_per_sqft)}`)
      contextLines.push(`Samples: ${priceStats.count || 0}`)
    }
    if (topLocalities) contextLines.push(`Hotspots: ${topLocalities}`)
    const marketContext = contextLines.join('\n')

    const messages = [
      { role: 'system', content: 'You are Valora AI integrated with a market engine. Use provided market context to answer. Be concise, numeric, and actionable.' },
      { role: 'system', content: `Market context:\n${marketContext}` },
      { role: 'system', content: `Top properties: ${(topProperties || []).slice(0,5).map(p => `${p.locality || ''} ₹${Math.round(p.price || 0)}`).join('; ')}` },
      { role: 'user', content: query }
    ]

    let aiResponse = ''
    try {
      const completion = await openai.chat.completions.create({
        model: process.env.OPENROUTER_MODEL || 'mistral-7b-instruct',
        messages,
        temperature: 0.4,
        max_tokens: 600
      })
      aiResponse = completion.choices[0]?.message?.content || ''
    } catch (llmErr) {
      console.warn('OpenRouter call failed, returning fallback analysis:', llmErr?.message)
      const bullets = []
      if (chosenCity) bullets.push(`City: ${chosenCity}`)
      if (propertyType) bullets.push(`Type: ${propertyType}`)
      if (priceStats) bullets.push(`Median: ₹${Math.round(priceStats.median_price || 0).toLocaleString()}`)
      if (Array.isArray(hotspots) && hotspots.length) bullets.push(`Hotspots: ${hotspots.slice(0,3).map(h=>h.locality).join(', ')}`)
      aiResponse = `Here is a quick market snapshot.\n- ${bullets.join('\n- ')}`
    }

    res.json({
      message: aiResponse,
      analysis: {
        city: chosenCity,
        property_type: propertyType,
        listing_type: listingType,
        price_stats: priceStats,
        hotspots,
        price_distribution: priceDistribution,
        top_properties: topProperties,
        rag_matches: ragMatches
      }
    })
  } catch (error) {
    console.error('Error in analyze endpoint:', error.message)
    res.status(500).json({ error: 'Failed to analyze query' })
  }
})

// Chat endpoint
app.post('/api/chat', async (req, res) => {
  try {
    const { message, history } = req.body

    if (!message) {
      return res.status(400).json({ error: 'Message is required' })
    }

    // Prepare messages for OpenRouter
    const messages = [
      {
        role: 'system',
        content: 'You are Valora AI, a friendly and intelligent assistant for a real estate platform. You can have casual conversations, answer general questions, and help with real estate queries. Be conversational, helpful, and engaging. For specific property searches or market analysis, let users know they can ask about properties, prices, locations, or market trends.'
      },
      ...history.map(msg => ({
        role: msg.role,
        content: msg.content
      })),
      {
        role: 'user',
        content: message
      }
    ]

    // Call OpenRouter API (supports multiple models)
    const completion = await openai.chat.completions.create({
      model: process.env.OPENROUTER_MODEL || 'mistral-7b-instruct',
      messages: messages,
      temperature: 0.7,
      max_tokens: 500
    })

    const aiResponse = completion.choices[0].message.content

    res.json({ message: aiResponse })
  } catch (error) {
    console.error('Error calling OpenRouter:', error)
    
    if (error.status === 401) {
      res.status(401).json({ 
        error: 'Invalid OpenRouter API key. Please check your .env file.' 
      })
    } else if (error.status === 429 || error.code === 429) {
      res.status(429).json({ 
        error: 'Rate limit exceeded. Please wait a moment and try again, or consider upgrading at openrouter.ai/credits',
        details: 'Free models have rate limits. Try waiting 10-30 seconds between requests.'
      })
    } else {
      const fallback = "I'm having trouble reaching the AI service right now. I can still help with maps and quick insights. Try asking me to show an area on the map, draw a polygon, or list hotspots."
      res.json({ message: fallback })
    }
  }
})

// Health check endpoint
app.get('/api/health', (req, res) => {
  res.json({ status: 'ok', message: 'Valora AI backend is running' })
})

// DMPE Integration endpoints
app.get('/api/market/summary', async (req, res) => {
  try {
    const response = await axios.get(`${DMPE_API_URL}/api/market/summary`)
    res.json(response.data)
  } catch (error) {
    console.error('Error fetching market summary:', error.message)
    res.status(500).json({ error: 'Failed to fetch market summary' })
  }
})

app.get('/api/market/properties', async (req, res) => {
  try {
    const response = await axios.get(`${DMPE_API_URL}/api/market/properties`, { params: req.query })
    res.json(response.data)
  } catch (error) {
    console.error('Error fetching properties:', error.message)
    res.status(500).json({ error: 'Failed to fetch properties' })
  }
})

app.post('/api/predict/price', async (req, res) => {
  try {
    const response = await axios.post(`${DMPE_API_URL}/api/predict/price`, req.body)
    res.json(response.data)
  } catch (error) {
    console.error('Error predicting price:', error.message)
    res.status(500).json({ error: 'Failed to predict price' })
  }
})

app.get('/api/market/forecast', async (req, res) => {
  try {
    const response = await axios.get(`${DMPE_API_URL}/api/market/forecast`, { params: req.query })
    res.json(response.data)
  } catch (error) {
    console.error('Error generating forecast:', error.message)
    res.status(500).json({ error: 'Failed to generate forecast' })
  }
})

app.get('/api/market/hotspots', async (req, res) => {
  try {
    const response = await axios.get(`${DMPE_API_URL}/api/market/hotspots`, { params: req.query })
    res.json(response.data)
  } catch (error) {
    console.error('Error fetching hotspots:', error.message)
    res.status(500).json({ error: 'Failed to fetch hotspots' })
  }
})

app.post('/api/property/valuation', async (req, res) => {
  try {
    const response = await axios.post(`${DMPE_API_URL}/api/property/valuation`, req.body)
    res.json(response.data)
  } catch (error) {
    console.error('Error generating valuation:', error.message)
    res.status(500).json({ error: 'Failed to generate valuation' })
  }
})

app.get('/api/analytics/price-distribution', async (req, res) => {
  try {
    const response = await axios.get(`${DMPE_API_URL}/api/analytics/price-distribution`, { params: req.query })
    res.json(response.data)
  } catch (error) {
    console.error('Error generating price distribution:', error.message)
    res.status(500).json({ error: 'Failed to generate price distribution' })
  }
})

// Top properties proxy
app.get('/api/properties/top', async (req, res) => {
  try {
    const response = await axios.get(`${DMPE_API_URL}/api/properties/top`, { params: req.query })
    res.json(response.data)
  } catch (error) {
    console.error('Error fetching top properties:', error.message)
    res.status(500).json({ error: 'Failed to fetch top properties' })
  }
})

// RAG query proxy
app.post('/api/rag/query', async (req, res) => {
  try {
    const response = await axios.post(`${DMPE_API_URL}/api/rag/query`, req.body)
    res.json(response.data)
  } catch (error) {
    console.error('Error performing RAG query:', error.message)
    res.status(500).json({ error: 'Failed to run RAG query' })
  }
})

app.listen(PORT, () => {
  console.log(`🚀 Valora AI backend server running on http://localhost:${PORT}`)
  console.log(`📡 Chat API: http://localhost:${PORT}/api/chat`)
  console.log(`🤖 Using model: ${process.env.OPENROUTER_MODEL || 'mistral-7b-instruct'}`)
  
  if (!process.env.OPENROUTER_API_KEY) {
    console.warn('⚠️  WARNING: OPENROUTER_API_KEY not found in .env file')
    console.warn('📝 Get your API key from: https://openrouter.ai/keys')
  }

  })
