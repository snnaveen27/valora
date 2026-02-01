#!/bin/bash

# Valora One-Command Deployment Script
# Usage: ./deploy.sh

set -e  # Exit on any error

echo "🚀 Starting Valora Deployment..."
echo "================================"

SCRIPT_PATH="$0"
SCRIPT_SHA_BEFORE=""
if command -v sha256sum >/dev/null 2>&1; then
  SCRIPT_SHA_BEFORE=$(sha256sum "$SCRIPT_PATH" | awk '{print $1}')
fi

# Navigate to project directory
cd /home/ubuntu/valora

# If ecosystem.config.cjs exists as an untracked file, it will block git pull.
# Backup it so the tracked version from GitHub can be pulled.
if [ -f "ecosystem.config.cjs" ]; then
  if ! git ls-files --error-unmatch "ecosystem.config.cjs" >/dev/null 2>&1; then
    ts=$(date +"%Y%m%d-%H%M%S")
    echo "📦 Found untracked ecosystem.config.cjs - backing up to ecosystem.config.cjs.bak.${ts}"
    mv "ecosystem.config.cjs" "ecosystem.config.cjs.bak.${ts}"
  fi
fi

# Stash any local changes (ignore if nothing to stash)
echo "📦 Stashing local changes..."
git stash >/dev/null 2>&1 || true

# Pull latest code
echo "⬇️  Pulling latest code from GitHub..."
git pull origin main

# If this script changed after pulling, re-exec to ensure we run the latest logic.
# Guard against infinite recursion.
if [ -z "${VALORA_DEPLOY_REEXEC:-}" ] && [ -n "$SCRIPT_SHA_BEFORE" ] && command -v sha256sum >/dev/null 2>&1; then
  SCRIPT_SHA_AFTER=$(sha256sum "$SCRIPT_PATH" | awk '{print $1}')
  if [ "$SCRIPT_SHA_BEFORE" != "$SCRIPT_SHA_AFTER" ]; then
    echo "🔁 deploy.sh updated by git pull; re-running latest script..."
    export VALORA_DEPLOY_REEXEC=1
    exec "$SCRIPT_PATH"
  fi
fi

# Install/update dependencies
echo "📦 Installing dependencies..."
if [ -f "package-lock.json" ]; then
  npm ci --include=dev
else
  npm install --include=dev
fi

# Build frontend with production optimizations
echo "🔨 Building frontend (with compression & code splitting)..."
NODE_ENV=production npm run build

# Clean up old PM2 processes
echo "🧹 Cleaning up old processes..."
pm2 delete valora-backend 2>/dev/null || true

# Start backend with ecosystem config
echo "🚀 Starting backend..."
pm2 start ecosystem.config.cjs

# Save PM2 configuration
pm2 save

# Wait for backend to start with retry logic
echo "⏳ Waiting for backend to start..."
max_retries=30
retry_count=0
while [ $retry_count -lt $max_retries ]; do
  if curl -s -f http://127.0.0.1:8000/health > /dev/null 2>&1; then
    echo "✅ Backend is healthy!"
    break
  fi
  retry_count=$((retry_count + 1))
  if [ $retry_count -lt $max_retries ]; then
    echo "Waiting for backend... ($retry_count/$max_retries)"
    sleep 3
  fi
done

if [ $retry_count -eq $max_retries ]; then
  echo "⚠️  Backend health check timeout. Check logs:"
  pm2 logs valora-backend --lines 20 --nostream
fi

# Show build statistics if available
if [ -f "dist/stats.html" ]; then
  echo ""
  echo "📊 Build statistics generated: dist/stats.html"
fi

# Show status
echo ""
echo "✅ Deployment Complete!"
echo "======================="
pm2 list

echo ""
echo "🎯 Production Optimizations Active:"
echo "   • Code splitting (vendor chunks)"
echo "   • Gzip + Brotli compression"
echo "   • Lazy loading for heavy components"
echo "   • Minified with console.log removal"
echo ""
echo "📊 View logs: pm2 logs valora-backend"
echo "🌐 Frontend: https://3.109.34.1.sslip.io/valora/"
echo "📈 Bundle stats: https://3.109.34.1.sslip.io/valora/stats.html"
