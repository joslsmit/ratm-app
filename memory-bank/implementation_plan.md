# RATM Draft Kit: Granular Implementation Plan for Yahoo! API

This document provides a highly detailed, step-by-step guide for implementing Yahoo Fantasy Sports API features. It is designed to be executed by an AI assistant, minimizing ambiguity and the need for inference.

**Note for AI Assistant:** Follow these instructions precisely. Do not deviate from the specified file names, function calls, or data structures.

---

## **Guiding Principle: Defensive JSON Parsing**

The Yahoo API's JSON is converted from XML and can be unpredictable. Keys may be missing, and a single item might be returned as an object while multiple items are a list of objects. All parsing logic **MUST** follow these defensive principles:

1.  **NEVER Use Direct Key Access:** Do not access dictionary keys like `data['key']`. This will raise an error if the key is missing.
2.  **ALWAYS Use `.get()` with Defaults:** Access keys using the `.get()` method and provide a default value (e.g., an empty dictionary `{}` or list `[]`). This prevents errors. 
    *   **Example:** `users = data.get('fantasy_content', {}).get('users', {})`
3.  **Wrap Logic in `try-except` Blocks:** Enclose the entire parsing function in a `try-except` block. If any unexpected error occurs, log the error and return a sensible default (e.g., `return []`).
4.  **Check Data Types:** Before iterating over a variable, check if it is a list. If it could be a single item or a list, handle both cases.
5.  **Log for Debugging:** In your `except` block, log the exception to help with debugging future issues.

--- 

## **Pre-requisite: Centralized League Data Endpoint**

*   **Goal:** Create a single, reusable backend endpoint to fetch all of a user's fantasy football leagues.

### **Backend Task: Create `/api/yahoo/leagues` Endpoint**

1.  **Modify File:** Open `backend/app.py`.
2.  **Define Route:** Create a new Flask route: `GET /api/yahoo/leagues`.
3.  **Authentication:** Protect the endpoint, requiring a Yahoo access token from the `Authorization: Bearer <token>` header.
4.  **API Call to Yahoo:**
    *   Make a `GET` request to: `https://fantasysports.yahooapis.com/fantasy/v2/users;use_login=1/games;game_keys=nfl/leagues?format=json`
5.  **Data Parsing & Transformation:**
    *   **CRITICAL:** Apply the **"Defensive JSON Parsing"** principles outlined above.
    *   **Parsing Logic:** The goal is to navigate the complex JSON to find the list of leagues. The path will be deeply nested.
        *   Start from the top level and safely traverse down using `.get()`.
        *   The leagues list is often found under a path similar to `data.get('fantasy_content', {}).get('users', {}).get('0', {}).get('user', [{}])[1].get('games', {}).get('0', {}).get('game', [{}])[1].get('leagues', {})`
        *   Iterate through the leagues. For each `league` object, you must safely extract:
            *   `league_key`
            *   `name`
            *   `team_key` (often found within a nested `teams` array)
    *   **Output Data Structure (Your API's Response):** The final response body **MUST** be a clean JSON array of objects. If parsing fails or no leagues are found, it **MUST** be an empty array `[]`.
        ```json
        [
          {
            "league_key": "414.l.12345",
            "league_name": "My Awesome League",
            "team_key": "414.l.12345.t.1"
          }
        ]
        ```
6.  **Validation:**
    *   Call your endpoint. Verify it returns a `200 OK` with a valid JSON array, even if the upstream Yahoo call fails or returns unexpected data.

---

## **Feature 1: Personalized Roster Analysis**

*   **Concept:** Display a user's Yahoo roster with integrated AI analysis for each player.

### **Phase 1.1: Backend - Roster Endpoint**

1.  **Modify File:** Open `backend/app.py`.
2.  **Define Route:** Create a new Flask route: `GET /api/yahoo/roster`.
3.  **Parameters:** The endpoint must accept a `team_key` as a URL query parameter.
4.  **API Call to Yahoo:**
    *   Make a `GET` request to: `https://fantasysports.yahooapis.com/fantasy/v2/team/{team_key}/roster?format=json`.
5.  **Parse and Enrich Data:**
    *   **CRITICAL:** Apply the **"Defensive JSON Parsing"** principles outlined above.
    *   **Parsing Logic:** Navigate the response to find the list of players. For each player, safely extract `player_key`, `name.full`, `editorial_position`, and `editorial_team_abbr`.
    *   **Enrichment Logic:** For each valid player found:
        1.  Call `normalize_player_name()` from `utils.py`.
        2.  Call `get_player_analysis()` from `utils.py`.
        3.  Merge the analysis data into the player object.
    *   **Output Data Structure:** The final response **MUST** be a JSON array of enriched player objects. Return `[]` on failure.
        ```json
        [
          {
            "player_key": "31000",
            "full_name": "Patrick Mahomes",
            /* ... other fields ... */
          }
        ]
        ```

### **Phase 1.2: Frontend - "My Team" View**

1.  **Create Component:** `frontend/src/components/MyTeam.js`.
2.  **Add Route:** In `frontend/src/App.js`, add a route for `/my-team`.
3.  **Update Sidebar:** In `frontend/src/components/Sidebar.js`, add a conditional "My Team" link.
4.  **Component Logic (`MyTeam.js`):**
    *   Fetch leagues from `/api/yahoo/leagues`.
    *   Display a `<select>` dropdown with the leagues.
    *   On selection, fetch the roster from `/api/yahoo/roster`.
    *   Display a loading spinner during fetches.
    *   Render the roster using the `<DraftCard />` component.

---

## **Feature 2: AI-Powered Waiver Wire Assistant (Yahoo Integrated)**

*   **Concept:** Provide personalized waiver wire recommendations.

### **Phase 2.1: Backend - Free Agent & Analysis Endpoint**

1.  **Modify File:** Open `backend/app.py`.
2.  **Define Route:** Create `GET /api/yahoo/waiver_wire`.
3.  **Parameters:** `league_key`, `team_key`, and optional `player_to_add`, `player_to_drop`.
4.  **API Calls to Yahoo:**
    *   Free Agents: `.../league/{league_key}/players;status=FA;...`
    *   User's Roster: `.../team/{team_key}/roster...`
5.  **Parse Data:** Apply **"Defensive JSON Parsing"** to both responses.
6.  **AI Analysis Logic:**
    *   If `player_to_add` and `player_to_drop` are present, construct the specific, templated prompt for the Gemini API as defined previously.
7.  **Final Response Structure:**
    *   Return a JSON object: `{ "free_agents": [], "user_roster": [], "ai_recommendation": "..." }`. The `ai_recommendation` key is optional.

### **Phase 2.2: Frontend - Enhanced Waiver Wire UI**

1.  **Modify Component:** `frontend/src/components/WaiverWireAssistant.js`.
2.  **Logic:** Add league selection, fetch initial data, allow user to select a player to add and drop, trigger analysis, and display the recommendation.
