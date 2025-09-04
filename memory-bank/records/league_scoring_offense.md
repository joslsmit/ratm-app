# League Scoring (Offense) — Calibration Notes

> Status: Active (2025 season)
> Purpose: Document offensive scoring settings and how deterministic baselines are calibrated to match league rules.

## Offensive Scoring (Yahoo League)
- Passing Yards: 1 pt per 25 yards
- Passing TD: 6 pts
- Interceptions: −1 pt
- Rushing Yards: 1 pt per 10 yards
- Rushing TD: 6 pts
- Receptions (PPR): 1 pt per reception
- Receiving Yards: 1 pt per 10 yards
- Receiving TD: 6 pts
- Return TD: 6 pts
- 2‑Point Conversions: 2 pts
- Fumbles Lost: −2 pts

## Deterministic Engine Calibration
- Weekly projections: Use DynastyProcess weekly PPR projections (r2p_pts). These already reflect PPR=1.0 and the typical stat components (yards, TDs, receptions, INT, etc.).
- Replacement baselines (Bench VOR):
  - QB: 12.0 (calibrated for 6‑pt passing TD league)
  - RB/WR: 7.5
  - TE: 5.0
- Whole‑roster scoring objective:
  - overall = Lineup + 0.7 × BenchVOR + 0.3 × Balance + 0.3 × Bye
  - Balance: small bench composition score (targets QB≤1, RB≥2, WR≥2, TE≥1)
  - Bye: small coverage bonus
- Rationale for QB 12.0 baseline:
  - In 6‑pt passing TD leagues, replacement QBs score higher than in 4‑pt TD formats. Raising the QB baseline from 10 → 12 better normalizes QB bench value, preventing overvaluation of mediocre bench QBs and improving cross‑position decisions.

## Notes
- These baselines remain fixed for the season (per product decision) to match league scoring.
- If we add multi‑league support with different scoring, we will either:
  - Detect pass‑TD value and adjust QB baseline; or
  - Offer a per‑league override; or
  - Compute dynamic baselines from projection distributions.
