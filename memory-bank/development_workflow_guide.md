# RATM App: Development Workflow Guide

> **File Type**: GO-FORWARD REFERENCE  
> **Last Updated**: August 30, 2025  
> **Purpose**: Streamlined instructions for production ↔ local development switching

## 🎯 CORE ISSUE IDENTIFIED

Your local development was working last week, but now fails because:
- **Yahoo OAuth URL hardcoded** to production in `backend/app.py` line 2377
- **Backend always redirects** to `https://ratm-app.onrender.com/api/yahoo/callback` 
- **Should redirect** to `https://localhost:5000/api/yahoo/callback` for local development

**Yahoo Console Setup**: ✅ Already correct - both URLs configured

---

## 🚀 PRODUCTION → LOCAL DEVELOPMENT

### 1. Branch & Start Servers
```bash
# Create feature branch
git checkout -b feature/[name]

# Terminal 1: Backend
cd backend && source venv/bin/activate && python app.py

# Terminal 2: Frontend  
cd frontend && npm start
```

### 2. Fix Yahoo OAuth for Local Testing (CRITICAL)
**⚠️ The main issue**: Temporarily change `backend/app.py` line 2377:

```python
# TEMPORARY - Change this line for local development:
YAHOO_REDIRECT_URI = 'https://localhost:5000/api/yahoo/callback'

# Instead of:
# YAHOO_REDIRECT_URI = 'https://ratm-app.onrender.com/api/yahoo/callback'
```

### 3. Restart Backend
```bash
# Stop backend (Ctrl+C) and restart
python app.py
```

**Result**: Yahoo OAuth now works locally, full functionality restored.

---

## 📤 LOCAL DEVELOPMENT → PRODUCTION

### 1. Revert OAuth URL (CRITICAL)
**⚠️ Before committing**: Change `backend/app.py` line 2377 back to:

```python
YAHOO_REDIRECT_URI = 'https://ratm-app.onrender.com/api/yahoo/callback'
```

### 2. Deploy to Production
```bash
# Commit changes
git add . && git commit -m "feat: [description]"

# Merge to main and push
git checkout main && git merge feature/[name] && git push origin main
```

### 3. Verify Deployment
- **Vercel + Render auto-deploy** from main branch (2-5 minutes)
- **Test**: https://ratm-app.vercel.app works with Yahoo login

---

## 🔧 QUICK TROUBLESHOOTING

**"Address already in use on port 5000"**
```bash
# Disable AirPlay Receiver: System Settings → General → AirDrop & Handoff → OFF
# Or kill process: sudo kill -9 $(lsof -ti:5000)
```

**"Yahoo OAuth 401 errors"**  
- Check: `YAHOO_REDIRECT_URI` matches environment (local vs production)
- Local needs: `https://localhost:5000/api/yahoo/callback`
- Production needs: `https://ratm-app.onrender.com/api/yahoo/callback`

**"Frontend can't connect to backend"**
- Check: Backend running on `https://localhost:5000`
- Check: No CORS errors in browser console

**"Production deployment broken"**
```bash
# Emergency revert
git revert HEAD && git push origin main
```

---

## ⚡ QUICK REFERENCE

### Start Local Development
```bash
git checkout -b feature/[name]
cd backend && source venv/bin/activate && python app.py
cd frontend && npm start
# Fix YAHOO_REDIRECT_URI in app.py line 2377
```

### Deploy to Production  
```bash
# Revert YAHOO_REDIRECT_URI in app.py line 2377
git checkout main && git merge feature/[name] && git push origin main
```

### Environment Check
```bash
lsof -i :5000  # Check port availability
git branch     # Verify current branch
```

---

**Key Point**: The only real blocker is the hardcoded Yahoo OAuth URL. Everything else in your local setup was already working correctly.