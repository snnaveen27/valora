#!/bin/bash

# Fix PM2 configuration for Valora backend
echo "=== Fixing Valora Backend PM2 Configuration ==="

# Stop the existing process
pm2 stop valora-backend
pm2 delete valora-backend

# Start with correct command
echo "Starting backend with correct uvicorn command..."
cd /home/ubuntu/valora

# Create logs directory
mkdir -p logs

# Start backend using the correct command
pm2 start "python3 -m uvicorn server:app --app-dir backend --port 8000 --host 0.0.0.0" \
  --name valora-backend \
  --cwd /home/ubuntu/valora \
  --restart-delay 5000 \
  --max-memory-restart 1G \
  --log /home/ubuntu/valora/logs/valora-backend.log \
  --error /home/ubuntu/valora/logs/valora-backend-error.log \
  --output /home/ubuntu/valora/logs/valora-backend-out.log

# Save PM2 configuration
pm2 save

# Show status
echo ""
echo "=== PM2 Status ==="
pm2 status

echo ""
echo "=== Testing Backend Health ==="
sleep 5
curl -f http://127.0.0.1:8000/health || echo "⚠️  Health check failed"

echo ""
echo "=== Fix Complete ==="
echo "Backend should now be running correctly"
echo "Check logs with: pm2 logs valora-backend"
