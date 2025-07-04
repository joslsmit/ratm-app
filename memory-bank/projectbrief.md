# RATM Draft Kit Project Brief

## 1. Project Overview
The RATM Draft Kit is a fantasy football draft assistant designed to provide AI-powered insights, comprehensive player analysis, and various tools to aid users in their draft decisions for the upcoming 2025 NFL season. It caters to fantasy football enthusiasts seeking data-driven advice.

## 2. Current Project Status
*   **Backend Deployment:** The Flask backend is deployed on Render.
*   **Frontend Deployment:** The React frontend is deployed on Vercel.
*   **Yahoo API Integration:** The application is integrated with the Yahoo Fantasy Sports API for user authentication and basic league listing. Local development now uses `mkcert` for HTTPS.

## 3. Technology Stack
*   **Frontend:** React, JavaScript, HTML, CSS, autoComplete.js, Showdown.js.
*   **Backend:** Flask, Python.
*   **Data Storage/Sources:**
    *   CSV files (`db_fpecr_latest.csv`, `values-players.csv`, `values-picks.csv`) for static data.
    *   Sleeper API (`https://api.sleeper.app/`) for player data and trending information.
    *   Yahoo Fantasy Sports API for user-specific league, roster, and player data.
*   **AI/ML:** Google Gemini API for player analysis and insights.
*   **Deployment Platforms:**
    *   Render (for Flask Backend)
    *   Vercel (for React Frontend)

## 4. Architecture Overview
*   **Client-Server Communication:** The Vercel-hosted React frontend communicates with the Render-hosted Flask backend via RESTful API calls.
*   **API Key Handling:** The Google Gemini API key is *not* stored on the server side. The frontend prompts the end-user for their personal API key, which is then sent with each relevant API request.
*   **Data Flow & Caching:**
    *   Initial player data and ECR data are loaded into memory caches when the Flask application starts.
    *   A `BackgroundScheduler` periodically refreshes this data.
    *   User-specific data is fetched on-demand from the Yahoo API, authorized via OAuth2.

## 5. Key Files and Directories
*   `backend/app.py`: The main Flask application file.
*   `backend/utils.py`: Utility functions, including AI prompt generation.
*   `frontend/src/context/AppContext.js`: Global context for the React application.
*   `frontend/src/hooks/useApi.js`: Custom React hook for API requests.
*   `frontend/src/components/`: Directory containing all React components.

## 6. Development & Deployment Workflow
*   **Git Branching:** Development is focused on the `oauth-dev` branch.
*   **Deployment Process:** Changes pushed to `oauth-dev` trigger automatic deployments on Render and Vercel.

## 7. Future Features (Roadmap)

The following features are planned for development, leveraging the new Yahoo API integration:

*   **Personalized Roster Analysis:** A new "My Team" view will display a user's Yahoo roster with integrated AI analysis for each player.
*   **AI-Powered Waiver Wire Assistant:** The existing tool will be enhanced to provide personalized waiver wire recommendations based on a user's specific league and roster needs.
*   **League-Aware Trade Analyzer:** The trade analyzer will be upgraded to analyze trades within the context of the two teams' actual rosters, pulled from Yahoo.
*   **"Draft Grade" Generator:** A new tool to provide a comprehensive AI-powered analysis and letter grade of a user's completed draft.
*   **Personalized "Market Inefficiency" Finder:** This tool will be enhanced to highlight players who are undervalued in a user's specific Yahoo league compared to the app's ECR and AI analysis.
