# Sit/Start (Lineup) Optimizer — Status & AI Analysis Design

Last Updated: September 5, 2025

## Summary
- Endpoint: `POST /api/optimize_lineup` (Yahoo mode). Suggests starters using weekly projections with strict slot rules; excludes BYE/OUT, flags Q/D; resolves ties with small opponent‑DEF correlation penalty and variance bias if trailing/favored.
- Analysis Output: Now returns both `ai_note` (markdown) and `ai_note_json` (structured) for the most impactful change.

## Deterministic Inputs Available
- From `combined_player_data_cache`: `projected_points`, `weekly_ecr`, `start_sit_grade`, `grade_confidence_score`, `projection_confidence`, `opponent`, `home_away`, `matchup_difficulty`, `weekly_ownership`, `sd_overall`, `team`, `bye_week`.
- From optimizer context: chosen starters by slot, opponent DEF team(s), trailing/favored bias.

## Reason Catalog (Grounded)
- Projection: delta_points = to.wp − from.wp (ECR‑based fallback included).
- Matchup: opponent codes, home/away context; categorical matchup_difficulty (Easy/Moderate/Tough) mapped to a small numeric nudge when the difference is ≥1 step. Text explicitly labels “Easier/Tougher matchup …”.
- Status/Availability: OUT/IR/BYE exclusions; Q/D flags.
- Variance: use `sd_overall` + trailing/favored bias for close calls.
- Correlation: opponent DEF clash (negative), QB stack (positive) on close calls.
- Consensus (ECR semantics): overall ECR across positions; weekly positional rank only within the same position. Never compare positional ranks across positions.
- Context: neutral “Overall ECR” line shown when overall ECR exists for both players but the gap is below threshold.

## Confidence Heuristic
- High: δ ≥ 2.0
- Medium: 0.5 ≤ δ < 2.0
- Low: δ < 0.5
- Downgrade with Q/D; minor upgrade if from‑player is BYE/OUT.

## JSON Schema
```
{
  "confidence": "High|Medium|Low",
  "headline": "Start X over Y at SLOT (+N.N pts)",
  "reasons": [
    { "type": "Projection|Matchup|Status|Variance|Correlation|FlexAllocation|Consensus|Usage|Confidence|Context", "text": "short sentence", "evidence": { /* numbers/flags */ } }
  ],
  "tags": ["Projection Edge", "Favorable Matchup", "Correlation Risk", "Variance Bias"],
  "score_breakdown": { "projection": number, "matchup": number, "correlation": number, "variance": number }
}
```

## Model Usage (Safe Rewriter)
- We compute headline + reason candidates deterministically. Gemini may paraphrase/select up to 3 reasons. It must return the exact JSON structure. If model fails or key missing, we fall back to deterministic JSON.

## Example
```
{
  "confidence": "Medium",
  "headline": "Start Rashid Shaheed over Zach Charbonnet at W/R/T (+1.4 pts)",
  "reasons": [
    { "type": "Projection", "text": "Projection edge of +1.4 points.", "evidence": { "delta_points": 1.4 } },
    { "type": "Matchup", "text": "Shaheed vs ARI (HOME) vs Charbonnet vs SF (HOME).", "evidence": { "to_opp": "ARI", "from_opp": "SF", "to_ha": "HOME", "from_ha": "HOME" } }
  ],
  "tags": ["Projection Edge", "Favorable Matchup"],
  "score_breakdown": { "projection": 1.4, "matchup": 0.10, "correlation": 0.0, "variance": 0.0 }
}
```

## Notes
- UI renders `ai_note_json` directly: chips for tags, a score row, and typed reasons with clarified labels (e.g., “Overall ECR”). Legacy markdown is hidden.
- No hallucinations: all facts derive from deterministic inputs; the model may only rephrase.
