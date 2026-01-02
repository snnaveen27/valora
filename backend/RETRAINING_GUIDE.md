# 🔄 Model Retraining Pipeline Guide

## Overview

The REALTY-GPT platform includes a production-ready model retraining pipeline that automatically updates ML models with new data. It supports both **Prefect** (enterprise-grade) and **APScheduler** (lightweight) orchestration.

## Features

✅ **Incremental Training** - Only retrain when needed  
✅ **Model Validation** - Verify performance before deployment  
✅ **Automatic Rollback** - Restore previous models if new ones fail  
✅ **Scheduled Execution** - Cron or interval-based scheduling  
✅ **Metrics Tracking** - Monitor model performance over time  
✅ **Background Processing** - Non-blocking API operations  
✅ **Retry Logic** - Automatic retry on failures  

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Retraining Pipeline                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  1. Check if Retraining Needed                               │
│     ├── Time-based (e.g., every 7 days)                     │
│     ├── Data drift detection                                 │
│     └── Performance degradation                              │
│                                                               │
│  2. Load & Validate Data                                     │
│     ├── Load new training data                               │
│     ├── Validate data quality                                │
│     └── Check minimum sample requirements                    │
│                                                               │
│  3. Backup Current Models                                    │
│     └── Save to backups/ directory                           │
│                                                               │
│  4. Retrain Models (Parallel)                                │
│     ├── Price Prediction (XGBoost)                          │
│     ├── Rental Yield (Gradient Boosting)                    │
│     └── Demand Index (Random Forest)                        │
│                                                               │
│  5. Validate New Models                                      │
│     ├── Compare metrics with previous version                │
│     ├── Check for improvement or acceptable degradation     │
│     └── Restore from backup if validation fails             │
│                                                               │
│  6. Save Models & Metrics                                    │
│     ├── Save new models to disk                              │
│     ├── Update retraining status                             │
│     └── Save performance metrics                             │
│                                                               │
│  7. Send Notifications                                       │
│     └── Log/notify stakeholders of results                   │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Option 1: APScheduler (Recommended for Getting Started)

```bash
# Install dependencies
pip install apscheduler

# Run immediate retraining
python backend/services/retraining_scheduler_aps.py --run-now --force

# Start scheduler with cron (every Sunday at 2 AM)
python backend/services/retraining_scheduler_aps.py --start --schedule cron --cron "0 2 * * 0"

# Start scheduler with interval (every 7 days)
python backend/services/retraining_scheduler_aps.py --start --schedule interval --interval 168

# Run as daemon (keeps running)
python backend/services/retraining_scheduler_aps.py --start --schedule cron --daemon
```

### Option 2: Prefect (For Production)

```bash
# Install Prefect
pip install prefect

# Configure Prefect (one-time setup)
prefect config set PREFECT_API_URL=http://127.0.0.1:4200/api

# Start Prefect server (in separate terminal)
prefect server start

# Run immediate retraining
python backend/services/retraining_scheduler_prefect.py --force

# Create scheduled deployment
python backend/services/retraining_scheduler_prefect.py --deploy --schedule cron --cron "0 2 * * 0"

# Start Prefect agent to execute scheduled runs
prefect agent start -q model-training
```

## API Endpoints

### Trigger Retraining

```bash
# Async (background) - recommended
curl -X POST "http://localhost:8000/api/models/retrain?force=false&run_async=true"

# Sync (blocking)
curl -X POST "http://localhost:8000/api/models/retrain?force=false&run_async=false"
```

Response:
```json
{
  "status": "started",
  "message": "Model retraining started in background",
  "forced": false,
  "timestamp": "2024-11-09T23:00:00",
  "check_status_at": "/api/models/retraining/status"
}
```

### Check Retraining Status

```bash
curl "http://localhost:8000/api/models/retraining/status"
```

Response:
```json
{
  "status": "success",
  "retraining_status": {
    "last_retrain": "2024-11-09T23:00:00",
    "next_scheduled": null,
    "total_retrains": 5,
    "last_metrics": {
      "price_model": {"r2": 0.89, "mae": 125000},
      "rental_yield_model": {"r2": 0.82, "mae": 0.15},
      "demand_model": {"r2": 0.87, "mae": 5.2}
    },
    "status": "success"
  }
}
```

### Get Retraining History

```bash
curl "http://localhost:8000/api/models/retraining/history?limit=10"
```

### Check if Retraining Needed

```bash
curl -X POST "http://localhost:8000/api/models/retraining/check"
```

### Scheduler Management

```bash
# Start scheduler
curl -X POST "http://localhost:8000/api/models/scheduler/start?schedule_type=cron&cron_expression=0 2 * * 0"

# Check scheduler status
curl "http://localhost:8000/api/models/scheduler/status"

# Stop scheduler
curl -X POST "http://localhost:8000/api/models/scheduler/stop"
```

### Get Model Metrics

```bash
curl "http://localhost:8000/api/models/metrics"
```

## Configuration

### Retraining Thresholds

Edit `backend/services/model_retraining.py`:

```python
class ModelRetrainingService:
    def __init__(self):
        # Minimum samples required for retraining
        self.min_samples_for_retrain = 100
        
        # Require 2% improvement to accept new model
        self.min_improvement_threshold = 0.02
        
        # Allow max 5% degradation
        self.max_degradation_threshold = 0.05
```

### Schedule Configuration

#### Cron Expressions

```bash
# Every day at 2 AM
"0 2 * * *"

# Every Sunday at 2 AM
"0 2 * * 0"

# Every Monday and Thursday at 3:30 AM
"30 3 * * 1,4"

# First day of every month at midnight
"0 0 1 * *"
```

#### Interval Scheduling

```bash
# Every 24 hours
--interval 24

# Every 7 days (168 hours)
--interval 168

# Every 12 hours
--interval 12
```

## Monitoring

### Metrics Files

Retraining metrics are saved to `backend/models/metrics/`:

```
retraining_metrics_20241109_230000.json
retraining_metrics_20241116_230000.json
...
```

### Log Files

Logs are written to `backend/logs/retraining.log`:

```
2024-11-09 23:00:00 - INFO - Starting full model retraining pipeline
2024-11-09 23:00:01 - INFO - Loaded 26,125 training samples
2024-11-09 23:00:02 - INFO - Backing up current models...
2024-11-09 23:02:15 - INFO - Price model retrained successfully
2024-11-09 23:03:30 - INFO - All models validated successfully
```

## Integration with Frontend

### AI-Agent Panel Integration

Add retraining controls to your AI-Agent Panel:

```javascript
// Trigger retraining
const triggerRetraining = async (force = false) => {
  const response = await fetch(
    `http://localhost:8000/api/models/retrain?force=${force}&run_async=true`,
    { method: 'POST' }
  );
  return await response.json();
};

// Check status
const checkStatus = async () => {
  const response = await fetch(
    'http://localhost:8000/api/models/retraining/status'
  );
  return await response.json();
};

// Get metrics
const getMetrics = async () => {
  const response = await fetch(
    'http://localhost:8000/api/models/metrics'
  );
  return await response.json();
};
```

## Best Practices

### 1. Schedule During Low Traffic
- Run retraining during off-peak hours (e.g., 2 AM)
- Avoid impacting user experience

### 2. Monitor Performance
- Track metrics over time
- Set up alerts for significant performance changes
- Review retraining history regularly

### 3. Validate Before Deploy
- Never skip validation
- Use appropriate thresholds
- Test new models on hold-out data

### 4. Backup Strategy
- Keep recent backups (automatic)
- Test rollback procedure
- Monitor disk space

### 5. Data Quality
- Validate input data quality
- Handle missing values appropriately
- Remove outliers and anomalies

## Troubleshooting

### Issue: Retraining Always Skipped

**Cause**: Time threshold not met  
**Solution**: Use `--force` flag or adjust time threshold

```bash
python backend/services/retraining_scheduler_aps.py --run-now --force
```

### Issue: Models Failing Validation

**Cause**: New data is different from training data  
**Solution**: 
1. Check data quality
2. Adjust validation thresholds
3. Investigate data drift

### Issue: Scheduler Not Running

**Cause**: Scheduler not started or crashed  
**Solution**:

```bash
# Check scheduler status
curl http://localhost:8000/api/models/scheduler/status

# Restart scheduler
curl -X POST "http://localhost:8000/api/models/scheduler/start"
```

### Issue: Out of Memory

**Cause**: Too much data loaded at once  
**Solution**: Implement batch processing or increase memory

## Advanced Features

### Custom Notification Handlers

Implement notifications in `retraining_scheduler_aps.py`:

```python
def _send_notification(self, result: Dict[str, Any]):
    """Send notification about retraining"""
    status = result.get("overall_status")
    
    # Email notification
    if status == "success":
        send_email(
            to="team@company.com",
            subject="Model Retraining Successful",
            body=f"Models retrained successfully: {result}"
        )
    
    # Slack notification
    slack_webhook(
        channel="#ml-notifications",
        text=f"Retraining status: {status}"
    )
```

### Custom Validation Logic

Override validation in `model_retraining.py`:

```python
def validate_model_performance(self, model, X_test, y_test, previous_metrics):
    """Custom validation logic"""
    # Your custom validation here
    new_metrics = calculate_metrics(model, X_test, y_test)
    
    # Custom acceptance criteria
    if custom_check(new_metrics, previous_metrics):
        return True, new_metrics
    else:
        return False, new_metrics
```

## Production Checklist

- [ ] Install dependencies (`apscheduler` or `prefect`)
- [ ] Configure schedule (cron or interval)
- [ ] Set validation thresholds
- [ ] Test retraining manually
- [ ] Set up monitoring/alerts
- [ ] Configure notifications
- [ ] Document rollback procedure
- [ ] Set up log rotation
- [ ] Test backup/restore
- [ ] Schedule regular reviews

## Support

For issues or questions:
- Check logs: `backend/logs/retraining.log`
- Review metrics: `backend/models/metrics/`
- API docs: http://localhost:8000/docs#/models

---

**Last Updated**: November 9, 2024  
**Version**: 2.0.0
