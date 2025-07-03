# RATM Draft Kit: Product Context

## 1. Product Vision & Mission
The RATM Draft Kit aims to be the indispensable tool for fantasy football managers, transforming complex data and AI insights into actionable advice. Its mission is to empower users to make smarter draft-day and in-season decisions, ultimately leading to more successful fantasy football teams and an enhanced user experience.

## 2. Core Features & Functionality

The application provides a suite of tools categorized for player analysis and team management:

### Player Analysis Tools:
*   **Player Dossier:** Provides in-depth analysis for individual players, including their Expert Consensus Rankings (ECR), Standard Deviation (SD) in rankings, best/worst ranks, and AI-generated insights (depth chart role, value analysis, risk factors, outlook, and final verdict). Features player lookup with autocomplete.
*   **Rookie Rankings:** Offers ranked lists of rookies, sortable by position, with AI-generated analysis.
*   **Positional Tiers:** Groups players into tiers by position (e.g., QB, RB, WR, TE) based on ECR, providing a visual and analytical understanding of player value within their position.
*   **Market Inefficiency Finder:** Identifies potential "sleepers" and "busts" by comparing player rankings and other data points, highlighting players whose perceived value might differ from their actual potential.
*   **Trending Players:** Displays players currently being added or dropped most frequently on Sleeper.app, providing real-time market sentiment.

### Team Management Tools:
*   **Keeper Evaluator:** Helps users assess the value of keeping players from previous seasons by comparing their ECR to their keeper cost (draft round equivalent).
*   **Trade Analyzer:** Evaluates proposed trades by analyzing the collective value of assets involved for both teams, providing an AI-driven verdict on fairness and winners.
*   **Draft Assistant:** Supports users during live drafts by providing real-time pick evaluations, suggesting optimal positions to target based on roster composition, and offering overall roster balance analysis.
*   **Target List:** Allows users to maintain a personalized list of players they want to target, enabling quick access to their data and analysis.
*   **Waiver Wire Assistant:** Aids in making informed waiver wire claims by analyzing potential adds and suggesting optimal drops from the current roster.

### Utility Features:
*   **API Key Management:** Users provide their own Google Gemini API key, stored locally in their browser for privacy and security.
*   **Data Refresh:** Backend data (ECR, player values) is periodically refreshed to ensure up-to-date information.
*   **Theme Toggle:** Users can switch between dark and light themes.
*   **Application Reset:** Option to clear all local data (API key, saved lists, draft board).
*   **Documentation:** Provides information on how to use the application and its features.

## 3. User Experience & Interaction
*   **Intuitive Navigation:** A sidebar allows easy switching between different tools.
*   **Player Search:** Global search and tool-specific autocomplete fields facilitate quick player lookups.
*   **Data Visualization:** ECR data, standard deviations, and other metrics are presented clearly to aid user understanding.
*   **AI Integration:** AI analysis is integrated directly into tool results, providing narrative insights alongside raw data.
*   **Configurability:** Users can adjust settings like ECR type preference (overall, positional, rookie) to tailor analysis to their needs.

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
