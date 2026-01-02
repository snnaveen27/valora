# Valora City Intelligence Engine

> **Version 2.1** | Production Ready | December 2024

The **Valora City Intelligence Engine** is an AI-powered urban real estate platform that transforms raw spatial data into actionable investment intelligence through a layered architecture: **Knowledge Substrate → Reasoning Layer → Narrative Generation → Memory Systems**.

## Core Capabilities

- 🏙️ **City Intelligence Engine** - Ward-level market state, growth phase classification, risk indexing, infrastructure impact simulation
- 📊 **DMPE** (Dynamic Market Prediction Engine) - Price forecasting, rental yield, demand prediction with GIS integration
- 🤖 **Multi-Agent Orchestrator** - 20+ specialized agents via Planner → Executor → Critic → Narrator pipeline
- 🗺️ **Spatial/3D Substrate** - PostGIS analysis, Mappls maps, Three.js Digital Twin viewer
- 🎤 **Voice Interface** - Deepgram-powered speech-to-text and TTS
- 📈 **Self-Learning LLM** - Feedback collection and auto-fine-tuning pipeline

## Features

- 🗺️ **Interactive Map View** - Powered by Mappls API with drawing tools
- 🤖 **AI Chat Assistant** - Multi-agent system with 20+ specialized agents
- 🏢 **Digital Twin Viewer** - 3D building visualization with Three.js
- 🎨 **Modern UI** - Built with React and TailwindCSS
- 📱 **Responsive Design** - Works on all screen sizes
- 🔍 **Location Search** - Search and navigate to locations
- 📍 **Geolocation** - Get your current location
- 🎤 **Voice Commands** - Speak to search and analyze

## Tech Stack

### Frontend
- **React 18** - UI framework
- **Vite** - Build tool
- **TailwindCSS** - Styling
- **Lucide React** - Icons
- **Axios** - HTTP client

### Backend
- **Express.js** - Server framework
- **OpenRouter API** - AI chat functionality with multiple model support
- **CORS** - Cross-origin resource sharing

### APIs
- **Mappls** - Map and location services
- **OpenRouter** - Unified API for multiple AI models (Llama, GPT, Claude, etc.)

## Prerequisites

Before you begin, ensure you have:
- **Node.js** (v18 or higher)
- **npm** or **yarn**
- **Python 3.8+** - For backend services
- **OpenRouter API Key** - Get it from [OpenRouter](https://openrouter.ai/keys)
- **Mappls API Key** - Get it from [Mappls Console](https://apis.mappls.com/console/)

## Cloud Services Setup (Recommended)

Valora uses **100% cloud-based** infrastructure for production:

- **Supabase** - PostgreSQL database (500 MB free)
- **Upstash Redis** - Cache layer (10K req/day free)
- **Cloudflare R2** - File storage (10 GB free)
- **Pinecone** - Vector search (already configured)

**📖 Full Setup Guide:** See [`docs/CLOUD_SETUP.md`](docs/CLOUD_SETUP.md)

**Quick Setup:**
1. Create accounts on Supabase, Upstash, Cloudflare
2. Update `.env` with credentials
3. Run `python scripts/init_supabase.py`
4. Done! No local PostgreSQL needed ✅

## Installation

1. **Clone or navigate to the project directory**

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Configure environment variables**
   
   Create a `.env` file in the root directory:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add both API keys:
   ```
   OPENROUTER_API_KEY=your-openrouter-api-key
   OPENROUTER_MODEL=meta-llama/llama-3.2-3b-instruct:free
   VITE_MAPPLS_API_KEY=your-actual-mappls-api-key
   PORT=3001
   ```

## Running the Application

### 1. Start Backend (FastAPI)
```bash
cd backend
python main.py
```
Backend will run on `http://localhost:8000`

### 2. Start Frontend (React + Vite)
```bash
npm run dev
```
Frontend will run on `http://localhost:5173`

### Optional: Express.js Server (Legacy)
```bash
npm run server
```
Legacy server runs on `http://localhost:3001`

## Usage

1. **Map View (Left Side)**
   - Use the search bar to find locations
   - Click the navigation icon to get your current location
   - Pan and zoom the map with mouse/touch

2. **AI Chat (Right Side)**
   - Type your questions or requests
   - The AI assistant can help with:
     - General information
     - Location-based queries
     - Recommendations
     - And more!

## Project Structure

```
valora-ai/
├── src/
│   ├── components/
│   │   ├── MapView.jsx       # Mappls map component
│   │   └── ChatPanel.jsx     # AI chat component
│   ├── App.jsx                # Main application
│   ├── main.jsx               # React entry point
│   └── index.css              # Global styles
├── server.js                  # Express backend server
├── index.html                 # HTML entry point
├── package.json               # Dependencies
├── vite.config.js             # Vite configuration
├── tailwind.config.js         # Tailwind configuration
└── .env.example               # Environment variables template
```

## Build for Production

```bash
npm run build
```

The production-ready files will be in the `dist/` directory.

## Troubleshooting

### Map not loading
- Ensure your Mappls API key is correctly added in `.env` as `VITE_MAPPLS_API_KEY`
- Check browser console for any errors
- Verify your Mappls API key is active
- Make sure to restart the dev server after adding the API key

### Chat not working
- Make sure the backend server is running (`npm run server`)
- Verify your OpenRouter API key is correct in `.env`
- Some models on OpenRouter are free, others require credits

### Port already in use
- Change the port in `.env` for backend
- Change the port in `vite.config.js` for frontend

## API Keys Setup

### Getting OpenRouter API Key
1. Visit [OpenRouter](https://openrouter.ai/)
2. Sign up or log in (supports GitHub login)
3. Navigate to [Keys section](https://openrouter.ai/keys)
4. Create a new API key
5. Add it to your `.env` file as `OPENROUTER_API_KEY`

**Free Models Available:**
- `meta-llama/llama-3.2-3b-instruct:free` (default)
- `google/gemma-2-9b-it:free`
- `microsoft/phi-3-mini-128k-instruct:free`

### Getting Mappls API Key
1. Visit [Mappls Console](https://apis.mappls.com/console/)
2. Sign up or log in
3. Create a new project
4. Generate API credentials
5. Add it to your `.env` file as `VITE_MAPPLS_API_KEY`

## License

This project is open source and available for personal and commercial use.

## Support

For issues or questions, please check:
- [OpenRouter Documentation](https://openrouter.ai/docs)
- [Mappls Documentation](https://github.com/mappls-api)

---

Built with ❤️ using React, Mappls, and OpenRouter
## 🏗️ Project Structure

```
windsurf-project/
├── backend/                  # Enhanced backend API (FastAPI)
│   ├── api/                 # API endpoints
│   │   └── main.py         # Main FastAPI application
│   ├── services/            # Business logic
│   │   ├── dmpe_engine.py  # Dynamic Market Prediction Engine
│   │   ├── data_processor.py # Data processing
│   │   └── mappls_integration.py # Mappls API
│   ├── models/              # ML models storage
│   ├── data/               # Data cache
│   ├── utils/              # Utilities
│   └── tests/              # Test cases
├── dmpe/                   # Original DMPE (legacy)
│   └── src/valora/        # Valora modules
├── src/                    # React frontend
│   ├── components/         # UI components
│   └── pages/             # Application pages
├── archive/               # Archived scripts
├── docs/                  # Documentation
├── start_all_services.py  # Unified startup script
├── check_environment.py   # Environment checker
└── test_new_backend.py    # API test suite
```

## 🚀 Quick Start

### 1. Check Environment
```bash
python check_environment.py
```

### 2. Start Services
```bash
python start_all_services.py
```

### 3. Access APIs
- **Backend API**: http://localhost:8000
- **DMPE API**: http://localhost:3002
- **API Docs**: http://localhost:8000/docs

### 4. Start Frontend
```bash
npm start
```

## 📡 Key Features

### Backend API (Port 8000)
- ✅ Price Prediction with XGBoost
- ✅ Rental Yield Analysis
- ✅ Demand Index Calculation
- ✅ Risk Assessment
- ✅ Market Analysis & Hotspots
- ✅ Portfolio Optimization
- ✅ Mappls Spatial Integration

### Legacy DMPE (Port 3002)
- ✅ Property Data Processing
- ✅ RAG-based Search
- ✅ Top Properties API

## 🧪 Testing

```bash
# Test new backend
python test_new_backend.py

# Run backend tests
cd backend && pytest tests/
```

