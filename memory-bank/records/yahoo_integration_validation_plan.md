# Yahoo Integration Validation Plan — Post‑Draft (GO-FORWARD)

> Status: Planning document created (Auth confirmed working)
> Owner: You + Assistant
> Goal: Validate we are pulling the “right” data from Yahoo Fantasy API and reliably enriching it with daily CSVs, with strong observability and tests.

## Objectives
- Confirm each Yahoo API call matches the official endpoint semantics and parameters.
- Validate correctness for My Team (roster) and Waiver Wire data, including week/status handling and pagination.
- Ensure robust enrichment from daily CSVs (ECR, bye weeks, projections, player values) with high match rates.
- Add debug tooling, fixtures, and tests so we can rapidly diagnose and prevent regressions.

## Scope
- Backend endpoints: `/api/yahoo/leagues`, `/api/yahoo/roster`, `/api/yahoo/waiver_wire`, `/api/yahoo/league_context` (+ new debug/diagnostics endpoints).
- Data sources: Yahoo API + CSVs: `db_fpecr_latest.csv`, `values-players.csv`, `values-picks.csv`, `fp_latest_weekly.csv`.
- Enrichment cache: `create_enhanced_combined_player_data_cache()`.

## “Right Data” Contracts
- Leagues: `users;use_login=1/games;game_keys=nfl/leagues;out=teams?format=json`
  - Output includes correct `league_key` and the authenticated user’s `team_key` for each league.
- My Team (roster): `team/{team_key}/roster/players?format=json` (fallback `roster`; supports `week`)
  - Fields: `player_key`, `player_id`, `name`, `selected_position` (lineup slot), `eligible_positions`, `status`.
  - Display position comes from enrichment (CSV), not the lineup slot.
- Waiver Wire (available players): `league/{league_key}/players;status={FA|W|A}?format=json`
  - Supports pagination (`start`, `count`).
  - Optional ownership detail if needed to strictly separate FA vs W.
  - Enriched with ECR, bye, team, projections.

## Phases & Tasks

### Phase 0 — Baseline Validation (Quick Wins)
- [ ] Verify keys flow: UI `league_key` and `team_key` match `/api/yahoo/leagues` output.
- [ ] Smoke curls with real token:
  - Roster: `curl -k -H "Authorization: Bearer $TOKEN" "https://localhost:5000/api/yahoo/roster?team_key=YOUR_TEAM_KEY"`
  - Waivers (A/FA/W): `curl -k -H "Authorization: Bearer $TOKEN" "https://localhost:5000/api/yahoo/waiver_wire?league_key=YOUR_LEAGUE_KEY&status=A"`
- [ ] Confirm roster fields populated and not conflating lineup slot vs player position.
- [ ] Confirm waivers return non‑zero and look plausible vs Yahoo UI.

### Phase 1 — Instrumentation & Debug
- [x] Add `/api/yahoo/waiver_debug` (like `roster_debug`): echoes exact Yahoo URL/params (`status`, `start`, `count`), status code, parse count, duration, sample players.
- [x] Add structure introspection in debug: report container types and counts to diagnose parsing.
- [ ] Add structured logs for Yahoo calls: url, params, status, parse_count, latency.

### Phase 2 — Waiver Pagination & Status Correctness
- [x] Implement internal pagination loop for waivers using `start`/`count` (e.g., 50 per page, cap ~150).
- [ ] Validate `status=FA`, `status=W`, and `status=A` produce expected subsets; compare sample to Yahoo UI.
- [ ] Keep output stable and sorted by ECR (missing ECR last).

### Phase 3 — CSV Freshness & Cache Rebuild
- [x] After `import_data()` runs daily, reload CSVs and rebuild `combined_player_data_cache()` automatically (no server restart required).
- [ ] Add CSV modified-time check and include timestamps in diagnostics.

### Phase 4 — Fixtures + Parsing Tests
- [ ] Capture raw JSON fixtures for your league:
  - Roster (current week and one alternate week).
  - Waivers: `status=FA`, `status=W`, and `status=A` for page 0 and page 1.
- [ ] Unit tests:
  - `parse_yahoo_roster_response`: counts > 0; fields populated; correct handling of week; `selected_position` not misused.
  - `parse_yahoo_waiver_response`: counts > 0; names/teams/positions non‑empty; pagination sums match expected; handles player_info[0] dict/list variants.
  - Enrichment coverage assertions: roster match rate ≥ 95%, waiver match rate ≥ 85%.

### Phase 5 — Data Health & Conformance Checklist
- [x] Add `/api/diagnostics/yahoo-data-health?league_key&team_key`:
  - Returns roster_count, waiver enrichment match, waiver A (first 2 pages) enrichment match, CSV modified times.
- [ ] Produce a one‑page conformance sheet per endpoint: URL patterns, params, subresources, mappings, edge cases.

### Phase 6 — Rollout & Validation
- [ ] Re‑run Phase 0 smoke tests.
- [ ] Validate UI flows: My Team shows enriched fields; Waiver grid shows expected volume after pagination; sorting by ECR works.
- [ ] Sign‑off against acceptance criteria.

## Acceptance Criteria
- Roster: Full team returned; lineup slot (`selected_position`) is distinct from display position; enrichment populated (team, position, bye, ECR). Match rate ≥ 95%.
- Waivers: `A`, `FA`, `W` produce expected counts; pagination returns ≥ 50–150 entries depending on league; sorted by ECR; enrichment populated. Match rate ≥ 85%.
- CSV Freshness: Files < 24h; automatic cache rebuild reflects new data; projections include `scrape_date` in responses.
- Observability: Debug endpoints and logs show URLs/params and parse counts; data health endpoint returns green metrics.

## Runbook (Auth is working)
1) Get keys: `curl -k -H "Authorization: Bearer $TOKEN" https://localhost:5000/api/yahoo/leagues`
2) Roster: `curl -k -H "Authorization: Bearer $TOKEN" "https://localhost:5000/api/yahoo/roster?team_key=YOUR_TEAM_KEY"`
3) Waivers: `curl -k -H "Authorization: Bearer $TOKEN" "https://localhost:5000/api/yahoo/waiver_wire?league_key=YOUR_LEAGUE_KEY&status=A"`
4) If waiver count looks small, use debug endpoint and add pagination (Phase 2).

## Notes & Risks
- Yahoo response structures are deeply nested; defensive parsing stays mandatory.
- Name normalization remains critical for high enrichment match rates (handle Jr./II/III, punctuation, abbreviations).
- Some leagues may differ in subresource availability; keep fallback branches.

## Update Log
- 2025‑09‑01: Plan created. Next: Phase 1 (debug endpoints + logs), Phase 2 (pagination).
- 2025‑09‑01: Implemented Phase 1 (part): added `/api/yahoo/waiver_debug` for URL/params/parse diagnostics.
- 2025‑09‑01: User league_key noted: `461.l.42889`; team_key noted: `461.l.42889.t.8` (for testing references).
- 2025‑09‑01: Implemented Phase 2: Added pagination to `/api/yahoo/waiver_wire` with cap and enrichment.
- 2025‑09‑01: Adjusted waiver pagination step to 25 (Yahoo page size) to aggregate multiple pages correctly.
- 2025‑09‑01: Implemented Phase 3: Added daily `refresh_external_data()` to re-download CSVs and rebuild combined cache.
- 2025‑09‑01: Hardened waiver parser to support Yahoo JSON variants (basic dict vs nested list) and improved debug structure reporting.
- 2025‑09‑01: Updated parser to support players container as dict or list; extraction helper for robust field mapping.
- 2025‑09‑01: Implemented diagnostics endpoint `/api/diagnostics/yahoo-data-health` with match rates and CSV freshness.
