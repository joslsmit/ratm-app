# Waiver Wire v4 — UX Simplification + Quality Overhaul (Plan)

> Purpose: Fix confusing UX, eliminate “self‑add” errors (e.g., recommending Rashee Rice when already rostered), and improve recommendation breadth/quality without overwhelming the user. Phased, low‑risk path with clear success metrics and validation.
> Scope: Frontend Waiver Wire page + Backend waiver v2/v3 endpoints. Yahoo mode first; traditional mode preserved but de‑emphasized.

## Executive Summary
- Problems today
  - Overly complex UI: too many toggles (“Show Alternatives”, Advanced, Browse Pool, Debug AI) with unclear meanings and interactions.
  - Limited and “pre‑determined” feeling: recommendations constrained by rigid candidate quotas and min‑benefit gating, producing narrow results.
  - Correctness flaw: Occasionally suggests adding a player already on your roster (e.g., Rashee Rice) due to missing hard guard in deterministic flow and potential ID/name mismatch.
  - Alternatives toggle unclear: Users don’t understand that it surfaces near‑neutral moves and why they appear.
- Goals
  - Make the page simple-by-default, powerful-on-demand.
  - Ensure rock‑solid correctness (never suggest a self‑add; never drop a non‑rostered player).
  - Improve breadth and personalization of candidates while keeping high signal and speed.
  - Provide transparent “why” without requiring users to read debug data.

## Key Findings (from code and behavior review)
- Frontend complexity
  - Controls cluster: Refresh, Show Alternatives (also alters minBenefit), Show Details, Advanced (reveals Status + Min Benefit), Browse Pool, Debug AI.
  - Alternatives semantics are hidden: it silently flips `min_benefit` to `-1.0` and reveals a slider only when Advanced is open.
  - Debug AI surfaced in primary UI: useful for development, confusing in production.
- Backend deterministic (v2) gaps
  - Candidate pool quotas are static (QB/RB/WR/TE). No early personalization from actual bench needs beyond scoring phase; can feel constrained or “pre‑determined”.
  - No explicit check excluding players already on roster before computing deltas (assumes Yahoo “A/FA/W” excludes rostered players; safe but brittle). If Yahoo returns data oddly or aliases mismatch, a self‑add could slip in.
- Backend AI (v3) strengths and gap
  - AI validation correctly filters out adding rostered players using normalized names; deterministic fallback does not apply the same guard.
  - AI prompt breadth is limited to top N candidates; results quality depends on how well the deterministic candidate set reflects actual needs.

## Root Causes
- UX: Parallel toggles with coupled behavior (Alternatives ↔ Min Benefit) create cognitive load and unpredictability.
- Deterministic engine: Rigid quotas + lack of early need‑aware pruning makes outcomes feel “pre‑determined”.
- Safety gap: Deterministic flow trusts pool status; lacks independent roster membership guard by Yahoo ID + normalized name.

## Design Principles (v4)
- Simple first view: clear “Top Moves” with small benefit pill, confidence chip, 1–2 badges, and “Why” bullets.
- One filters drawer: collapse complexity behind a single “Filters” button. No debug in primary UI.
- Safety first: hard guards on roster membership using Yahoo IDs and normalized names in every path (deterministic and AI).
- Need‑aware breadth: adapt candidate pool to team’s bench composition and shallow positions.
- Plain‑English labeling: “Include near‑neutral moves” instead of “Show Alternatives”. Explain what it does in a one‑line helper.

## Phase Plan

### Phase 0 — Immediate Hotfixes (0.5–1 day)
- Backend v2 guard (app.py)
  - Build `roster_id_set` and `roster_name_set` (normalized) from enriched roster.
  - Filter candidate pool: exclude any candidate whose Yahoo `player_id` is in roster_id_set OR normalized name is in roster_name_set.
  - Apply same guard again just before appending a recommendation as a belt‑and‑suspenders.
- Frontend guard (WaiverWireAssistant)
  - Cross‑check `recommendations` add.name against roster (from `/api/yahoo/roster`) and suppress any self‑add card with a small inline warning: “Already on your roster.”
  - Rename “Show Alternatives” → “Include near‑neutral moves” with a helper tooltip: “Show small or lateral gains to explore options.”
- Acceptance
  - Can’t reproduce self‑add on any league tested.
  - Alternatives toggle text and helper updated; no UI console errors.

### Phase 1 — UX Simplification (1–2 days)
- Controls consolidation
  - Replace 5+ controls with a single `Filters` drawer containing:
    - Status filter: A | FA | W
    - Include near‑neutral moves [checkbox]
    - Min Estimated Benefit [slider] (visible only when checkbox is on)
  - Move “Browse Pool” to a secondary, collapsible section below recommendations (closed by default) or a separate sub‑page link.
  - Hide “Debug AI” behind Settings → Developer mode; remove it from primary waiver UI.
- Card polish
  - Always show: confidence chip, `+Estimated Benefit` pill, up to 2 badges, and 2–3 “Why” bullets.
  - Keep “Show details” for baseline numbers; not open by default.
- Empty state & copy
  - Clear, single empty state: “No clear upgrades found. Try Include near‑neutral moves in Filters.”
- Acceptance
  - First‑view shows only “Refresh Recommendations” and a single “Filters” button.
  - No more than 1–2 lines of helper text are visible by default.

### Phase 2 — Recommendation Quality (2–3 days)
- Need‑aware candidate pool
  - Adjust quotas dynamically based on bench composition (e.g., more WR candidates if bench WR depth < target; reduce QB when bench already has 1+ QB).
  - Expand pool size when coverage is low (projections missing) to maintain breadth.
- League‑aware baselines
  - Slightly tune replacement baselines based on league signals if available (e.g., 6‑pt pass TD already handled; verify and parametrize for edge leagues).
- Personalization heuristics
  - Upweight candidates covering imminent starter byes and addressing shallow positions.
  - Downweight redundant QB additions when bench already has 1 QB.
- Acceptance
  - More variety in top 10 without quality drop.
  - At least one recommendation explicitly addresses the user’s shallowest position when a viable candidate exists.

### Phase 3 — Alternatives Reframe (1 day)
- Rename and explain
  - “Include near‑neutral moves” replaces “Show Alternatives”.
  - Inline explainer below the toggle: “Also show small or lateral upgrades that improve balance, depth or bye coverage.”
- Ordering & limits
  - Keep near‑neutral moves grouped under a small subheader below main moves (“Explore options”).
  - Limit to top 5 alternatives to prevent overwhelm.
- Acceptance
  - Users can easily distinguish strong upgrades vs exploratory options.

### Phase 4 — AI Narrative & Validation Polish (1–2 days)
- Validation
  - Reuse v2 roster guards in AI path before accepting AI moves (by ID + normalized name) to unify safety.
  - If AI proposes a self‑add after normalization, add a debug metric and auto‑drop the move.
- Narrative
  - Keep concise: 2–4 bullets per move; highlight main driver (Projection/Depth/Bye).
  - Summary: “Top move: Add X, drop Y (+N.N)” where N.N is Estimated Benefit.
- Acceptance
  - JSON strictly validates; deterministic fallback always present.
  - Summary line aligns with the first recommendation.

### Phase 5 — Observability + E2E Tests (1–2 days)
- Headless tests
  - Scenarios: full roster, partial bench, empty bench; ensure no self‑add; ensure Include near‑neutral surfaces options; verify simplified UI.
  - Automate with Playwright or Cypress headless in CI.
- Lightweight telemetry
  - Count of suppressed self‑add candidates (should trend to zero after Phase 0). No PII.
- Acceptance
  - Tests cover core flows and pass locally and in CI.

### Phase 6 — Rollout & Safeguards (0.5 day)
- Feature flag
  - Gate v4 UI behind `WAIVER_V4_UI=true` initially (env or small config) to allow rapid rollback.
- A/B (optional)
  - 10–20% cohort for v4 UI; simple funnel metrics: clicks on Refresh, Filters opens, cards expanded.

## Implementation Sketch (targeted, low‑risk)

- Backend (app.py)
  - In `/api/yahoo/waiver_recommendations_v2`:
    - After enriching roster, compute `roster_id_set` and `roster_name_set` (normalized via existing `normalize_player_name`).
    - In `_collect_enriched_pool`, optionally accept `roster_id_set` and filter; or post‑filter pool at call site to avoid signature change.
    - Before appending each recommendation, skip when add is in roster set.
  - In `/api/yahoo/waiver_recommendations_ai`:
    - Mirror the roster membership guards by Yahoo ID in addition to the existing normalized name check.
- Frontend (WaiverWireAssistant.js)
  - Replace control cluster with a `Filters` drawer.
  - Rename Alternatives; show slider only when checked; remove Debug AI button from primary UI.
  - Add client guard to hide any card where add ∈ roster (also show a small “Already on roster” note if ever encountered).
  - Keep “Browse Pool” collapsed and secondary.

## Risks & Mitigations
- Risk: Over‑broad filtering removes legitimate edge cases.
  - Mitigation: Use Yahoo `player_id` first, fall back to normalized name only when `player_id` missing.
- Risk: Reduced transparency for advanced users.
  - Mitigation: Move Debug AI to Settings → Developer mode, not removed entirely.
- Risk: Too many candidates slows response.
  - Mitigation: Dynamic quotas capped; only expand when projection coverage is low; keep hard cap (~120) with priority ordering.

## Success Metrics
- UX
  - 50% fewer visible controls on first view (from 5+ to 2: Refresh + Filters).
  - 80%+ users understand “Include near‑neutral” from one‑line helper (measured via quick tooltip copy test or feedback).
- Quality & Safety
  - 0 self‑add recommendations in production.
  - ≥1 recommendation addresses shallowest position when a viable candidate exists.
  - Broader mix: at least 3 positions represented across top 10 when viable.
- Performance
  - Endpoint p95 unchanged or improved (<1s without AI; <2s with AI).

## Validation Checklist
- Deterministic v2 rejects any add that is already on roster (ID + normalized name).
- AI v3 moves re‑validated with the same rule.
- UI shows concise cards; Filters consolidates advanced options; no Debug AI in primary view.
- Alternatives renamed and clearly explained; grouped under “Explore options”.
- Headless tests cover self‑add, near‑neutral inclusion, basic flows.

## Proposed Timeline
- Phase 0: Today (hotfix guards + label rename)
- Phase 1: +1–2 days (UI simplify)
- Phase 2–4: +3–6 days (quality + AI polish)
- Phase 5–6: +1–2 days (tests + rollout)

## Next Actions (Do you want me to proceed?)
- Implement Phase 0 now:
  - Backend v2 guard (ID + name) and AI ID guard.
  - Frontend label rename and temporary client‑side guard.
- Then refactor WaiverWireAssistant controls into a Filters drawer (Phase 1).

