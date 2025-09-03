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
- Whole‑roster scoring (Implemented):
  - overall = lineup_week_points + α·bench_VOR + β·balance + γ·bye_coverage
  - α=0.7, β=0.3, γ=0.3 (conservative; tunable)
  - Bench VOR = Σ bench(max(0, effective_points − replacement_baseline(position)))
  - Balance: small penalty for imbalanced bench (targets QB≤1; RB≥2; WR≥2; TE≥1)
  - Bye Coverage: small bonus when bench covers starter byes
  - Cross‑position guard: penalty unless balance improves; plus penalties for surplus bench QBs and RB/WR shortages
- Scoring data flow (Implemented):
  - Weekly‑first (fp_latest_weekly.csv r2p_pts)
  - ECR→points fallback curves when weekly missing (QB ~20→10; RB/WR ~15→6; TE ~10→4)
  - ID‑based enrichment: Yahoo `player_id` ↔ ECR `yahoo_id` join
- Candidate pool (Implemented):
  - Broad set with position quotas (e.g., QB 10, RB 40, WR 50, TE 20) to avoid QB crowding; fill remainder by effective score
  - Excludes K/DEF by default
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

## 7) UI/Display (Next)
- Terminology: “Estimated Benefit” (replace “delta”)
- Breakdown for top N:
  - Lineup: +X.X, Bench VOR: +Y.Y, Balance/Bye: small modifiers
- Badges:
  - Depth (strengthens RB/WR/TE bench)
  - Bye Coverage (covers Week N starter bye)
  - Insurance (handcuff/next‑up depth)
  - Upside (rookie/trend)
  - Risk (injury/uncertainty)
- Alternatives mode (opt‑in): show best near‑neutral suggestions with badges when strict mode yields few ideas

## 8) Rollout
- Phase 1 (Done): Whole‑roster scoring, conservative fallback, ID join, QB crowding prevention, diagnostics
- Phase 2 (Next): Alternatives mode (opt‑in) + UI badges & wording
- Phase 3: AI narrative integration (few‑shots, strict JSON) and frontend rendering with badges

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
- Left:
  - Alternatives mode (opt‑in)
  - UI badges & “Estimated Benefit” wording in responses/UI
  - AI narrative (prompting + strict JSON) and frontend rendering

## 12) Recommended Next Steps
1) Implement Alternatives Mode (opt‑in)
   - API: add `include_alternatives=true` and `min_benefit` (e.g., −1.0) to include best near‑neutral suggestions with badges
   - Clearly mark as “Consider” with rationale (Depth/Bye/Insurance/Upside)
2) Add UI badges & wording stub in endpoint output
   - Include computed badges list per recommendation; switch wording to “Estimated Benefit”
3) Wire AI Narrative (few‑shots; strict JSON)
   - Summarize why top 3–5 moves make sense; include badges and component highlights
4) Frontend updates
   - Render breakdown & badges; add toggle for alternatives mode; filter by min Estimated Benefit

## 13) Update Log (Key Milestones)
- 2025‑09‑01: Initial plan; endpoints draft; test scripts
- 2025‑09‑02: CSV importer refresh; `/api/admin/refresh_data`; coverage diagnostics
- 2025‑09‑03: Whole‑roster scoring (lineup + bench VOR + balance + bye), ID join, cross‑pos & bench composition guards; UI badge plan and wording captured
