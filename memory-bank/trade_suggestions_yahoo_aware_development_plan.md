# Yahoo‑Aware Trade Suggestions — Development Plan

> File Type: Development Plan
> Review Priority: High
> Last Updated: 2025-09-19
> Status: Proposed (ready for implementation once approved)

## 1) Goals & Scope
- Generate actionable, Yahoo-aware trade proposals that improve our team first while remaining plausible for the counterparty.
- Bench-first target discovery: scan opponent benches before starters; expand to starters when needed.
- Support package trades: 1-for-1, 2-for-1, 1-for-2, 2-for-2 (cap 2 per side initially).
- Optimize for in-season outcomes: emphasize near-term window (N weeks) and ROS; optionally include playoff weeks. Default weights tuned for redraft/in-season.
- Hybrid engine: deterministic generation + AI re-ranking and explanations.

## 1.1 Default Presets (Season-Focused)
- Evaluation window weights: `w_nw=0.50` (Next 3 weeks), `w_ros=0.30`, `w_po=0.20`.
- Composite value weights: `w_pp=0.55` (projections window points), `w_vorp=0.30`, `w_tv=0.10` (from values-players.csv), `w_risk=0.05`.
- Final ranking blend: `alpha=0.70` (YourDelta), `1-alpha=0.30` (AcceptanceProb).
- Parity minimum: `ParityMin=92%` OR allow if `TheirDeltaPts >= 5`.
- Acceptance threshold: `AcceptanceMin=0.35`.
- Bench-first: apply small bonus to final score (e.g., `+0.03`) when inbound assets are bench targets.
- Package size cap: `max_per_side=2` (1–1, 2–1, 1–2, 2–2). Return `top_k=12` proposals.
- Filters: exclude `DEF` and `K` by default; `include_injured=false` (Out/IR excluded; Q/D downgraded).
- Search limits: `beam_width=50` per opponent; `max_candidates=5000` overall.

## 2) Assumptions & Dependencies
- Yahoo OAuth is configured; we have read access to league, teams, and rosters.
- Existing name normalization/matching endpoints are available (waiver wire modules) and will be reused.
- CSV data exists and is loaded at runtime into in-memory caches (following existing data hygiene):
  - Trade value indices (dynasty/redraft aware if available).
  - Weekly projections and ROS projections.
  - Injury/status flags and bye weeks.
- Backend follows current patterns: Flask app, in-memory caches with scheduled refresh, utils for normalization.
- Frontend follows current patterns: React thin client, custom `useApi`, debug toggles.
- Season focus: this plan targets current-season improvement (redraft semantics). Dynasty-specific behavior is out of scope for initial implementation.

## 3) Data Sources & Schemas

### 3.1 Yahoo (Read-only)
- League context: league_key, scoring settings, roster positions (including flex types), schedule weeks.
- Team metadata: team_key, team name, manager name.
- Team rosters: per-player entries including selected position (starter vs bench), eligible positions, injury status, bye week.

Proposed aggregator: backend composes a league snapshot (teams + rosters + starters/bench flags) to minimize client round-trips.

### 3.2 Local CSVs (Cached)
- Trade Values CSV
  - Source: `values-players.csv` (canonical for player trade values).
  - Required columns (normalized after ingest): player_id, name, pos, team, trade_value, trade_value_type (dynasty|redraft), last_updated.
  - Optional: tier, volatility, age.
- Projections CSV(s)
  - Weekly projections: player_id, week, proj_points, floor, ceiling, opp, is_bye.
  - ROS projection: player_id, ros_points (or per-week rollup), playoff_weeks subset if available.
- Injuries/Status
  - player_id, status (Healthy, Q, D, O, IR), last_update.

Note: player_id is our internal normalized ID; ingest must map source names/IDs via existing normalization utilities.

## 4) Core Computations

### 4.1 Replacement & VORP Baselines
- For each position group P (e.g., QB, RB, WR, TE, DEF, K; plus FLEX types), compute a replacement-level baseline:
  - Option A (preferred): From current league FA pool, take median of top R replacement candidates at position P for the evaluation window.
  - Option B (fallback): Use league-wide baseline derived from projections: average of players ranked at slots equal to required starters per team × team count (i.e., last starter tier).
- VORP(player, P) = ProjectedPoints(player, window) − ReplacementPoints(P, window).

### 4.2 Player Value Vector (per player)
Let the evaluation window be a weighted mix:
- WindowPoints = w_nw * NextNWeeksPoints + w_ros * ROSPoints + w_po * PlayoffPoints
- Normalize features to [0,1] within position:
  - TV = normalized TradeValue
  - PP = normalized WindowPoints
  - VORP_N = normalized VORP
  - Risk = normalized risk (injury/role volatility) where higher = riskier

CompositeValue = w_tv * TV + w_pp * PP + w_vorp * VORP_N − w_risk * Risk

Default emphasis (season-focused): higher w_pp and w_vorp, moderate w_tv, conservative risk discount.
Dynasty behavior is deferred; future work can introduce a toggle that increases w_tv and age/trajectory features.

### 4.3 Team Needs & Surplus
- Compute each team’s Best Legal Lineup (see 4.4) to get baseline total points for the window.
- Need score by position P: LeagueMedianStarterPoints(P) − TeamStarterPoints(P) (clamped ≥ 0).
- Surplus score by position P: BenchDepthPointsAboveReplacement(P) (how many bench players materially above replacement).

### 4.4 Best Legal Lineup (lineup optimization)
- Inputs: roster with eligible positions, league roster rules (including FLEX types), position scoring.
- Output: max-sum assignment of players to valid slots for the evaluation window points.
- Approach: greedy with backtracking for FLEX:
  1) Fill fixed slots (QB, RB1, RB2, WR1, WR2, TE, etc.) using highest WindowPoints eligible players.
  2) Fill FLEX slots by considering remaining eligible players across allowed positions, choose highest WindowPoints.
  3) If superflex/2QB, include QB in FLEX eligibility as per rules.
- Keep both variants: current roster and post-trade roster to compute deltas.

## 5) Package Generation (Deterministic)

### 5.1 Candidate Pool
- Targets: opponent bench players first; then starters if bench yields insufficient options.
- Your Offers: players classified as surplus by position (surplus score > threshold) and with lower marginal impact on your best lineup.

### 5.2 Package Forms
- Allowed: [1-for-1], [2-for-1], [1-for-2], [2-for-2].
- Cap per side initially at 2 to control search size.

### 5.3 Search Strategy (beam-style)
1) Seed pairs from YourSurplus × TheirBenchTargets, ranked by (YourImprovement preliminary + ValueParity closeness + TheirNeed match).
2) For seeds that fail fairness/acceptance thresholds, expand by adding an extra asset on the weaker side (2-for-1 / 1-for-2) from the corresponding surplus pool.
3) Maintain a beam of top B partial packages per counterparty (e.g., B=50) and prune by:
   - Roster legality feasibility (pre-check by counts/eligibility).
   - Injury/bye filters (if enabled).
   - Duplicate/commutative packages.

### 5.4 Roster Legality and Size
- Validate pre- and post-trade rosters for both teams:
  - Total roster size within limits (consider IR slots and status if supported).
  - Positional slot feasibility for starters after trade.
- If inflow > outflow for our team, propose a companion drop (or suggest best waiver drop via existing waiver engine); include in result as a suggestion, not part of the trade package.

## 6) Scoring & Ranking

### 6.1 Point Deltas
- MyDeltaPts = BestLineupPointsAfter − BestLineupPointsBefore (using window weights).
- TheirDeltaPts = TheirBestAfter − TheirBestBefore.

### 6.2 Value Parity
- Sum trade values on each side; adjust by positional scarcity weight s(P) (e.g., TE premium, superflex).
- ParityPct = 100 * (1 − |SideA − SideB| / max(SideA, SideB)).
- Require ParityPct ≥ ParityMin (e.g., 92%) or compensate with TheirDeltaPts ≥ threshold.

### 6.3 Acceptance Likelihood (proxy model)
Features:
- f1 = scaled(TheirDeltaPts)
- f2 = ParityPct
- f3 = −DepthPenalty (taking their only viable backup at scarce P)
- f4 = −ScarcityPenalty (if their starters at P degrade)
- f5 = Contender/Rebuilder alignment (optional; disabled by default in season-focused mode)

AcceptanceProb = sigmoid(β0 + β1 f1 + β2 f2 + β3 f3 + β4 f4 + β5 f5)

### 6.4 Final Rank Score
- Score = α * MyDeltaPtsNorm + (1 − α) * AcceptanceProb, default α=0.7.
- Discard if AcceptanceProb < min_accept (e.g., 0.35) or MyDeltaPts ≤ 0.
- Bench-first bonus: boost Score if inbound players originated from bench.

Defaults in effect: `alpha=0.70`, `min_accept=0.35`, bench bonus `+0.03` to Score.

### 6.5 Positional Scope Defaults
- Exclude DEF and K from proposals by default (both giving and receiving).
- Provide optional toggle to include DEF/K; default remains OFF.

## 7) AI Integration (Hybrid)

### 7.1 Inputs to AI (top M proposals, M≈12–20)
- Compact JSON context:
  - league: scoring highlights, roster rules.
  - my_team: starters, bench, weaknesses; current record/standings if available.
  - opp_team: same as above.
  - proposals: [{ my_side[], their_side[], my_delta_pts, their_delta_pts, parity_pct, flags[] }].
  - projections summary for involved players (window points, volatility, schedule notes).

### 7.2 AI Tasks
- Re-rank ties/near-ties using qualitative heuristics (role stability, bye/stack dynamics, playoff fit).
- Generate explanations:
  - 3–5 bullets: why this helps us and why it’s reasonable for them.
  - 1–2 sentence negotiation pitch tailored to opponent needs/surplus.

### 7.3 AI Output Schema
```json
{
  "trade_id": "string",
  "my_side": ["player_id"],
  "their_side": ["player_id"],
  "my_delta_points": 0.0,
  "their_delta_points": 0.0,
  "value_parity_pct": 0,
  "acceptance_prob": 0.0,
  "flags": ["bench_target", "pos_scarcity"],
  "reasons": ["string"],
  "negotiation_pitch": "string"
}
```

## 8) Backend API Design

### 8.1 Yahoo Snapshot
- GET `/api/yahoo/league_snapshot?league_key=...&include_bench=1`
  - Returns: teams[], each with roster entries {player_id, name, pos, eligible_pos[], is_starter, status, bye_week}.

### 8.2 Trade Suggestions
- POST `/api/trade_suggestions`
  - Body:
```json
{
  "league_key": "string",
  "my_team_key": "string",
  "target_team_keys": ["string"],
  "horizon_weeks": 3,
  "ros_weight": 0.3,
  "playoff_weight": 0.2,
  "max_package_size": 2,
  "include_injured": false,
  "dynasty_mode": false,  
  "dynasty_mode_note": "ignored for now; season-focused defaults in effect",
  "use_ai": true,
  "bench_first": true,
  "debug": 0
}
```
  - Response: `{ proposals: [AI Output Schema with deterministic fields], meta: { timing, filters } }`.

### 8.3 Debug Endpoint
- GET `/api/trade_suggestions/debug?trade_id=...`
  - Returns: pre/post lineups for both teams, scoring breakdown, inputs to AI, and prompt (if applicable).

## 9) Frontend UX
- New “Trade Center” page under Tools.
- Controls:
  - Horizon slider (weeks), ROS/playoff toggles, dynasty toggle.
  - Max package size, include injured, target teams multi-select.
  - Bench-first (default ON), min acceptance threshold.
- Results list:
  - Proposal card: players per side with positions, delta chips for both teams, parity badge, acceptance%, bench badge, flags.
  - Expand to show: reasons, negotiation pitch, post-trade lineup preview for both teams.
  - Actions: copy summary, copy Yahoo search links, open debug view.

## 10) Implementation Steps (Phased)

### Phase 1: Deterministic MVP
1. Add league snapshot aggregator endpoint; cache rosters + starters/bench flags.
2. Ingest/normalize trade values; validate mapping coverage against league rosters.
3. Implement evaluation window computation (NextNWeeks, ROS, playoff weighting).
4. Implement Best Legal Lineup optimizer and delta calculations.
5. Implement needs/surplus detection and bench-first target discovery.
6. Implement package generator (1-for-1, 2-for-1, 1-for-2), roster legality checks, parity filters.
7. Implement scoring (MyDeltaPts, TheirDeltaPts, Parity) and initial ranking.
8. Add backend POST `/api/trade_suggestions` with debug model; basic JSON output.
9. Frontend Trade Center MVP (no AI, simple table/cards) + debug toggle.

### Phase 2: AI & Acceptance
1. Add acceptance likelihood proxy model (logistic) with tunable coefficients.
2. Integrate AI re-ranking + explanation generation for top M.
3. Expand package forms to 2-for-2; add bench-first bonus.
4. Frontend: explanations, negotiation pitch, acceptance% badge.

### Phase 3: Playoff & Waiver Tie-ins
1. Playoff-week emphasis presets; schedule difficulty blending.
2. Companion drop/waiver suggestions when inflow > outflow (reuse waiver engine).
3. Superflex/2QB and TE-premium nuances (scarcity weights & lineup rules).

### Phase 4: Personalization & Polish
1. Opponent profile heuristics (contender vs rebuilder via standings/points for).
2. Caching strategies, performance tuning, and rate limit handling.
3. A/B toggles for α and acceptance threshold defaults.

## 11) Validation & Testing
- Unit tests
  - Normalization coverage: 100% of snapshot players map to internal IDs or are reported.
  - Lineup optimizer: deterministic fixtures with expected outputs for varied roster rules.
  - VORP baseline: sanity against FA pool and projection ranks.
  - Package legality: generated trades always pass roster legality validator.
- Integration tests
  - Golden snapshot fixtures (sanitized) to produce stable top K proposals.
  - Regression on scoring outputs after data refresh.
- Manual QA
  - Debug views show deltas, parity math, and pre/post lineups for spot checks.

## 12) Observability
- Logging: proposal generation steps, pruning reasons, acceptance features, AI latency.
- Metrics: time per stage, proposals generated, accepted after filters, cache hit rates.
- Error reporting: name mismatches, missing projections/trade values, Yahoo API failures.

## 13) Performance & Caching
- Cache league snapshot for session or 5–10 minutes; allow manual refresh.
- Precompute per-position baselines and normalized feature scales per request.
- Beam search caps: B=50 per opponent; hard cap total candidates evaluated (e.g., 5k).
- Short-circuit if no positive MyDeltaPts possible for a given opponent.

## 14) Security & Privacy
- Use `FLASK_SECRET_KEY` for sessions; never log OAuth tokens or PII.
- Redact manager names in debug artifacts unless user opts in.

## 15) Risks & Mitigations
- Sparse or noisy trade values → blend with projections/VORP; show confidence.
- Name mismatches → leverage existing normalization; produce mismatch report in debug with suggested aliases.
- Roster rule edge cases (superflex, multi-FLEX) → test fixtures and generalized optimizer.
- Overfitting acceptance heuristic → conservative thresholds; user-adjustable sliders.

## 16) Open Questions
- Preferred evaluation window defaults (e.g., 3 weeks + ROS 0.3, playoffs 0.2)?
- Any league veto culture constraints or managers to exclude?

## 17) API Contracts (Examples)

### Request
```json
{
  "league_key": "nhl.l.12345", 
  "my_team_key": "nhl.l.12345.t.3",
  "target_team_keys": ["nhl.l.12345.t.5", "nhl.l.12345.t.7"],
  "horizon_weeks": 3,
  "ros_weight": 0.3,
  "playoff_weight": 0.2,
  "max_package_size": 2,
  "include_injured": false,
  "dynasty_mode": false,
  "use_ai": true,
  "bench_first": true,
  "debug": 1
}
```

### Response (one proposal)
```json
{
  "trade_id": "T-5f8a",
  "my_side": ["pid_123"],
  "their_side": ["pid_456", "pid_789"],
  "my_delta_points": 14.2,
  "their_delta_points": 7.8,
  "value_parity_pct": 94,
  "acceptance_prob": 0.41,
  "flags": ["bench_target", "pos_scarcity_te"],
  "reasons": [
    "We upgrade WR2 by ~9 pts over next 3 weeks",
    "They add RB depth aligning with their weak RB2",
    "Parity within 6% supported by short-term gain"
  ],
  "negotiation_pitch": "You’re light at RB; this gives you two playable options while we consolidate WR production."
}
```

## 18) Pseudocode Highlights

BestLineup(roster, rules):
1) Assign fixed slots by highest WindowPoints eligible.
2) For each FLEX slot type, pick next-best among eligible remaining players.
3) Return total points and assignments.

GeneratePackages(my, opp):
1) targets = opp.benchTargets ∪ (opp.starterTargets if needed)
2) offers = my.surplus
3) seeds = topPairs(offers × targets)
4) for each seed not passing filters: add asset from weaker side; re-evaluate
5) validate legality; compute deltas and parity; keep top-K by Score

AcceptanceProb(features): return sigmoid(β · features)

## 19) TODO (Upon Approval)
- Confirm CSV schemas and canonical trade value source per league type.
- Lock default weights: α, β coefficients, window weights, ParityMin.
- Define snapshot JSON contract and implement `/api/yahoo/league_snapshot`.
- Implement deterministic engine (Phases 1–2 steps 1–7), then add AI.
- Build Trade Center MVP with debug view; iterate on UX.
