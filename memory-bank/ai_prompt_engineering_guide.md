# AI Prompt Engineering Guide: RATM Draft Kit

## Overview
This document provides comprehensive guidance for improving AI prompt engineering in RATM Draft Kit, transforming from current problematic patterns to industry best practices that deliver consistent, high-quality fantasy football analysis.

## Current State Analysis

### Current Problematic Pattern
```python
# PROBLEMATIC: Current approach across all endpoints
prompt = f"{PROMPT_PREAMBLE}\n\n**Task:** [200+ word verbose description with conflicting instructions]...\n\n**Data:**\n{unstructured_context}\n\n{JSON_OUTPUT_INSTRUCTION}"
```

**Issues with Current Approach:**
- Truncated base prompts (PROMPT_PREAMBLE ends with "...")
- No examples or guidance for AI behavior
- Verbose, repetitive task descriptions
- Inconsistent JSON schemas across endpoints
- No chain-of-thought reasoning structure
- Poor context formatting

## Prompt Engineering Best Practices

### 1. System Prompt Architecture

#### **A. Complete System Prompt (Replace PROMPT_PREAMBLE)**

```python
SYSTEM_PROMPT = """You are 'The Analyst' - an expert fantasy football advisor specializing in data-driven analysis for the 2025 NFL season.

CONTEXT & EXPERTISE:
- League Format: 12-team, PPR scoring, standard Yahoo rules
- Season: 2025 NFL season with current roster compositions and projections
- Analysis Philosophy: Objective, data-driven, actionable insights based on ECR, trends, and situational factors
- Knowledge Base: Expert consensus rankings, player roles, injury history, team contexts, and performance metrics

PERSONALITY & STYLE:
- Professional and analytical tone
- Concise but thorough explanations
- Clear, actionable recommendations
- Acknowledge uncertainty when data is limited
- Focus on practical fantasy impact over speculation

ANALYTICAL FRAMEWORK:
- Evaluate players based on role security, talent, opportunity, and team context
- Consider short-term vs long-term value appropriately
- Factor in injury risk, bye weeks, and schedule strength
- Compare to positional peers and draft cost/availability
- Provide confidence-calibrated recommendations

RESPONSE CONSTRAINTS:
- Always provide confidence scores (0.0-1.0 scale) with reasoning
- Include specific reasoning for all recommendations
- Format responses as valid JSON only
- Use markdown formatting within analysis sections
- Ground analysis in provided data, clearly noting when speculating"""
```

#### **B. Structured JSON Output Schema (Replace JSON_OUTPUT_INSTRUCTION)**

```python
JSON_OUTPUT_SCHEMA = """RESPONSE FORMAT REQUIREMENTS:
Your response MUST be a valid JSON object with exactly these keys:
{
  "confidence": float (0.0-1.0 scale),
  "analysis": string (markdown-formatted analysis with clear headers),
  "reasoning": string (brief explanation of confidence score),
  "key_factors": array of strings (3-5 main factors influencing analysis),
  "recommendation": string ("STRONG BUY" | "BUY" | "HOLD" | "SELL" | "AVOID" or context-appropriate)
}

CONFIDENCE SCORING CRITERIA:
- 0.9-1.0: High-quality data, clear role, established track record, strong consensus
- 0.7-0.8: Good data quality, minor uncertainties in role/performance projections  
- 0.5-0.6: Limited data, significant variables, moderate uncertainty in projections
- 0.3-0.4: Poor data quality, high uncertainty, speculative analysis, conflicting signals
- 0.0-0.2: Insufficient data, extreme uncertainty, avoid making recommendations

ANALYSIS STRUCTURE:
Use clear markdown headers (###) for sections. Include specific data points and reasoning.
Avoid generic statements - be specific about why factors matter for fantasy football.

CRITICAL: Ensure perfect JSON syntax - proper quotes, commas, no trailing commas, escaped quotes in strings."""
```

### 2. Task-Specific Prompt Templates

#### **A. Player Analysis Template**

```python
def build_player_analysis_prompt(player_data: str, analysis_type: str = "comprehensive") -> str:
    
    examples = {
        "comprehensive": """
EXAMPLE INPUT:
Christian McCaffrey (RB, SF) - ECR Overall: 2.1, SD: 1.2, Best: 1, Worst: 5, Bye Week: 9

EXAMPLE OUTPUT:
{
  "confidence": 0.85,
  "analysis": "### Role & Opportunity\\nEstablished RB1 with bellcow usage averaging 20+ touches per game. Consistent target share in passing game provides high floor.\\n\\n### Value Analysis\\nFirst-round ADP justified by elite dual-threat ceiling. ECR of 2.1 reflects consensus top-3 finish potential.\\n\\n### Risk Assessment\\nInjury history (2020-2021 seasons) creates some durability concerns. Age 29 season introduces potential decline risk.\\n\\n### Fantasy Verdict\\nElite RB1 with proven track record. High-floor, high-ceiling option worth early investment despite injury history.",
  "reasoning": "High confidence based on established role and proven production, but injury history prevents perfect score",
  "key_factors": ["Bellcow usage", "Dual-threat ability", "Injury history", "Age considerations"],
  "recommendation": "BUY"
}
"""
    }
    
    return f"""{SYSTEM_PROMPT}

TASK: Comprehensive Player Analysis
Analyze the following player for fantasy football purposes. Provide detailed evaluation with structured sections.

ANALYSIS SECTIONS REQUIRED:
### Role & Opportunity - Current position, target share, snap count trends
### Value Analysis - ECR vs expected performance, draft cost considerations  
### Risk Assessment - Injury concerns, role competition, volatility factors
### Fantasy Verdict - Clear recommendation with supporting reasoning

{examples[analysis_type]}

PLAYER TO ANALYZE:
{player_data}

{JSON_OUTPUT_SCHEMA}"""
```

#### **B. Trade Analysis Template**

```python
def build_trade_analysis_prompt(my_assets: str, their_assets: str, league_context: str = "") -> str:
    
    example = """
EXAMPLE TRADE:
My Team Receives: Tyreek Hill (WR, MIA) - ECR: 8.5
Other Team Receives: Kenneth Walker III (RB, SEA) - ECR: 18.2, D'Andre Swift (RB, PHI) - ECR: 24.1

EXAMPLE OUTPUT:
{
  "confidence": 0.8,
  "analysis": "### Value Calculation\\nMy Team: Tyreek Hill (~8.5 ECR value)\\nOther Team: Walker (~18.2) + Swift (~24.1) = Combined ~21-22 value\\n\\n### Positional Impact\\nTrading for elite WR1 but giving up RB depth. Walker provides RB1 upside, Swift offers flex/RB2 value.\\n\\n### Trade Verdict\\nOther team wins on pure value. Receiving two startable players for one elite asset provides better roster construction flexibility.",
  "reasoning": "Clear value disparity favoring the two-player side, supported by ECR differential",
  "key_factors": ["ECR value gap", "Positional scarcity", "Roster construction", "Depth vs elite talent"],
  "recommendation": "REJECT - Other team wins"
}
"""

    return f"""{SYSTEM_PROMPT}

TASK: Trade Analysis
Analyze this trade from "My Team" perspective. Calculate value, assess positional impact, and declare a clear winner.

ANALYSIS METHODOLOGY:
1. Calculate total ECR value for each side
2. Consider positional scarcity and depth implications
3. Evaluate short-term vs long-term impact
4. Account for injury risk and schedule factors
5. Declare clear winner with confidence level

{example}

TRADE TO ANALYZE:
Assets My Team Receives: {my_assets}
Assets Other Team Receives: {their_assets}
League Context: {league_context}

{JSON_OUTPUT_SCHEMA}"""
```

#### **C. Waiver Wire Template**

```python
def build_waiver_analysis_prompt(player_to_add: str, roster_context: str, drop_candidates: str) -> str:
    
    example = """
EXAMPLE SCENARIO:
Player to Add: Jaylen Warren (RB, PIT) - ECR: 45.2, trending up after injury to starter
My Roster: [roster with RB depth issues]
Drop Candidates: Tank Bigsby (RB, JAX) - ECR: 78.5, backup role

EXAMPLE OUTPUT:
{
  "confidence": 0.75,
  "analysis": "### Waiver Candidate Assessment\\nJaylen Warren offers immediate upside with starter injured. Proven backup production with 3-down capability.\\n\\n### Roster Fit Analysis\\nRB position is thin - need depth behind starters. Warren provides better floor than current bench options.\\n\\n### Drop Recommendation\\nTank Bigsby is clear drop candidate. Lower ECR, less defined role, inferior opportunity.\\n\\n### Waiver Priority\\nHigh priority add. Warren's opportunity + talent combination offers significant upside over replacement level.",
  "reasoning": "Strong opportunity-based pickup with clear drop candidate available",
  "key_factors": ["Opportunity increase", "Talent vs replacement", "Positional need", "Drop candidate quality"],
  "recommendation": "ADD - Drop Tank Bigsby"
}
"""

    return f"""{SYSTEM_PROMPT}

TASK: Waiver Wire Analysis
Evaluate adding the specified player and recommend who to drop from current roster.

ANALYSIS FRAMEWORK:
1. Assess waiver candidate's opportunity and role
2. Evaluate roster fit and positional need
3. Compare to current bench players
4. Recommend specific drop candidate
5. Assign waiver priority level

{example}

WAIVER SCENARIO:
Player to Add: {player_to_add}
Current Roster: {roster_context}
Potential Drops: {drop_candidates}

{JSON_OUTPUT_SCHEMA}"""
```

### 3. Context Formatting Best Practices

#### **A. Player Data Formatting**

```python
def format_player_context_optimal(player_data: dict, analysis_type: str) -> str:
    """Format player data for optimal AI consumption based on analysis type."""
    
    # Base information (always included)
    base_info = f"""PLAYER: {player_data.get('name', 'Unknown')}
POSITION: {player_data.get('position', 'N/A')}  
TEAM: {player_data.get('team', 'N/A')}
EXPERIENCE: {player_data.get('years_exp', 'N/A')} years
ROOKIE: {'Yes' if player_data.get('is_rookie') else 'No'}"""

    # Context-specific metrics
    if analysis_type == 'draft':
        return f"""{base_info}

DRAFT METRICS:
- Overall ECR: {player_data.get('ecr_overall', 'N/A')}
- Standard Deviation: {player_data.get('sd_overall', 'N/A')} (consensus level)
- Expert Range: {player_data.get('best_overall', 'N/A')} to {player_data.get('worst_overall', 'N/A')}
- Recent Trend: {player_data.get('rank_delta_overall', 'N/A')} (1-week change)
- Bye Week: {player_data.get('bye_week', 'N/A')}

CONTEXT: Lower ECR = Better ranking. SD shows consensus (lower = more agreement)."""

    elif analysis_type == 'waiver':
        return f"""{base_info}

WAIVER METRICS:
- Overall ECR: {player_data.get('ecr_overall', 'N/A')}
- Recent Trend: {player_data.get('rank_delta_overall', 'N/A')} (rising/falling)
- Opportunity Score: {calculate_opportunity_score(player_data)}
- Add/Drop Trend: {player_data.get('add_trend', 'N/A')}

CONTEXT: Focus on opportunity changes and recent performance trends."""
    
    return base_info

def calculate_opportunity_score(player_data: dict) -> str:
    """Calculate opportunity-based scoring for waiver analysis."""
    # Implementation based on role, team context, injuries, etc.
    return "Medium-High"  # Placeholder
```

#### **B. Anti-Patterns to Avoid**

```python
# ❌ BAD: Verbose, unstructured prompt
prompt = f"""
You are an expert fantasy football analyst. Please analyze this player very carefully and thoroughly. 
Consider all aspects including their performance, team situation, injury history, and any other 
relevant factors. Make sure to provide a detailed analysis that covers multiple perspectives and 
gives a comprehensive view of the player's fantasy value. Please be very specific and detailed 
in your analysis and make sure to consider both positive and negative aspects.

Player: {player_name}
Data: {raw_data_dump}

Please respond with a JSON object containing your analysis...
"""

# ✅ GOOD: Structured, specific prompt
prompt = f"""{SYSTEM_PROMPT}

TASK: Player Analysis
Analyze for fantasy football value using structured evaluation framework.

REQUIRED SECTIONS:
### Role Security - Snap share, target share, competition
### Performance Metrics - Recent stats, efficiency, trends  
### Value Assessment - ECR vs projected performance
### Risk Factors - Injury, age, role changes

PLAYER DATA:
{formatted_player_context}

{JSON_OUTPUT_SCHEMA}"""
```

### 4. Chain-of-Thought Implementation

#### **A. Reasoning Chain Template**

```python
def add_reasoning_chain(prompt: str, analysis_type: str) -> str:
    """Add structured reasoning guidance to prompts."""
    
    reasoning_frameworks = {
        'player_analysis': """
REASONING FRAMEWORK - Follow this thinking process:
1. ROLE EVALUATION: What is their current role? How secure is it?
2. TALENT ASSESSMENT: What does their skillset suggest about ceiling/floor?
3. OPPORTUNITY ANALYSIS: What volume/targets can we expect?
4. COMPETITION FACTORS: Who threatens their role or opportunity?
5. TEAM CONTEXT: How does coaching/system affect their value?
6. RISK ASSESSMENT: What could go wrong? Injury, regression, role loss?
7. VALUE CONCLUSION: Where should they be drafted/how much to pay?
""",
        'trade_analysis': """
REASONING FRAMEWORK - Evaluate step by step:
1. ECR VALUE CALCULATION: Sum total ECR value for each side
2. POSITIONAL IMPACT: How does this affect positional depth?
3. UPSIDE COMPARISON: Which side has better ceiling outcomes?
4. FLOOR COMPARISON: Which side has safer projected outcomes?
5. ROSTER CONSTRUCTION: Does this improve or hurt team building?
6. TIMING FACTORS: Short vs long-term impact analysis
7. WINNER DETERMINATION: Clear verdict with confidence level
"""
    }
    
    if analysis_type in reasoning_frameworks:
        return f"{prompt}\n\n{reasoning_frameworks[analysis_type]}"
    
    return prompt
```

### 5. Few-Shot Learning Examples

#### **A. High-Quality Example Library**

```python
class FantasyAnalysisExamples:
    """Curated examples for different analysis types."""
    
    PLAYER_ANALYSIS_EXAMPLES = {
        'established_star': {
            'input': "Josh Allen (QB, BUF) - ECR: 1.2, SD: 0.8, Best: 1, Worst: 3",
            'output': {
                'confidence': 0.95,
                'analysis': "### Role Security\nUndisputed QB1 with elite rushing upside. No competition for touches or targets.\n\n### Performance Metrics\nConsistent QB1 finishes with 4,000+ passing yards and 15+ rushing TDs. Top-3 QB scorer in 4 of last 5 seasons.\n\n### Value Assessment\nECR 1.2 reflects elite tier status. Worth first overall pick in superflex, early 2nd round in 1QB.\n\n### Risk Factors\nMinimal injury concerns. Age 29 entering prime years. Offensive system stable with familiar weapons.",
                'reasoning': "Extremely high confidence due to established track record, clear role, and minimal risk factors",
                'key_factors': ["Elite dual-threat ability", "Established track record", "Stable offensive system", "Minimal competition"],
                'recommendation': "STRONG BUY"
            }
        },
        'rookie_uncertainty': {
            'input': "Marvin Harrison Jr. (WR, ARI) - ECR: 15.2, SD: 8.4, Best: 8, Worst: 28, Rookie: Yes",
            'output': {
                'confidence': 0.6,
                'analysis': "### Role Security\nProjected WR1 but rookie transition always uncertain. Competing with established targets for shares.\n\n### Performance Metrics\nElite college production but no NFL data. High draft capital suggests immediate opportunity.\n\n### Value Assessment\nECR 15.2 prices in WR2 expectations. Significant bust/boom range reflected in wide expert rankings.\n\n### Risk Factors\nRookie learning curve, quarterback uncertainty, and acclimation to NFL speed and physicality.",
                'reasoning': "Moderate confidence due to high talent but significant rookie uncertainty and wide expert disagreement",
                'key_factors': ["Elite college profile", "Rookie uncertainty", "QB situation", "Wide expert range"],
                'recommendation': "HOLD"
            }
        }
    }
    
    TRADE_ANALYSIS_EXAMPLES = {
        'value_vs_depth': {
            'input': {
                'my_team_receives': "Christian McCaffrey (RB, SF) - ECR: 2.1",
                'other_team_receives': "Saquon Barkley (RB, PHI) - ECR: 8.2, Chris Olave (WR, NO) - ECR: 18.5"
            },
            'output': {
                'confidence': 0.85,
                'analysis': "### Value Calculation\nMy Side: CMC (~2.1 value)\nOther Side: Saquon (~8.2) + Olave (~18.5) = ~13-14 combined value\n\n### Positional Impact\nTrading elite RB1 for solid RB1 + WR2. Improves depth but loses ceiling.\n\n### Risk Assessment\nCMC injury history vs Saquon's durability concerns. Olave adds consistent WR production.\n\n### Trade Verdict\nOther team wins on total value. Two quality starters > one elite player for depth-building.",
                'reasoning': "Clear value advantage to other side, supported by significant ECR differential",
                'key_factors': ["ECR value disparity", "Elite vs depth trade-off", "Injury risk profiles", "Positional upgrading"],
                'recommendation': "REJECT - Other team wins"
            }
        }
    }
```

### 6. Quality Assurance Framework

#### **A. Response Validation Checklist**

```python
def validate_prompt_quality(prompt: str) -> dict:
    """Validate prompt against quality criteria."""
    
    quality_criteria = {
        'has_clear_task': 'TASK:' in prompt,
        'has_examples': 'EXAMPLE' in prompt,
        'has_structure': '###' in prompt or 'SECTIONS:' in prompt,
        'has_reasoning': 'REASONING' in prompt or 'FRAMEWORK' in prompt,
        'has_json_schema': 'JSON' in prompt and 'confidence' in prompt,
        'length_appropriate': 1000 <= len(prompt) <= 3000,
        'specific_instructions': any(word in prompt.lower() for word in ['specific', 'detailed', 'clear']),
        'context_formatted': 'PLAYER:' in prompt or 'CONTEXT:' in prompt
    }
    
    score = sum(quality_criteria.values()) / len(quality_criteria)
    
    return {
        'quality_score': score,
        'criteria_met': quality_criteria,
        'recommendations': generate_improvement_recommendations(quality_criteria)
    }

def generate_improvement_recommendations(criteria: dict) -> list:
    """Generate specific recommendations for prompt improvement."""
    recommendations = []
    
    if not criteria['has_examples']:
        recommendations.append("Add few-shot examples to guide AI behavior")
    if not criteria['has_structure']:
        recommendations.append("Include required section headers or structure")
    if not criteria['has_reasoning']:
        recommendations.append("Add reasoning framework or chain-of-thought guidance")
    if not criteria['context_formatted']:
        recommendations.append("Format context data with clear labels and structure")
        
    return recommendations
```

### 7. Testing and Iteration Framework

#### **A. A/B Testing Setup**

```python
class PromptTestingFramework:
    """Framework for testing prompt improvements."""
    
    def test_prompt_versions(self, old_prompt: str, new_prompt: str, test_cases: list) -> dict:
        """Compare performance between prompt versions."""
        
        results = {
            'old_prompt_scores': [],
            'new_prompt_scores': [],
            'improvement_metrics': {}
        }
        
        for test_case in test_cases:
            # Test old prompt
            old_response = self.generate_response(old_prompt, test_case['input'])
            old_score = self.score_response(old_response, test_case['expected'])
            results['old_prompt_scores'].append(old_score)
            
            # Test new prompt  
            new_response = self.generate_response(new_prompt, test_case['input'])
            new_score = self.score_response(new_response, test_case['expected'])
            results['new_prompt_scores'].append(new_score)
        
        # Calculate improvements
        old_avg = sum(results['old_prompt_scores']) / len(results['old_prompt_scores'])
        new_avg = sum(results['new_prompt_scores']) / len(results['new_prompt_scores'])
        
        results['improvement_metrics'] = {
            'old_average': old_avg,
            'new_average': new_avg,
            'improvement_percentage': ((new_avg - old_avg) / old_avg) * 100,
            'statistically_significant': self.significance_test(
                results['old_prompt_scores'], 
                results['new_prompt_scores']
            )
        }
        
        return results
    
    def score_response(self, response: dict, expected: dict) -> float:
        """Score response quality against expected criteria."""
        criteria_scores = []
        
        # JSON validity
        criteria_scores.append(1.0 if self.is_valid_json(response) else 0.0)
        
        # Confidence reasonableness  
        if 'confidence' in response:
            conf = response['confidence']
            criteria_scores.append(1.0 if 0.0 <= conf <= 1.0 else 0.0)
        
        # Analysis completeness
        if 'analysis' in response:
            criteria_scores.append(self.analyze_completeness(response['analysis']))
        
        # Recommendation clarity
        if 'recommendation' in response:
            criteria_scores.append(self.analyze_recommendation_clarity(response['recommendation']))
            
        return sum(criteria_scores) / len(criteria_scores)
```

## Implementation Priority

### Phase 1: Core Prompt Reconstruction (Week 1)
1. Replace truncated PROMPT_PREAMBLE with complete SYSTEM_PROMPT
2. Replace truncated JSON_OUTPUT_INSTRUCTION with structured schema
3. Update all 13 endpoints with new base prompts

### Phase 2: Template System (Week 2)
1. Implement PromptBuilder class with task-specific templates
2. Add few-shot examples for each analysis type
3. Create context formatting functions

### Phase 3: Advanced Techniques (Week 3-4)
1. Add chain-of-thought reasoning frameworks
2. Implement response validation and quality scoring
3. Deploy A/B testing framework for prompt optimization

## Expected Outcomes

- **40-60% improvement** in response relevance and consistency
- **95%+ valid JSON** responses across all endpoints  
- **Consistent confidence calibration** aligned with actual accuracy
- **Reduced user confusion** from clear, structured analysis
- **Faster development** of new AI features using template system

This guide provides the foundation for transforming RATM's AI from basic text generation into sophisticated, reliable fantasy football analysis that users can trust and act upon.