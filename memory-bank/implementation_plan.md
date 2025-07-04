# RATM Draft Kit: Yahoo! API Feature Implementation Plan

This document provides a detailed, phased approach for implementing five new features that leverage the Yahoo Fantasy Sports API. The plan includes core tasks, UX considerations, and validation steps for each phase.

---

## **Feature 1: Personalized Roster Analysis**

*   **Concept:** Display a user's Yahoo Fantasy Football roster with integrated AI analysis for each player.
*   **UX Vision:** A new "My Team" tab will appear in the sidebar after a user logs in with Yahoo. This view will feature a dropdown to select a league and will display a card for each player on their roster, reusing the familiar `DraftCard` or `PlayerDossier` styling.

### **Phase 1.1: Backend - Roster Endpoint**

*   **Tasks:**
    1.  Create a new Flask endpoint: `/api/yahoo/roster`.
    2.  This endpoint will require an `Authorization` header with the user's Yahoo access token.
    3.  It will also accept a `league_id` as a parameter.
    4.  The endpoint will call the Yahoo API to fetch the user's team and roster for the specified league.
    5.  For each player on the roster, it will reuse the existing `get_player_analysis` logic from `utils.py` to generate the ECR data and AI insights.
    6.  The final JSON response will be an array of player objects, each containing both the Yahoo roster data and the app's own analysis.
*   **Validation:**
    *   Use a tool like Postman or `curl` to call the `/api/yahoo/roster` endpoint with a valid access token and `league_id`.
    *   Verify that the response is a successful `200 OK`.
    *   Check that the returned JSON contains a list of players.
    *   Confirm that each player object in the response contains the expected fields from both Yahoo (name, position, team) and the app's analysis (ECR, AI outlook, etc.).
    *   Ensure the endpoint returns a `401 Unauthorized` error if the access token is missing or invalid.

### **Phase 1.2: Frontend - "My Team" View**

*   **Tasks:**
    1.  Create a new React component: `MyTeam.js`.
    2.  Add a new route for `/my-team` in `App.js`.
    3.  Update `Sidebar.js` to conditionally display a "My Team" link if the user is logged in with Yahoo (i.e., if a Yahoo access token is present in `localStorage`).
    4.  In `MyTeam.js`, add a dropdown menu that is populated with the user's leagues (fetched from the `/api/yahoo/leagues` endpoint).
    5.  When a user selects a league, call the new `/api/yahoo/roster` backend endpoint.
    6.  Display the returned player data using a modified version of the `DraftCard.js` component for each player.
*   **Validation:**
    *   Log in with Yahoo. Verify the "My Team" link appears in the sidebar.
    *   Navigate to the "My Team" page. The league dropdown should be populated.
    *   Select a league. The app should display a loading indicator while fetching data.
    *   Once loaded, the user's roster should be displayed as a series of player cards.
    *   Verify that each card correctly shows the player's name, position, and the ECR/AI analysis.
    *   Confirm that switching leagues in the dropdown correctly updates the displayed roster.

---

## **Feature 2: AI-Powered Waiver Wire Assistant (Yahoo Integrated)**

*   **Concept:** Provide personalized waiver wire recommendations based on a user's league and roster.
*   **UX Vision:** The existing "Waiver Wire Assistant" will be enhanced. When a user is logged in with Yahoo, it will show a league selector. The UI will present a list of top free agents and allow the user to select a player from their own roster to drop, triggering a personalized AI analysis.

### **Phase 2.1: Backend - Free Agent & Analysis Endpoint**

*   **Tasks:**
    1.  Create a new Flask endpoint: `/api/yahoo/waiver_wire`.
    2.  This endpoint will require an `Authorization` header and a `league_id` parameter.
    3.  It will call the Yahoo API to fetch the top available free agents in the league.
    4.  It will also need to fetch the user's current roster to know who they can drop.
    5.  The endpoint will accept an optional `player_to_drop` parameter. If this parameter is provided, the endpoint will construct a detailed prompt for the Gemini API, including the user's full roster, the player to drop, and the list of top free agents.
    6.  The AI will be asked to rank the free agents and provide a justification for the best pickup.
*   **Validation:**
    *   Call the `/api/yahoo/waiver_wire` endpoint with a valid access token and `league_id`.
    *   Verify the response contains a list of free agents.
    *   Call the endpoint again, this time including the `player_to_drop` parameter.
    *   Verify the response includes an `ai_recommendation` field with a textual analysis.
    *   Check the Flask server logs to inspect the prompt being sent to the Gemini API to ensure it's well-formed.

### **Phase 2.2: Frontend - Enhanced Waiver Wire UI**

*   **Tasks:**
    1.  Modify the `WaiverWireAssistant.js` component.
    2.  If the user is logged in with Yahoo, display the league selector dropdown.
    3.  On league selection, fetch the data from `/api/yahoo/waiver_wire`.
    4.  Display the list of top free agents.
    5.  Add a second dropdown that is populated with the user's current roster, allowing them to select a player to drop.
    6.  When a player is selected from the "drop" dropdown, re-call the `/api/yahoo/waiver_wire` endpoint with the `player_to_drop` parameter.
    7.  Display the returned AI recommendation in a prominent position.
*   **Validation:**
    *   Navigate to the "Waiver Wire Assistant" tool.
    *   Select a league. The list of free agents should appear.
    *   The "player to drop" dropdown should be populated with the user's roster.
    *   Select a player to drop. An AI-generated recommendation should appear, suggesting who to pick up.

---

## **Feature 3: League-Aware Trade Analyzer**

*   **Concept:** Analyze trades within the context of the specific league and the rosters of the teams involved.
*   **UX Vision:** The "Trade Analyzer" will be updated to include dropdowns to select the league and the two teams involved in the trade. The player selection inputs will then be populated with the actual rosters of those teams.

### **Phase 3.1: Backend - Team Roster & Trade Analysis Endpoint**

*   **Tasks:**
    1.  Create a new Flask endpoint: `/api/yahoo/trade_analyzer`.
    2.  This endpoint will require an `Authorization` header and a `league_id` parameter.
    3.  It will also accept `team_1_id` and `team_2_id` as parameters.
    4.  The endpoint will fetch the rosters for both teams from the Yahoo API.
    5.  It will also accept two lists of player names: `team_1_players` and `team_2_players`.
    6.  The AI prompt will be constructed to include the full rosters of both teams and the players being traded. The AI will be asked to analyze the trade from both sides, considering team needs.
*   **Validation:**
    *   Call the `/api/yahoo/trade_analyzer` endpoint with valid parameters for a league and two teams.
    *   Verify the response includes the rosters for both teams.
    *   Call the endpoint again, this time including the `team_1_players` and `team_2_players` parameters.
    *   Verify the response includes a detailed `ai_analysis` of the trade.

### **Phase 3.2: Frontend - Enhanced Trade Analyzer UI**

*   **Tasks:**
    1.  Modify the `TradeAnalyzer.js` component.
    2.  Add dropdowns to select the league and the two teams involved. The team dropdown will be populated by calling the Yahoo API to get a list of all teams in the selected league.
    3.  Once the teams are selected, the player input fields will become dropdowns populated with the players from each team's roster.
    4.  When the "Analyze" button is clicked, call the `/api/yahoo/trade_analyzer` endpoint with all the required parameters.
    5.  Display the returned AI analysis.
*   **Validation:**
    *   Navigate to the "Trade Analyzer" tool.
    *   Select a league and two teams.
    *   The player selection dropdowns should be populated with the correct rosters.
    *   Select players for the trade and click "Analyze."
    *   The AI analysis should appear, discussing the trade in the context of the teams' rosters.

---

## **Feature 4: "Draft Grade" Generator**

*   **Concept:** Provide a comprehensive AI-powered analysis and letter grade of a user's completed draft.
*   **UX Vision:** A new "Draft Grade" tool will be added. After logging in with Yahoo and selecting a league, the user will get a detailed report card for their draft, including an overall grade, strengths, weaknesses, and best/riskiest picks.

### **Phase 4.1: Backend - Draft Results & Analysis Endpoint**

*   **Tasks:**
    1.  Create a new Flask endpoint: `/api/yahoo/draft_grade`.
    2.  This endpoint will require an `Authorization` header and a `league_id` parameter.
    3.  It will call the Yahoo API to fetch the full draft results for the specified league (which player was picked in which slot by which team).
    4.  It will also fetch the user's final roster.
    5.  A complex AI prompt will be constructed, providing the draft results, the user's roster, and the app's ECR data. The AI will be asked to generate a detailed analysis and an overall letter grade.
*   **Validation:**
    *   Call the `/api/yahoo/draft_grade` endpoint with a valid access token and `league_id`.
    *   Verify the response contains a field for `draft_grade` (e.g., "A-") and a detailed `ai_analysis`.
    *   Check the server logs to ensure the AI prompt is correctly formatted with all the necessary data.

### **Phase 4.2: Frontend - Draft Grade View**

*   **Tasks:**
    1.  Create a new React component: `DraftGrade.js`.
    2.  Add a new route and a new link in the `Sidebar.js` for this tool.
    3.  The component will have a league selector. On selection, it will call the `/api/yahoo/draft_grade` endpoint.
    4.  Display the returned grade and analysis in a clean, report-card-style format.
*   **Validation:**
    *   Navigate to the "Draft Grade" tool.
    *   Select a league. A loading indicator should appear.
    *   The final report card should be displayed with a clear letter grade and detailed analysis sections.

---

## **Feature 5: Personalized "Market Inefficiency" Finder**

*   **Concept:** Highlight players who are undervalued in a user's specific Yahoo league compared to the app's ECR and AI analysis.
*   **UX Vision:** The "Market Inefficiency Finder" will be enhanced with a league selector for logged-in users, showing a tailored list of potential draft-day bargains by comparing app ECR to the Yahoo league's pre-draft player rankings.

### **Phase 5.1: Backend - League Player Ranks Endpoint**

*   **Tasks:**
    1.  Create a new Flask endpoint: `/api/yahoo/market_inefficiency`.
    2.  This endpoint will require an `Authorization` header and a `league_id` parameter.
    3.  It will call the Yahoo API to fetch the pre-draft player rankings for the specified league. **(This is the biggest technical risk and needs to be verified with the Yahoo API documentation first).**
    4.  The endpoint will then compare these ranks with the app's internal ECR data.
    5.  It will return a list of players with the largest positive and negative rank differentials.
*   **Validation:**
    *   First, confirm that the Yahoo API can provide pre-draft player rankings for a given league.
    *   Call the `/api/yahoo/market_inefficiency` endpoint.
    *   Verify the response is a list of players, each with their app ECR, Yahoo rank, and the calculated differential.

### **Phase 5.2: Frontend - Enhanced Market Inefficiency UI**

*   **Tasks:**
    1.  Modify the `MarketInefficiencyFinder.js` component.
    2.  Add a league selector for logged-in users.
    3.  On league selection, call the `/api/yahoo/market_inefficiency` endpoint.
    4.  Display the results in a table, highlighting the players with the biggest rank differences.
*   **Validation:**
    *   Navigate to the "Market Inefficiency Finder" tool.
    *   Select a league.
    *   The table should populate with players, sorted by the rank differential, clearly showing which players are most under/overvalued in that specific league.
