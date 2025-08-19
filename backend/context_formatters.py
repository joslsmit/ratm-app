"""
Enhanced Context Formatters for Analysis-Type-Specific Data Presentation

Optimizes how player and league data is formatted for AI consumption based on
the specific type of fantasy football analysis being performed.

Phase 0B Implementation: Dynamic context adjustment and emphasis.
"""

from typing import Dict, List, Any, Optional
from enum import Enum


class AnalysisType(Enum):
    """Types of fantasy football analysis."""
    PLAYER_DOSSIER = "player_dossier"
    TRADE_ANALYSIS = "trade_analysis"  
    KEEPER_EVALUATION = "keeper_evaluation"
    WAIVER_ANALYSIS = "waiver_analysis"
    DRAFT_ASSISTANCE = "draft_assistance"
    TIER_GENERATION = "tier_generation"
    MARKET_INEFFICIENCY = "market_inefficiency"
    ROOKIE_EVALUATION = "rookie_evaluation"


class ContextFormatter:
    """Formats player and league data for optimal AI consumption based on analysis type."""
    
    @staticmethod
    def format_enhanced_player_context(
        player_data: Dict[str, Any],
        analysis_type: AnalysisType,
        additional_context: Optional[Dict] = None
    ) -> str:
        """
        Format player data with analysis-type-specific emphasis and context.
        
        Args:
            player_data: Raw player data dictionary from combined_player_data_cache
            analysis_type: Type of analysis being performed
            additional_context: Optional additional context (league settings, etc.)
            
        Returns:
            Formatted player context string optimized for the analysis type
        """
        
        if not player_data:
            return "No player data available"
            
        # Base player information (always included)
        base_context = ContextFormatter._format_base_player_info(player_data)
        
        # Analysis-type-specific formatting
        if analysis_type == AnalysisType.PLAYER_DOSSIER:
            return ContextFormatter._format_for_player_dossier(player_data, base_context, additional_context)
        elif analysis_type == AnalysisType.TRADE_ANALYSIS:
            return ContextFormatter._format_for_trade_analysis(player_data, base_context, additional_context)
        elif analysis_type == AnalysisType.KEEPER_EVALUATION:
            return ContextFormatter._format_for_keeper_evaluation(player_data, base_context, additional_context)
        elif analysis_type == AnalysisType.WAIVER_ANALYSIS:
            return ContextFormatter._format_for_waiver_analysis(player_data, base_context, additional_context)
        elif analysis_type == AnalysisType.ROOKIE_EVALUATION:
            return ContextFormatter._format_for_rookie_evaluation(player_data, base_context, additional_context)
        elif analysis_type == AnalysisType.TIER_GENERATION:
            return ContextFormatter._format_for_tier_generation(player_data, base_context, additional_context)
        elif analysis_type == AnalysisType.DRAFT_ASSISTANCE:
            return ContextFormatter._format_for_draft_assistance(player_data, base_context, additional_context)
        elif analysis_type == AnalysisType.MARKET_INEFFICIENCY:
            return ContextFormatter._format_for_market_inefficiency(player_data, base_context, additional_context)
        else:
            # Default comprehensive format
            return base_context
    
    @staticmethod
    def _format_base_player_info(player_data: Dict[str, Any]) -> str:
        """Format core player information that's relevant for all analysis types."""
        
        name = player_data.get('name', 'Unknown Player')
        position = player_data.get('position', 'N/A')
        team = player_data.get('team', 'N/A')
        
        base_info = f"**{name}** ({position}, {team})"
        
        # Core stats
        details = []
        
        # Experience and rookie status
        years_exp = player_data.get('years_exp')
        if years_exp is not None:
            details.append(f"Experience: {int(years_exp)} years")
        
        is_rookie = "Yes" if player_data.get('is_rookie') else "No"
        details.append(f"Rookie: {is_rookie}")
        
        # Bye week (always relevant)
        bye_week = player_data.get('bye_week')
        if bye_week:
            details.append(f"Bye Week: {int(bye_week)}")
        
        if details:
            base_info += f"\n- {' | '.join(details)}"
            
        return base_info
    
    @staticmethod
    def _format_for_player_dossier(player_data: Dict, base_context: str, additional_context: Optional[Dict]) -> str:
        """Format context specifically for comprehensive player analysis."""
        
        context = f"{base_context}\n\n**FANTASY RANKINGS & CONSENSUS:**"
        
        # ECR data with emphasis on consensus
        ecr_overall = player_data.get('ecr_overall')
        if ecr_overall:
            context += f"\n- Overall ECR: {ecr_overall:.1f}"
            
            # Standard deviation (consensus indicator)
            sd_overall = player_data.get('sd_overall')
            if sd_overall:
                consensus_level = "High" if sd_overall < 3 else "Medium" if sd_overall < 6 else "Low"
                context += f" (SD: {sd_overall:.1f} - {consensus_level} Expert Consensus)"
        
        # Ranking range for uncertainty assessment  
        best_rank = player_data.get('best_overall')
        worst_rank = player_data.get('worst_overall')
        if best_rank and worst_rank:
            range_width = worst_rank - best_rank
            context += f"\n- Expert Range: #{int(best_rank)} to #{int(worst_rank)} (Range: {range_width} spots)"
        
        # Recent trend
        rank_delta = player_data.get('rank_delta_overall')
        if rank_delta:
            trend = "Rising" if rank_delta < -1 else "Falling" if rank_delta > 1 else "Stable"
            context += f"\n- Recent Trend: {trend} ({rank_delta:+.1f} spots this week)"
        
        # Position-specific ECR if different from overall
        ecr_positional = player_data.get('ecr_positional')
        if ecr_positional and abs(ecr_overall - ecr_positional) > 3:
            context += f"\n- Positional ECR: {ecr_positional:.1f} (Variance from overall: {ecr_positional - ecr_overall:+.1f})"
        
        return context
    
    @staticmethod 
    def _format_for_trade_analysis(player_data: Dict, base_context: str, additional_context: Optional[Dict]) -> str:
        """Format context specifically for trade evaluation."""
        
        context = f"{base_context}\n\n**TRADE EVALUATION METRICS:**"
        
        # Focus on ECR for value calculation
        ecr_overall = player_data.get('ecr_overall')
        if ecr_overall:
            # Convert ECR to approximate draft round/pick
            draft_round = int((ecr_overall - 1) // 12) + 1
            draft_pick = int(ecr_overall)
            context += f"\n- Current Value: ECR {ecr_overall:.1f} (~Round {draft_round}, Pick {draft_pick})"
        
        # Age/experience for trade timeline considerations  
        years_exp = player_data.get('years_exp')
        if years_exp is not None:
            age_category = ContextFormatter._categorize_player_age(years_exp, player_data.get('position', ''))
            context += f"\n- Age Factor: {age_category} ({int(years_exp)} years experience)"
        
        # Bye week for roster management
        bye_week = player_data.get('bye_week')
        if bye_week:
            context += f"\n- Bye Week Impact: Week {int(bye_week)}"
        
        # Injury/consistency risk via standard deviation
        sd_overall = player_data.get('sd_overall')
        if sd_overall:
            risk_level = "Low" if sd_overall < 3 else "Medium" if sd_overall < 6 else "High"
            context += f"\n- Volatility Risk: {risk_level} (Expert SD: {sd_overall:.1f})"
        
        return context
    
    @staticmethod
    def _format_for_keeper_evaluation(player_data: Dict, base_context: str, additional_context: Optional[Dict]) -> str:
        """Format context specifically for keeper decisions."""
        
        context = f"{base_context}\n\n**KEEPER VALUE ANALYSIS:**"
        
        # Market value
        ecr_overall = player_data.get('ecr_overall')
        if ecr_overall:
            context += f"\n- Market Value: ECR {ecr_overall:.1f} (Expected ~Round {int((ecr_overall - 1) // 12) + 1})"
        
        # Contract/age considerations
        years_exp = player_data.get('years_exp')
        if years_exp is not None:
            age_trajectory = ContextFormatter._assess_age_trajectory(years_exp, player_data.get('position', ''))
            context += f"\n- Age Trajectory: {age_trajectory}"
        
        # Consistency/reliability for multi-year value
        sd_overall = player_data.get('sd_overall')
        if sd_overall:
            reliability = "High" if sd_overall < 3 else "Medium" if sd_overall < 6 else "Low"
            context += f"\n- Value Reliability: {reliability} (Expert SD: {sd_overall:.1f})"
        
        # Add keeper cost if provided in additional_context
        if additional_context and 'keeper_cost' in additional_context:
            keeper_cost = additional_context['keeper_cost']
            context += f"\n- Keeper Cost: {keeper_cost}"
            
        return context
    
    @staticmethod
    def _format_for_waiver_analysis(player_data: Dict, base_context: str, additional_context: Optional[Dict]) -> str:
        """Format context specifically for waiver wire decisions."""
        
        context = f"{base_context}\n\n**WAIVER WIRE EVALUATION:**"
        
        # Enhanced ECR and positional ranking
        ecr_overall = player_data.get('ecr_overall')
        ecr_positional = player_data.get('ecr_positional')
        position = player_data.get('position', 'N/A')
        
        if ecr_overall:
            context += f"\n- Overall ECR: {ecr_overall:.1f}"
            
            # Add positional rank with tier context
            if ecr_positional:
                context += f"\n- Positional Rank: {position}#{int(ecr_positional)}"
                
                # Add tier classification for better AI understanding
                if position == 'QB':
                    if ecr_positional <= 12:
                        tier = "QB1 (Elite/Starter)"
                    elif ecr_positional <= 24:
                        tier = "QB2 (Backup/Streaming)"
                    else:
                        tier = "QB3+ (Deep League Only)"
                elif position in ['RB', 'WR']:
                    if ecr_positional <= 24:
                        tier = f"{position}1 (Elite)"
                    elif ecr_positional <= 48:
                        tier = f"{position}2 (Solid)"
                    else:
                        tier = f"{position}3+ (Depth)"
                elif position == 'TE':
                    if ecr_positional <= 12:
                        tier = "TE1 (Elite)"
                    else:
                        tier = "TE2+ (Streaming)"
                else:
                    tier = "Standard"
                    
                context += f" → {tier}"
            
            # Waiver value assessment with enhanced tiers
            if ecr_overall < 50:
                value_tier = "⭐ High-Value Pickup"
            elif ecr_overall < 100:
                value_tier = "✅ Solid Addition"
            elif ecr_overall < 150:
                value_tier = "📊 Depth/Streaming Option"
            else:
                value_tier = "🔍 Deep League Only"
            context += f"\n- Value Assessment: {value_tier}"
        
        # Recent trend for waiver timing
        rank_delta = player_data.get('rank_delta_overall')
        if rank_delta:
            if rank_delta < -5:
                trend_note = "🔥 Rising Fast - High Priority"
            elif rank_delta < -2:
                trend_note = "📈 Trending Up"
            elif rank_delta > 5:
                trend_note = "📉 Falling - Proceed with Caution"
            elif rank_delta > 2:
                trend_note = "⚠️ Trending Down"
            else:
                trend_note = "➡️ Stable"
            context += f"\n- Trend Status: {trend_note} ({rank_delta:+.1f} spots)"
        
        # Opportunity assessment for rookies/young players
        is_rookie = player_data.get('is_rookie')
        years_exp = player_data.get('years_exp')
        if is_rookie or (years_exp and years_exp < 3):
            context += f"\n- Opportunity Factor: High upside potential for young player"
        
        return context
    
    @staticmethod
    def _format_for_rookie_evaluation(player_data: Dict, base_context: str, additional_context: Optional[Dict]) -> str:
        """Format context specifically for rookie analysis."""
        
        context = f"{base_context}\n\n**ROOKIE EVALUATION METRICS:**"
        
        # Rookie-specific ECR
        ecr_rookie = player_data.get('ecr_rookie')
        ecr_overall = player_data.get('ecr_overall')
        
        if ecr_rookie:
            context += f"\n- Rookie ECR: {ecr_rookie:.1f}"
        if ecr_overall:
            context += f"\n- Overall ECR: {ecr_overall:.1f}"
            
        # Uncertainty indicators
        sd_overall = player_data.get('sd_overall', 0)
        if sd_overall > 8:
            context += f"\n- Expert Uncertainty: Very High (SD: {sd_overall:.1f}) - Wide range of opinions"
        elif sd_overall > 5:
            context += f"\n- Expert Uncertainty: High (SD: {sd_overall:.1f}) - Significant disagreement"
        else:
            context += f"\n- Expert Uncertainty: Moderate (SD: {sd_overall:.1f}) - Some consensus"
        
        # Draft capital context
        if additional_context and 'draft_capital' in additional_context:
            draft_info = additional_context['draft_capital']
            context += f"\n- NFL Draft: {draft_info}"
        
        return context
    
    @staticmethod
    def _format_for_tier_generation(player_data: Dict, base_context: str, additional_context: Optional[Dict]) -> str:
        """Format context specifically for tier/ranking generation."""
        
        context = f"{base_context}\n\n**TIER ANALYSIS DATA:**"
        
        # Multiple ECR types for tier comparison
        ecr_overall = player_data.get('ecr_overall')
        ecr_positional = player_data.get('ecr_positional')
        
        if ecr_overall:
            context += f"\n- Overall ECR: {ecr_overall:.1f}"
        if ecr_positional:
            context += f"\n- Positional ECR: {ecr_positional:.1f}"
        
        # Standard deviation for tier boundaries
        sd_overall = player_data.get('sd_overall')
        if sd_overall:
            tier_confidence = "Clear Tier" if sd_overall < 3 else "Tier Boundary" if sd_overall < 6 else "Tier Overlap"
            context += f"\n- Tier Clarity: {tier_confidence} (SD: {sd_overall:.1f})"
        
        return context
    
    @staticmethod
    def _format_for_draft_assistance(player_data: Dict, base_context: str, additional_context: Optional[Dict]) -> str:
        """Format context specifically for draft assistance."""
        
        context = f"{base_context}\n\n**DRAFT DECISION DATA:**"
        
        # ADP vs ECR comparison
        ecr_overall = player_data.get('ecr_overall')
        if ecr_overall:
            context += f"\n- Current ECR: {ecr_overall:.1f} (Round {int((ecr_overall - 1) // 12) + 1})"
        
        # Value assessment
        if additional_context and 'pick_number' in additional_context:
            pick_number = additional_context['pick_number']
            if ecr_overall:
                value_diff = pick_number - ecr_overall
                if value_diff < -10:
                    value_note = "🔴 Significant Reach"
                elif value_diff < -3:
                    value_note = "⚠️ Slight Reach"  
                elif value_diff > 10:
                    value_note = "🟢 Excellent Value"
                elif value_diff > 3:
                    value_note = "💚 Good Value"
                else:
                    value_note = "➡️ Fair Value"
                context += f"\n- Value at Pick {pick_number}: {value_note} ({value_diff:+.1f})"
        
        return context
    
    @staticmethod
    def _format_for_market_inefficiency(player_data: Dict, base_context: str, additional_context: Optional[Dict]) -> str:
        """Format context specifically for market inefficiency analysis."""
        
        context = f"{base_context}\n\n**MARKET INEFFICIENCY INDICATORS:**"
        
        # ECR vs other metrics comparison
        ecr_overall = player_data.get('ecr_overall')
        if ecr_overall:
            context += f"\n- Consensus ECR: {ecr_overall:.1f}"
        
        # Standard deviation as inefficiency indicator
        sd_overall = player_data.get('sd_overall')
        if sd_overall:
            if sd_overall > 8:
                inefficiency_note = "🎯 High Disagreement - Potential Inefficiency"
            elif sd_overall > 5:
                inefficiency_note = "🤔 Moderate Disagreement - Worth Investigating"
            else:
                inefficiency_note = "✅ Strong Consensus - Limited Inefficiency"
            context += f"\n- Expert Agreement: {inefficiency_note} (SD: {sd_overall:.1f})"
        
        # Ranking range for opportunity identification
        best_rank = player_data.get('best_overall')
        worst_rank = player_data.get('worst_overall')
        if best_rank and worst_rank and (worst_rank - best_rank) > 15:
            context += f"\n- Opportunity Range: #{int(best_rank)} to #{int(worst_rank)} - Wide variance suggests inefficiency"
        
        return context
    
    @staticmethod
    def _categorize_player_age(years_exp: int, position: str) -> str:
        """Categorize player age based on position-specific curves."""
        
        # Position-specific age considerations
        if position in ['RB']:
            if years_exp < 3:
                return "Prime Years (Young RB)"
            elif years_exp < 6:
                return "Peak Window (Prime RB)"
            elif years_exp < 8:
                return "Decline Phase (Aging RB)"
            else:
                return "High Risk (Old RB)"
        elif position in ['QB']:
            if years_exp < 5:
                return "Development Phase"
            elif years_exp < 12:
                return "Prime Years"
            else:
                return "Veteran (Experience Advantage)"
        elif position in ['WR', 'TE']:
            if years_exp < 3:
                return "Early Career"
            elif years_exp < 8:
                return "Prime Years"
            elif years_exp < 12:
                return "Veteran Experience"
            else:
                return "Declining Years"
        else:
            if years_exp < 3:
                return "Young Player"
            elif years_exp < 8:
                return "Prime Years"
            else:
                return "Veteran"
    
    @staticmethod
    def _assess_age_trajectory(years_exp: int, position: str) -> str:
        """Assess age trajectory for keeper value."""
        
        if position == 'RB':
            if years_exp < 4:
                return "Ascending (Prime RB years ahead)"
            elif years_exp < 7:
                return "Peak Window (Maximum value now)"
            else:
                return "Declining (Age-related risk increasing)"
        elif position == 'QB':
            if years_exp < 8:
                return "Ascending (Peak years ahead or current)"
            elif years_exp < 15:
                return "Peak/Stable (Prime years)"
            else:
                return "Late Career (Experience vs decline)"
        else:
            if years_exp < 5:
                return "Ascending (Prime years ahead)"
            elif years_exp < 10:
                return "Peak Window (Prime years)"
            else:
                return "Declining (Age-related concerns)"

    @staticmethod
    def format_multiple_players_context(
        players_data: List[Dict[str, Any]],
        analysis_type: AnalysisType,
        additional_context: Optional[Dict] = None
    ) -> str:
        """Format context for multiple players (trades, comparisons, etc.)"""
        
        if not players_data:
            return "No player data provided"
        
        formatted_players = []
        for i, player_data in enumerate(players_data, 1):
            player_context = ContextFormatter.format_enhanced_player_context(
                player_data, analysis_type, additional_context
            )
            formatted_players.append(f"PLAYER {i}:\n{player_context}")
        
        return "\n\n".join(formatted_players)


# Test function to validate context formatters
def test_context_formatters():
    """Test the enhanced context formatting functionality."""
    
    # Mock player data
    sample_player_data = {
        'name': 'Josh Allen',
        'position': 'QB',
        'team': 'BUF',
        'years_exp': 7,
        'is_rookie': False,
        'bye_week': 12,
        'ecr_overall': 1.2,
        'ecr_positional': 1.0,
        'sd_overall': 0.8,
        'best_overall': 1,
        'worst_overall': 3,
        'rank_delta_overall': -0.5
    }
    
    # Test different analysis types
    dossier_context = ContextFormatter.format_enhanced_player_context(
        sample_player_data, AnalysisType.PLAYER_DOSSIER
    )
    
    trade_context = ContextFormatter.format_enhanced_player_context(
        sample_player_data, AnalysisType.TRADE_ANALYSIS
    )
    
    keeper_context = ContextFormatter.format_enhanced_player_context(
        sample_player_data, AnalysisType.KEEPER_EVALUATION,
        {'keeper_cost': '2nd Round Pick'}
    )
    
    waiver_context = ContextFormatter.format_enhanced_player_context(
        sample_player_data, AnalysisType.WAIVER_ANALYSIS
    )
    
    return {
        'dossier_length': len(dossier_context),
        'trade_length': len(trade_context),
        'keeper_length': len(keeper_context),
        'waiver_length': len(waiver_context),
        'dossier_has_consensus': 'Expert Consensus' in dossier_context,
        'trade_has_age_factor': 'Age Factor' in trade_context,
        'keeper_has_cost': 'Keeper Cost' in keeper_context,
        'waiver_has_trend': 'Trend Status' in waiver_context
    }


if __name__ == "__main__":
    # Test the context formatters
    results = test_context_formatters()
    print("Context Formatters Test Results:")
    print(f"Player dossier context length: {results['dossier_length']} characters")
    print(f"Trade analysis context length: {results['trade_length']} characters") 
    print(f"Keeper evaluation context length: {results['keeper_length']} characters")
    print(f"Waiver analysis context length: {results['waiver_length']} characters")
    print(f"Dossier includes consensus data: {results['dossier_has_consensus']}")
    print(f"Trade includes age factor: {results['trade_has_age_factor']}")
    print(f"Keeper includes cost data: {results['keeper_has_cost']}")
    print(f"Waiver includes trend data: {results['waiver_has_trend']}")