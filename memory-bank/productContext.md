# RATM Draft Kit: Product Context - GO-FORWARD

> **File Type**: GO-FORWARD  
> **Review Priority**: Medium  
> **Last Updated**: September 19, 2025  
> **Purpose**: Product vision, features, and user experience specifications

## 1. Product Vision & Mission
The RATM Draft Kit aims to be the indispensable tool for fantasy football managers, transforming complex data and AI insights into actionable advice. Its mission is to empower users to make smarter draft-day and in-season decisions, ultimately leading to more successful fantasy football teams and an enhanced user experience.

## 2. Core Features & Functionality

The application provides a suite of tools categorized for player analysis and team management:

### Player Analysis Tools:
*   **Player Dossier:** Provides in-depth analysis for individual players, including their Expert Consensus Rankings (ECR), Standard Deviation (SD) in rankings, best/worst ranks, and AI-generated insights (depth chart role, value analysis, risk factors, outlook, and final verdict). Features player lookup with autocomplete.
    - Layout order (Sept 4, 2025): Quick Scan → Player Overview → Expert Consensus & Rankings → AI Analysis → Weekly Outlook → Market Analysis → Age/Trajectory. Ordering is enforced via CSS flex `order` in `PlayerDossier.module.css` and will override JSX order.
*   **Rookie Rankings:** Offers ranked lists of rookies, sortable by position, with AI-generated analysis.
*   **Positional Tiers:** Groups players into tiers by position (e.g., QB, RB, WR, TE) based on ECR, providing a visual and analytical understanding of player value within their position.
*   **Market Inefficiency Finder (Yahoo Enhanced):** ✅ Identifies potential "sleepers" and "busts" with two modes: (1) Traditional mode for general market analysis, and (2) Yahoo mode for authenticated users providing league-specific inefficiency analysis based on actual ownership patterns and league characteristics.
*   **Trending Players:** Displays players currently being added or dropped most frequently on Sleeper.app, providing real-time market sentiment.

### Team Management Tools:
*   **Keeper Evaluator:** Helps users assess the value of keeping players from previous seasons by comparing their ECR to their keeper cost (draft round equivalent).
*   **Trade Analyzer:** Evaluates proposed trades by analyzing the collective value of assets involved for both teams, providing an AI-driven verdict on fairness and winners.
*   **Trade Suggestions (Yahoo Enhanced) - PARTIAL:** ⚠️ Deterministic engine ✅ WORKING (1x1, 2x1, 1x2, 2x2 with lineup-aware scoring) and Gemini enhancement ✅ LIVE (reasons, negotiation pitch, confidence). Trade Center MVP renders proposals with filters and dossier links; remaining UX polish focuses on explaining horizon/acceptance sliders and translating parity/acceptance metrics into plain-English callouts.
*   **Draft Assistant:** Supports users during live drafts by providing real-time pick evaluations, suggesting optimal positions to target based on roster composition, and offering overall roster balance analysis.
*   **Target List:** Allows users to maintain a personalized list of players they want to target, enabling quick access to their data and analysis.
*   **Waiver Wire Assistant (Yahoo Enhanced):** ✅ Aids in making informed waiver wire claims with two modes: (1) Traditional mode for manual roster input, and (2) Yahoo mode for authenticated users showing actual league free agents and personalized AI recommendations based on real roster and available players.
    - Recommendations‑first UX with concise “Why” bullets by default; numbers on demand.
    - Source chip indicates whether a card is AI‑ranked or deterministic fallback.
    - Player names link to Player Dossier for deeper research.
*   **Sit/Start Optimizer (Yahoo):** ✅ Optimizes weekly lineup from deterministic projections with grounded AI notes.
    - Structured card shows: tags (Projection Edge, Favorable Matchup, etc.), numeric score chips (projection, matchup ±0.10), headline, and up to 3 typed reasons.
    - ECR semantics enforced: overall ECR used for cross‑position decisions; weekly positional rank only within same position; neutral “Overall ECR” context when gaps are small.
    - Matchup uses opponent + HOME/AWAY context; categorical difficulty (Easy/Moderate/Tough) adds a small numeric nudge when meaningful.
*   **Trade Suggestions (Yahoo‑Aware):** Proposed — Generates league‑aware trade packages prioritizing opponent bench assets, blending projections, VORP, and trade values with an acceptance heuristic and AI explanations. See `memory-bank/trade_suggestions_yahoo_aware_development_plan.md` (MVP live; additional UX/education work in progress).
*   **Market Inefficiency Finder (Yahoo Enhanced):** ✅ Identifies undervalued and overvalued players with two modes: (1) Traditional mode for general market analysis, and (2) Yahoo mode for league-specific analysis incorporating ownership patterns, league size, competitive level, and personalized player recommendations.
    - In‑season (Week 2+) behavior: Sleepers and Traps (Avoid) come strictly from the available FA/W pool; your roster is excluded via Yahoo auth. Cards show a headline and up to 3 concise reasons (Projection/Trend/Consensus/Waivers) for quick, human‑readable decisions.

### Utility Features:
*   **API Key Management:** Users provide their own Google Gemini API key, stored locally in their browser for privacy and security.
*   **Yahoo API Integration:** ✅ OAuth authentication with Yahoo Fantasy Sports for personalized league data, roster analysis, and waiver wire recommendations.
*   **Data Health (Settings):** ✅ Diagnostics card shows CSV freshness and enrichment coverage; supports an admin refresh action to rebuild data caches.
*   **Data Refresh:** Backend data (ECR, player values) is periodically refreshed to ensure up-to-date information.
*   **Theme Toggle:** Users can switch between dark and light themes.
*   **Application Reset:** Option to clear all local data (API key, saved lists, draft board).
*   **Documentation:** Provides information on how to use the application and its features.

## 3. User Experience & Interaction
*   **Season‑Aware Navigation:** The sidebar groups tools by Season Mode (In‑Season vs Pre‑Season) with a Show All toggle. A quick actions row exposes Player Dossier search, Sit/Start, and Waiver, plus a Yahoo status chip. Recent Dossier chips deep‑link to player dossiers.
*   **Player Search:** Global search and tool-specific autocomplete fields facilitate quick player lookups.
*   **Data Visualization:** ECR data, standard deviations, and other metrics are presented clearly to aid user understanding.
*   **AI Integration:** AI analysis is integrated directly into tool results, providing narrative insights alongside raw data.
*   **Configurability:** ECR Type toggle removed; the app defaults to overall ECR semantics and uses positional ranks only for within‑position comparisons.

## 4. Key Data & Insights
The application leverages various data points to generate its insights:
*   **Expert Consensus Rankings (ECR):** Provides a baseline for player value.
*   **Standard Deviation (SD):** Indicates the level of consensus among experts for a player's ranking.
*   **Best/Worst Ranks:** Shows the range of expert opinions.
*   **Rank Delta:** Tracks changes in a player's ranking over time.
*   **Sleeper.app Data:** Provides real-time player information (team, position, years experience) and trending data (adds/drops).
*   **Dynasty Values:** (Implied from backend files) Player and pick values for dynasty leagues.

## 5. Monetization/Business Model (if applicable)
(Currently, the application relies on users providing their own Gemini API keys, implying a free-to-use model for the application itself, with AI costs borne by the user. If there's a future monetization strategy, it would be outlined here.)
