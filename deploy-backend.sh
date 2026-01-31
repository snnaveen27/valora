#!/bin/bash

# Valora AI Deployment Script
# This script properly configures and starts the backend service

echo "=== Valora AI Backend Deployment ==="

# Create logs directory if it doesn't exist
mkdir -p logs

# Install Python dependencies if needed
if [ ! -d "backend/venv" ]; then
    echo "Creating Python virtual environment..."
    cd backend
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cd ..
fi

# Set environment variables
if [ ! -f ".env" ]; then
    echo "Creating .env from template..."
    cp .env.production .env
    echo "⚠️  Please update .env with your actual API keys and database URL"
fi

# Stop existing PM2 processes
echo "Stopping existing PM2 processes..."
pm2 stop valora-backend 2>/dev/null || true
pm2 delete valora-backend 2>/dev/null || true

# Start backend with PM2
echo "Starting backend with PM2..."
pm2 start ecosystem.config.js

# Save PM2 configuration
pm2 save

# Show status
echo ""
echo "=== PM2 Status ==="
pm2 status

echo ""
echo "=== Backend Health Check ==="
sleep 3
curl -f http://localhost:8000/api/health || echo "⚠️  Backend health check failed"

echo ""
echo "=== Deployment Complete ==="
echo "Backend should be running at: http://localhost:8000"
echo "Logs available in: logs/ directory"
echo "PM2 commands:"
echo "  pm2 logs valora-backend    # View logs"
echo "  pm2 restart valora-backend  # Restart service"
echo "  pm2 status                  # Check status"
