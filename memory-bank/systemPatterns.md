# RATM Draft Kit: System Patterns

This document outlines the key architectural patterns, design patterns, and coding conventions employed within the RATM Draft Kit project. Understanding these patterns is crucial for consistent development, maintenance, and debugging.

## 1. Architectural Patterns

### A. Client-Server Architecture (Frontend-Backend Separation)
*   **Description:** The project adheres to a strict client-server architecture, with the React application serving as the frontend client and the Flask application as the backend server.
*   **Communication:** All interactions between the frontend and backend occur via RESTful API calls over HTTP(S). Local development uses `mkcert` for trusted HTTPS connections to `localhost`.
*   **Benefits:** Clear separation of concerns, scalability (frontend and backend can be scaled independently), easier maintenance, and ability to use different technologies for each layer.
*   **Implementation:**
    *   Frontend (React): Uses `fetch` API calls, encapsulated within a custom `useApi` hook.
    *   Backend (Flask): Defines API endpoints using `@app.route` decorators, handling requests and returning JSON responses.

### B. API-Driven Development
*   **Description:** The backend exposes a well-defined set of API endpoints that the frontend consumes. The frontend is built entirely around these APIs, making it a "thin client."
*   **Benefits:** Promotes modularity, simplifies integration with other potential clients (e.g., mobile apps), and enforces a contract between frontend and backend development.

## 2. Design Patterns

### A. Centralized State Management (React - AppContext)
*   **Description:** For global application state (like the API base URL, user API key, active tool, and shared data caches), React's Context API is used. The `AppContext.js` file serves as a central store for this shared state.
*   **Benefits:** Avoids "prop drilling" (passing props through many nested components), makes global state easily accessible where needed, and simplifies state management for widely used data.
*   **Implementation:** `AppContext.Provider` wraps the main application components, and `useContext(AppContext)` is used by consumer components.

### B. Custom Hooks (React - `useApi`)
*   **Description:** Common logic for making API requests (handling loading states, errors, and including the user's API key) is encapsulated in a custom React Hook (`useApi.js`).
*   **Benefits:** Promotes code reusability, simplifies component logic, and ensures consistent API interaction patterns across the frontend.

### C. Data Caching (Flask Backend)
*   **Description:** Frequently accessed static data (player information, ECR, values) is loaded into in-memory global caches upon application startup. A background scheduler periodically refreshes this data.
*   **Benefits:** Reduces the need for repeated file reads or external API calls, significantly improving response times for data-intensive operations.
*   **Implementation:** Global variables (e.g., `player_data_cache`, `static_ecr_overall_data`) store data, and `APScheduler` manages refresh intervals.

### D. AI Model Integration (Gemini API Wrapper)
*   **Description:** Interactions with the Google Gemini API are abstracted into a dedicated function (`make_gemini_request` in `utils.py`). This function handles API key configuration and the actual content generation request.
*   **Benefits:** Centralizes AI interaction logic, makes it easier to swap out AI models or providers in the future, and separates AI-specific logic from core application business logic.

## 3. Coding Conventions & Practices

### A. Python (`backend/`)
*   **Environment Variables:** Sensitive information (like `FLASK_SECRET_KEY`) is loaded from environment variables using `os.getenv()`.
*   **Error Handling:** `try-except` blocks are used for robust error handling in API endpoints and data loading functions. **For production, replace `traceback.print_exc()` with generic error messages for users, and log detailed errors server-side.**
*   **Logging:** Basic logging is implemented to track application events and AI responses.
*   **Data Normalization:** Player names are normalized (`normalize_player_name` in `utils.py`) for consistent matching across different data sources.

### B. JavaScript/React (`frontend/`)
*   **Functional Components & Hooks:** Primarily uses React functional components and hooks for state and lifecycle management.
*   **State Management:** `useState` for local component state, `useCallback` and `useMemo` for performance optimization of functions and memoized values.
*   **External Libraries:** Integration of libraries like `autoComplete.js` and `showdown.js` for specific UI/data presentation needs.
*   **CSS Modules:** (Implied by some file names like `LoadingSpinner.module.css`) Likely uses CSS Modules for scoping component-specific styles to prevent global style collisions.

## 4. Deployment Patterns
*   **Continuous Deployment:** Changes pushed to the `oauth-dev` branch automatically trigger deployments on both Render (backend) and Vercel (frontend).
*   **Separated Deployments:** Frontend and backend are deployed independently to specialized platforms, allowing each to leverage platform-specific optimizations (e.g., Vercel's CDN for static assets, Render's Python environment).
*   **CORS Configuration for Production:** Explicitly whitelisting frontend origins on the backend to enable cross-origin communication in a secure manner.
