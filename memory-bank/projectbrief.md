# RATM Draft Kit Project Brief

## 1. Project Overview
The RATM Draft Kit is a fantasy football draft assistant designed to provide AI-powered insights, comprehensive player analysis, and various tools to aid users in their draft decisions for the upcoming 2025 NFL season. It caters to fantasy football enthusiasts seeking data-driven advice.

## 2. Current Project Status
*   **Backend Deployment:** The Flask backend is deployed on Render.
*   **Frontend Deployment:** The React frontend is deployed on Vercel, specifically from the `oauth-dev` Git branch.
*   **Recent Fixes:**
    *   **CORS Issue Resolution:** The backend's Cross-Origin Resource Sharing (CORS) policy was updated to allow requests from both `http://localhost:3000` (local development) and `https://ratm-app-git-oauth-dev-joshua-smiths-projects-2dcfc522.vercel.app` (Vercel deployment URL). This resolved communication issues between the frontend and backend.
    *   **Backend Data Loading Fix:** The data loading and caching logic in `backend/app.py` was moved out of the `if __name__ == '__main__':` block to ensure it runs consistently upon application startup in production environments (e.g., when run with Gunicorn on Render). This fixed `AttributeError: 'NoneType' object has no attribute 'get'` errors and enabled proper data initialization for features like player autocomplete and dossier.

## 3. Technology Stack
*   **Frontend:** React, JavaScript, HTML, CSS, autoComplete.js, Showdown.js.
*   **Backend:** Flask, Python.
*   **Data Storage/Sources:**
    *   CSV files (`db_fpecr_latest.csv`, `values-players.csv`, `values-picks.csv`) for static data.
    *   Sleeper API (`https://api.sleeper.app/`) for player data and trending information.
*   **AI/ML:** Google Gemini API for player analysis and insights.
*   **Deployment Platforms:**
    *   Render (for Flask Backend)
    *   Vercel (for React Frontend)
*   **Key Python Dependencies:** Flask, Flask-Cors, python-dotenv, requests, pandas, google-generativeai, APScheduler, gunicorn.
*   **Key JavaScript/Node.js Dependencies:** react, react-dom, react-scripts, @tarekraafat/autocomplete.js, showdown.

## 4. Architecture Overview
*   **Client-Server Communication:** The Vercel-hosted React frontend communicates with the Render-hosted Flask backend via RESTful API calls.
*   **CORS Configuration:** Explicitly configured on the Flask backend to permit cross-origin requests from the Vercel frontend URL, ensuring secure and functional communication.
*   **API Key Handling:** The Google Gemini API key is *not* stored on the server side. Instead, the frontend prompts the end-user for their personal API key, which is then sent with each relevant API request via the `X-API-Key` header. This key is saved locally in the user's browser.
*   **Data Flow & Caching:**
    *   Initial player data, ECR data, and dynasty values are loaded into memory caches (`player_data_cache`, `static_ecr_overall_data`, etc.) when the Flask application starts.
    *   A `BackgroundScheduler` is used to periodically refresh this data (currently every 24 hours).
    *   The frontend fetches processed data and AI analyses from the backend API endpoints.

## 5. Key Files and Directories
*   `backend/app.py`: The main Flask application file. Contains API endpoints, core application logic, and the central data loading/initialization mechanism.
*   `backend/utils.py`: A collection of utility functions, including player name normalization, fuzzy matching, player context generation for AI prompts, and a wrapper for Gemini API requests.
*   `backend/data_importer.py`: (Assumed) Contains logic for importing and processing data from CSVs and external APIs into the application's caches.
*   `backend/requirements.txt`: Lists all Python dependencies with pinned versions required for the Flask backend.
*   `frontend/src/context/AppContext.js`: Provides global context for the React application, including the `API_BASE_URL` (pointing to the Render backend), user API key state, and other shared data/functions.
*   `frontend/src/hooks/useApi.js`: A custom React hook abstracting API request logic, handling loading states, errors, and consistently including the user's API key and ECR type preference in requests.
*   `frontend/src/components/`: Directory containing various React components implementing specific features of the Draft Kit (e.g., `PlayerDossier`, `RookieRankings`, `TradeAnalyzer`, `Sidebar`).

## 6. Development & Deployment Workflow
*   **Git Branching:** Development and deployment efforts are focused on the `oauth-dev` branch.
*   **Deployment Process:**
    *   **Backend (Render):** Changes pushed to `oauth-dev` trigger an automatic deployment on Render.
    *   **Frontend (Vercel):** Changes pushed to `oauth-dev` trigger an automatic deployment on Vercel, as the `oauth-dev` branch is configured as the production branch in Vercel settings.

## 7. Future Considerations / To-Dos
*   (Add any specific known issues, planned features, or refactoring ideas here)
