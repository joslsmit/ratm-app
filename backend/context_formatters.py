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
        """
        REVOLUTIONARY waiver analysis context with multi-factor integration.
        
        Enhancement: Combines tier classification + projections + matchups + ownership + age
        """
        
        context = f"{base_context}\n\n**COMPREHENSIVE WAIVER WIRE EVALUATION:**"
        
        # EXISTING: Enhanced ECR and positional ranking (keep existing logic)
        ecr_overall = player_data.get('ecr_overall')
        ecr_positional = player_data.get('ecr_positional')
        position = player_data.get('position', 'N/A')
        
        if ecr_overall:
            context += f"\n- Overall ECR: {ecr_overall:.1f}"
            
            if ecr_positional:
                context += f"\n- Positional Rank: {position}#{int(ecr_positional)}"
                
                # Enhanced tier classification (existing logic)
                tier_info = ContextFormatter._get_tier_classification(position, ecr_positional)
                context += f" → {tier_info}"
        
        # NEW: WEEKLY PROJECTION ANALYSIS
        projected_points = player_data.get('projected_points')
        start_sit_grade = player_data.get('start_sit_grade')
        
        if projected_points or start_sit_grade:
            context += f"\n\n**WEEKLY PROJECTION ANALYSIS:**"
            
            if projected_points:
                projection_tier = ContextFormatter._get_projection_tier(projected_points, position)
                context += f"\n- Weekly Projection: {projected_points} points ({projection_tier})"
            
            if start_sit_grade:
                grade_confidence = player_data.get('grade_confidence_score', 0)
                confidence_desc = ContextFormatter._get_confidence_description(grade_confidence)
                context += f"\n- Expert Grade: {start_sit_grade} ({confidence_desc})"
        
        # NEW: MATCHUP ANALYSIS
        opponent = player_data.get('opponent')
        matchup_difficulty = player_data.get('matchup_difficulty')
        home_away = player_data.get('home_away')
        
        if opponent or matchup_difficulty:
            context += f"\n\n**MATCHUP ANALYSIS:**"
            
            if opponent and home_away:
                location_icon = "🏠" if home_away == "Home" else "✈️" if home_away == "Away" else "🏟️"
                context += f"\n- This Week: {location_icon} {home_away} vs. {opponent}"
            
            if matchup_difficulty:
                difficulty_icon = ContextFormatter._get_difficulty_icon(matchup_difficulty)
                context += f"\n- Matchup Difficulty: {difficulty_icon} {matchup_difficulty}"
                
                # Add matchup-specific advice
                matchup_advice = ContextFormatter._get_matchup_advice(matchup_difficulty, position)
                if matchup_advice:
                    context += f"\n- Matchup Impact: {matchup_advice}"
        
        # NEW: OWNERSHIP ARBITRAGE ANALYSIS
        weekly_ownership = player_data.get('weekly_ownership')
        value_opportunity_score = player_data.get('value_opportunity_score')
        
        if weekly_ownership is not None or value_opportunity_score:
            context += f"\n\n**MARKET OPPORTUNITY ANALYSIS:**"
            
            if weekly_ownership is not None:
                ownership_tier = ContextFormatter._get_ownership_tier(weekly_ownership)
                context += f"\n- Current Ownership: {weekly_ownership}% ({ownership_tier})"
            
            if value_opportunity_score:
                opportunity_rating = ContextFormatter._get_opportunity_rating(value_opportunity_score)
                context += f"\n- Value Opportunity: {opportunity_rating}"
                
                # Identify arbitrage opportunities
                if weekly_ownership is not None and projected_points:
                    arbitrage_alert = ContextFormatter._identify_arbitrage_opportunity(
                        weekly_ownership, projected_points, start_sit_grade
                    )
                    if arbitrage_alert:
                        context += f"\n- 🚨 **ARBITRAGE ALERT**: {arbitrage_alert}"
        
        # NEW: AGE AND DEVELOPMENT ANALYSIS
        age = player_data.get('age')
        age_category = player_data.get('age_category')
        draft_year = player_data.get('draft_year')
        
        if age or age_category:
            context += f"\n\n**ROSTER BUILDING CONTEXT:**"
            
            if age and age_category:
                context += f"\n- Age Factor: {age} years old ({age_category})"
            
            if draft_year:
                experience_level = ContextFormatter._calculate_experience_level(draft_year)
                context += f"\n- Experience: {experience_level}"
            
            # Add age-specific strategic advice
            age_advice = ContextFormatter._get_age_strategic_advice(age_category, position)
            if age_advice:
                context += f"\n- Strategic Context: {age_advice}"
        
        # NEW: COMPREHENSIVE OUTLOOK
        projection_confidence = player_data.get('projection_confidence')
        from utils import get_weekly_outlook
        weekly_outlook = get_weekly_outlook(player_data)
        
        if projection_confidence or weekly_outlook:
            context += f"\n\n**OUTLOOK ASSESSMENT:**"
            
            if projection_confidence:
                context += f"\n- Projection Reliability: {projection_confidence}"
            
            if weekly_outlook:
                context += f"\n- Short-term Outlook: {weekly_outlook}"
            
            # Final recommendation context
            recommendation_context = ContextFormatter._generate_recommendation_context(player_data)
            if recommendation_context:
                context += f"\n- **KEY FACTORS**: {recommendation_context}"
        
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

    # --- Enhanced Waiver Analysis Helper Methods ---
    
    @staticmethod
    def _get_tier_classification(position: str, ecr_positional: float) -> str:
        """Get tier classification for position and rank."""
        if position == 'QB':
            if ecr_positional <= 12:
                return "QB1 (Elite/Starter)"
            elif ecr_positional <= 24:
                return "QB2 (Backup/Streaming)"
            else:
                return "QB3+ (Deep League Only)"
        elif position in ['RB', 'WR']:
            if ecr_positional <= 24:
                return f"{position}1 (Elite)"
            elif ecr_positional <= 48:
                return f"{position}2 (Solid)"
            else:
                return f"{position}3+ (Depth)"
        elif position == 'TE':
            if ecr_positional <= 12:
                return "TE1 (Elite)"
            else:
                return "TE2+ (Streaming)"
        else:
            return "Standard"
    
    @staticmethod
    def _get_projection_tier(projected_points: float, position: str) -> str:
        """Get projection tier description."""
        try:
            points = float(projected_points)
            if position == 'QB':
                if points >= 22:
                    return "Elite QB1 Week"
                elif points >= 18:
                    return "Solid QB1 Performance"
                elif points >= 15:
                    return "QB2 Production"
                else:
                    return "Streaming Option"
            elif position == 'RB':
                if points >= 20:
                    return "RB1 Ceiling Week"
                elif points >= 15:
                    return "Solid RB2 Floor"
                elif points >= 10:
                    return "Flex-Worthy"
                else:
                    return "Depth Option"
            elif position == 'WR':
                if points >= 18:
                    return "WR1 Potential"
                elif points >= 14:
                    return "WR2 Production"
                elif points >= 10:
                    return "Flex-Worthy"
                else:
                    return "Deep League"
            elif position == 'TE':
                if points >= 15:
                    return "TE1 Ceiling"
                elif points >= 10:
                    return "TE1 Floor"
                elif points >= 7:
                    return "Streaming"
                else:
                    return "Deep League"
            else:
                return "Standard"
        except (ValueError, TypeError):
            return "Standard"
    
    @staticmethod
    def _get_confidence_description(confidence_score: int) -> str:
        """Get confidence description from score."""
        if confidence_score >= 90:
            return "Very High Expert Confidence"
        elif confidence_score >= 80:
            return "High Expert Confidence"
        elif confidence_score >= 70:
            return "Moderate Expert Confidence"
        elif confidence_score >= 60:
            return "Standard Expert Confidence"
        else:
            return "Low Expert Confidence"
    
    @staticmethod
    def _get_difficulty_icon(difficulty: str) -> str:
        """Get icon for matchup difficulty."""
        if difficulty == 'Easy':
            return "🟢"
        elif difficulty == 'Tough':
            return "🔴"
        elif difficulty == 'Moderate':
            return "🟡"
        else:
            return "⚪"
    
    @staticmethod
    def _get_matchup_advice(difficulty: str, position: str) -> str:
        """Get matchup-specific advice."""
        if difficulty == 'Easy':
            return f"Favorable spot for {position} production"
        elif difficulty == 'Tough':
            return f"Challenging matchup may limit {position} ceiling"
        elif difficulty == 'Moderate':
            return "Neutral matchup - rely on talent/usage"
        else:
            return ""
    
    @staticmethod
    def _get_ownership_tier(ownership_pct: float) -> str:
        """Get ownership tier description."""
        try:
            pct = float(ownership_pct)
            if pct < 10:
                return "Ultra-Low Ownership"
            elif pct < 25:
                return "Low Ownership"
            elif pct < 50:
                return "Moderate Ownership"
            elif pct < 75:
                return "High Ownership"
            else:
                return "Widely Owned"
        except (ValueError, TypeError):
            return "Unknown"
    
    @staticmethod
    def _get_opportunity_rating(score: float) -> str:
        """Get opportunity rating from value score."""
        try:
            value_score = float(score)
            if value_score >= 25:
                return "🎯 Exceptional Value Opportunity"
            elif value_score >= 20:
                return "💎 High Value Opportunity"
            elif value_score >= 15:
                return "✅ Good Value Opportunity"
            elif value_score >= 10:
                return "📊 Standard Value"
            else:
                return "⚪ Limited Value"
        except (ValueError, TypeError):
            return "⚪ Limited Value"
    
    @staticmethod
    def _identify_arbitrage_opportunity(ownership_pct: float, projected_points: float, grade: str) -> str:
        """Identify specific arbitrage opportunities."""
        try:
            ownership = float(ownership_pct)
            points = float(projected_points)
            
            # High projection + low ownership = arbitrage
            if ownership < 10 and points >= 17:
                return f"{points} projected points with only {ownership}% ownership"
            elif ownership < 25 and points >= 15 and grade in ['A+', 'A']:
                return f"Grade {grade} player with {ownership}% ownership"
            elif ownership < 15 and points >= 12:
                return f"Undervalued at {ownership}% ownership given {points} point projection"
        except (ValueError, TypeError):
            pass
        return ""
    
    @staticmethod
    def _calculate_experience_level(draft_year: int) -> str:
        """Calculate experience level from draft year."""
        try:
            current_year = 2025  # Current season
            years_exp = current_year - int(draft_year)
            
            if years_exp == 1:
                return "Rookie Season"
            elif years_exp == 2:
                return "Second-Year Player"
            elif years_exp <= 4:
                return f"Young Veteran ({years_exp} years)"
            elif years_exp <= 8:
                return f"Experienced Veteran ({years_exp} years)"
            else:
                return f"Long-Term Veteran ({years_exp} years)"
        except (ValueError, TypeError):
            return "Unknown"
    
    @staticmethod
    def _get_age_strategic_advice(age_category: str, position: str) -> str:
        """Get strategic advice based on age category."""
        if not age_category:
            return ""
        
        if "Prime Ascending" in age_category:
            return f"Ideal time to acquire {position} - peak years approaching"
        elif "Peak Window" in age_category:
            return f"Maximum value window for {position} production"
        elif "Decline Phase" in age_category and position == 'RB':
            return "Proceed with caution - RB aging curve concerns"
        elif "Veteran" in age_category:
            return "Experience advantage may offset physical decline"
        else:
            return ""
    
    @staticmethod
    def _generate_recommendation_context(player_data: Dict) -> str:
        """Generate key factors for recommendation."""
        factors = []
        
        # High value opportunities
        value_score = player_data.get('value_opportunity_score', 0)
        if value_score and value_score >= 20:
            factors.append("High value opportunity")
        
        # Favorable matchups
        difficulty = player_data.get('matchup_difficulty')
        if difficulty == 'Easy':
            factors.append("Favorable matchup")
        
        # Low ownership with production
        ownership = player_data.get('weekly_ownership')
        projected = player_data.get('projected_points')
        if ownership and projected and ownership < 25 and projected >= 15:
            factors.append("Low ownership + high projection")
        
        # Age considerations
        age_category = player_data.get('age_category')
        if age_category and "Prime" in age_category:
            factors.append("Prime age window")
        
        return ", ".join(factors) if factors else "Standard evaluation factors"


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