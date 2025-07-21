# RATM Draft Kit: Comprehensive Implementation Roadmap

This document provides the complete implementation roadmap for RATM Draft Kit, prioritizing AI enhancement as the foundation before expanding feature set.

**CRITICAL PRIORITY SHIFT:** AI Enhancement (Phase 0) now supersedes all other features as the core app functionality depends on reliable AI analysis.

**CURRENT STATUS:** Documentation phase complete - ready for implementation. Complete step-by-step guide available in `ai_implementation_complete_guide.md` with exact code changes and testing procedures.

**Note for AI Assistant:** AI enhancement must be completed before any new feature development. Follow the phased approach precisely.

---

## **PHASE 0: AI ENHANCEMENT (CRITICAL PRIORITY)**

### **Overview**
AI analysis quality is the core value proposition of RATM Draft Kit. Current AI integration has critical issues that undermine user experience and must be resolved before any feature expansion.

### **Critical Issues Identified**
1. **Truncated Core Prompts**: PROMPT_PREAMBLE and JSON_OUTPUT_INSTRUCTION are incomplete with "..."
2. **Poor Response Processing**: Complex regex parsing, file-based logging, inconsistent error handling
3. **No Prompt Engineering**: Missing examples, chain-of-thought, structured templates
4. **Performance Issues**: Slow processing, high error rates, unreliable responses

### **Phase 0A: Emergency Fixes (Week 1) - IMMEDIATE PRIORITY**

#### **Task 1: Reconstruct Core Prompts**
- **File**: `backend/app.py` lines 273-274
- **Action**: Replace truncated constants with complete, structured prompts
- **Details**: See `ai_implementation_complete_guide.md` for exact code and implementation steps

#### **Task 2: Implement Enhanced Response Processing**
- **File**: `backend/utils.py` 
- **Action**: Add `process_ai_response_v2()` alongside existing function
- **Features**: JSON schema validation, structured error handling, standardized confidence scoring
- **Details**: See `ai_implementation_complete_guide.md` for complete function code

#### **Task 3: Update All AI Endpoints**
- **Files**: 11 endpoints in `backend/app.py`
- **Action**: Standardize prompt construction and response processing
- **Endpoints**: player_dossier, rookie_rankings, keeper_evaluator, trade_analyzer, generate_tiers, find_market_inefficiencies, suggest_position, pick_evaluator, roster_composition_analysis, waiver_swap_analysis, waiver_wire_analysis
- **Template**: See `ai_implementation_complete_guide.md` for line-by-line changes

### **Phase 0B: Prompt Engineering Overhaul (Week 2-3)**

#### **Task 1: Create Modular Prompt System**
- **File**: `backend/prompt_templates.py` (new)
- **Features**: Reusable templates, structured task definitions, consistent formatting
- **Classes**: PromptBuilder, PromptTemplate, ExampleLibrary

#### **Task 2: Implement Few-Shot Prompting** 
- **Action**: Add high-quality examples for each analysis type
- **Benefits**: 40-60% improvement in response relevance and consistency
- **Examples**: Player analysis, trade evaluation, waiver recommendations

#### **Task 3: Add Chain-of-Thought Reasoning**
- **Purpose**: Guide AI through structured reasoning process
- **Implementation**: Step-by-step analysis templates for complex decisions

### **Phase 0C: Advanced AI Features (Week 4-6)**

#### **Task 1: Dynamic Context Adjustment**
- **File**: `backend/context_formatters.py` (new)
- **Purpose**: Optimize data presentation based on analysis type
- **Features**: Relevance filtering, structured formatting, contextual comparisons

#### **Task 2: Response Validation Framework**
- **File**: `backend/response_schemas.py` (new)
- **Purpose**: Ensure consistent, high-quality AI responses
- **Features**: JSON schema validation, confidence calibration, error detection

#### **Task 3: Performance Optimization**
- **Metrics**: Sub-5 second response times, <2% error rate, 95%+ proper formatting
- **Monitoring**: Quality tracking, user feedback collection, A/B testing framework

### **Success Criteria for Phase 0**
- ✅ All truncated prompts reconstructed and functional
- ✅ Consistent JSON response format across all 11 endpoints
- ✅ Confidence scores calibrated and meaningful (High/Medium/Low scale)
- ✅ 40-60% improvement in response quality metrics
- ✅ Sub-5 second response times for 95% of requests
- ✅ Error rate below 2% across all AI endpoints

---

## **PHASE 1: YAHOO API INTEGRATION (Dependent on Phase 0 Completion)**

### **Prerequisites**
- ✅ **Phase 0 Complete**: AI enhancement must be finished before Yahoo features
- ✅ **Rationale**: All Yahoo features depend on reliable AI analysis for value proposition

## **Guiding Principle: Defensive JSON Parsing**

The Yahoo API's JSON is converted from XML and can be unpredictable. Keys may be missing, and a single item might be returned as an object while multiple items are a list of objects. All parsing logic **MUST** follow these defensive principles:

1.  **NEVER Use Direct Key Access:** Do not access dictionary keys like `data['key']`. This will raise an error if the key is missing.
2.  **ALWAYS Use `.get()` with Defaults:** Access keys using the `.get()` method and provide a default value (e.g., an empty dictionary `{}` or list `[]`). This prevents errors. 
    *   **Example:** `users = data.get('fantasy_content', {}).get('users', {})`
3.  **Wrap Logic in `try-except` Blocks:** Enclose the entire parsing function in a `try-except` block. If any unexpected error occurs, log the error and return a sensible default (e.g., `return []`).
4.  **Check Data Types:** Before iterating over a variable, check if it is a list. If it could be a single item or a list, handle both cases.
5.  **Log for Debugging:** In your `except` block, log the exception to help with debugging future issues.

--- 

## **Phase 1.0: Pre-requisite - Centralized League Data Endpoint** ✅ COMPLETED

*   **Status:** **COMPLETED** - This functionality is already implemented and operational
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

## **Phase 1.1: Personalized Roster Analysis** ✅ COMPLETED

*   **Status:** **COMPLETED** - Both backend and frontend implementation finished
*   **Concept:** Display a user's Yahoo roster with integrated AI analysis for each player.

### **Phase 1.1A: Backend - Roster Endpoint** ✅ COMPLETED

1.  **Modify File:** Open `backend/app.py`.
2.  **Define Route:** Create a new Flask route: `GET /api/yahoo/roster`.
3.  **Parameters:** The endpoint must accept a `team_key` as a URL query parameter.
4.  **API Call to Yahoo:**
    *   Make a `GET` request to: `https://fantasysports.yahooapis.com/fantasy/v2/team/{team_key}/roster?format=json`.
5.  **Parse and Enrich Data:**
    *   **CRITICAL:** Apply the **"Defensive JSON Parsing"** principles outlined above.
    *   **⚠️ FIELD CORRECTIONS:** Based on API research, actual field names are:
        *   `name.full` → `name` (simpler structure)
        *   `editorial_position` → `selected_position` 
        *   `editorial_team_abbr` → verify in implementation
    *   **Parsing Logic:** Navigate the response to find the list of players. For each player, safely extract `player_key`, `name`, `selected_position`, and verify other fields.
    *   **Enrichment Logic:** For each valid player found:
        1.  Call `normalize_player_name()` from `utils.py`.
        2.  Call `get_player_context()` from `utils.py` (NOT `get_player_analysis()` - that function doesn't exist).
        3.  Merge the analysis data into the player object.
    *   **⚠️ IMPLEMENTATION NOTE:** See `yahoo_roster_implementation.md` for complete, researched implementation details.
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

### **Phase 1.1B: Frontend - "My Team" View** ✅ COMPLETED

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

## **PHASE 1.2+: FUTURE YAHOO API FEATURES (🚨 BLOCKED - Dependent on Phase 0 Completion)**

**CRITICAL DEPENDENCY**: All future Yahoo API features are **BLOCKED** until Phase 0 (AI Enhancement) is completed. These features depend on reliable AI analysis to provide value to users.

### **Blocking Rationale**
- All Yahoo features integrate with AI analysis endpoints
- Current AI issues (truncated prompts, poor processing) would undermine these features
- User experience would be poor with unreliable AI recommendations
- Technical debt would compound if built on flawed AI foundation

---

## **Phase 1.2: AI-Powered Waiver Wire Assistant (Yahoo Integrated)** 🚨 BLOCKED

*   **Concept:** Provide personalized waiver wire recommendations.

### **Phase 1.2A: Backend - Free Agent & Analysis Endpoint**

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

### **Phase 1.2B: Frontend - Enhanced Waiver Wire UI**

1.  **Modify Component:** `frontend/src/components/WaiverWireAssistant.js`.
2.  **Logic:** Add league selection, fetch initial data, allow user to select a player to add and drop, trigger analysis, and display the recommendation.
