# ☁️ Valora Cloud Data Layer Setup Guide

Complete guide to setting up Valora's cloud-based data infrastructure using free-tier services.

---

## 📋 Overview

Valora uses a **100% cloud-based data layer** with free-tier services:

| Service | Purpose | Free Tier | Cost After |
|---------|---------|-----------|------------|
| **Supabase** | PostgreSQL + PostGIS + pgvector | 500 MB, Unlimited API | $25/mo for 8 GB |
| **Upstash Redis** | Cache layer | 10K req/day, 256 MB | $10/mo for 1M req/day |
| **Cloudflare R2** | File storage | 10 GB, 1M ops/month | $0.015/GB |
| **Pinecone** | Vector search | 1 index, 100K vectors | $70/mo for more |

**Total Monthly Cost:** **$0** for MVP/Testing

---

## 🚀 Step-by-Step Setup

### **1. Supabase (Primary Database)**

#### **Create Project**

1. Go to https://supabase.com
2. Click **"Start your project"**
3. Sign in with GitHub
4. Click **"New Project"**
   - **Organization:** Create new or select existing
   - **Name:** `valora-ai` (or your choice)
   - **Database Password:** Generate strong password (save it!)
   - **Region:** `ap-south-1` (Mumbai - closest to India)
   - **Pricing Plan:** Free
5. Wait 2-3 minutes for provisioning

#### **Get Connection Details**

1. Go to **Settings → Database**
2. Scroll to **Connection String**
3. Select **"Connection pooling"** tab (important for serverless)
4. Copy the URI (looks like `postgresql://postgres:[password]@db.xxx.supabase.co:6543/postgres?pgbouncer=true`)
5. Replace `[password]` with your actual database password

#### **Get API Keys**

1. Go to **Settings → API**
2. Copy:
   - **Project URL** (e.g., `https://xxx.supabase.co`)
   - **anon public** key
   - **service_role** key (keep secret!)

#### **Update .env**

```bash
# In your .env file
DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@db.YOUR_REF.supabase.co:6543/postgres?pgbouncer=true
SUPABASE_URL=https://YOUR_REF.supabase.co
SUPABASE_ANON_KEY=your_anon_key_here
SUPABASE_SERVICE_KEY=your_service_role_key_here
```

#### **Initialize Database**

```bash
# Install dependencies
pip install python-dotenv sqlalchemy psycopg2-binary

# Run initialization script
python scripts/init_supabase.py
```

This will:
- Enable PostGIS, pgvector, and other extensions
- Create all tables (properties, localities, transactions, etc.)
- Set up indexes and constraints

#### **Seed Sample Data (Optional)**

```bash
python scripts/seed_data.py
```

Adds sample Bangalore localities and properties for testing.

---

### **2. Upstash Redis (Cache Layer)**

#### **Create Database**

1. Go to https://console.upstash.com
2. Sign up (GitHub login recommended)
3. Click **"Create Database"**
   - **Name:** `valora-cache`
   - **Type:** `Global` (multi-region replication)
   - **Region:** Primary: `ap-south-1` (Mumbai)
   - **Eviction:** `allkeys-lru` (auto-remove old keys)
4. Click **Create**

#### **Get Connection Details**

1. In database dashboard, go to **"REST API"** tab
2. Copy:
   - **UPSTASH_REDIS_REST_URL**
   - **UPSTASH_REDIS_REST_TOKEN**
3. Go to **"CLI"** tab
4. Copy the Redis URL (format: `redis://default:password@endpoint.upstash.io:6379`)

#### **Update .env**

```bash
REDIS_URL=redis://default:YOUR_PASSWORD@YOUR_ENDPOINT.upstash.io:6379
UPSTASH_REDIS_REST_URL=https://YOUR_ENDPOINT.upstash.io
UPSTASH_REDIS_REST_TOKEN=your_token_here
```

#### **Verify Connection**

```python
# Test Redis connection
python -c "
import os
from redis import Redis
redis_client = Redis.from_url(os.getenv('REDIS_URL'))
redis_client.set('test', 'hello')
print('✅ Redis working:', redis_client.get('test').decode())
"
```

---

### **3. Cloudflare R2 (File Storage)**

#### **Create R2 Bucket**

1. Go to https://dash.cloudflare.com
2. Navigate to **R2 Object Storage**
3. Click **"Create bucket"**
   - **Bucket name:** `valora-storage`
   - **Location:** Automatic (distributed globally)
4. Click **Create bucket**

#### **Generate API Token**

1. Go to **R2 → Manage R2 API Tokens**
2. Click **"Create API Token"**
   - **Token name:** `valora-api-token`
   - **Permissions:** `Object Read & Write`
   - **Apply to:** Specific bucket: `valora-storage`
3. Copy:
   - **Access Key ID**
   - **Secret Access Key**
   - **Endpoint URL** (format: `https://[ACCOUNT_ID].r2.cloudflarestorage.com`)

#### **Update .env**

```bash
R2_ACCOUNT_ID=your_account_id
R2_ACCESS_KEY_ID=your_access_key
R2_SECRET_ACCESS_KEY=your_secret_key
R2_BUCKET_NAME=valora-storage
R2_ENDPOINT=https://YOUR_ACCOUNT_ID.r2.cloudflarestorage.com
```

#### **Test Connection**

```python
# Test R2 connection
python -c "
import boto3
import os
s3 = boto3.client('s3',
    endpoint_url=os.getenv('R2_ENDPOINT'),
    aws_access_key_id=os.getenv('R2_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY'))
s3.put_object(Bucket='valora-storage', Key='test.txt', Body=b'Hello from Valora!')
print('✅ R2 storage working')
"
```

---

### **4. Pinecone (Vector Search)** - Already Configured ✅

Your `.env` already has:
```bash
PINECONE_API_KEY=pcsk_7SC4c3_...
PINECONE_INDEX=valora-realestate
```

No changes needed!

---

## 🔍 Verification Checklist

Run this script to verify all services:

```bash
python -c "
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from redis import Redis

load_dotenv()

# 1. Check Supabase
try:
    engine = create_engine(os.getenv('DATABASE_URL'))
    with engine.connect() as conn:
        result = conn.execute(text('SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = \'public\''))
        tables = result.fetchone()[0]
        print(f'✅ Supabase: {tables} tables created')
except Exception as e:
    print(f'❌ Supabase: {str(e)[:50]}')

# 2. Check Redis
try:
    redis_client = Redis.from_url(os.getenv('REDIS_URL'))
    redis_client.ping()
    print('✅ Upstash Redis: Connected')
except Exception as e:
    print(f'❌ Redis: {str(e)[:50]}')

# 3. Check R2 (boto3 required)
try:
    import boto3
    s3 = boto3.client('s3',
        endpoint_url=os.getenv('R2_ENDPOINT'),
        aws_access_key_id=os.getenv('R2_ACCESS_KEY_ID'),
        aws_secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY'))
    buckets = s3.list_buckets()
    print(f'✅ Cloudflare R2: {len(buckets[\"Buckets\"])} buckets')
except Exception as e:
    print(f'⚠️  R2: Not configured (optional)')

print('\n🎉 Cloud infrastructure ready!')
"
```

---

## 📊 Admin Dashboard Monitoring

Once configured, go to **Admin Dashboard → Data Layer** to see:

- **Cloud Status:** Real-time health of Supabase, Redis, R2
- **Data Sources:** All active data sources
- **Storage Usage:** Database size, cache hits, file storage
- **Performance:** Query latency, cache efficiency

---

## 🔧 Configuration Summary

Your final `.env` should have:

```bash
# ===== CLOUD DATABASE (SUPABASE) =====
DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[REF].supabase.co:6543/postgres?pgbouncer=true
SUPABASE_URL=https://[REF].supabase.co
SUPABASE_ANON_KEY=[ANON_KEY]
SUPABASE_SERVICE_KEY=[SERVICE_KEY]

# ===== CLOUD CACHE (UPSTASH REDIS) =====
REDIS_URL=redis://default:[PASSWORD]@[ENDPOINT].upstash.io:6379
UPSTASH_REDIS_REST_URL=https://[ENDPOINT].upstash.io
UPSTASH_REDIS_REST_TOKEN=[TOKEN]

# ===== CLOUD STORAGE (CLOUDFLARE R2) =====
R2_ACCOUNT_ID=[ACCOUNT_ID]
R2_ACCESS_KEY_ID=[ACCESS_KEY]
R2_SECRET_ACCESS_KEY=[SECRET_KEY]
R2_BUCKET_NAME=valora-storage
R2_ENDPOINT=https://[ACCOUNT_ID].r2.cloudflarestorage.com

# ===== VECTOR SEARCH (PINECONE) - Already set =====
PINECONE_API_KEY=pcsk_7SC4c3_...
PINECONE_INDEX=valora-realestate
```

---

## 📈 Scaling Guide

### **When to Upgrade**

| Metric | Free Tier Limit | When to Upgrade | Paid Tier Cost |
|--------|-----------------|-----------------|----------------|
| **Database Size** | 500 MB | ~50K properties | Supabase Pro: $25/mo (8 GB) |
| **Cache Requests** | 10K/day | ~300 users/day | Upstash: $10/mo (1M req/day) |
| **File Storage** | 10 GB | ~50K images | R2: Pay per GB ($0.015/GB) |

### **Upgrade Steps**

1. **Supabase Pro:**
   - Go to Settings → Billing
   - Upgrade to Pro plan
   - Get 8 GB database, 100 GB bandwidth

2. **Upstash Pro:**
   - Dashboard → Upgrade
   - Get 1M req/day, 1 GB storage

3. **R2 Paid:**
   - Automatic billing
   - Only pay for what you use

---

## 🛠️ Troubleshooting

### **Supabase Connection Issues**

```bash
# Check if using connection pooler (port 6543, not 5432)
echo $DATABASE_URL | grep "6543"

# Verify password doesn't have special characters breaking URL
# If it does, URL-encode it
```

### **Redis Connection Timeout**

```bash
# Try REST API instead of native Redis protocol
# Use UPSTASH_REDIS_REST_URL with HTTP requests
```

### **R2 Access Denied**

```bash
# Verify bucket name matches exactly
# Check API token has Read & Write permissions
# Ensure endpoint URL is correct
```

---

## 📚 Additional Resources

- **Supabase Docs:** https://supabase.com/docs
- **Upstash Docs:** https://docs.upstash.com/redis
- **Cloudflare R2 Docs:** https://developers.cloudflare.com/r2/
- **Valora Architecture:** See `docs/ARCHITECTURE.md`

---

## ✅ Success Criteria

You're ready when:

- ✅ `python scripts/init_supabase.py` completes successfully
- ✅ Admin Dashboard → Data Layer shows "Cloud Data Layer Active"
- ✅ Backend starts without database errors
- ✅ Properties can be added/retrieved from Supabase
- ✅ Cache is working (check Redis keys in Upstash dashboard)

---

**Need Help?** Check logs in:
- Backend: `logs/backend/dmpe.log`
- Admin Dashboard: Browser console (F12)
- Supabase: Dashboard → Logs
- Upstash: Dashboard → Metrics
