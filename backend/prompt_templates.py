"""
Advanced Prompt Engineering System for RATM Draft Kit

This module provides structured prompt templates, few-shot examples, and chain-of-thought
reasoning frameworks to enhance AI analysis quality across all fantasy football tools.

Phase 0B Implementation: Modular prompt system with reusable components.
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass
import json

# Import existing constants from app.py to maintain compatibility
# These will be used as base templates and extended with advanced techniques
EXISTING_PROMPT_PREAMBLE = """You are 'The Analyst' - an expert fantasy football advisor specializing in data-driven analysis for the 2025 NFL season.

CONTEXT:
- League Format: 12-team, PPR scoring, standard Yahoo rules
- Season: 2025 NFL season with current roster compositions
- Data Sources: Expert Consensus Rankings (ECR), injury reports, depth charts
- Analysis Philosophy: Objective, data-driven, actionable insights

APPROACH:
- Base recommendations on provided ECR data (lower ECR = better ranking)
- Consider positional scarcity and value-based drafting
- Factor in injury history, role security, and team context
- Account for bye week timing and roster construction
- Acknowledge uncertainty when data is limited

RESPONSE STYLE:
- Professional and analytical tone
- Concise but thorough explanations
- Clear section headers using markdown formatting
- Focus on actionable recommendations with reasoning
- Provide confidence assessment based on data quality"""

EXISTING_JSON_OUTPUT_INSTRUCTION = """RESPONSE FORMAT REQUIREMENTS:
Your response MUST be a valid JSON object with exactly these keys:
{
  "confidence": "High" | "Medium" | "Low",
  "analysis": "markdown-formatted analysis string"
}

CONFIDENCE DEFINITIONS:
- "High": Strong data consensus, established patterns, minimal uncertainty
- "Medium": Good data quality with some variables or moderate uncertainty  
- "Low": Limited data, high uncertainty, or significant unknowns

ANALYSIS FORMATTING:
- Use markdown headers (### Section Name) for organization
- Include bullet points and bold text for emphasis
- Structure analysis logically with clear reasoning
- End with actionable recommendation or summary

CRITICAL JSON REQUIREMENTS:
- Use double quotes for all strings
- No trailing commas
- Escape any internal quotes properly
- Ensure valid JSON syntax throughout"""


@dataclass
class PromptTemplate:
    """Structured prompt template for consistent AI interactions."""
    task_description: str
    methodology: List[str]
    output_format: str
    examples: List[Dict[str, Any]]
    specific_instructions: List[str]
    chain_of_thought_steps: Optional[List[str]] = None


class PromptBuilder:
    """Builds consistent, high-quality prompts for different analysis types using advanced techniques."""
    
    @staticmethod
    def get_base_system_prompt() -> str:
        """Get the enhanced base system prompt with chain-of-thought guidance."""
        return f"""{EXISTING_PROMPT_PREAMBLE}

ADVANCED REASONING APPROACH:
- Think step-by-step through your analysis before concluding
- Consider multiple perspectives and potential scenarios
- Weigh conflicting data points and acknowledge uncertainties
- Validate your reasoning against the provided data
- Structure your thinking logically and transparently"""

    @staticmethod  
    def get_json_instruction() -> str:
        """Get the JSON output instruction (maintains backward compatibility)."""
        return EXISTING_JSON_OUTPUT_INSTRUCTION

    @staticmethod
    def build_enhanced_prompt(
        task_description: str,
        player_data: str,
        methodology_steps: List[str],
        examples: Optional[List[Dict]] = None,
        chain_of_thought: Optional[List[str]] = None
    ) -> str:
        """
        Build an enhanced prompt with methodology, examples, and chain-of-thought reasoning.
        
        Args:
            task_description: Clear description of the analysis task
            player_data: Formatted player context data
            methodology_steps: Step-by-step analysis methodology
            examples: Few-shot examples (optional)
            chain_of_thought: Reasoning steps (optional)
            
        Returns:
            Complete prompt string ready for AI consumption
        """
        
        base_prompt = PromptBuilder.get_base_system_prompt()
        
        # Build methodology section
        methodology_text = "ANALYSIS METHODOLOGY:\n"
        for i, step in enumerate(methodology_steps, 1):
            methodology_text += f"{i}. {step}\n"
        
        # Build examples section if provided
        examples_text = ""
        if examples:
            examples_text = "\nEXAMPLE ANALYSIS:\n"
            for i, example in enumerate(examples[:2], 1):  # Limit to 2 examples for context efficiency
                examples_text += f"\nExample {i}:\n"
                examples_text += f"Input: {example.get('input', 'N/A')}\n"
                examples_text += f"Expected Output: {json.dumps(example.get('output', {}), indent=2)}\n"
        
        # Build chain-of-thought section if provided
        thinking_text = ""
        if chain_of_thought:
            thinking_text = "\nSTEP-BY-STEP THINKING PROCESS:\n"
            for i, step in enumerate(chain_of_thought, 1):
                thinking_text += f"{i}. {step}\n"
        
        # Combine all sections
        complete_prompt = f"""{base_prompt}

TASK: {task_description}

{methodology_text}{examples_text}{thinking_text}

PLAYER DATA:
{player_data}

{PromptBuilder.get_json_instruction()}"""
        
        return complete_prompt

    @staticmethod
    def build_player_analysis_prompt(
        player_data: str, 
        analysis_type: str = "comprehensive"
    ) -> str:
        """
        Build enhanced player analysis prompt with methodology and structure.
        
        Args:
            player_data: Formatted player context
            analysis_type: Type of analysis (comprehensive, trade, waiver, etc.)
            
        Returns:
            Enhanced prompt for player analysis
        """
        
        task_description = "Comprehensive Player Analysis for Fantasy Football"
        
        methodology_steps = [
            "Evaluate depth chart position and role security within team context",
            "Compare Expert Consensus Ranking (ECR) to projected performance and value",
            "Assess injury history, age, and durability concerns for the position",
            "Analyze supporting cast, offensive system, and coaching stability",
            "Project 2025 season outlook considering all variables and uncertainties",
            "Synthesize analysis into clear, actionable recommendation with confidence level"
        ]
        
        chain_of_thought = [
            "What is this player's current role and how secure is their position?",
            "How does their ECR compare to their projected fantasy value?",
            "What are the main risk factors I need to consider?",
            "What does the 2025 season setup look like for this player?",
            "Based on all factors, what's my confident recommendation?"
        ]
        
        return PromptBuilder.build_enhanced_prompt(
            task_description=task_description,
            player_data=player_data,
            methodology_steps=methodology_steps,
            chain_of_thought=chain_of_thought
        )

    @staticmethod
    def build_trade_analysis_prompt(
        my_assets: str,
        their_assets: str,
        league_context: str = ""
    ) -> str:
        """
        Build enhanced trade analysis prompt with clear winner determination methodology.
        
        Args:
            my_assets: Players/picks my team would receive
            their_assets: Players/picks the other team would receive  
            league_context: Additional league-specific context
            
        Returns:
            Enhanced prompt for trade analysis
        """
        
        task_description = "Trade Analysis with Clear Winner Determination"
        
        methodology_steps = [
            "Calculate total fantasy value of each side using ECR and projections",
            "Assess positional scarcity and roster construction impact for both teams",
            "Evaluate short-term versus long-term value implications",
            "Consider injury risk, age curves, and schedule factors",
            "Account for bye week management and roster flexibility",
            "Declare clear winner with supporting reasoning and confidence assessment"
        ]
        
        chain_of_thought = [
            "What's the raw value comparison between both sides of this trade?",
            "How does positional scarcity affect the value calculation?",
            "Are there any timing or situational factors that change the evaluation?",
            "Which team benefits more in the short-term vs long-term?",
            "Based on total analysis, which side clearly wins this trade?"
        ]
        
        player_data = f"""TRADE ANALYSIS:

My Team Receives:
{my_assets}

Other Team Receives:  
{their_assets}

League Context:
{league_context if league_context else "Standard 12-team PPR league"}"""
        
        return PromptBuilder.build_enhanced_prompt(
            task_description=task_description,
            player_data=player_data,
            methodology_steps=methodology_steps,
            chain_of_thought=chain_of_thought
        )


# Utility function for backward compatibility testing
def test_prompt_builder():
    """Test function to ensure prompt builder works correctly."""
    
    sample_player_data = """Josh Allen (QB, BUF)
- Overall ECR: 1.2, SD: 0.8, Best: 1, Worst: 3
- Team: Buffalo Bills, Bye Week: 12
- Years Experience: 7, Rookie: No"""
    
    # Test player analysis prompt
    player_prompt = PromptBuilder.build_player_analysis_prompt(sample_player_data)
    
    # Test trade analysis prompt
    trade_prompt = PromptBuilder.build_trade_analysis_prompt(
        my_assets="Josh Allen (QB, BUF) - ECR: 1.2",
        their_assets="Lamar Jackson (QB, BAL) - ECR: 2.1, Travis Kelce (TE, KC) - ECR: 12.5"
    )
    
    return {
        'player_prompt_length': len(player_prompt),
        'trade_prompt_length': len(trade_prompt),
        'player_prompt_preview': player_prompt[:200] + "...",
        'trade_prompt_preview': trade_prompt[:200] + "..."
    }


if __name__ == "__main__":
    # Quick test when running the module directly
    test_results = test_prompt_builder()
    print("Prompt Builder Test Results:")
    print(f"Player analysis prompt length: {test_results['player_prompt_length']} characters")
    print(f"Trade analysis prompt length: {test_results['trade_prompt_length']} characters")
    print("\nPlayer prompt preview:")
    print(test_results['player_prompt_preview'])
    print("\nTrade prompt preview:")  
    print(test_results['trade_prompt_preview'])