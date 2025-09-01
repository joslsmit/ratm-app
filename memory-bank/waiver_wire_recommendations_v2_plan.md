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
  - Phase 4 (recommendations v2):
    - `curl -sk -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"league_key":"'$LEAGUE_KEY'","team_key":"'$TEAM_KEY'","week":null,"status":"A","top_n":10}' "$BASE/api/yahoo/waiver_recommendations_v2" | jq '{count:(.recommendations|length), first:(.recommendations[0])}'`
  - Provide one-paste wrappers in docs for each phase (similar to the scripts we used today).

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
- Implement `/api/yahoo/waiver_pool` and `/api/yahoo/waiver_recommendations_v2` (backend), then wire the frontend view.
- Add alias mapping + diagnostics for unmatched names.
- Tune scoring weights after initial real-league validation.
