# Waiver Wire Recommendations v2 — GO-FORWARD

> Status: Planning (PRIORITY)
> Purpose: Deliver roster- and slot-aware waiver recommendations using Yahoo data + daily CSV enrichment, excluding K/DEF, with clear add/drop suggestions.

## Objectives
- Use your actual Yahoo roster + a large, paginated set of available players (FA + W) to compute upgrade opportunities.
- Be position-aware and roster-slot-aware (including FLEX slots like W/R/T and W/T).
- Exclude K/DEF from candidate pool and from comparisons unless explicitly requested.
- Blend Yahoo truth (availability, eligibility, ownership) with CSV enrichment (ECR, bye, weekly projections) to rank recommendations.
- Provide AI-backed narrative that explains the top recommendations and tradeoffs concisely.

## Inputs & Data Sources
- Yahoo API (already implemented and validated):
  - Roster: `team/{team_key}/roster/players?format=json` (fallback to `roster`); supports `week`.
  - Available players: `league/{league_key}/players;status={FA|W|A};start={n};count=25` with pagination.
- CSV Enrichment (daily refreshed):
  - `db_fpecr_latest.csv` — Overall/positional/rookie ECR and team/bye.
  - `fp_latest_weekly.csv` — Weekly projections, matchup, ownership, start/sit grade.
  - `values-players.csv` — Value overlays (used as tie-breakers).
- Local cache: `combined_player_data_cache` (normalized names, enriched fields).

## API Design
- GET `/api/yahoo/waiver_pool`
  - Params: `league_key` (req), `status` (default `A`), `exclude_positions=K,DEF` (default), `max=200` (cap aggregation).
  - Behavior: Paginate Yahoo in steps of 25 until `max` or exhaustion; enrich; filter positions; return full enriched pool (server-side sorted by ECR/weekly points).
- GET `/api/yahoo/roster` (existing)
  - Use `week` param when provided; include `selected_position` (lineup slot) and `eligible_positions`.
- POST `/api/yahoo/waiver_recommendations_v2`
  - Body: `{ league_key, team_key, week, status: 'A'|'FA'|'W', top_n: 10, exclude_positions: ['K','DEF'] }`
  - Response: `{ recommendations: [ { add_player, drop_player, score_breakdown, lineup_delta, notes } ], metadata }`
  - Notes: For `status='W'`, mark `claim_only: true` and handle timing priority messaging.

## Data Model (server response snippets)
- Pool player (enriched): `{ player_key, name, team, positions: ["WR"], primary_position, ecr, sd, best, worst, rank_delta, bye_week, weekly_points, weekly_ecr, ownership, is_rookie, injury_status }`
- Roster player: `{ player_key, name, team, selected_position (slot), eligible_positions, position (from CSV), bye_week, weekly_points }`
- Recommendation: `{ add: {...}, drop: {...}, delta_points, delta_ecr, slot_impact: { before: lineup[], after: lineup[] }, rationale: [...], claim_only }`

## Core Algorithm (Deterministic + Scoring)
1) Fetch & preprocess
   - Roster: split into starters (based on `selected_position` non-BN/IR) vs bench; map each slot; normalize positions to standard set (QB, RB, WR, TE; ignore K/DEF).
   - Pool: aggregate up to ~200 players (A or FA+W), filter out K/DEF, dedupe, enrich from CSV. Keep players with at least one of: weekly_points, ecr.
2) Eligibility & slot mapping
   - Maintain a slot schema for your league (e.g., QB, RB, WR, TE, W/R/T, W/T, BN).
   - Function `can_fill(slot, player_position, eligible_positions)` returns True if player can be placed there (reuse existing `is_valid_player_for_position` and extend for flex slots).
3) Lineup optimizer (fast heuristic)
   - Build best starting lineup for the given week by choosing one eligible player per slot maximizing `weekly_points` (fallback to `ecr`-derived proxy when missing).
   - Save `baseline_points` and `baseline_lineup`.
4) Candidate evaluation loop
   - For each candidate in pool:
     - Find valid drop candidates from your current roster (exclude K/DEF; prefer bench; if none, allow the weakest starter of the same position group).
     - For each candidate→drop pair: recompute best lineup points with candidate added and drop removed; take the best delta.
     - Score = `delta_points` (primary) + tie-breakers: `+ w1 * (baseline_pos_need_improvement)` + `+ w2 * (ecr_delta)` + `+ w3 * (bye_week_coverage_gain)` − penalties for `injury_status`, `low_snap_share`.
   - Keep top `N` add/drop pairs with highest scores.
5) W vs FA handling
   - If `status='W'` or the individual player is in W, set `claim_only: true` and annotate timing/priority.
6) Exclusions & guards
   - Skip candidates with missing name or missing position eligibility; skip ambiguous players; always exclude K/DEF.

## Scoring Details
- Primary metric: `delta_points = optimized_points_after - baseline_points` using weekly projections.
- If weekly projections missing, estimate proxy points from ECR tier (e.g., map ECR rank to expected points by position curve).
- Tie-breakers (weights tuned empirically):
  - Positional need factor: if your starter at that position is weak or injured, boost.
  - ECR delta: `(roster_replacement_ecr - candidate_ecr)`.
  - Bye alignment: prefer candidates that improve bye coverage in congested weeks.
  - Risk: subtract for `injury_status` flagged, very high `sd` in ECR ranges, or low ownership confidence.

## AI Recommendation Layer
 - Input context:
  - Your roster summary by slot, bench depth, bye map, injuries (if known), and positional needs.
  - Top K candidate add/drop pairs with numeric deltas and reasoning features (need, bye, schedule, risk).
- Output:
  - 3–5 prioritized recommendations: “Add X (WR, LAC) over Y (WR, NO). +2.3 expected points this week; improves WR2/FLEX depth; bye week 12 coverage; moderate risk.”
  - Notes for W players: “Claim only; monitor claim priority and timing.”
- Safety: Response must be JSON (“confidence”, “analysis” markdown), consistent with existing AI response formatters.

### AI Prompting Integration (leveraging existing AI docs)
- Source docs in memory-bank/records to incorporate:
  - `ai_prompt_engineering_guide.md` — structure prompts with sections, constraints, and clarity for add/drop rationale.
  - `ai_response_processing_redesign.md` — enforce strict JSON format and robust parsing with fallbacks.
  - `ai_enhancement_masterplan.md` & `ai_implementation_complete_guide.md` — guidance on temperature, few-shot selection, safety, and retries.
  - `ai_testing_procedures.md` — test prompts against fixtures and edge cases.
- Integration steps:
  - Reuse backend modules: `PromptBuilder`, `ExampleLibrary`, `ChainOfThought`, and existing `JSON_OUTPUT_INSTRUCTION` pattern.
  - Add a new Waiver v2 prompt builder that injects: slot-aware baseline vs delta, candidate/drop features, bye/risk notes, and league context.
  - Include 2–3 few-shot examples of high-quality waiver recommendations (tailored to JSON schema and rationale style).
  - Enforce JSON contract and implement retry-on-parse-fail with minimal temperature bump.
  - Add unit tests per `ai_testing_procedures` using saved fixture inputs (pool + roster) to validate JSON structure and content sanity.

## Frontend UX (Waiver Page)
- Inputs: Yahoo auth + league/team selection, week selector.
- Sections:
  - “Top Recommendations” list with add/drop pair, delta points, badges (Need/Bye/Risk), claim-only tag.
  - “Alternatives” tab with sortable table (ECR, projections, team, position, bye).
  - Filters: FA only, exclude rookies, min projection threshold.
- Exclude K/DEF by default; allow optional toggle to include.

## Implementation Phases
1) Backend foundation
   - New endpoint `/api/yahoo/waiver_pool` (pool aggregation, enrichment, exclusions, pagination=25 steps).
   - New endpoint `/api/yahoo/waiver_recommendations_v2` (or repurpose existing `/api/yahoo_waiver_analysis`) implementing optimizer + scoring.
   - Reuse `is_valid_player_for_position`, add helper for slot schema + flex rules.
2) Scoring + optimizer
   - Build fast lineup optimizer (deterministic greedy within constraints) using weekly projections; ECR proxy fallback.
   - Implement add/drop candidate loop; compute deltas; cap evaluations (e.g., top 120 candidates by projection/ECR).
3) AI narrative
   - Build concise prompt using computed data; produce 3–5 JSON recommendations with reasoning; integrate with existing AI wrappers.
   - Apply `ai_prompt_engineering_guide` patterns (sections, constraints, clarity), use `ExampleLibrary` few-shots, and `ai_response_processing_redesign` for parsing.
4) Frontend
   - Render recommendations list; add controls for week/status filters; graceful error/empty states.
5) Quality gates
   - Diagnostics: extend data-health to report match rates for pool and the share with usable projections.
   - Tests: fixture-based parsing for pool + sanity checks for optimizer (before/after delta positive when it should be).

## Defensive Coding & Dev Scripts
- Defensive patterns:
  - Yahoo JSON variants: handle players container as dict or list; scan nested arrays for `player_key`, `name.full`, `eligible_positions`, `editorial_team_abbr`.
  - Pagination: always iterate in 25-item steps until exhaustion or cap; stop on short page.
  - Input validation: require `league_key`, `team_key` where appropriate; validate `status` in {A, FA, W}.
  - Exclusions: filter K/DEF early; never propose K/DEF in recommendations.
  - Fallbacks: use ECR-derived proxy when weekly projections missing; default safe values; graceful JSON parse errors with retries for AI.
  - Rate/timeout handling: timeouts with retries/backoff; informative error JSON to frontend.
  - Name normalization: centralize normalization + alias map; log unmatched names for iterative improvement.
- Phase test scripts (zsh; copy-paste friendly):
  - Phase 1 (pool + roster smoke):
    - `leagues`: `curl -sk -H "Authorization: Bearer $TOKEN" "$BASE/api/yahoo/leagues" | jq '. | length'`
    - `roster`: `curl -sk -H "Authorization: Bearer $TOKEN" "$BASE/api/yahoo/roster?team_key=$TEAM_KEY" | jq 'length'`
    - `pool A paged`: loop waiver_debug for A/FA/W at start=0/50, print counts (script provided in diagnostics doc).
  - Phase 2 (waiver_wire totals):
    - `curl .../waiver_wire?league_key=$LEAGUE_KEY&status=A | jq -r '"available_players=\(.available_players|length) total_count=\(.total_count)'"`
  - Phase 3 (diagnostics):
    - `curl .../diagnostics/yahoo-data-health?league_key=$LEAGUE_KEY&team_key=$TEAM_KEY | jq '{roster:.roster.enrichment.match_rate, waiversA:.waivers_A_first2pages.enrichment.match_rate, csv:.csv_freshness}'`
  - Phase 3.1 (data refresh from DynastyProcess):
    - `bash backend/backend/tests/test_csv_sources.sh` (calls `/api/admin/refresh_data`, prints CSV sizes and modified times)
  - Phase 4 (recommendations v2):
    - `curl -sk -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"league_key":"'$LEAGUE_KEY'","team_key":"'$TEAM_KEY'","week":null,"status":"A","top_n":10}' "$BASE/api/yahoo/waiver_recommendations_v2" | jq '{count:(.recommendations|length), first:(.recommendations[0])}'`
  - Provide one-paste wrappers in docs for each phase (similar to the scripts we used today).

### Calibration & Coverage Targets
- Scoring fallback set to 0 when weekly projections are missing (prevents inflated deltas).
- Targets after enrichment improvements and alias mapping:
  - Roster projection coverage ≥ 90% (excluding K/DEF by default).
  - Pool projection coverage ≥ 70% for top 120 candidates (excluding K/DEF).
  - Typical weekly recommendation deltas in 1–15 range (position/context dependent).

## Testing Plan
- Backend:
  - Fixture tests for waiver pool aggregation (A/FA/W) with pagination and enrichment (no K/DEF).
  - Optimizer unit tests for slot/flex rules and delta computation.
- Integration:
  - End-to-end call with your `league_key`/`team_key`: confirm non-empty recommendations, stable JSON schema.
- Acceptance:
  - Recommendations reflect actual roster and highlight tangible weekly gains.

## Success Criteria
- Recommendations consistently cite adds and matching drops with expected weekly improvement.
- Excludes K/DEF by default; respects flex slots; never produces illegal lineups.
- Uses Yahoo availability + eligibility; leverages CSV projections/ECR to rank; diagnostics show >80% enrichment coverage in pool (excluding K/DEF).

## Notes & Risks
- Weekly projections coverage varies; ECR proxy fallback mitigates missing points.
- Name normalization affects enrichment; maintain alias map for recurring mismatches (especially rookies).
- W vs FA timings affect actionability; we’ll flag claim-only with clear messaging.

## Next Steps
- Implement `/api/yahoo/waiver_pool` and `/api/yahoo/waiver_recommendations_v2` (backend) — IN PROGRESS.
- Add alias mapping + diagnostics for unmatched names.
- Tune scoring weights after initial real-league validation.

## Update Log
- 2025-09-01: Added plan to memory-bank (active file).
- 2025-09-01: Implemented backend endpoints draft: `/api/yahoo/waiver_pool` (aggregation, enrichment, exclusions) and `/api/yahoo/waiver_recommendations_v2` (greedy optimizer + scoring). Added helper functions.
- 2025-09-01: Added test script `backend/backend/tests/test_waiver_v2_endpoints.sh` for quick manual validation.
- 2025-09-02: Fixed scoring fallback (0 if no weekly projections) for realistic deltas; added alias support and loading at startup/refresh; exposed coverage metrics and unmatched name lists in recommendations metadata.
- 2025-09-02: Added scripts: `test_waiver_v2_coverage.sh` (coverage + baseline) and `test_waiver_v2_unmatched.sh` (unmatched names) to speed iteration.
- 2025-09-02: Importer now downloads `fp_latest_weekly.csv` from DynastyProcess; added `/api/admin/refresh_data` and `test_csv_sources.sh` for on-demand refresh & inspection.
- 2025-09-03: Implemented whole‑roster scoring in backend: lineup points + bench VOR + balance + bye coverage; ID join enrichment; cross‑position penalties and bench composition guards (avoid surplus QBs, preserve RB/WR depth). Recommendations now realistic and balanced.

## UI & Display Notes (Badges + Clarity)
- Replace raw “delta” wording with clearer copy like “Estimated Benefit” (overall roster score gain).
- Show compact component breakdown for the top few recs:
  - Lineup: +X.X pts, Bench: +Y.Y VOR (vs replacement), Balance/Bye: small modifiers.
- Badges (icons/colors) for rationale:
  - Depth: strengthens [RB/WR/TE] bench
  - Bye Coverage: covers [position] in Week N
  - Insurance: handcuff/next‑up depth behind [starter]
  - Upside: rookie/positive trend
  - Risk: injury/uncertainty (SD/injury flag)
- Alternatives mode (opt‑in) when strict mode yields few ideas: present best neutral/near‑neutral suggestions with rationale badges.

## Current Status (Backend)
- Implemented:
  - Whole‑roster scoring with lineup + bench VOR + balance + bye coverage
  - Conservative ECR→points fallback (weekly-first)
  - Position quotas to prevent QB crowding; broad candidate pool otherwise
  - ID-based enrichment (Yahoo `player_id` ↔ ECR `yahoo_id`)
  - Weekly diagnostics (row_count, scrape_date, anchor presence)
- Next:
  - Alternatives mode (opt‑in) and UI badges wiring
  - AI narrative integration and frontend rendering per badges and breakdown

## Detailed Go-Forward Plan (Comprehensive)

Objectives
- Raise waiver pool “effective coverage” using weekly projections or conservative ECR fallbacks.
- Keep deltas realistic and maintain slot-/position-legal lineups.
- Ensure data freshness parity (local == prod) with clear diagnostics.
- Deliver concise, actionable recommendations with solid reasoning.

Current State
- Data refresh working: all four DynastyProcess CSVs fetched locally (ECR, weekly, values-players, values-picks).
- Roster coverage ≈ 92% (good). Pool coverage lower due to missing weekly projections for many deep FA/W players.
- Recommendations empty with conservative 0-scoring fallback for missing weekly.

Root Causes
- Weekly file doesn’t include every FA; many deep players lack r2p_pts.
- Scoring falls to 0 for missing weekly, avoiding inflated deltas but limiting candidate viability.

Plan: Scoring + Matching + Data Sourcing
- Scoring fallback (position-aware ECR→points)
  - Add small, conservative curves mapping season-long ECR to weekly points when r2p_pts is missing:
    - QB ≈ 20 → 10 (ECR 1 → 30+)
    - RB/WR ≈ 15 → 6
    - TE ≈ 10 → 4
  - Use position from combined cache + season-long ECR from db_fpecr_latest.csv.
  - Weekly projections remain primary; ECR fallback engages only when projection missing.
- Candidate selection bias
  - Prefer candidates with weekly projections; fill remainder with best ECR fallback candidates.
  - Exclude K/DEF by default.
- Robust matching without manual aliasing
  - Exact normalized name (primary), then Yahoo id join (ECR.yahoo_id vs Yahoo player_id) where present.
  - Guarded fuzzy fallback (high threshold; constrained by position and team) with in-memory caching.
  - Keep optional alias file only for rare edge cases.
- Data sourcing parity (local == prod)
  - Importer pulls all four CSVs from DynastyProcess (done), including fp_latest_weekly.csv.
  - Diagnostics expose CSV sizes, last-modified, weekly scrape_date, and row count.
  - Anchor checks (Hurts/McCaffrey/Chase/Kelce/Allen) to detect weekly gaps quickly.

Diagnostics & Scripts
- Recommendations metadata (already present): roster/pool coverage + unmatched name arrays.
- Refresh + inspect: `/api/admin/refresh_data` + `test_csv_sources.sh` (done).
- Coverage checks: `test_waiver_v2_coverage.sh` + `test_waiver_v2_unmatched.sh` (done).
- Weekly freshness (to add): extend `/api/diagnostics/yahoo-data-health` with row count, scrape_date, anchor checks.

AI Narrative (after coverage improves)
- PromptBuilder + few-shots to produce 3–5 recommendations including: add/drop, weekly delta (weekly or fallback), slot impact, bye/risk/need notes; claim-only flag for W.
- Strict JSON contract + retry on parse failure.

Rollout Phases
1) Scoring fallback + candidate bias
   - Implement ECR→points fallback; bias towards candidates with weekly projections.
   - Validate: effective pool coverage rises; non-empty recommendations; deltas ~1–15.
2) Matching robustness
   - Add id join + guarded fuzzy fallback; validate fewer unmatched names even without weekly entries.
3) Diagnostics enhancement
   - Weekly row count, scrape_date, anchor checks; clear red/green states.
4) AI narrative + frontend
   - Integrate prompt and render concise, justified add/drop recommendations.

Success Criteria
- Roster coverage ≥ 90% (excluding K/DEF).
- Effective pool coverage ≥ 70% for top 120 candidates (projections or ECR fallback).
- Recommendations not empty; deltas typically 1–15 points.

## Whole‑Roster Objective Update (Bench Value Included)

Revision
- Optimize for the entire roster, not only the weekly starting lineup. Bench upgrades matter for depth, bye coverage, insurance and upside.

Scoring Objective
- overall_score = lineup_week_points + α·bench_value + β·roster_balance + γ·bye_coverage + δ·insurance + ε·upside − risk
  - lineup_week_points: best weekly lineup (existing component).
  - bench_value: VOR for bench (conservative ROS ECR→points curves vs replacement baselines by position).
  - roster_balance: encourages healthy positional distribution on bench; penalizes lopsided benches.
  - bye_coverage: rewards bench covering upcoming starter byes.
  - insurance: small bonus for handcuff/next‑up proxy depth behind fragile starters.
  - upside/risk: rookie/positive trend vs high SD/injury status.
  - Initial weights: α=0.7, β=0.2, γ=0.2, δ=0.2, ε=0.1 (conservative; tune after observation).

Candidate Pool Breadth
- Do NOT restrict N candidates/M drops for performance; maintain position quotas to prevent QB crowding, then include broad sets ranked by effective score (weekly or ECR fallback). Exclude K/DEF by default.

Fallbacks
- Weekly projections remain primary. If missing, estimate from position‑aware ECR curves. Use weekly ECR and positional ECR as secondary sources when overall ECR missing.
- Matching: exact normalized name → Yahoo id join → guarded fuzzy (position/team constrained, high threshold) only if needed.

Recommendations Output
- Strict mode: return only positive overall_score deltas.
- Alternatives mode (opt‑in): if strict yields 0, return top K within a safe band (e.g., ≥ −1.0) with rationale badges (bye/insurance/depth/upside).

Diagnostics
- Continue reporting coverage/unmatched; add component breakdown in metadata (lineup points, bench VOR, balance/bye, etc.) and an explain block when 0 recs.

Phases
1) Implement bench VOR + overall_score; validate positive deltas for true bench upgrades.
2) Add alternatives mode; small matching enhancements if needed.
3) AI narrative + UI.
- Diagnostics highlight freshness/coverage issues with actionable next steps.

DynastyProcess Files: Additional Significant Value
- Primary high-value files used: db_fpecr_latest.csv, fp_latest_weekly.csv, values-players.csv, values-picks.csv.
- Potential incremental: ROS ECR (if available) for tie-breaks. Injury/snap/depth would be high value but are not in DP files and require separate sources.
