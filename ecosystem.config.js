module.exports = {
  apps: [
    {
      name: 'valora-backend',
      script: 'backend/venv/bin/python',
      args: '-m uvicorn server:app --app-dir backend --port 8000 --host 0.0.0.0',
      cwd: '/home/ubuntu/valora',
      instances: 1,
      exec_mode: 'fork',
      autorestart: true,
      watch: false,
      max_memory_restart: '2G',
      env: {
        NODE_ENV: 'production',
        PYTHONPATH: '/home/ubuntu/valora/backend',
        PYTHONUNBUFFERED: '1'
      },
      error_file: './logs/valora-backend-error.log',
      out_file: './logs/valora-backend-out.log',
      log_file: './logs/valora-backend-combined.log',
      time: true,
      merge_logs: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z'
    }
  ]
};
