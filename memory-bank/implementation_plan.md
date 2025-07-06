# RATM Draft Kit: Yahoo! API Feature Implementation Plan

This document provides a detailed, phased approach for implementing new features that leverage the Yahoo Fantasy Sports API. The plan includes core tasks, UX considerations, and validation steps for each phase.

**Note for the User:** This plan has been updated to reflect the specific requirements of the Yahoo Fantasy Sports API and to explicitly integrate with existing application patterns like player name normalization and context-based state management.

---

## **Pre-requisite: Centralized League Data Endpoint**

*   **Goal:** Create a single, reusable backend endpoint to fetch all of a user's fantasy football leagues. This is a foundational step for all other Yahoo-integrated features.

### **Backend Task: Create `/api/yahoo/leagues` Endpoint**

1.  **Create the Endpoint:** In `backend/app.py`, define a new Flask route: `GET /api/yahoo/leagues`.
2.  **Authentication:** This endpoint must be protected and require the user's Yahoo access token, passed in the `Authorization` header.
3.  **API Call:**
    *   Inside the endpoint, make a `GET` request to the Yahoo API to fetch the user's leagues.
    *   **URL:** `https://fantasysports.yahooapis.com/fantasy/v2/users;use_login=1/games;game_keys=nfl/leagues?format=json`
    *   Include the user's access token in the `Authorization: Bearer <token>` header of this request.
4.  **Data Parsing & Transformation:**
    *   **IMPORTANT:** The JSON response from Yahoo can be complex. You will need to carefully parse it.
    *   The goal is to extract a clean list of league objects. For each league, you must extract:
        *   `league_key`: A unique identifier for the league (e.g., `414.l.12345`).
        *   `league_name`: The human-readable name of the league.
        *   `team_key`: The unique identifier for the user's team *within that league* (e.g., `414.l.12345.t.1`).
    *   Return this transformed, clean list of league objects as the JSON response.
5.  **Error Handling:** If the API returns no leagues, or an error occurs, return an empty array `[]` to prevent frontend errors.
6.  **Validation:**
    *   Call your new `/api/yahoo/leagues` endpoint with a valid token.
    *   Verify you get a `200 OK` response.
    *   Confirm the response body is a JSON array. If leagues exist, each object should contain `league_key`, `league_name`, and `team_key`. If not, it should be an empty array.
    *   Ensure a `401 Unauthorized` error is returned if the token is missing or invalid.

---

## **Feature 1: Personalized Roster Analysis**

*   **Concept:** Display a user's Yahoo Fantasy Football roster with integrated AI analysis for each player.
*   **UX Vision:** A new "My Team" tab will appear in the sidebar. This view will feature a dropdown to select a league and will display a card for each player on their roster.

### **Phase 1.1: Backend - Roster Endpoint**

1.  **Create the Endpoint:** In `backend/app.py`, define a new Flask route: `GET /api/yahoo/roster`.
2.  **Authentication:** Protect the endpoint; require the Yahoo access token.
3.  **Parameters:** The endpoint should accept a `team_key` as a URL parameter (e.g., `/api/yahoo/roster?team_key=414.l.12345.t.1`).
4.  **API Call to Yahoo:**
    *   Make a `GET` request to the Yahoo API to fetch the roster for the given `team_key`.
    *   **URL:** `https://fantasysports.yahooapis.com/fantasy/v2/team/{team_key}/roster?format=json` (replace `{team_key}` with the parameter).
5.  **Parse and Enrich Data:**
    *   Parse the Yahoo response to get the list of players on the roster.
    *   For each player, extract key details like `player_key`, `full_name`, `position`, and `team_abbr`.
    *   **CRITICAL:** For each player, use the `normalize_player_name()` function from `utils.py` on the `full_name` received from Yahoo before passing it to your analysis function.
    *   For each normalized player, call the existing `get_player_analysis` logic from `utils.py` to add the app's ECR data and AI insights.
6.  **Final Response:** Return a JSON array of these "enriched" player objects. Each object should contain both the data from Yahoo and the analysis from your application.
7.  **Validation:**
    *   Call your `/api/yahoo/roster` endpoint with a valid `team_key`.
    *   Verify the response is `200 OK` and contains a list of players.
    *   Check that each player object contains the expected fields from both Yahoo (name, position) and your app's analysis (ECR, AI outlook). This confirms the name normalization and data enrichment is working.

### **Phase 1.2: Frontend - "My Team" View**

1.  **Create Component:** Create a new React component: `MyTeam.js`.
2.  **Add Route:** Add a new route for `/my-team` in `App.js`, rendering the `MyTeam.js` component.
3.  **Update Sidebar:** In `Sidebar.js`, add a "My Team" link that is only visible if a user is logged in with Yahoo (check for the token in `AppContext`).
4.  **Fetch Leagues:**
    *   In `MyTeam.js`, when the component mounts, get the auth token from `AppContext`.
    *   Using the `useApi` hook, call the `/api/yahoo/leagues` endpoint.
    *   Store the returned list of leagues in the component's state. If the list is empty, display a message like "No fantasy football leagues found for your Yahoo account."
5.  **League Selector Dropdown:**
    *   Create a dropdown menu. Populate it with the leagues from the state, showing the `league_name` to the user.
6.  **Fetch and Display Roster:**
    *   When the user selects a league from the dropdown:
        *   Find the corresponding `team_key` for that league from the data you stored in the state.
        *   Using the `useApi` hook, call your backend's `/api/yahoo/roster` endpoint, passing the selected `team_key`.
        *   Display a `LoadingSpinner` component while the data is being fetched.
        *   Once the data returns, map over the array of players and render each one using the existing `DraftCard.js` or a similar reusable component.
7.  **Validation:**
    *   Log in with Yahoo. Check that the "My Team" link appears.
    *   Go to the "My Team" page. The league dropdown should appear and be populated.
    *   Select a league. A loading spinner should show, followed by the player cards for your roster in that league.
    *   Switching leagues should correctly fetch and display the roster for the newly selected league.

---

## **Feature 2: AI-Powered Waiver Wire Assistant (Yahoo Integrated)**

*   **Concept:** Provide personalized waiver wire recommendations based on a user's league and roster.
*   **UX Vision:** The "Waiver Wire Assistant" will be enhanced with a league selector. It will show top free agents and allow the user to select a player from their roster to drop, triggering a personalized AI analysis.

### **Phase 2.1: Backend - Free Agent & Analysis Endpoint**

1.  **Create Endpoint:** In `backend/app.py`, define a new route: `GET /api/yahoo/waiver_wire`.
2.  **Authentication:** Protect the endpoint; require the Yahoo access token.
3.  **Parameters:** The endpoint should accept a `league_key` and the user's `team_key`.
4.  **API Calls to Yahoo:**
    *   **Call 1 (Free Agents):** Fetch the top available free agents.
        *   **URL:** `https://fantasysports.yahooapis.com/fantasy/v2/league/{league_key}/players;status=FA;sort=AR;count=25?format=json`
    *   **Call 2 (User's Roster):** Fetch the user's current roster.
        *   **URL:** `https://fantasysports.yahooapis.com/fantasy/v2/team/{team_key}/roster?format=json`.
5.  **Parse Data:** Parse the responses from both API calls to create a list of free agents and a list of the user's current players. Remember to normalize player names using `normalize_player_name()` for consistency.
6.  **Handle AI Analysis Request:**
    *   The endpoint should also accept optional `player_to_add` and `player_to_drop` parameters (these will be player names).
    *   If these parameters are present, construct a detailed, well-structured prompt for the Gemini API.
    *   **Prompt Structure:** The prompt must clearly present the context for the AI, for example: 1) List the user's complete current roster. 2) List the top available free agents. 3) State the proposed transaction: "Analyze the impact of dropping [player_to_drop] to add [player_to_add]."
7.  **Final Response:**
    *   If no `player_to_add/drop` is provided, return the list of free agents and the user's roster.
    *   If `player_to_add/drop` is provided, return the same data *plus* a new `ai_recommendation` field containing the text from the Gemini API.
8.  **Validation:**
    *   Call the endpoint with a `league_key` and `team_key`. Verify you get back lists of free agents and roster players.
    *   Call it again, including `player_to_add` and `player_to_drop`. Verify the response now contains the `ai_recommendation` field.

### **Phase 2.2: Frontend - Enhanced Waiver Wire UI**

1.  **Modify Component:** Update the `WaiverWireAssistant.js` component.
2.  **League Selection:**
    *   If the user is logged in (check `AppContext`), use the `/api/yahoo/leagues` data to show a league selector dropdown.
3.  **Initial Data Fetch:**
    *   On league selection, get the `league_key` and `team_key`.
    *   Call `/api/yahoo/waiver_wire` with these keys using the `useApi` hook.
    *   Store the returned free agents and user's roster in the component's state.
4.  **Display Data & Selections:**
    *   Display the list of free agents. Make each free agent selectable.
    *   Create a dropdown menu and populate it with the user's roster from the state. This will be the "player to drop" selector.
    *   Clearly display the currently selected `player_to_add` and `player_to_drop` in the UI so the user knows what they are about to analyze.
5.  **Trigger Analysis:**
    *   Create an "Analyze" button that becomes active only when both a player to add and a player to drop have been selected.
    *   When the button is clicked, re-call the `/api/yahoo/waiver_wire` endpoint, including the `player_to_add` and `player_to_drop` parameters.
6.  **Show Recommendation:**
    *   When the API returns a response containing the `ai_recommendation`, display it clearly to the user.
7.  **Validation:**
    *   Navigate to the tool. Select a league. The free agent list and "player to drop" dropdown should populate.
    *   Select a player to add and a player to drop. The UI should reflect your selections.
    *   Click the "Analyze" button. An AI-generated recommendation should appear.
