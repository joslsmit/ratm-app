"""
Few-Shot Examples Library for Advanced Prompt Engineering

High-quality examples that guide AI behavior and demonstrate proper response formatting
for different fantasy football analysis types.

Phase 0B Implementation: Comprehensive example library with realistic scenarios.
"""

from typing import Dict, List, Any


class ExampleLibrary:
    """Library of high-quality few-shot examples for different analysis types."""
    
    # Player Analysis Examples - Show proper structure and reasoning
    PLAYER_ANALYSIS_EXAMPLES = [
        {
            "input": "Christian McCaffrey (RB, SF) - ECR: 1.8, SD: 1.2, Best: 1, Worst: 4, Team: San Francisco 49ers, Bye Week: 9, Years Experience: 8, Rookie: No",
            "output": {
                "confidence": "High",
                "analysis": """### Depth Chart Role
Undisputed RB1 with elite bellcow usage in Kyle Shanahan's run-heavy system. Zero competition for touches with clear three-down role including goal-line and receiving work.

### Value Analysis  
ECR of 1.8 reflects consensus as the #1 fantasy RB. Justified by elite dual-threat ability - only player capable of 1,000+ rushing and 500+ receiving yards. Premium draft cost warranted by ceiling and floor combination.

### Risk Factors
**Injury History Concerns**: Missed significant time in 2020-2021 with ankle/hamstring issues. Age 28 entering 2025 season puts him at traditional RB decline phase. Heavy workload could increase injury risk.

### 2025 Outlook
Projected for 250+ carries and 60+ targets in Shanahan's offense. Should lead all RBs in total touches. Excellent offensive line and QB play support efficiency. Clear RB1 overall if healthy.

### Final Verdict
**DRAFT CONFIDENTLY**: Elite floor/ceiling combination with minimal competition. Injury history creates some uncertainty, but when healthy he's unmatched at the position. Worth #1 overall pick in most formats."""
            }
        },
        {
            "input": "Marvin Harrison Jr. (WR, ARI) - ECR: 24.3, SD: 8.7, Best: 12, Worst: 45, Team: Arizona Cardinals, Bye Week: 11, Years Experience: 1, Rookie: Yes",
            "output": {
                "confidence": "Medium", 
                "analysis": """### Depth Chart Role
Projected WR1 for Arizona with immediate target share. Exceptional college production suggests NFL-ready skill set, but rookie WR adjustment period is common even for elite prospects.

### Value Analysis
ECR in the 24 range reflects cautious optimism around rookie receiver. High draft capital (4th overall pick) indicates team commitment. Range from pick 12-45 shows significant expert disagreement on rookie timeline.

### Risk Factors  
**Rookie Uncertainty**: No NFL experience creates unknown variables. Cardinals offensive system and QB play (Kyler Murray) add complexity. Wide standard deviation indicates expert uncertainty about floor/ceiling.

### 2025 Outlook
Cardinals likely to feature him heavily despite rookie status. Excellent route-running and size suggest faster NFL adjustment than typical. Should see 100+ targets if healthy, but efficiency questions remain.

### Final Verdict
**CALCULATED RISK**: Elite talent with first-round draft capital, but rookie variables create uncertainty. Best suited for teams willing to accept inconsistency for upside. Consider in rounds 3-4 based on risk tolerance."""
            }
        },
        {
            "input": "Gardner Minshew (QB, LV) - ECR: 187.5, SD: 15.2, Best: 142, Worst: 234, Team: Las Vegas Raiders, Bye Week: 10, Years Experience: 6, Rookie: No",
            "output": {
                "confidence": "Low",
                "analysis": """### Depth Chart Role
Backup QB with limited starting opportunities unless injury occurs to primary starter. Historical role as capable fill-in but not long-term starter material for most teams.

### Value Analysis
ECR near 187 reflects streaming/backup QB status. Wide range (142-234) indicates even experts unsure of his 2025 role and opportunity. Very late draft consideration only.

### Risk Factors
**Limited Opportunity**: Unlikely to see consistent starting time. When he does start, typically shows decent production but inconsistent week-to-week. Team situation in flux adds uncertainty.

### 2025 Outlook
Realistic ceiling is 8-10 starts if injury occurs ahead of him. Has shown 250+ yard passing ability and rushing upside in spot starts. Better real-life QB than fantasy asset due to opportunity limitations.

### Final Verdict
**AVOID IN DRAFTS**: Only draft as 3rd QB in superflex leagues or deep 2-QB formats. Better to stream during bye weeks or injury situations. No standalone value in standard leagues."""
            }
        }
    ]
    
    # Trade Analysis Examples - Show clear winner determination
    TRADE_ANALYSIS_EXAMPLES = [
        {
            "input": {
                "my_team_receives": "Tyreek Hill (WR, MIA) - ECR: 8.5, SD: 3.2",
                "other_team_receives": "Kenneth Walker III (RB, SEA) - ECR: 18.2, SD: 5.1 + D'Andre Swift (RB, PHI) - ECR: 24.1, SD: 7.8"
            },
            "output": {
                "confidence": "High",
                "analysis": """**WINNER: Other Team**

### Value Calculation
- My side: Tyreek Hill (ECR 8.5) = Elite WR1 value
- Their side: Kenneth Walker III (18.2) + D'Andre Swift (24.1) = RB2 + Flex value

**Total ECR Value**: Hill (8.5) vs Walker + Swift (combined ~21 average) = Roughly even on paper

### Positional Scarcity Analysis  
**Critical Factor**: RB scarcity heavily favors the two-RB side. Elite RBs are harder to find and replace than WRs. Swift and Walker both have clear starting roles with upside.

### Short-term vs Long-term Impact
- **Short-term**: Hill provides consistent WR1 production immediately
- **Long-term**: Two young RBs provide more roster flexibility and combined upside

### Risk Assessment
Hill has age concerns (30+) while Walker (24) and Swift (25) are in their primes. Injury to Hill devastates value, while having two RBs provides insurance.

### Final Verdict
The combination of positional scarcity, age curves, and total value strongly favors receiving two productive RBs over one aging (albeit elite) WR. This is a clear loss for the Hill side."""
            }
        },
        {
            "input": {
                "my_team_receives": "Josh Allen (QB, BUF) - ECR: 1.2 + 2025 3rd Round Pick",
                "other_team_receives": "Lamar Jackson (QB, BAL) - ECR: 2.1 + Travis Kelce (TE, KC) - ECR: 12.5 + DeAndre Hopkins (WR, TEN) - ECR: 45.8"
            },
            "output": {
                "confidence": "High", 
                "analysis": """**WINNER: Other Team (By A Landslide)**

### Value Calculation Disaster
- My side: Josh Allen (1.2) + 3rd round pick (~30 value) = ~16 total value
- Their side: Lamar (2.1) + Kelce (12.5) + Hopkins (45.8) = ~20 combined value + massive depth

**This is not even close** - I'm giving up similar QB production plus getting fleeced on total value.

### Positional Impact Analysis
- **QB Swap**: Allen to Lamar is minimal downgrade (both elite dual-threat QBs)
- **Receiving Haul**: Getting Kelce (TE1) + Hopkins (solid WR3) is massive value addition
- **Roster Construction**: They get elite TE + viable WR while I get marginal QB upgrade

### Strategic Blunder Assessment  
This trade makes zero sense from any angle:
1. **Value**: Massively losing on total player value
2. **Depth**: Giving up depth for marginal improvement
3. **Positional Needs**: Unless I desperately need QB help, this is terrible asset management

### Final Verdict
**REJECT IMMEDIATELY**: This is one of the worst trade proposals possible. The other team is trying to fleece you. Allen and Lamar are nearly identical in value, but you're throwing in enormous additional assets for essentially nothing. Never make this trade under any circumstances."""
            }
        },
        {
            "input": {
                "my_team_receives": "Saquon Barkley (RB, PHI) - ECR: 6.2 + Malik Nabers (WR, NYG) - ECR: 28.7",
                "other_team_receives": "Ja'Marr Chase (WR, CIN) - ECR: 3.8 + James Conner (RB, ARI) - ECR: 42.5"
            },
            "output": {
                "confidence": "Medium",
                "analysis": """**WINNER: My Team (Slight Edge)**

### Value Assessment
- My side: Barkley (6.2) + Nabers (28.7) = RB1 + emerging WR2
- Their side: Chase (3.8) + Conner (42.5) = Elite WR1 + aging RB3

**Raw Value**: Slightly favors Chase side, but situational factors matter significantly.

### Age and Trajectory Analysis
**Favor My Side**:
- Barkley (27): Fresh start in Eagles system, should bounce back
- Nabers (22): Rising young WR with high target ceiling

**Favor Their Side**:
- Chase (25): Proven elite WR1 in prime years
- Conner (29): Declining, injury-prone veteran

### Positional Scarcity Considerations
Trading elite WR1 (Chase) for RB1 + WR2 combo provides better roster balance. RB production harder to replace than single elite WR, especially with emerging receiver like Nabers.

### Risk Evaluation  
**My Risks**: Barkley age concerns, Nabers sophomore development
**Their Risks**: Conner durability, over-reliance on Chase for WR production

### Final Verdict
**SLIGHT WIN**: The combination of positional value (RB1 + emerging WR) outweighs single elite WR + aging RB. Barkley's change of scenery upside and Nabers' growth trajectory create more total value than Chase alone can provide."""
            }
        }
    ]
    
    # Keeper Analysis Examples - Show value-based decision making
    KEEPER_ANALYSIS_EXAMPLES = [
        {
            "input": "Puka Nacua (WR, LAR) - ECR: 15.8, Keeper Cost: 8th Round (Pick 96), Contract: 2 years remaining",
            "output": {
                "confidence": "High",
                "analysis": """### Keeper Value Assessment
**Market Value**: ECR 15.8 projects to ~2nd round pick (pick 20-24 range)
**Keeper Cost**: 8th round pick (96th overall)
**Value Surplus**: Getting ~2nd round production for 8th round cost = **6+ rounds of value**

### Player Evaluation
Elite target share in Sean McVay's system with established role alongside Cooper Kupp. Sophomore breakout sustainable given route-running ability and red zone usage. Minimal competition for targets.

### Contract Analysis  
Two-year keeper window provides excellent value runway. Can keep at 8th round cost this year, then 7th round cost next year - both significantly below market value.

### Opportunity Cost
Keeping Nacua in 8th round allows drafting another position of need earlier. The 6+ rounds of surplus value is exceptional keeper return.

### Final Verdict
**KEEP IMMEDIATELY**: This is textbook keeper value - proven WR2 production at WR4 draft cost. One of the best keeper values available. The surplus value alone justifies the decision."""
            }
        }
    ]
    
    # Positional Tier Examples - Show grouping methodology
    TIER_ANALYSIS_EXAMPLES = [
        {
            "input": "QB Tier Analysis: Josh Allen, Lamar Jackson, Jalen Hurts, Dak Prescott, Anthony Richardson",
            "output": {
                "confidence": "High",
                "analysis": """### Tier 1: Elite Dual-Threat (Picks 1-3)
**Josh Allen, Lamar Jackson**
- Proven rushing floors (600+ yards) with elite passing upside
- Weekly league-winning ceiling with 30+ point games
- Minimal risk of losing starting job or significant role change

### Tier 2: High-End QB1 with Questions (Picks 4-6)  
**Jalen Hurts**
- Elite rushing production but passing efficiency concerns
- TD regression risk after historically high red zone rushing TDs
- Still top-6 ceiling but more volatile week-to-week

### Tier 3: Traditional Pocket Passers (Picks 7-10)
**Dak Prescott** 
- High-volume passing with solid TD upside
- Limited rushing floor creates weekly volatility
- Dependable QB1 but lower ceiling than dual-threat QBs

### Tier 4: High-Risk, High-Reward (Picks 11-15)
**Anthony Richardson**
- Massive dual-threat ceiling if development continues
- Significant bust risk due to accuracy and durability concerns  
- Best suited for teams willing to accept volatility for league-winning upside

### Drafting Strategy
Target one QB from Tier 1-2 in rounds 2-4, then wait until rounds 10+ for backup. Avoid reaching for Tier 3-4 QBs ahead of skilled position depth."""
            }
        }
    ]

    @staticmethod
    def get_examples_for_analysis_type(analysis_type: str) -> List[Dict[str, Any]]:
        """Get relevant examples for a specific analysis type."""
        
        example_map = {
            'player_analysis': ExampleLibrary.PLAYER_ANALYSIS_EXAMPLES,
            'player_dossier': ExampleLibrary.PLAYER_ANALYSIS_EXAMPLES,
            'trade_analysis': ExampleLibrary.TRADE_ANALYSIS_EXAMPLES,
            'trade_analyzer': ExampleLibrary.TRADE_ANALYSIS_EXAMPLES,  
            'keeper_analysis': ExampleLibrary.KEEPER_ANALYSIS_EXAMPLES,
            'keeper_evaluator': ExampleLibrary.KEEPER_ANALYSIS_EXAMPLES,
            'tier_analysis': ExampleLibrary.TIER_ANALYSIS_EXAMPLES,
            'generate_tiers': ExampleLibrary.TIER_ANALYSIS_EXAMPLES
        }
        
        return example_map.get(analysis_type, ExampleLibrary.PLAYER_ANALYSIS_EXAMPLES[:1])
    
    @staticmethod
    def get_random_example(analysis_type: str) -> Dict[str, Any]:
        """Get a single random example for the specified analysis type."""
        import random
        
        examples = ExampleLibrary.get_examples_for_analysis_type(analysis_type)
        return random.choice(examples) if examples else {}
    
    @staticmethod  
    def format_example_for_prompt(example: Dict[str, Any]) -> str:
        """Format an example for inclusion in a prompt."""
        
        if not example:
            return ""
            
        if 'input' in example and 'output' in example:
            # Standard player/keeper analysis format
            return f"""EXAMPLE INPUT: {example['input']}

EXAMPLE OUTPUT: {example['output']}"""
        
        elif 'my_team_receives' in example['input']:
            # Trade analysis format
            input_data = example['input']
            return f"""EXAMPLE TRADE:
My Team Receives: {input_data['my_team_receives']}
Other Team Receives: {input_data['other_team_receives']}

EXAMPLE ANALYSIS: {example['output']}"""
        
        return str(example)


# Test function to validate examples
def test_example_library():
    """Test the example library functionality."""
    
    # Test getting examples for different analysis types
    player_examples = ExampleLibrary.get_examples_for_analysis_type('player_analysis')
    trade_examples = ExampleLibrary.get_examples_for_analysis_type('trade_analysis') 
    keeper_examples = ExampleLibrary.get_examples_for_analysis_type('keeper_analysis')
    
    # Test random example selection
    random_player = ExampleLibrary.get_random_example('player_dossier')
    random_trade = ExampleLibrary.get_random_example('trade_analyzer')
    
    # Test example formatting
    formatted_example = ExampleLibrary.format_example_for_prompt(player_examples[0])
    
    return {
        'player_examples_count': len(player_examples),
        'trade_examples_count': len(trade_examples),
        'keeper_examples_count': len(keeper_examples),
        'random_player_confidence': random_player.get('output', {}).get('confidence', 'Unknown'),
        'random_trade_winner': 'Found winner' if 'WINNER:' in str(random_trade.get('output', {}).get('analysis', '')) else 'No winner found',
        'formatted_example_length': len(formatted_example)
    }


if __name__ == "__main__":
    # Test the example library
    results = test_example_library()
    print("Example Library Test Results:")
    print(f"Player examples: {results['player_examples_count']}")
    print(f"Trade examples: {results['trade_examples_count']}")  
    print(f"Keeper examples: {results['keeper_examples_count']}")
    print(f"Random player example confidence: {results['random_player_confidence']}")
    print(f"Random trade example: {results['random_trade_winner']}")
    print(f"Formatted example length: {results['formatted_example_length']} characters")