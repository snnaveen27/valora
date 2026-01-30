# Pricing Database Security

## Why Database Instead of JSON?

### Security Issues with JSON Files
❌ **File system access** - Anyone with file access can edit prices  
❌ **No audit trail** - Can't track who changed what  
❌ **Git exposure** - Risk of committing sensitive pricing to GitHub  
❌ **No access control** - File permissions are weak  

### Security Benefits of Database
✅ **Application-level access** - Only backend can modify  
✅ **Full audit trail** - Every change logged with user ID  
✅ **Database ACLs** - Proper access control  
✅ **Transactions** - Atomic updates, no corruption  
✅ **Backup & recovery** - Easy to backup and restore  

---

## Implementation

### Database Schema

```sql
-- Main pricing config (single row)
CREATE TABLE pricing_config (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    config_json TEXT NOT NULL,
    last_updated TEXT NOT NULL,
    updated_by TEXT,
    version INTEGER DEFAULT 1
);

-- Audit log (all changes tracked)
CREATE TABLE pricing_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    changed_at TEXT NOT NULL,
    changed_by TEXT NOT NULL,
    change_type TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    description TEXT
);
```

### Files Created

1. **`backend/database/pricing_db.py`**
   - `PricingDatabase` class
   - `get_config()` - Load pricing from database
   - `save_config()` - Save with audit trail
   - `get_audit_log()` - View change history

2. **`backend/migrate_pricing_to_db.py`**
   - One-time migration script
   - Moves JSON → Database
   - Verifies migration

### Files Updated

1. **`backend/usage_tracker.py`**
   - Changed from `_load_pricing_config()` reading JSON
   - Now reads from database via `pricing_db.get_config()`

2. **`backend/admin_routes.py`**
   - `/api/admin/pricing/config` now uses database
   - Logs admin email in audit trail

---

## Migration

### Run Once (Already Done)
```bash
cd backend
python migrate_pricing_to_db.py
```

### Output
```
✅ Migration completed successfully!

📌 SECURITY NOTE:
   - Pricing now stored in SQLite database (pricing.db)
   - All changes logged with audit trail
   - Database location: backend/database/pricing.db
   - JSON file can be deleted (no longer used)
```

---

## How It Works

### Loading Pricing (Startup)
```python
from database.pricing_db import get_pricing_db

pricing_db = get_pricing_db()
config = pricing_db.get_config()
# Returns: {action_costs, tier_limits, pricing, etc.}
```

### Saving Pricing (Admin Panel)
```python
pricing_db.save_config(config, updated_by="admin@example.com")
# Automatically:
# - Saves to database
# - Logs old vs new values
# - Records admin email
# - Increments version number
```

### Viewing Audit Trail
```python
audit_log = pricing_db.get_audit_log(limit=50)
# Returns:
# [
#   {
#     "changed_at": "2026-01-30T05:50:00",
#     "changed_by": "admin@example.com",
#     "description": "Pricing configuration updated"
#   }
# ]
```

---

## Security Features

### 1. Application-Level Access
Only the backend API can modify pricing. Direct file manipulation is prevented.

### 2. Admin Authentication Required
```python
@router.post("/pricing/config")
async def update_pricing_config(admin: User = Depends(require_admin)):
    # Only admins with valid JWT can access
```

### 3. Audit Trail
Every change records:
- ✅ Timestamp
- ✅ Admin email
- ✅ Old value (entire config)
- ✅ New value (entire config)
- ✅ Description

### 4. Input Validation
All pricing values validated:
```python
@validator('action_costs')
def validate_action_costs(cls, v):
    for action, cost in v.items():
        if cost < 0 or cost > 1000:
            raise ValueError(f'Invalid cost: {cost}')
```

### 5. Database ACLs
Database file permissions:
```bash
chmod 600 backend/database/pricing.db  # Owner read/write only
```

---

## Backup & Recovery

### Backup Database
```bash
cp backend/database/pricing.db backend/database/pricing.db.backup
```

### Restore from Backup
```bash
cp backend/database/pricing.db.backup backend/database/pricing.db
```

### View Audit Log (SQL)
```bash
sqlite3 backend/database/pricing.db
SELECT * FROM pricing_audit_log ORDER BY id DESC LIMIT 10;
```

---

## Production Deployment

### Checklist
- [x] Database migrated from JSON
- [x] JSON file gitignored
- [x] Database file gitignored
- [x] Admin authentication enforced
- [x] Audit logging enabled
- [x] Input validation active
- [ ] Database backed up regularly (production)
- [ ] Monitor audit log for suspicious changes

### Environment Setup
```bash
# Set proper permissions
chmod 600 backend/database/pricing.db

# Backup cron job (production)
0 2 * * * cp /path/to/pricing.db /path/to/backup/pricing-$(date +\%Y\%m\%d).db
```

---

## FAQ

**Q: Can I still use JSON files?**  
A: No, JSON support is removed. Database is the only storage.

**Q: What if database gets corrupted?**  
A: Restore from backup. Backups are essential in production.

**Q: Can I manually edit the database?**  
A: Not recommended. Use Admin Panel for all changes (audit trail).

**Q: Where are changes logged?**  
A: Two places:
1. `pricing_audit_log` table (full history)
2. `usage_logs` table (admin action tracking)

**Q: Can I rollback a pricing change?**  
A: Yes, view `pricing_audit_log`, copy `old_value`, and save via Admin Panel.

---

## Comparison: Before vs After

| Feature | JSON File | Database |
|---------|-----------|----------|
| Storage | File system | SQLite DB |
| Security | File permissions | Application-level |
| Audit | None | Full trail |
| Backup | Manual copy | DB backup tools |
| Recovery | Restore file | Restore DB |
| Access | Anyone with file access | Admin API only |
| Validation | None | Full validation |
| Git-safe | ❌ Risk exposure | ✅ Gitignored |

---

**Your pricing is now secure! 🔒**
