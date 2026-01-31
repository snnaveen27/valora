# Valora AI - Production Deployment Guide

**Server:** Ubuntu 22.04 on AWS Lightsail  
**URL:** https://3.109.34.1.sslip.io/valora/  
**Backend Port:** 8000  
**Process Manager:** PM2

---

## Prerequisites

### Server Requirements
- Ubuntu 22.04 LTS
- Python 3.11+
- Node.js 18+
- PM2 (installed globally)
- Git

### Required Files (Not in Git)
- `src/data/valora.db` (853MB SQLite database)
- `.env` with production API keys

---

## Quick Deployment (Existing Server)

If the server is already set up, run these commands:

```bash
# SSH into server
ssh -i "LightsailMumbai.pem" ubuntu@3.109.34.1

# Pull latest code
cd /home/ubuntu/valora
git pull origin main

# Install dependencies if package.json changed
npm install

# Install Python dependencies if requirements.txt changed
source backend/venv/bin/activate
pip install -r backend/requirements.txt
deactivate

# Build frontend (optional, only if frontend changes)
npm run build

# Restart backend
pm2 restart valora-backend

# Check status
pm2 list
pm2 logs valora-backend --lines 20
```

---

## First-Time Server Setup

### 1. Clone Repository

```bash
cd /home/ubuntu
git clone https://github.com/snnaveen27/valora.git
cd valora
```

### 2. Setup Python Virtual Environment

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
cd ..
```

### 3. Install Node Dependencies

```bash
npm install
```

### 4. Upload Database

From your local machine:

```bash
# Windows PowerShell
scp -i "LightsailMumbai.pem" "C:\Users\Nvnsa\Downloads\New folder\realestate\CascadeProjects\windsurf-project\src\data\valora.db" ubuntu@3.109.34.1:/home/ubuntu/valora/src/data/
```

Or from Linux/Mac:
```bash
scp -i LightsailMumbai.pem ./src/data/valora.db ubuntu@3.109.34.1:/home/ubuntu/valora/src/data/
```

### 5. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit with production values
nano .env
```

**Required Environment Variables:**
- `OPENROUTER_API_KEY` - Your OpenRouter API key
- `MAPBOX_API_KEY` - Your Mapbox API key
- `VITE_API_URL` - Set to `https://3.109.34.1.sslip.io`
- `VITE_CESIUM_TOKEN` - Your Cesium Ion token

### 6. Build Frontend

```bash
npm run build
```

### 7. Create Logs Directory

```bash
mkdir -p logs
```

### 8. Start with PM2

```bash
# Using ecosystem config
pm2 start ecosystem.config.js

# Or manually
pm2 start "backend/venv/bin/python -m uvicorn server:app --app-dir backend --port 8000 --host 0.0.0.0" --name valora-backend

# Save PM2 configuration
pm2 save
```

### 9. Verify Deployment

```bash
# Check PM2 status
pm2 list

# Check logs
pm2 logs valora-backend --lines 50

# Test endpoints
curl http://localhost:8000/health
curl http://localhost:8000/api/status
```

---

## API Health Checks

```bash
# Basic health
curl http://localhost:8000/health

# Full status with all services
curl http://localhost:8000/api/status

# City Intelligence
curl http://localhost:8000/api/city-intelligence/status

# Test valuation endpoint
curl -X POST http://localhost:8000/api/valuation/estimate \
  -H "Content-Type: application/json" \
  -d '{"lat":12.9716,"lng":77.5946,"bedrooms":2,"covered_area":1200}'
```

---

## Troubleshooting

### Backend Not Starting

```bash
# Check Python version
python3 --version  # Should be 3.11+

# Check venv
ls backend/venv/bin/python

# Try running manually
cd /home/ubuntu/valora
source backend/venv/bin/activate
python -m uvicorn server:app --app-dir backend --port 8000 --host 0.0.0.0
```

### Database Not Found

```bash
# Check database exists
ls -la src/data/valora.db

# Should show ~853MB file
# If missing, upload using scp command above
```

### Port Already in Use

```bash
# Check what's using port 8000
lsof -i :8000

# Kill if necessary
kill -9 <PID>
```

### Memory Issues

```bash
# Check memory usage
free -h

# Check PM2 memory
pm2 monit

# Restart if memory high
pm2 restart valora-backend
```

### Trading Bot Conflict

The trading bot runs separately. Verify it's not affected:

```bash
pm2 list
# Should show both:
# - valora-backend (port 8000)
# - trading-bot (different port)
```

---

## Rollback Procedure

If something goes wrong:

```bash
# Stop current version
pm2 stop valora-backend

# Restore from backup (if created)
cd /home/ubuntu
rm -rf valora
mv valora-backup-YYYYMMDD valora

# Restart
cd valora
pm2 restart valora-backend
```

---

## Updating the Application

### Standard Update

```bash
cd /home/ubuntu/valora
git pull origin main
npm install  # if package.json changed
source backend/venv/bin/activate
pip install -r backend/requirements.txt
deactivate
pm2 restart valora-backend
```

### Database Update

If database needs updating:

```bash
# Backup current database
cp src/data/valora.db src/data/valora.db.backup

# Upload new database from local machine
# (run from local machine)
scp -i "LightsailMumbai.pem" ./src/data/valora.db ubuntu@3.109.34.1:/home/ubuntu/valora/src/data/

# Restart backend to pick up new data
pm2 restart valora-backend
```

---

## PM2 Commands Reference

```bash
pm2 list                     # List all processes
pm2 logs valora-backend      # View logs
pm2 restart valora-backend   # Restart
pm2 stop valora-backend      # Stop
pm2 delete valora-backend    # Remove from PM2
pm2 monit                    # Real-time monitoring
pm2 save                     # Save current config
pm2 startup                  # Setup auto-start on boot
```

---

## Important Notes

1. **Database is NOT in git** - Must be uploaded separately via SCP
2. **API keys are NOT in git** - Configure .env on server manually
3. **Trading bot** - Runs on different port, should not be affected
4. **Logs** - Check `logs/` directory and `pm2 logs` for debugging
5. **Memory** - Backend uses ~800MB RAM, monitor with `pm2 monit`

---

## Contact

- **Repository:** https://github.com/snnaveen27/valora
- **Server IP:** 3.109.34.1
- **SSH Key:** LightsailMumbai.pem
