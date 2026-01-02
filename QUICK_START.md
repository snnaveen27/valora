# 🚀 Quick Start Guide - REALTY-GPT Advanced AI Platform

## ⚡ 5-Minute Setup

### **Step 1: Start Services** (3 terminals)

**Terminal 1 - Backend API:**
```bash
cd "C:\Users\Nvnsa\Downloads\New folder\realestate\CascadeProjects\windsurf-project"
.venv\Scripts\activate
python -m uvicorn backend.api.main:app --port 8000 --reload
```

**Terminal 2 - Chat Server:**
```bash
cd "C:\Users\Nvnsa\Downloads\New folder\realestate\CascadeProjects\windsurf-project"
npm start
```

**Terminal 3 - Frontend:**
```bash
cd "C:\Users\Nvnsa\Downloads\New folder\realestate\CascadeProjects\windsurf-project"
npm run dev
```

### **Step 2: Access the Platform**
Open your browser: **http://localhost:3000**

### **Step 3: Try These Features**

#### **🔍 Search Properties:**
Type in chat:
```
"Find 3BHK apartments in Whitefield under 1 crore"
```

#### **⏰ Time Travel:**
1. Look at the **time slider** at the top of the map
2. Drag it to **+2 years** in the future
3. Watch property values update!

#### **📍 Analyze Any Location:**
1. **Right-click** anywhere on the map
2. See instant analysis popup
3. View importance score and investment grade

#### **🏠 Property Details:**
1. **Click** any green/yellow marker on map
2. See comprehensive property analysis
3. View price trends and recommendations

---

## 💡 What You Get

### **Instant Features:**
- ✅ **16,276 properties** ready to explore
- ✅ **Time slider** with 7-year range
- ✅ **AI chat** for property search
- ✅ **Smart predictions** with confidence scores
- ✅ **Investment grades** for any location
- ✅ **Market cycles** and trends

### **Data Loaded:**
- ✅ All Bangalore property data
- ✅ 36 GIS layers (zones, roads, POIs)
- ✅ 29,503 RAG documents processed
- ✅ Mappls integration active

---

## 🎮 Sample Interactions

### **Chat Commands:**
```
✅ "Find properties in HSR Layout"
✅ "Show 2BHK apartments under 50 lakhs"
✅ "Compare Koramangala vs Whitefield"
✅ "What's the rental yield in Electronic City?"
✅ "Predict property values for 2027"
✅ "Draw 2km buffer around Manyata Tech Park"
```

### **Map Interactions:**
```
✅ Right-click → Drop analysis pin
✅ Left-click property → View details
✅ Drag time slider → See future values
✅ Click Play → Watch market evolution
```

---

## 📊 Quick Tests

```bash
# Test complete system
python test_complete_system.py

# Test advanced features
python test_advanced_features.py

# Quick health check
python test_services.py
```

---

## 🎯 Key URLs

| Service | URL |
|---------|-----|
| **Frontend** | http://localhost:3000 |
| **API** | http://localhost:8000 |
| **API Docs** | http://localhost:8000/docs |
| **Chat** | http://localhost:3001 |
| **Health** | http://localhost:8000/health |

---

## ⚠️ Troubleshooting

### **Services Not Starting?**
```bash
# Check if ports are free
netstat -ano | findstr "8000"
netstat -ano | findstr "3001"
netstat -ano | findstr "3000"
```

### **Database Issues?**
```bash
# Verify database connection
python -c "from backend.database.multiconnection import mdb; print('✅ DB OK')"
```

### **Frontend Not Loading?**
- Clear browser cache
- Check console for errors
- Restart Vite server

---

## 📚 More Documentation

- **Complete Guide**: `COMPLETE_DOCUMENTATION.md`
- **Advanced Features**: `ADVANCED_FEATURES.md`
- **Test Results**: `TEST_RESULTS.md`
- **API Reference**: http://localhost:8000/docs

---

## 🎉 You're Ready!

Your **Advanced Real Estate AI Platform** is now running!

### **What to Explore:**
1. **Time Slider** - See property values change over time
2. **Pin Analysis** - Analyze any location instantly
3. **Property Search** - Find your dream property
4. **Market Predictions** - Understand future trends
5. **Investment Insights** - Get AI-powered recommendations

---

**Happy Exploring!** 🏠✨

*Need help? Check `COMPLETE_DOCUMENTATION.md` for detailed information.*
