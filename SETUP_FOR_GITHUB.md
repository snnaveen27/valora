# Setup for GitHub Push

## Pre-Push Checklist

### 1. Verify Sensitive Files are Gitignored

Check that these files are NOT being committed:

```bash
# Check what will be committed
git status

# These should NOT appear:
# ❌ backend/config/pricing_config.json (use template instead)
# ❌ backend/training_data/*.jsonl
# ❌ backend/session_memory/*.json
# ❌ backend/admin_config.json
# ❌ backend/llm_config.json
# ❌ .env
# ❌ *.db files
```

### 2. Create Template Files

```bash
# Pricing config template (already created)
# backend/config/pricing_config.template.json ✅

# Create .env.example
cat > .env.example << 'EOF'
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/valora

# Payment Gateways
RAZORPAY_KEY_ID=rzp_test_xxxxxxxxxxxxx
RAZORPAY_KEY_SECRET=xxxxxxxxxxxxxxxxxxxxxxxx
CASHFREE_APP_ID=xxxxxxxxxxxxxxxxxxxxx
CASHFREE_SECRET_KEY=xxxxxxxxxxxxxxxxxxxxxxxx
STRIPE_SECRET_KEY=sk_test_xxxxxxxxxxxxx
STRIPE_PUBLISHABLE_KEY=pk_test_xxxxxxxxxxxxx
STRIPE_WEBHOOK_SECRET=whsec_xxxxxxxxxxxxx

# JWT
JWT_SECRET=your-secret-key-here

# LLM (Optional)
OPENAI_API_KEY=sk-xxxxxxxxxxxxx
EOF
```

### 3. Create .gitkeep Files

```bash
# Keep empty directories
touch backend/training_data/.gitkeep
touch backend/session_memory/.gitkeep
touch backend/cache/.gitkeep
```

### 4. Test Locally

```bash
# Backend
cd backend
python server.py
# Should start without errors

# Frontend (new terminal)
npm run dev
# Should start on http://localhost:3000
```

### 5. Initialize Git (if not already)

```bash
# Check if git is initialized
git status

# If not initialized:
git init
git branch -M main
```

### 6. Add Files

```bash
# Add all files (respecting .gitignore)
git add .

# Verify what's being added
git status

# Should see:
# ✅ backend/config/pricing_config.template.json
# ✅ backend/usage_tracker.py
# ✅ backend/admin_routes.py
# ✅ src/components/PricingManager.jsx
# ✅ docs/*.md
# ✅ .gitignore

# Should NOT see:
# ❌ backend/config/pricing_config.json
# ❌ backend/training_data/*.jsonl
# ❌ .env
```

### 7. Commit

```bash
git commit -m "feat: Add usage-based monetization with admin pricing config

- Implemented usage tracking with compute units
- Added admin-editable pricing configuration
- Created pricing management UI in admin panel
- Added security measures (rate limiting, input validation, audit logs)
- Organized backend files and documentation
- Added training data collection for ML
- Aligned pricing with business model (1,2,3,10,15,20,25 units)
- Added tier-based monthly limits (Free:50, Pro:1000, Team:3000)
- Implemented 402 Payment Required responses with upgrade options"
```

### 8. Create GitHub Repository

**Option A: Via GitHub CLI**
```bash
gh repo create valora-ai --public --source=. --remote=origin
```

**Option B: Via GitHub Web**
1. Go to https://github.com/new
2. Repository name: `valora-ai`
3. Description: "Offline-first 3D GIS + AI reasoning platform for real estate intelligence"
4. Public or Private (your choice)
5. Don't initialize with README (we have one)
6. Click "Create repository"

### 9. Add Remote and Push

```bash
# Add remote (replace with your username)
git remote add origin https://github.com/YOUR_USERNAME/valora-ai.git

# Verify remote
git remote -v

# Push to GitHub
git push -u origin main
```

### 10. Post-Push Setup on GitHub

**Add Repository Description:**
- Offline-first 3D GIS + AI reasoning platform for real estate intelligence

**Add Topics:**
- `real-estate`
- `gis`
- `ai`
- `3d-visualization`
- `offline-first`
- `fastapi`
- `react`
- `cesiumjs`
- `monetization`

**Create Releases:**
```bash
# Tag current version
git tag -a v1.0.0 -m "Initial release with usage-based monetization"
git push origin v1.0.0
```

**Setup GitHub Actions (Optional):**
Create `.github/workflows/test.yml` for CI/CD

---

## Post-Deployment Setup

### For Production Server

1. **Clone repository:**
```bash
git clone https://github.com/YOUR_USERNAME/valora-ai.git
cd valora-ai
```

2. **Create production config:**
```bash
cp backend/config/pricing_config.template.json backend/config/pricing_config.json
# Edit with production values
```

3. **Set environment variables:**
```bash
cp .env.example .env
# Edit with production credentials
```

4. **Install dependencies:**
```bash
# Backend
cd backend
pip install -r requirements.txt

# Frontend
cd ..
npm install
npm run build
```

5. **Initialize database:**
```bash
python backend/database/init_db.py
```

6. **Start services:**
```bash
# Use PM2, systemd, or Docker
pm2 start backend/server.py --name valora-backend
pm2 start npm --name valora-frontend -- start
```

---

## Troubleshooting

### Issue: Pricing config not found
**Solution:**
```bash
cp backend/config/pricing_config.template.json backend/config/pricing_config.json
```

### Issue: Training data directory missing
**Solution:**
```bash
mkdir -p backend/training_data
touch backend/training_data/.gitkeep
```

### Issue: Permission denied on push
**Solution:**
```bash
# Setup SSH key or use personal access token
gh auth login
```

### Issue: Large files rejected
**Solution:**
```bash
# Check file sizes
find . -type f -size +50M

# Add to .gitignore if needed
echo "large_file.db" >> .gitignore
```

---

## Security Checklist Before Push

- [ ] No API keys in code
- [ ] No passwords in code
- [ ] No database credentials in code
- [ ] `.env` is gitignored
- [ ] `pricing_config.json` is gitignored (template only)
- [ ] Training data is gitignored
- [ ] Session data is gitignored
- [ ] Database files are gitignored
- [ ] All secrets use environment variables

---

## Ready to Push?

Run this final check:

```bash
# Check for secrets
git grep -i "api_key\|password\|secret" | grep -v ".gitignore\|.md\|template"

# Should return nothing or only safe references
```

If clean, proceed with push! 🚀
