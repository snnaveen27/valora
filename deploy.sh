#!/bin/bash

# Valora One-Command Deployment Script
# Usage: ./deploy.sh

set -e  # Exit on any error

echo "🚀 Starting Valora Deployment..."
echo "================================"

# Navigate to project directory
cd /home/ubuntu/valora

# Stash any local changes
echo "📦 Stashing local changes..."
git stash

# Pull latest code
echo "⬇️  Pulling latest code from GitHub..."
git pull origin main

# Build frontend
echo "🔨 Building frontend..."
npm run build

# Clean up old PM2 processes
echo "🧹 Cleaning up old processes..."
pm2 delete valora-backend 2>/dev/null || true

# Start backend with ecosystem config
echo "🚀 Starting backend..."
pm2 start ecosystem.config.cjs

# Save PM2 configuration
pm2 save

# Wait for backend to start
echo "⏳ Waiting for backend to start..."
sleep 3

# Show status
echo ""
echo "✅ Deployment Complete!"
echo "======================="
pm2 list

# Test backend health
echo ""
echo "🏥 Testing backend health..."
curl -f http://localhost:8000/api/health && echo "✅ Backend is healthy!" || echo "⚠️  Backend health check failed"

echo ""
echo "📊 View logs with: pm2 logs valora-backend"
echo "🌐 Frontend: https://3.109.34.1.sslip.io/valora/"
