# RATM Draft Kit: Technical Context

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
    *   `https://ratm-app-git-oauth-dev-joshua-smiths-projects-2dcfc522.vercel.app` (for Vercel-deployed frontend)
*   **Purpose:** Ensures the browser allows the frontend to make requests to the backend API.

### D. Data Paths
*   **`basedir`:** Defined in `backend/app.py` to correctly resolve paths to local data files.
*   **CSV Files:** `db_fpecr_latest.csv`, `values-players.csv`, `values-picks.csv` are expected to be present in the `backend/` directory.

## 3. Tool-Specific Context

### A. Git & GitHub
*   **Main Branch:** `main` (for stable releases, though not heavily used in active development).
*   **Development Branch:** `oauth-dev` (primary branch for active development, features, and deployments).
*   **Commit Messages:** General convention is descriptive and follows a clear purpose (e.g., "Fix: ...", "Feat: ...", "Update: ...").

### B. Render
*   **Service Type:** Web Service.
*   **Build Command:** (Typically `pip install -r requirements.txt` or similar, depending on Render's auto-detection).
*   **Start Command:** (Typically `gunicorn app:app` or `gunicorn app:app --chdir backend`, depending on project structure and Render's configuration).
*   **Environment Variables:** Must be set manually in the Render dashboard.

### C. Vercel
*   **Project Linking:** Linked to the GitHub repository.
*   **Production Branch:** Configured to `oauth-dev` to enable automatic deployments from this branch.
*   **Build & Start Commands:** Vercel automatically detects React projects and handles these.

## 5. Security Considerations (Production Roadmap)

*   **Secure Yahoo Token Handling:** For production deployments, the current method of passing Yahoo access tokens via URL parameters is insecure. Implement a more robust and secure method, such as HTTP-only cookies or server-side token exchange, to prevent token exposure.

*   **Frontend not loading/connecting:**
    *   Check `API_BASE_URL` in `frontend/src/context/AppContext.js` for correctness (should be `https://localhost:5000/api` for local development).
    *   Verify Vercel deployment status.
*   **Yahoo OAuth `INVALID_REDIRECT_URI` error:**
    *   Ensure `YAHOO_REDIRECT_URI` in `backend/app.py` exactly matches the active `localhost` URL (`https://localhost:5000/api/yahoo/callback`).
    *   Verify that the Yahoo Developer Network application settings have *only* `https://localhost:5000/api/yahoo/callback` registered as a redirect URI.
    *   Confirm Client ID and Client Secret are correct in `backend/.env`.
    *   If persistent, create a new Yahoo application with fresh credentials and the correct `localhost` redirect URI.
*   **Backend errors/API calls failing:**
    *   Check Render service logs for Python tracebacks (e.g., `AttributeError: 'NoneType' object has no attribute 'get'`).
    *   Verify environment variables are set correctly on Render.
    *   Confirm data files (`.csv`) are accessible on Render.
    *   Check CORS origins in `backend/app.py` match the frontend's URL.
*   **Git issues:**
    *   Ensure correct branch is checked out.
    *   Check `git status` for untracked/uncommitted changes.
    *   Verify remote tracking branches are set up correctly (`git branch -vv`).
