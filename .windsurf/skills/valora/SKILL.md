---
name: valora
description: Valora Local MVP - City Intelligence Platform development with 3D visualization, multi-agent chat, and spatial analysis for Bangalore
---

# Valora Local MVP Development Skill

## Overview
Valora is a City Intelligence Platform focusing on real estate analysis, 3D visualization, and AI-powered insights. The Local MVP is a focused development environment for building production-ready features.

## Core Architecture

### Three-Panel Layout (MainApp.jsx)
1. **Left Panel (Chat)** - Multi-agent chat interface
2. **Center Panel (Map)** - Cesium 3D map visualization
3. **Right Panel (Analysis)** - Data analysis and insights

### Key Components
- **Cesium3DMap.jsx** - 3D city visualization with Bangalore as default location
- **ChatPanelMultiAgent.jsx** - AI chat with specialized agents
- **MapAnalysisPanel.jsx** - Analysis results display
- **AdminDashboard.jsx** - Admin controls with Local MVP tab

## Bangalore Configuration

### Default Location (Indiranagar)
```javascript
const DEFAULT_LOCATION = {
  lng: 77.6412,
  lat: 12.9716,
  zoom: 14,
  height: 1500
}
```

### Available Areas
- Indiranagar: 77.6412, 12.9716
- Hebbal: 77.5946, 13.0359
- Whitefield: 77.7499, 12.9698

## Multi-Agent System

### Agents
1. **Query Agent** - Basic queries and information retrieval
2. **Analysis Agent** - Data analysis and insights
3. **Simulation Agent** - What-if scenarios and simulations
4. **Narrative Agent** - Storytelling and explanations

### Agent UI Control
Agents can control the frontend UI via `ui_actions`:
- `openPanel/closePanel` - Toggle analysis panel
- `switchTab` - Change active tab
- `setCinemaMode` - Enable cinematic storytelling

## Local MVP Structure

### Location
`local_mvp/` folder contains:
- `config/` - MVP settings
- `data/` - Sample data (25,714 buildings)
- `scripts/` - Setup and utilities
- `docs/` - Documentation
- `tests/` - Test suite

### Quick Start
```bash
# Setup
python local_mvp/scripts/setup/mvp_setup.py

# Start backend
python local_mvp/scripts/setup/start_mvp_backend.py

# Start frontend (separate terminal)
npm run dev
```

### Admin Dashboard
Access via: http://localhost:3000 → Login → Admin Dashboard → 🚀 Local MVP

## Development Guidelines

### When Working on Frontend
- Always preserve the three-panel layout
- Ensure Cesium map loads with Bangalore coordinates
- Test all panels are visible and functional
- Verify responsive design

### When Working on Backend
- Keep API endpoints in `backend/api/`
- Use multi-agent orchestrator for chat
- Validate data paths in MVP config

### When Adding Features
1. Update `local_mvp/config/mvp_settings.json`
2. Add to LocalMVPTab.jsx if admin-visible
3. Document in `local_mvp/docs/`
4. Add tests to `local_mvp/tests/`

## Common Tasks

### Verify Cesium Map
- Check DEFAULT_LOCATION is Bangalore
- Ensure Ion token is set
- Verify terrain and buildings load
- Test camera controls work

### Verify Three-Panel Layout
- Left: Chat panel visible
- Center: Cesium map renders
- Right: Analysis panel toggles
- All panels responsive

### Update MVP Configuration
Edit: `local_mvp/config/mvp_settings.json`
- Enable/disable features
- Set data paths
- Configure services

### Test MVP Features
Use Admin Dashboard → Local MVP tab:
- Run quick tests
- Check service status
- Verify data loaded
- Monitor endpoints

## Important Files

### Frontend
- `src/components/MainApp.jsx` - Three-panel layout
- `src/spatial/Cesium3DMap.jsx` - 3D map (Bangalore)
- `src/components/ChatPanelMultiAgent.jsx` - Chat interface
- `src/components/admin/LocalMVPTab.jsx` - MVP dashboard

### Backend
- `backend/api/main.py` - FastAPI main
- `backend/services/multi_agent_orchestrator.py` - Agent routing
- `backend/services/simulation_engine.py` - Simulations
- `backend/services/narrative_generator.py` - Storytelling

### Configuration
- `local_mvp/config/mvp_settings.json` - MVP config
- `.env` - Environment variables
- `vite.config.js` - Frontend build config

## Troubleshooting

### Map Not Loading
1. Check Cesium Ion token in `.env`
2. Verify DEFAULT_LOCATION coordinates
3. Check browser console for errors
4. Ensure Cesium assets served at `/cesium/`

### Panels Not Showing
1. Check MainApp.jsx three-panel layout
2. Verify panel width calculations
3. Test toggle buttons work
4. Check responsive breakpoints

### Backend Errors
1. Check backend running on port 8000
2. Verify API endpoints responding
3. Check logs in `backend/logs/`
4. Test with `/health` endpoint

## Production Transition

When MVP is complete:
1. Review all MVP code
2. Run full test suite
3. Complete documentation
4. Restructure to production folders
5. Add multi-city support

## Reference Documentation
- Main README: `local_mvp/README.md`
- Quick Start: `local_mvp/START_HERE.md`
- Architecture: `local_mvp/docs/architecture.md`
