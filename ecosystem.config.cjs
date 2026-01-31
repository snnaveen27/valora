module.exports = {
  apps: [{
    name: 'valora-backend',
    script: '/home/ubuntu/valora/backend/venv/bin/python',
    args: '-m uvicorn server:app --app-dir backend --port 8000 --host 0.0.0.0',
    cwd: '/home/ubuntu/valora',
    instances: 1,
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',
    env: {
      NODE_ENV: 'production',
      PYTHONPATH: '/home/ubuntu/valora/backend'
    },
    error_file: '/home/ubuntu/valora/logs/valora-backend-error.log',
    out_file: '/home/ubuntu/valora/logs/valora-backend-out.log',
    log_file: '/home/ubuntu/valora/logs/valora-backend-combined.log',
    time: true
  }]
};
