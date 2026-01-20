---
description: Complete workflow for Valora Local MVP development and deployment
---

# Valora Local MVP Workflow

This workflow guides you through setting up, developing, and deploying the Valora Local MVP.

## Prerequisites Check

Before starting, verify:
- [ ] Node.js 18+ installed
- [ ] Python 3.10+ installed
- [ ] Git repository cloned
- [ ] `.env` file exists with required keys

## Step 1: Initial MVP Setup

```bash
# Run MVP setup script
python local_mvp/scripts/setup/mvp_setup.py
```

This will:
- Create directory structure
- Copy sample data files
- Validate configuration
- Check environment variables

**Expected Output:**
- ✅ Directory structure created
- ✅ Data files copied (25,714 buildings)
- ✅ Configuration valid
- ✅ Environment checked

## Step 2: Start Backend Service

```bash
# Start backend with MVP configuration
python local_mvp/scripts/setup/start_mvp_backend.py
```

**Verify:**
- Backend running on http://localhost:8000
- Visit http://localhost:8000/health
- Should return `{"status": "healthy"}`

## Step 3: Start Frontend Service

In a **new terminal**:

```bash
# Start Vite dev server
npm run dev
```

**Verify:**
- Frontend running on http://localhost:3000
- Browser automatically opens
- No console errors

## Step 4: Access Admin Dashboard

1. Open http://localhost:3000 in browser
2. Login (create account if first time)
3. Navigate to **Admin Dashboard**
4. Click **🚀 Local MVP** tab in sidebar

**Verify in Local MVP Dashboard:**
- ✅ 3D Map: 25,714 buildings loaded
- ✅ Backend: Running status
- ✅ Frontend: Running status
- ✅ All services showing green

## Step 5: Verify Three-Panel Layout

1. Exit admin dashboard (click "View as User")
2. Verify three panels visible:
   - **Left**: Chat panel with AI interface
   - **Center**: Cesium 3D map showing Bangalore
   - **Right**: Analysis panel (toggle to open/close)

**Test:**
- Map shows Bangalore (Indiranagar area)
- Camera controls work (zoom, rotate, tilt)
- Chat accepts messages
- Analysis panel opens/closes

## Step 6: Test Core Features

### Test 3D Map (Bangalore)

// turbo
```bash
# From Admin Dashboard → Local MVP → Quick Actions
# Click "Test 3D Map Loading"
```

**Expected:**
- Map loads Bangalore coordinates
- Buildings render in 3D
- Camera positioned at Indiranagar
- Controls responsive

### Test Multi-Agent Chat

In chat panel, type:
```
What is the average building height in this area?
```

**Expected:**
- Agent responds with analysis
- Stats appear in analysis panel
- No errors in console

### Test Simulation

In chat panel, type:
```
Simulate adding a metro station at Indiranagar
```

**Expected:**
- Simulation agent activates
- Cinema mode may trigger
- Impact analysis shown
- Camera may animate

## Step 7: Development Workflow

### Making Frontend Changes

1. Edit files in `src/` folder
2. Vite hot-reloads automatically
3. Check browser for changes
4. Verify in both user and admin views

### Making Backend Changes

1. Edit files in `backend/` folder
2. Backend auto-reloads (uvicorn --reload)
3. Test via Admin Dashboard → Local MVP
4. Check API endpoints in browser

### Testing Changes

// turbo
```bash
# Run MVP test suite
python local_mvp/tests/run_mvp_tests.py
```

Or use Admin Dashboard → Local MVP → Tests tab

## Step 8: Monitor & Debug

### Check Service Status

Admin Dashboard → Local MVP → Overview
- View service uptime
- Check data file status
- Monitor API endpoints
- See recent test results

### View Logs

**Frontend:** Browser console (F12)
**Backend:** Terminal running backend

### Common Issues

**Map not loading:**
1. Check `.env` has `CESIUM_ION_TOKEN`
2. Verify sample data exists
3. Check browser console

**Backend errors:**
1. Check port 8000 not in use
2. Verify Python dependencies installed
3. Check `backend/logs/` folder

**Panel layout broken:**
1. Refresh browser (Ctrl+R)
2. Clear browser cache
3. Check console for React errors

## Step 9: Add New Features

When adding features to MVP:

1. **Update Configuration**
   ```json
   // local_mvp/config/mvp_settings.json
   "features": {
     "new_feature": {
       "enabled": true,
       "setting": "value"
     }
   }
   ```

2. **Implement Feature**
   - Add to appropriate component
   - Update backend if needed
   - Add to LocalMVPTab if admin-visible

3. **Test Feature**
   - Manual testing in browser
   - Add automated test
   - Run full MVP test suite

4. **Document Feature**
   - Update `local_mvp/docs/`
   - Add to README if needed
   - Update this workflow if necessary

## Step 10: Pre-Production Checklist

Before moving to production:

- [ ] All MVP tests passing
- [ ] Three-panel layout working perfectly
- [ ] Cesium map loads Bangalore correctly
- [ ] Multi-agent chat functional
- [ ] All features documented
- [ ] No console errors
- [ ] Performance acceptable
- [ ] Admin dashboard shows all green
- [ ] Sample data loads correctly
- [ ] API endpoints responsive

## Step 11: Production Transition

When MVP is complete and tested:

1. **Code Review**
   - Review all changes
   - Check code quality
   - Verify best practices

2. **Full Testing**
   - Run complete test suite
   - Manual QA testing
   - Load testing
   - Security audit

3. **Documentation**
   - Complete all docs
   - Update README
   - Create deployment guide

4. **Restructure**
   - Move MVP code to production structure
   - Update imports and paths
   - Remove MVP-specific config

5. **Deploy**
   - Set up production environment
   - Configure CI/CD
   - Deploy to production
   - Monitor post-deployment

---

## Quick Commands Reference

```bash
# Setup
python local_mvp/scripts/setup/mvp_setup.py

# Start backend
python local_mvp/scripts/setup/start_mvp_backend.py

# Start frontend
npm run dev

# Run tests
python local_mvp/tests/run_mvp_tests.py

# Access admin dashboard
# http://localhost:3000 → Login → Admin Dashboard → Local MVP
```

## Support Resources

- **Documentation**: `local_mvp/README.md`
- **Quick Start**: `local_mvp/START_HERE.md`
- **Architecture**: `local_mvp/docs/architecture.md`
- **Skill Guide**: `.windsurf/skills/valora/SKILL.md`

---

**Last Updated**: January 16, 2026  
**MVP Version**: 1.0
