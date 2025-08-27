# RATM Draft Kit: Technical Context - GO-FORWARD

> **File Type**: GO-FORWARD  
> **Review Priority**: High  
> **Last Updated**: August 19, 2025  
> **Purpose**: Development environment, configurations, and technical setup details

This document provides detailed technical information about the RATM Draft Kit project, covering development environment setup, key configurations, and specific tool usages.

## 1. Development Environment

### A. Local Setup
*   **Backend:** Python 3.x, `pip` for package management. Virtual environment (e.g., `venv`) is recommended for dependency isolation.
*   **Frontend:** Node.js (LTS version recommended), `npm` or `yarn` for package management.
*   **Git:** Version control system.
*   **Editor:** VS Code (recommended) with relevant extensions (Python, ESLint, Prettier, etc.).

### B. Dependencies
*   **Python Dependencies (backend/requirements.txt):**
    *   `Flask==3.1.1`: Web framework.
    *   `Flask-Cors==6.0.1`: Handles Cross-Origin Resource Sharing.
    *   `python-dotenv==1.1.1`: Loads environment variables from `.env` files.
    *   `requests==2.32.4`: HTTP library for making external API calls (e.g., to Sleeper API).
    *   `pandas==2.3.0`: Data manipulation and analysis (used for CSV processing).
    *   `google-generativeai==0.8.5`: Python client for Google Gemini API.
    *   `APScheduler==3.11.0`: Advanced Python Scheduler for background tasks (data refresh).
    *   `gunicorn`: WSGI HTTP Server for UNIX (production web server).
    *   Other transitive dependencies as listed in `requirements.txt`.
*   **JavaScript Dependencies (frontend/package.json):**
    *   `react`, `react-dom`, `react-scripts`: Core React development.
    *   `@tarekraafat/autocomplete.js`: Frontend autocomplete functionality.
    *   `showdown`: Markdown to HTML conversion.
    *   Other development and production dependencies as listed in `package.json`.

## 2. Key Configurations

### A. Environment Variables
*   **`FLASK_SECRET_KEY`:** Used by Flask for session management and security. Loaded via `os.getenv("FLASK_SECRET_KEY")` in `backend/app.py`.
*   **`.env` files:** Used for local development to store environment variables. **`.env` and `.env.test` are listed in `.gitignore` and should not be committed to the repository.**
*   **Render Environment:** `FLASK_SECRET_KEY` must be set as an environment variable directly in the Render dashboard for production deployment.

### B. API Endpoints
*   **Frontend `API_BASE_URL`:** Configured in `frontend/src/context/AppContext.js`.
    *   Local: `https://localhost:5000/api` (using `mkcert` for HTTPS)
    *   Production: `https://ratm-app.onrender.com/api`
*   **Backend `/api/*` endpoints:** All API endpoints are prefixed with `/api/` (e.g., `/api/player_dossier`, `/api/rookie_rankings`).

### C. CORS Configuration
*   **Location:** `backend/app.py`
*   **Allowed Origins:**
    *   `http://localhost:3000` (for local frontend development)
    *   `https://localhost:5000` (for local HTTPS development with mkcert)
    *   `https://ratm-app-git-oauth-dev-joshua-smiths-projects-2dcfc522.vercel.app` (legacy Vercel deployment)
    *   `https://ratm-app.vercel.app` (current production Vercel frontend)
*   **Purpose:** Ensures the browser allows the frontend to make requests to the backend API.
*   **Production Issue Resolution (August 27, 2025):** Added `https://ratm-app.vercel.app` to CORS origins to resolve "Access-Control-Allow-Origin" errors when frontend deployed to production.

### D. Data Paths
*   **`basedir`:** Defined in `backend/app.py` to correctly resolve paths to local data files.
*   **CSV Files:** `db_fpecr_latest.csv`, `values-players.csv`, `values-picks.csv` are expected to be present in the `backend/` directory.

## 3. Tool-Specific Context

### A. Git & GitHub
*   **Main Branch:** `main` (production branch for stable releases and deployments).
*   **Development Branches:** `yahoo-features`, `oauth-dev` (feature development branches, merged to main for production).
*   **Branch Protection:** Temporarily removed for direct main branch updates (August 27, 2025).
*   **Commit Messages:** General convention is descriptive and follows a clear purpose (e.g., "Fix: ...", "Feat: ...", "Update: ...").

### B. Render (Backend Deployment)
*   **Service Type:** Web Service.
*   **Production Branch:** `main` (automatically deploys from main branch).
*   **Build Command:** `pip install -r requirements.txt` (auto-detected).
*   **Start Command:** `gunicorn app:app` (auto-detected).
*   **Environment Variables:** Must be set manually in the Render dashboard (FLASK_SECRET_KEY, YAHOO_CLIENT_ID, YAHOO_CLIENT_SECRET).
*   **Production URL:** `https://ratm-app.onrender.com`

### C. Vercel (Frontend Deployment)
*   **Project Linking:** Linked to the GitHub repository.
*   **Production Branch:** `main` (updated August 27, 2025 from oauth-dev).
*   **Root Directory:** `frontend` (auto-detected React project).
*   **Build & Start Commands:** Vercel automatically detects React projects and handles these.
*   **Production URL:** `https://ratm-app.vercel.app`

## 5. Production Deployment (Updated August 27, 2025)

### ✅ Current Production Status
*   **Frontend:** Successfully deployed at `https://ratm-app.vercel.app`
*   **Backend:** Successfully deployed at `https://ratm-app.onrender.com`
*   **Database:** All CSV data files properly loaded and accessible
*   **CORS:** Configured to allow production frontend access
*   **Connection:** Frontend successfully connects to backend API
*   **Yahoo OAuth:** ✅ Production configuration completed (August 27, 2025)
    *   Environment variables set in Render dashboard: YAHOO_CLIENT_ID, YAHOO_CLIENT_SECRET, FLASK_SECRET_KEY
    *   Redirect URI updated from localhost to production: `https://ratm-app.onrender.com/api/yahoo/callback`
    *   Yahoo Developer Console updated with production URLs

### Production Deployment Process
1. **Branch Management:** Merge feature branches to `main` for production
2. **Automatic Deployment:** Both Vercel and Render automatically deploy from `main` branch
3. **CORS Configuration:** Ensure `ratm-app.vercel.app` is included in backend CORS origins
4. **Environment Variables:** Set required variables in Render dashboard (FLASK_SECRET_KEY, Yahoo OAuth credentials)

## 6. Security Considerations (Production Roadmap)

*   **Secure Yahoo Token Handling:** For production deployments, the current method of passing Yahoo access tokens via URL parameters is insecure. Implement a more robust and secure method, such as HTTP-only cookies or server-side token exchange, to prevent token exposure.

## 7. Common Issues & Troubleshooting

*   **CORS Errors (RESOLVED August 27, 2025):**
    *   **Symptom:** "Access-Control-Allow-Origin" header missing errors in browser console
    *   **Solution:** Add production frontend domain to CORS origins in `backend/app.py`
    *   **Fix Applied:** Added `https://ratm-app.vercel.app` to allowed origins list
*   **Frontend not loading/connecting:**
    *   Check `API_BASE_URL` in `frontend/src/context/AppContext.js` for correctness (should automatically switch to production URL).
    *   Verify Vercel deployment status.
*   **Yahoo OAuth `INVALID_REDIRECT_URI` error:**
    *   Ensure `YAHOO_REDIRECT_URI` in `backend/app.py` matches the environment (localhost for dev, production URL for prod).
    *   Verify Yahoo Developer Network application settings match the redirect URI.
    *   Confirm Client ID and Client Secret are correct in environment variables.
*   **Backend errors/API calls failing:**
    *   Check Render service logs for Python tracebacks.
    *   Verify environment variables are set correctly on Render.
    *   Confirm data files (`.csv`) are accessible on Render.
    *   Check CORS origins in `backend/app.py` match the frontend's URL.
*   **Git issues:**
    *   Ensure correct branch is checked out.
    *   Check `git status` for untracked/uncommitted changes.
    *   Verify remote tracking branches are set up correctly (`git branch -vv`).

## 6. Testing Infrastructure (Updated August 19, 2025)

### A. Backend Test Suite
*   **Location:** `backend/tests/` directory with organized test scripts and documentation
*   **Test Scripts:**
    *   `test_yahoo_waiver_endpoints.py` - Primary endpoint validation with HTTPS support
    *   `test_yahoo_waiver_validation.py` - Parameter validation focused tests
    *   `test_complete_implementation.py` - Comprehensive implementation overview
    *   `test_yahoo_waiver_complete.py` - Enhanced analysis endpoint testing
    *   `README.md` - Complete testing documentation and usage instructions
*   **Usage:** Run from `backend/tests/` with activated virtual environment
*   **Purpose:** Validate Yahoo implementations (waiver wire, market inefficiency) structure and error handling
*   **Current Status:** ✅ All priority Yahoo implementations tested and validated
