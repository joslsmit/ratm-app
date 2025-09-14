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
*   **`FLASK_SECRET_KEY`:** Required for Flask sessions (Yahoo OAuth state). Store in Render env (prod) and `backend/.env` (local). Generate with `python3 -c "import secrets; print(secrets.token_hex(32))"`.
*   **`YAHOO_CLIENT_ID` / `YAHOO_CLIENT_SECRET`:** Yahoo OAuth credentials. Use PROD app credentials on Render; DEV app credentials in `backend/.env` locally.
*   **`YAHOO_REDIRECT_URI`:** OAuth callback. PROD: `https://ratm-app.onrender.com/api/yahoo/callback`. Local: `https://localhost:5000/api/yahoo/callback` (set in `backend/.env`).
*   **`.env` files:** Local development uses `backend/.env` (git‑ignored) so secrets are not committed.
*   **Render Environment:** Set `FLASK_SECRET_KEY`, `YAHOO_CLIENT_ID`, `YAHOO_CLIENT_SECRET`, and `YAHOO_REDIRECT_URI` in the Render dashboard.

### B. API Endpoints
*   **Frontend `API_BASE_URL`:** Configured in `frontend/src/context/AppContext.js`.
    *   Local: `https://localhost:5000/api` (using `mkcert` for HTTPS)
    *   Production: `https://ratm-app.onrender.com/api`
*   **Backend `/api/*` endpoints:** All API endpoints are prefixed with `/api/` (e.g., `/api/player_dossier`, `/api/rookie_rankings`). Key endpoints:
    - `GET /api/yahoo/waiver_pool`
    - `POST /api/yahoo/waiver_recommendations_v2`
    - `POST /api/yahoo/waiver_recommendations_ai` — AI‑authority, supports `?debug=1` to return full prompt and diagnostics
    - `POST /api/optimize_lineup` — Yahoo lineup optimizer: returns `suggested_lineup`, `diff`, `eligibility_info`, plus `ai_note_json` with `{ confidence, headline, reasons[], tags[], score_breakdown{} }`. Supports `?debug=1` (or body `{debug:true}`) to include `consensus_inputs`, `matchup_inputs`, `opponent_projection`, and `slots_filled`.
    - `GET /api/diagnostics/yahoo-data-health` — League diagnostics (CSV freshness, enrichment coverage); requires Yahoo Authorization and `league_key`.
    - `POST /api/admin/refresh_data` — Admin/developer CSV refresh that rebuilds caches.
    - Dev (local only, enable with `RATM_DEV_ENABLE=1`):
      - `POST /api/dev/configure` — store Yahoo token, `league_key`, `team_key`, optional `gemini_key` (saved in `backend/.dev/waiver_v4.json`)
      - `POST /api/dev/run_waiver_v4_test` — runs roster + v2 + AI using stored config; returns compact JSON bundle

### C. CORS Configuration
*   **Location:** `backend/app.py`
*   **Allowed Origins:**
    *   `http://localhost:3000` (for local frontend development)
    *   `https://localhost:5000` (for local HTTPS development with mkcert)
    *   `https://ratm-app-git-oauth-dev-joshua-smiths-projects-2dcfc522.vercel.app` (legacy Vercel deployment)
    *   `https://ratm-app.vercel.app` (current production Vercel frontend)
*   **Purpose:** Ensures the browser allows the frontend to make requests to the backend API.
*   **Production Issue Resolution (August 27, 2025):** Added `https://ratm-app.vercel.app` to CORS origins to resolve "Access-Control-Allow-Origin" errors when frontend deployed to production.

### D. Data & Navigation
*   **`basedir`:** Defined in `backend/app.py` to correctly resolve paths to local data files.
*   **CSV Data:** The backend downloads/refreshes CSV data at runtime (`import_data()` at startup and via `/api/admin/refresh_data`). CSV files are no longer tracked in Git and are ignored by `.gitignore`.
*   **Navigation:** Sidebar uses a Season Mode switch (In‑Season / Pre‑Season) with a Show All toggle; quick actions provide direct access to common in‑season tools.

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

## 5. Production Deployment (Updated September 3, 2025)

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

### Debug verbosity control

- Backend prints are concise by default. A single one‑line summary is emitted after CSV/ECR/projections load, e.g.
  - `Data loaded | players:11400 ECR[bo:521, bp:574, drk:113] weekly:892 combined:1141 aliases:0`
- Set `RATM_DEBUG=1` to re‑enable detailed DEBUG traces:
  - Yahoo pagination and parse traces, raw response key hints, roster parsing fallbacks, waiver pool paging/enrichment messages
  - CSV download/update messages in `backend/data_importer.py`
- Example:
  ```bash
  export RATM_DEBUG=1
  cd backend && python app.py
  ```

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

## 7. Waiver Wire v3 — Implementation Notes (Sept 3)
- AI‑first endpoint `/api/yahoo/waiver_recommendations_ai` combines deterministic candidate generation with Gemini ranking/explanation.
- Debug: `?debug=1` returns full prompt, prompt length, coverage, and AI response meta.
- Deterministic baselines calibrated for 6‑pt passing TD leagues (QB 12.0; RB/WR 7.5; TE 5.0).
- Frontend shows “AI” vs “Deterministic” source chip on each recommendation card; “Why” bullets shown by default; details collapsed.

### League Scoring Reference
- Offensive scoring settings documented in `records/league_scoring_offense.md`.
- Bench VOR baselines are aligned to these rules; projections consumed are PPR (r2p_pts).
## 8. Sit/Start Optimizer — Implementation Notes (Sept 4–5)
- Yahoo‑only endpoint implemented; deterministic selection driven by weekly projections; excludes BYE/OUT; Q/D flagged.
- Structured AI note: up to 3 grounded reasons (Projection/Matchup/Status/Variance/Correlation/Consensus/Usage/Confidence/Context) with canonical tags and a score breakdown (projection plus small nudges: matchup ±0.10, correlation/variance in close calls).
- ECR: overall ECR used for cross‑position; weekly positional rank only for same‑position; neutral Overall ECR context when gaps are small.
- Matchup: opponent + HOME/AWAY always shown; categorical difficulty (Easy/Moderate/Tough) mapped and surfaced when meaningful with a small numeric nudge.
- UI renders structured card only; markdown hidden.
- Test script: project root `./test_script` — set `TOKEN` (Yahoo), optional `GEMINI_KEY`; add `INSECURE=1` if using mkcert locally. Smoketest also available at `scripts/test_lineup_optimizer.zsh`.
## 9. Waiver Wire v4 — Dev Runner & Scripts (Sept 14)
- Enable dev mode for backend: `export RATM_DEV_ENABLE=1; python app.py`
- Configure once with your token/keys (local only):
  - `scripts/dev_config_waiver_v4.zsh` (reads `TOKEN`, `LEAGUE_KEY`, `TEAM_KEY`, optional `GEMINI_KEY` from env)
- One‑shot run (roster + v2 + AI):
  - `scripts/dev_run_waiver_v4.zsh` (optional overrides: `STATUS`, `ALTS`, `MINB`, `USE_AI`)
- Notes: endpoints use loopback HTTPS; scripts pass `-k` to allow mkcert self‑signed certs locally.
