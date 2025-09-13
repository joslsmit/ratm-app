# Waiver Wire Recommendations v2 → v3 — Consolidated Go‑Forward Plan

> Status: In Progress (backend implemented; UI/Narrative next)
> Purpose: Recommend add/drop pairs that improve the entire roster (not just starters), using Yahoo data + DynastyProcess CSVs. Excludes K/DEF by default. Present a clear “Estimated Benefit” with rationale badges.

## 1) Objectives
- Optimize overall roster quality (starters + bench), not only the weekly lineup.
- Blend Yahoo truth (availability, eligibility) with DP data (weekly projections, ECR, bye, values) for robust, conservative scoring.
- Be transparent in the UI: concise explanation, component breakdown, rationale badges.

## 2) Current Status (Backend)
- Endpoints (Implemented):
  - GET `/api/yahoo/waiver_pool` — Aggregates A/FA/W with 25‑step paging; enriches with weekly projections and conservative ECR fallback; excludes K/DEF.
  - POST `/api/yahoo/waiver_recommendations_v2` — Whole‑roster scoring; returns top add/drop pairs with score breakdown and metadata.
  - POST `/api/yahoo/waiver_recommendations_ai` — AI‑authority endpoint. Uses deterministic engine to compute candidates + metadata, then prompts Gemini with full roster context (starters, bench, components) and a legend; returns `{ summary, moves, metadata }`. Supports `?debug=1` to return full prompt + diagnostics.
- Whole‑roster scoring (Implemented):
  - overall = lineup_week_points + α·bench_VOR + β·balance + γ·bye_coverage
  - α=0.7, β=0.3, γ=0.3 (conservative; tunable)
  - Bench VOR = Σ bench(max(0, effective_points − replacement_baseline(position)))
  - Balance: small penalty for imbalanced bench (targets QB≤1; RB≥2; WR≥2; TE≥1)
  - Bye Coverage: small bonus when bench covers starter byes
  - Cross‑position guard: penalty unless balance improves; plus penalties for surplus bench QBs and RB/WR shortages
  - Replacement baselines (calibrated for 6‑pt pass TD league): QB 12.0, RB/WR 7.5, TE 5.0
- Scoring data flow (Implemented):
  - Weekly‑first (fp_latest_weekly.csv r2p_pts)
  - ECR→points fallback curves when weekly missing (QB ~20→10; RB/WR ~15→6; TE ~10→4)
  - ID‑based enrichment: Yahoo `player_id` ↔ ECR `yahoo_id` join
- Candidate pool (Implemented):
  - Broad set with position quotas (e.g., QB 10, RB 40, WR 50, TE 20) to avoid QB crowding; fill remainder by effective score
  - Excludes K/DEF by default
  - AI breadth: up to top 15 deterministic candidates passed to AI for ranking/explanation
- Diagnostics (Implemented):
  - GET `/api/diagnostics/yahoo-data-health` — weekly row_count, latest scrape_date, anchor presence; coverage metrics
  - POST `/api/admin/refresh_data` — downloads DP CSVs and rebuilds caches
- Local scripts (Implemented):
  - `backend/backend/tests/test_csv_sources.sh` — refresh + CSV stats
  - `backend/backend/tests/test_waiver_v2_coverage.sh` — baseline + coverage
  - `backend/backend/tests/test_waiver_v2_unmatched.sh` — coverage + unmatched arrays
  - `backend/backend/tests/test_waiver_v2_endpoints.sh` — pool + rec summary

## 3) Inputs & Data Sources
- Yahoo API:
  - Roster: `team/{team_key}/roster/players?format=json` (fallback `roster`; supports `week`)
  - Available: `league/{league_key}/players;status={A|FA|W};start={n};count=25` + `?format=json`
- DynastyProcess CSVs (files/):
  - db_fpecr_latest.csv — ECR (bo/bp/drk), bye, team, yahoo_id
  - fp_latest_weekly.csv — weekly projections (r2p_pts), weekly ecr, opponent, ownership, scrape_date
  - values-players.csv — value_1qb/value_2qb, ecr_pos, age, draft_year
  - values-picks.csv — not used for weekly waivers

## 4) API Surface (Stable)
- GET `/api/yahoo/waiver_pool`
  - Query: `league_key` (req), `status` (A|FA|W; default A), `exclude_positions` (default K,DEF), `max`
  - Returns: `{ league_key, status_filter, total_count, available_players: [ { player_key, player_id, name, team, positions, primary_position, position, weekly_points, ecr_overall, bye_week, ... } ] }`
- POST `/api/yahoo/waiver_recommendations_v2`
  - Body: `{ league_key, team_key, week?, status='A'|'FA'|'W', top_n=10, exclude_positions=['K','DEF'] }`
  - Returns: `{ recommendations: [ { add_player, drop_player, estimated_benefit, score_breakdown, badges, claim_only } ], metadata }`
  - metadata includes: `baseline_points`, `baseline_bench_vor`, `baseline_balance`, `baseline_bye`, `baseline_overall`, coverage stats
  
- POST `/api/yahoo/waiver_recommendations_ai` (NEW)
  - Body: `{ league_key, team_key, week?, status, top_n, include_alternatives?, min_benefit?, exclude_positions? }`
  - Headers: `Authorization: Bearer <YahooToken>`, `X-API-Key: <GeminiKey>`
  - Returns: `{ summary, moves: [ { add, drop, confidence, estimated_benefit, rationale_bullets, badges } ], metadata, recommendations }`
  - Notes: `recommendations` is the deterministic fallback list (v2); UI renders `moves` when present.

## 5) Scoring (Whole‑Roster) — Details
- Lineup (weekly): optimize weekly points per slot
- Bench VOR: sum over bench of max(0, eff_points − replacement_baseline)
  - Replacement baselines (conservative; league‑size aware): QB ~10; RB/WR ~7.5; TE ~5.0
  - eff_points = weekly r2p_pts if present, else ECR→points conservative fallback
- Balance: small penalty for imbalanced bench (targets QB≤1, RB≥2, WR≥2, TE≥1)
- Bye Coverage: small bonus when bench covers starter byes (capped)
- Cross‑position guard: apply penalty unless balance improves; plus penalties for surplus bench QBs and RB/WR shortages
- Estimated Benefit = overall_after − baseline_overall

## 6) Matching & Fallbacks (Defensive)
- Name normalized key → Yahoo id join when name missing → (optional) guarded fuzzy (pos/team‑constrained, high threshold)
- Fallback ECR when overall ECR missing: use weekly ecr and positional ecr (values‑players ecr_pos) conservatively

## 7) UI/Display (Updated)
- Terminology: “Estimated Benefit” (replace “delta”)
- “Why” bullets default visible; “Show details” reveals numbers only when requested
- Breakdown for top N (in details): Lineup +X.X, Bench VOR +Y.Y, Balance/Bye modifiers
- Badges:
  - Depth (strengthens RB/WR/TE bench)
  - Bye Coverage (covers Week N starter bye)
  - Insurance (handcuff/next‑up depth)
  - Upside (rookie/trend)
  - Risk (injury/uncertainty)
- Alternatives mode (opt‑in): show best near‑neutral suggestions with badges when strict mode yields few ideas
 - Source chip per card: “AI” vs “Deterministic”
 - Dossier links: Add/Drop names deep‑link to Player Dossier (`/?tool=dossier&player=NAME`)
 - Browse Pool: loads on first open and when a single league is auto‑selected

## 8) Rollout
- Phase 1 (Done): Whole‑roster scoring, conservative fallback, ID join, QB crowding prevention, diagnostics
- Phase 2 (Done): Yahoo‑first frontend UX, “Why” bullets default, source chip, Dossier links, Browse Pool fix; AI‑authority endpoint; debug panel with full prompt
- Phase 3 (Next): Alternatives mode polish + badge/iconography refinements; optional dossier extras in AI prompt (ownership, value score, age category)

## 9) Success Criteria
- Roster weekly coverage ≥ 90% (excluding K/DEF)
- Effective pool coverage ≥ 70% of top 120 (weekly or fallback)
- Recommendations realistic and balanced (1–15 “Estimated Benefit” typical), avoid surplus QB picks when bench already has one

## 10) Notes & Risks
- Weekly file won’t include every FA; fallback keeps decisions conservative and comparable
- Balance/bye weights are modest by design; tune with real‑league observations
- ID joins remove most name issues; optional fuzzy only if needed

## 11) What’s Done vs. What’s Left
- Done:
  - Backend endpoints
  - Whole‑roster scoring, conservative fallback, ID join, cross‑pos & bench composition guards
  - Position‑quota candidate pooling; excludes K/DEF
  - Diagnostics: weekly freshness and coverage; refresh endpoint; test scripts
  - Frontend: Yahoo‑first Waiver UX; recommendations via AI endpoint when API key is present, else deterministic; inline badges; “Why” default; Dossier links; Browse Pool fixed
  - AI: `/api/yahoo/waiver_recommendations_ai` with full roster + bench context, component deltas, legend; up to 15 candidates
- Left:
  - Alternatives mode (opt‑in) UX polish
  - Optional dossier extras (ownership %, value_opportunity_score, age_category) in AI prompt

## 12) Recommended Next Steps
1) Implement Alternatives Mode (opt‑in)
   - API: add `include_alternatives=true` and `min_benefit` (e.g., −1.0) to include best near‑neutral suggestions with badges
   - Clearly mark as “Consider” with rationale (Depth/Bye/Insurance/Upside)
2) Add UI badge/iconography refinements
   - Include computed badges list per recommendation; switch wording to “Estimated Benefit”
3) Optional: Add dossier extras to AI prompt (ownership %, value score, age)
   - Summarize why top 3–5 moves make sense; include badges and component highlights
4) Frontend updates
   - Alternatives mode toggle polish; filter by min Estimated Benefit
   - Keep recommendations‑first view; pool remains secondary

## 14) Frontend UX (Yahoo‑First, No Extra Sidebar)
- Header (minimal): League selector (if needed), Refresh button, Show Alternatives toggle (off by default), Advanced (Status, Min Benefit) in collapse, Browse Pool in collapse
- Summary: Chips hidden by default; available under “Show Details” collapse (Baseline Overall, Lineup, Bench VOR, Balance, Bye, Pool coverage)
- Content: Top Recommendations (cards) with Add/Drop title, confidence badge, small benefit pill; badges (max 3) inline; per-card “Why?” expands to short bullets; “Show details” reveals metrics; Alternatives and Pool are collapsed by default
- Manual mode: Traditional roster input hidden by default; available via toggle when not using Yahoo
- Error UX: Clear token expiration messaging; local dev hint for HTTPS issues

## 15) AI Narrative & Prompting
- Mode: Lightweight narrative for top 3–5 moves. “Why” bullets surfaced by default; details on demand.
- Transport: Strict JSON via AI endpoint; frontend renders without requiring markdown.
- Schema (summary): `{ moves: [ { add, drop, confidence, estimated_benefit, rationale_bullets[], badges[] } ] }`
 - Prompt data includes: Baseline (overall, lineup, bench VOR, balance, bye), Legend (field meanings and baselines), Starters (slot + wp/ecr/sched), Bench (name + wp/ecr/sched), and up to 15 candidate moves with component deltas.
 - Hard guards: AI instructed to pick only from the listed candidates; each candidate carries `id=`; AI may return `candidate_id`. Backend strictly validates AI moves against roster and pool and falls back to deterministic candidates when necessary (no invented players, no adding rostered players, no dropping non‑rostered players).
- Prompt records: See `records/waiver_wire_v3_ai_prompts.md`.

## 13) Update Log (Key Milestones)
- 2025‑09‑01: Initial plan; endpoints draft; test scripts
- 2025‑09‑02: CSV importer refresh; `/api/admin/refresh_data`; coverage diagnostics
- 2025‑09‑03: Whole‑roster scoring (lineup + bench VOR + balance + bye), ID join, cross‑pos & bench composition guards; UI badge plan and wording captured
