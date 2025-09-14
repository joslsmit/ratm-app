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

### 2. Yahoo OAuth for Local Testing (Two‑App Recommended)
**Preferred**: Use two Yahoo apps so you don’t flip Homepage.

**Local Dev app**: Homepage `http://localhost:3000`, Redirect `https://localhost:5000/api/yahoo/callback`
**Production app**: Homepage `https://ratm-app.vercel.app`, Redirect `https://ratm-app.onrender.com/api/yahoo/callback`

**Local backend config**: put credentials in `backend/.env`:
```
YAHOO_CLIENT_ID=YOUR_DEV_YAHOO_CLIENT_ID
YAHOO_CLIENT_SECRET=YOUR_DEV_YAHOO_CLIENT_SECRET
YAHOO_REDIRECT_URI=https://localhost:5000/api/yahoo/callback
FLASK_SECRET_KEY=YOUR_LOCAL_SECRET  # generate with: python3 -c "import secrets; print(secrets.token_hex(32))"
```
Start backend from `backend/` so `load_dotenv()` picks up `backend/.env`.

### 3. Restart Backend
```bash
# Stop backend (Ctrl+C) and restart
python app.py
```

**Result**: Yahoo OAuth now works locally, redirects to localhost, full functionality restored.

---

## 📤 LOCAL DEVELOPMENT → PRODUCTION

### 1. Production deploy checklist (Two‑App model)
- Render env: `YAHOO_CLIENT_ID`/`YAHOO_CLIENT_SECRET` (PROD), `YAHOO_REDIRECT_URI=https://ratm-app.onrender.com/api/yahoo/callback`, `FLASK_SECRET_KEY`
- No need to flip Yahoo Homepage if using two apps.

### 2. Test Production Configuration Locally (Optional but Recommended)
```bash
# Temporarily test with production OAuth settings
# Verify no localhost overrides remain in your shell
unset YAHOO_REDIRECT_URI
# Test that production redirects work as expected
```

### 3. Deploy to Production
```bash
# Commit changes
git add . && git commit -m "feat: [description]"

# Merge to main and push
git checkout main && git merge feature/[name] && git push origin main
```

### 4. Verify Deployment
- **Vercel + Render auto-deploy** from main branch (2-5 minutes)
- **Test**: https://ratm-app.vercel.app works with Yahoo login
- **Verify**: OAuth redirects to Vercel (not localhost)

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
# Ensure backend/.env contains your Local Dev Yahoo credentials
```

### Deploy to Production  
```bash
# Render has PROD Yahoo credentials + redirect + FLASK_SECRET_KEY
git checkout main && git merge feature/[name] && git push origin main
```

### Environment Check
```bash
lsof -i :5000  # Check port availability
git branch     # Verify current branch
```

---

**Key Point**: The only real blocker is the hardcoded Yahoo OAuth URL. Everything else in your local setup was already working correctly.
