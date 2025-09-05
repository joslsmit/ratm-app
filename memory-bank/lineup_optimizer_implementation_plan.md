# Lineup Optimizer Implementation Plan — Hybrid (Deterministic + AI)

> Priority: HIGH — In‑Season Functionality Enhancement  
> Status: PARTIALLY IMPLEMENTED (Yahoo mode live)  
> Last Updated: August 31, 2025  
> Estimated Effort: 12–16 hours dev + 4–6 hours testing  
> Complexity: MEDIUM (reuses existing infra)  
> Risk: LOW (additive, feature‑flag ready)

## 1. Objectives
- Deliver weekly start/sit “Lineup Optimizer” as a second mode inside the Waiver Wire Assistant.
- Use a deterministic optimizer for reliability and speed; add a concise AI “Analyst’s Note” explaining key swaps.
- Zero breaking changes to existing waiver flows. Graceful degradation if data/AI unavailable.

## 2. Approach Overview (Hybrid)
- Deterministic core: Optimize starters using projections and roster/slot constraints (fast, testable, reproducible).
- AI explanation: Generate a short narrative for the most impactful 1–2 changes via existing PromptBuilder + process_ai_response_v2.
- Dual data modes: 
  - Yahoo mode (preferred): Backend fetches roster/status + league slots via Yahoo using existing patterns.
  - Traditional mode (fallback): Frontend submits a roster-by-slot payload (reuses current manual roster UI), optimizer runs the same core.

## 3. Data & Inputs
- Projections & matchup context: Reuse existing weekly projections/matchup fields already used by enhanced waiver logic (e.g., `projected_points`, `matchup_difficulty`, `opponent`, `home_away`).
- Status & eligibility: Use Yahoo editorial status when available; otherwise infer from local data. Exclude OUT/IR and BYE from starters; allow Q/D but flag.
- League & slots:
  - Standard target slots: `QB, RB1, RB2, WR1, WR2, TE, W/T, W/R/T, K, DEF` (match existing roster schema).
  - Slot rules:
    - `QB`: only QBs
    - `RB1/RB2`: RBs
    - `WR1/WR2`: WRs
    - `TE`: TEs
    - `W/T`: WR or TE
    - `W/R/T`: WR or RB or TE
    - `K`: Kickers
    - `DEF`: Team defenses
  - Bench: All remaining eligible players not selected for starters.
  - Support `week` parameter for weekly specificity where applicable.

## 4. API Design

Endpoint: `POST /api/optimize_lineup`

Request (Yahoo mode):
```
{
  "mode": "yahoo",
  "team_key": "461.l.12345.t.8",
  "league_key": "461.l.12345",  // optional if derivable from team_key
  "week": 1                       // optional; defaults to current
}
```

Request (Traditional mode):
```
{
  "mode": "traditional",
  "roster": {
    "QB": "Josh Allen",
    "RB1": "Saquon Barkley",
    "RB2": "James Cook",
    "WR1": "Tyreek Hill",
    "WR2": "Amon-Ra St. Brown",
    "TE": "Sam LaPorta",
    "W/T": "",
    "W/R/T": "",
    "K": "Justin Tucker",
    "DEF": "49ers",
    "BN1": "Tony Pollard",
    "BN2": "Jerry Jeudy",
    "BN3": "..."
  },
  "week": 1
}
```

Success Response (common):
```
{
  "suggested_lineup": {
    "QB": "Josh Allen",
    "RB1": "Saquon Barkley",
    "RB2": "James Cook",
    "WR1": "Tyreek Hill",
    "WR2": "Amon-Ra St. Brown",
    "TE": "Sam LaPorta",
    "W/T": "Tony Pollard",
    "W/R/T": "Jerry Jeudy",
    "K": "Justin Tucker",
    "DEF": "49ers"
  },
  "bench": ["..."],
  "total_projected_points": 120.8,
  "diff": [
    {"slot": "W/T", "from": "", "to": "Tony Pollard"},
    {"slot": "W/R/T", "from": "Tony Pollard", "to": "Jerry Jeudy"}
  ],
  "eligibility_info": {
    "excluded": ["Player X (OUT)", "Player Y (IR)", "Defense Z (BYE)"],
    "flagged": ["Player Q (Questionable)", "Player D (Doubtful)"]
  },
  "ai_note_json": {
    "confidence": "High|Medium|Low",
    "headline": "string",
    "reasons": [{"type":"Projection|Matchup|Status|Variance|Correlation|FlexAllocation|Consensus|Usage|Confidence|Context","text":"string","evidence":{}}],
    "tags": ["string"],
    "score_breakdown": { "projection": number, "matchup": number, "correlation": number, "variance": number }
  }
}
```

Error Response:
```
{ "error": "Descriptive message" }
```

Headers:
- `X-API-Key`: user’s Gemini key (existing pattern) for AI note (optional if AI is disabled).
- Yahoo token header (match existing Yahoo endpoints; reuse current handling in backend/app.py).

## 5. Deterministic Optimizer Spec

### 5.1 Eligibility & Preprocessing
- Build canonical player objects with: name, pos, team, status, bye_week, projected_points (float), opponent, home_away, matchup_difficulty (if available).
- Exclusions from starters: status in {OUT, IR} or bye in selected week.
- Allowed but flagged: status in {Questionable, Doubtful}.
- If projections missing: impute with conservative fallback using ECR-based proxy (lower ECR => higher baseline) and mark `imputed: true`.

### 5.2 Constraints & Slots
- Target starter counts: 1 QB, 2 RB, 2 WR, 1 TE, 1 W/T (WR/TE), 1 W/R/T (WR/RB/TE), 1 K, 1 DEF.
- Each player can occupy at most one slot.
- Flex slots draw from remaining pool after filling strict slots.

### 5.3 Objective & Tie-Breaks
- Maximize sum(projected_points) over starters.
- Tie-break order:
  1) Higher projected_points
  2) Lower matchup_difficulty (if provided)
  3) Home > Away
  4) Lower ECR (better rank)
  5) Deterministic name tiebreak (e.g., lexicographic)

### 5.4 Algorithm (Efficient + Testable)
1) Select strict singleton slots first: `QB, TE, K, DEF` — pick top eligible per slot.
2) Fill base multi-slots: choose top 2 RB, top 2 WR.
3) Build flex candidate pools from remaining bench:
   - `W/T`: WR or TE
   - `W/R/T`: WR or RB or TE
4) Greedy fill flex slots with best remaining candidates, then run local improvement:
   - Local search (1–2 pass hill climbing) over swaps between RB/WR/TE and flex to improve total.
   - Consider top N (e.g., 3) candidates per flex to explore small combinations; roster size is small so O(N^2) is fine.
5) Output starters, bench, totals, and diff vs submitted current lineup (if provided/derivable).

Notes:
- This achieves near‑optimal results for typical roster sizes without external solvers; deterministic and <300ms target.
- If we later add an ILP/Hungarian solver, this interface remains stable.

## 6. AI “Analyst’s Note” (Concise Narrative)
- Purpose: Explain the most impactful change in up to three grounded bullets, with small score chips.
- Prompting:
  - System: "You are a fantasy football analyst. Explain the key lineup change(s) succinctly and data‑driven."
  - User context includes: player_in/out, projections, opponent, status flags, and why the optimizer preferred one over the other (projection delta, slot scarcity, matchup).
- Implementation:
  - Use `PromptBuilder` (extend with `build_lineup_note_prompt`), then call Gemini with user `X-API-Key`.
- Process via `process_ai_response_v2` or strict JSON parse; attach `ai_note_json` with `{ confidence, headline, reasons[], tags[], score_breakdown{} }`.
- Failure mode: If AI call fails, omit `ai_note` and still return deterministic result.

## 7. Frontend UI/UX
- Mode toggle: Reuse Waiver Wire Assistant component; add `assistantMode = 'waiver' | 'lineup'`.
- Action button: “Optimize My Lineup” (Yahoo mode) or “Analyze Current Lineup” (traditional mode).
- Side‑by‑side view: Current vs Suggested with changes and points total.
- Structured note card: tags (chips), score breakdown chips (projection, matchup ±0.10, etc.), headline, and typed reason bullets. Legacy markdown hidden.

## 8. Security & Config
- Yahoo OAuth: Reuse existing header/token flow; do not persist tokens server‑side.
- Local vs Prod: Respect current redirect toggle guidance in `development_workflow_guide.md` (switch redirect URI for local testing).
- CORS unchanged; endpoint follows existing `/api/*` patterns.
- Feature flag: Allow hiding lineup mode behind an env flag or UI toggle if desired.

## 9. Performance Targets
- Backend optimization: <300ms typical; <1s p95 including data enrichment.
- AI call: <1.5s typical on “flash” tier; total endpoint p95 <2.0s with AI; <0.7s without AI.
- Cache: Memoize enriched roster for team/week during request scope; optional short‑lived cache by team_key/week.

## 10. Testing Plan
- Unit (backend):
  - Eligibility filter: OUT/IR/BYE excluded; Q/D flagged.
  - Slot assignment: Respect `W/T`, `W/R/T` constraints; no duplicates; deterministic tie‑breaks.
  - Local improvement: Improves or equals greedy baseline on targeted scenarios (close RB/WR/TE tradeoffs).
  - Imputation: When projections missing, imputed values used and marked.
- Integration:
  - Yahoo mode: Mock Yahoo roster and league slots; verify optimizer output and `diff` correctness.
  - Traditional mode: Provide manual roster payload; verify same core results.
  - Error paths: Missing token, empty roster, no eligible players, AI failure (still returns deterministic result).
  - Debug: Use `?debug=1` to inspect `consensus_inputs` and `matchup_inputs` (raw values and applied bonus) for transparency.
- Frontend:
  - Render tests for mode toggle, loader, error display, and side‑by‑side diff.
  - Snapshot test for result rendering with `ai_note` present/absent.
- E2E (optional):
  - Yahoo login → league select → optimize → see suggested lineup and analyst note.

## 11. Implementation Phases & Tasks

Phase A — Spec Lock (0.5h)
- Confirm slot set and tie‑break order match current product defaults.
- Confirm projections and matchup fields available from existing enrichment utilities.

Phase B — Backend Core (3–4h)
- Add optimizer module/functions:
  - `build_eligible_pool(roster, week)`
  - `select_strict_slots(pool)`
  - `select_base_slots_rb_wr(pool)`
  - `fill_flex_with_local_improvement(pool, starters)`
  - `compute_diff(current, suggested)`
- Deterministic sort utilities for tie‑breaks.

Phase C — Endpoint & Yahoo/Traditional Integration (2–3h)
- Create `POST /api/optimize_lineup`:
  - Yahoo mode: fetch roster + statuses + (optional) league scoring/slots using existing helpers.
  - Traditional mode: validate roster payload, normalize names, enrich using existing `get_player_context`.
  - Return schema above with `eligibility_info` and `diff`.

Phase D — AI Analyst Note (1–2h)
- Extend `PromptBuilder` with `build_lineup_note_prompt`.
- Add endpoint call to Gemini gated by presence of `X-API-Key`.
- Parse via `process_ai_response_v2`; attach `ai_note` in response.

Phase E — Frontend (3–4h)
- Add mode toggle in Waiver Wire Assistant.
- Implement side‑by‑side comparison component; show arrows/badges; render markdown note.
- Wire Yahoo vs traditional calls; reuse existing loaders/errors.

Phase F — Tests & Polish (3–4h)
- Unit tests for optimizer core + integration tests with mocks.
- Frontend render tests; manual smoke across desktop/mobile; dark/light themes.
- Performance check and minor refactors.

## 12. Rollout & Validation
- Deploy behind a soft toggle (optional). Monitor backend logs (latency, error rate) and frontend errors.
- Success metrics:
  - Zero regressions in waiver flows.
  - Endpoint p95 <2.0s with AI; <0.7s without AI.
  - Positive user feedback on clarity of suggestions and note.

## 13. Open Questions (Decide Before Coding)
- Do we always exclude BYE from starters? (Recommended: yes.)
- Should `W/T` be prioritized for TE when TE is strong vs WR3? (Handled by projections; tie‑break ok.)
- Include week parameter default to current server week? (Recommended: yes.)

---

This plan merges deterministic optimization for correctness and speed with concise AI explanations for user trust and clarity. It reuses your existing Yahoo integration, data enrichment, PromptBuilder, and response processing, minimizing risk and time‑to‑ship while ensuring a professional, testable implementation.
