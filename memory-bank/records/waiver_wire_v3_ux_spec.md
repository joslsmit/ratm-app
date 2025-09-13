# Waiver Wire v3 UX Spec — Yahoo‑First (No Extra Sidebar)

> Status: In Progress (initial implementation landed)
> Scope: Frontend UX for Yahoo‑integrated Waiver Wire recommendations aligned to v3 backend

## Goals
- Make the Waiver page actionable by default for Yahoo‑authenticated users.
- Present top add/drop recommendations with clear “Estimated Benefit” and badges.
- Avoid conflicting navigation by not introducing any new sidebars.

## Layout
- Header Controls (inline):
  - League selector (when multiple)
  - Status filter: `A | FA | W`
  - Include alternatives (checkbox)
  - Min Estimated Benefit slider (−5.0 to +5.0, step 0.5; default −1.0 when alternatives enabled)
  - Refresh button
- Summary Chips (compact row): Baseline Overall, Lineup, Bench VOR, Balance, Bye
- Content Sections (stacked):
  1. Recommendations (default):
     - Card per add/drop with: title (“Add X • Drop Y”), benefit badge, mini breakdown placeholders, badges row, claim‑only tag for W
  2. Available Pool (secondary):
     - Grid/top N of available players with position, team, effective ECR; keep filters minimal initially
- Manual Mode: Traditional roster entry hidden when Yahoo token present; accessible when Yahoo mode is off.

## Data Flow
- Recommendations: `POST /api/yahoo/waiver_recommendations_v2`
  - Body: `{ league_key, team_key, status, top_n, include_alternatives, min_benefit, exclude_positions=['K','DEF'] }`
  - Auth: `Authorization: Bearer <access_token>`
- Pool (for secondary display): `GET /api/yahoo/waiver_wire?league_key=...&status=A`

## Copy & Badges
- Label “Estimated Benefit” replaces “delta” across the UI.
- Badges displayed inline: Depth, Bye Coverage, Insurance, Upside, Risk.

## Error UX
- Token expiry: Prompt re‑auth and clear stale token.
- Local dev: If HTTPS fetch fails, hint mkcert/trusted localhost backend setup.

## Next UX Iterations
- Add mini component breakdown (Lineup/Bench/Balance/Bye) inside cards.
- Add position filters and search to Pool.
- Add alternatives ribbon/badge for near‑neutral suggestions.

## Completion Criteria
- Default Yahoo mode shows recommendations list without relying on AI narrative endpoint.
- Users can adjust status and alternatives to refine suggestions.
- No additional sidebar introduced; integrates cleanly with existing app nav.

