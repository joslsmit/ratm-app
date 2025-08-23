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
        """
        COMPREHENSIVE player dossier with multi-dimensional analysis.
        
        Enhancement: Combines ECR + projections + matchups + trends + age trajectory
        """
        
        context = f"{base_context}\n\n**COMPREHENSIVE PLAYER ANALYSIS:**"
        
        # SECTION 1: ENHANCED FANTASY RANKINGS & CONSENSUS (Existing + Enhanced)
        ecr_overall = player_data.get('ecr_overall')
        ecr_positional = player_data.get('ecr_positional')
        position = player_data.get('position', 'N/A')
        
        if ecr_overall:
            context += f"\n\n**📊 FANTASY RANKINGS & CONSENSUS:**"
            context += f"\n- Overall ECR: #{ecr_overall:.1f}"
            
            # Enhanced consensus analysis
            sd_overall = player_data.get('sd_overall')
            if sd_overall:
                consensus_level = ContextFormatter._get_consensus_strength(sd_overall)
                expert_agreement = ContextFormatter._get_expert_agreement_description(sd_overall)
                context += f" (SD: {sd_overall:.1f} - {consensus_level})"
                context += f"\n- Expert Agreement: {expert_agreement}"
            
            # Positional context
            if ecr_positional:
                tier_info = ContextFormatter._get_detailed_tier_classification(position, ecr_positional)
                context += f"\n- Positional Rank: {position}#{int(ecr_positional)} → {tier_info}"
            
            # Ranking range and volatility
            best_rank = player_data.get('best_overall')
            worst_rank = player_data.get('worst_overall')
            if best_rank and worst_rank:
                range_analysis = ContextFormatter._analyze_ranking_range(best_rank, worst_rank)
                context += f"\n- Expert Range: #{int(best_rank)} to #{int(worst_rank)} ({range_analysis})"
        
        # SECTION 2: WEEKLY PROJECTION ANALYSIS (New)
        projected_points = player_data.get('projected_points')
        start_sit_grade = player_data.get('start_sit_grade')
        projection_confidence = player_data.get('projection_confidence')
        
        if projected_points or start_sit_grade:
            context += f"\n\n**📈 WEEKLY OUTLOOK ANALYSIS:**"
            
            if projected_points:
                projection_tier = ContextFormatter._get_detailed_projection_tier(projected_points, position)
                weekly_upside = ContextFormatter._calculate_weekly_upside(projected_points, position)
                context += f"\n- Weekly Projection: {projected_points} points ({projection_tier})"
                context += f"\n- Scoring Potential: {weekly_upside}"
            
            if start_sit_grade:
                grade_confidence = player_data.get('grade_confidence_score', 0)
                grade_analysis = ContextFormatter._get_comprehensive_grade_analysis(start_sit_grade, grade_confidence)
                context += f"\n- Expert Grade: {start_sit_grade} ({grade_analysis})"
            
            if projection_confidence:
                context += f"\n- Projection Reliability: {projection_confidence}"
            
            # Weekly vs Season ECR comparison
            weekly_ecr = player_data.get('weekly_ecr')
            if weekly_ecr and ecr_overall:
                ecr_variance = ContextFormatter._analyze_ecr_variance(weekly_ecr, ecr_overall)
                context += f"\n- Weekly vs Season Form: {ecr_variance}"
        
        # SECTION 3: MATCHUP AND SCHEDULE ANALYSIS (New)
        opponent = player_data.get('opponent')
        matchup_difficulty = player_data.get('matchup_difficulty')
        home_away = player_data.get('home_away')
        
        if opponent or matchup_difficulty:
            context += f"\n\n**⚔️ MATCHUP & SCHEDULE ANALYSIS:**"
            
            if opponent and home_away:
                location_advantage = ContextFormatter._get_location_advantage(home_away, position)
                context += f"\n- Current Matchup: {ContextFormatter._get_location_icon(home_away)} {opponent} ({location_advantage})"
            
            if matchup_difficulty:
                difficulty_analysis = ContextFormatter._get_detailed_matchup_analysis(matchup_difficulty, position, opponent)
                context += f"\n- Matchup Assessment: {ContextFormatter._get_difficulty_icon(matchup_difficulty)} {difficulty_analysis}"
            
            # Upcoming schedule preview (if available)
            schedule_outlook = ContextFormatter._generate_schedule_outlook(player_data)
            if schedule_outlook:
                context += f"\n- Schedule Outlook: {schedule_outlook}"
        
        # SECTION 4: MARKET VALUE & OWNERSHIP ANALYSIS (New)
        weekly_ownership = player_data.get('weekly_ownership')
        value_opportunity_score = player_data.get('value_opportunity_score')
        value_1qb = player_data.get('value_1qb')
        
        if weekly_ownership is not None or value_opportunity_score or value_1qb:
            context += f"\n\n**💰 MARKET VALUE & OWNERSHIP:**"
            
            if weekly_ownership is not None:
                ownership_analysis = ContextFormatter._get_detailed_ownership_analysis(weekly_ownership, projected_points)
                context += f"\n- Current Ownership: {weekly_ownership}% ({ownership_analysis})"
            
            if value_1qb:
                value_analysis = ContextFormatter._get_value_tier_analysis(value_1qb, position)
                context += f"\n- Market Value: {value_1qb} ({value_analysis})"
            
            if value_opportunity_score:
                opportunity_analysis = ContextFormatter._get_detailed_opportunity_analysis(value_opportunity_score, weekly_ownership)
                context += f"\n- Value Opportunity: {opportunity_analysis}"
            
            # Identify specific market inefficiencies
            market_inefficiency = ContextFormatter._identify_dossier_market_inefficiency(
                weekly_ownership, projected_points, ecr_overall
            )
            if market_inefficiency:
                context += f"\n- 🚨 **MARKET INSIGHT**: {market_inefficiency}"
        
        # SECTION 5: AGE & DEVELOPMENT TRAJECTORY (New)
        age = player_data.get('age')
        age_category = player_data.get('age_category')
        draft_year = player_data.get('draft_year')
        
        if age or age_category or draft_year:
            context += f"\n\n**📅 AGE & DEVELOPMENT TRAJECTORY:**"
            
            if age and age_category:
                age_trajectory = ContextFormatter._get_detailed_age_trajectory(age, age_category, position)
                context += f"\n- Age Analysis: {age} years old ({age_trajectory})"
            
            if draft_year:
                experience_analysis = ContextFormatter._get_detailed_experience_analysis(draft_year, position)
                career_stage = ContextFormatter._get_career_stage_analysis(draft_year, age, position)
                context += f"\n- Experience Level: {experience_analysis}"
                context += f"\n- Career Stage: {career_stage}"
            
            # Performance trajectory modeling
            trajectory_model = ContextFormatter._generate_performance_trajectory(age, position, draft_year)
            if trajectory_model:
                context += f"\n- Performance Outlook: {trajectory_model}"
        
        # SECTION 6: TREND ANALYSIS & MOMENTUM (Enhanced)
        rank_delta = player_data.get('rank_delta_overall')
        if rank_delta is not None:
            context += f"\n\n**📊 TREND ANALYSIS & MOMENTUM:**"
            
            trend_analysis = ContextFormatter._get_detailed_trend_analysis(rank_delta, ecr_overall)
            momentum_indicator = ContextFormatter._get_momentum_indicator(rank_delta)
            context += f"\n- Recent Trend: {momentum_indicator} ({trend_analysis})"
            
            # Trend sustainability analysis
            trend_sustainability = ContextFormatter._analyze_trend_sustainability(rank_delta, sd_overall)
            context += f"\n- Trend Outlook: {trend_sustainability}"
        
        # SECTION 7: COMPREHENSIVE PLAYER SUMMARY (New)
        player_summary = ContextFormatter._generate_comprehensive_player_summary(player_data)
        if player_summary:
            context += f"\n\n**🎯 PLAYER SUMMARY & STRATEGY:**"
            context += f"\n{player_summary}"
        
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

    # --- Enhanced Player Dossier Helper Methods ---
    
    @staticmethod
    def _get_consensus_strength(sd_overall: float) -> str:
        """Get consensus strength description from standard deviation."""
        if sd_overall < 2:
            return "Very High Consensus"
        elif sd_overall < 4:
            return "High Consensus"
        elif sd_overall < 6:
            return "Medium Consensus"
        elif sd_overall < 8:
            return "Low Consensus"
        else:
            return "Very Low Consensus"
    
    @staticmethod
    def _get_expert_agreement_description(sd_overall: float) -> str:
        """Get detailed expert agreement description."""
        if sd_overall < 2:
            return "Strong expert consensus with minimal disagreement"
        elif sd_overall < 4:
            return "Good expert agreement with some variance"
        elif sd_overall < 6:
            return "Moderate agreement with noticeable expert differences"
        elif sd_overall < 8:
            return "Significant expert disagreement, wide opinion range"
        else:
            return "Very high disagreement, experts widely split"
    
    @staticmethod
    def _get_detailed_tier_classification(position: str, ecr_positional: float) -> str:
        """Enhanced tier classification with detailed context."""
        if position == 'QB':
            if ecr_positional <= 6:
                return "QB1 Elite (Must-Start Every Week)"
            elif ecr_positional <= 12:
                return "QB1 (Reliable Weekly Starter)"
            elif ecr_positional <= 18:
                return "QB2 High-End (Streaming/Backup)"
            elif ecr_positional <= 24:
                return "QB2 (Matchup-Dependent Start)"
            else:
                return "QB3+ (Deep League/Emergency Only)"
        
        elif position in ['RB', 'WR']:
            if ecr_positional <= 12:
                return f"{position}1 Elite (League Winner Potential)"
            elif ecr_positional <= 24:
                return f"{position}1 (Consistent Weekly Starter)"
            elif ecr_positional <= 36:
                return f"{position}2 (Solid Weekly Option)"
            elif ecr_positional <= 48:
                return f"{position}2 (Flex/Depth Piece)"
            else:
                return f"{position}3+ (Handcuff/Lottery Ticket)"
        
        elif position == 'TE':
            if ecr_positional <= 6:
                return "TE1 Elite (Significant Positional Advantage)"
            elif ecr_positional <= 12:
                return "TE1 (Reliable Weekly Starter)"
            else:
                return "TE2+ (Streaming/Matchup Play)"
        
        return "Standard Tier"
    
    @staticmethod
    def _analyze_ranking_range(best_rank: float, worst_rank: float) -> str:
        """Analyze ranking range for expert consensus insights."""
        range_width = worst_rank - best_rank
        if range_width <= 10:
            return "Tight range - strong consensus"
        elif range_width <= 20:
            return "Moderate range - some disagreement"
        elif range_width <= 40:
            return "Wide range - significant disagreement"
        else:
            return "Very wide range - major expert divide"
    
    @staticmethod
    def _get_detailed_projection_tier(projected_points: float, position: str) -> str:
        """Detailed projection analysis with context."""
        if position == 'QB':
            if projected_points >= 25:
                return "Elite Performance Week (Top-3 Potential)"
            elif projected_points >= 22:
                return "Excellent Week (QB1 Production)"
            elif projected_points >= 18:
                return "Solid Week (QB2 Production)"
            elif projected_points >= 15:
                return "Serviceable Week (Streaming Viable)"
            else:
                return "Challenging Week (Limited Upside)"
        
        elif position == 'RB':
            if projected_points >= 20:
                return "Elite Performance Week (RB1 Ceiling)"
            elif projected_points >= 16:
                return "Strong Week (RB1/2 Production)"
            elif projected_points >= 12:
                return "Solid Week (RB2/Flex Production)"
            elif projected_points >= 8:
                return "Serviceable Week (Deep Flex Option)"
            else:
                return "Limited Week (Touchdown Dependent)"
        
        elif position == 'WR':
            if projected_points >= 18:
                return "Elite Week (WR1 Ceiling)"
            elif projected_points >= 15:
                return "Strong Week (WR1/2 Production)"
            elif projected_points >= 12:
                return "Solid Week (WR2/Flex Production)"
            elif projected_points >= 8:
                return "Serviceable Week (Deep Flex Option)"
            else:
                return "Limited Week (Touchdown Dependent)"
        
        elif position == 'TE':
            if projected_points >= 15:
                return "Elite Week (TE1 Ceiling)"
            elif projected_points >= 12:
                return "Strong Week (TE1 Production)"
            elif projected_points >= 8:
                return "Solid Week (Streaming Viable)"
            elif projected_points >= 5:
                return "Limited Week (Touchdown Dependent)"
            else:
                return "Poor Week (Avoid If Possible)"
        
        return "Standard Week"
    
    @staticmethod
    def _calculate_weekly_upside(projected_points: float, position: str) -> str:
        """Calculate weekly upside potential."""
        if position == 'QB' and projected_points >= 22:
            return "High weekly ceiling with QB1 upside"
        elif position in ['RB', 'WR'] and projected_points >= 16:
            return "Strong weekly upside with top-tier potential"
        elif position == 'TE' and projected_points >= 12:
            return "Excellent weekly ceiling for position"
        elif projected_points >= 10:
            return "Solid weekly upside for fantasy value"
        else:
            return "Limited weekly ceiling, TD-dependent"
    
    @staticmethod
    def _get_comprehensive_grade_analysis(grade: str, confidence_score: int) -> str:
        """Get comprehensive analysis of expert grades."""
        grade_map = {
            'A+': 'Must-start with extreme confidence',
            'A': 'Strong start recommendation',
            'B+': 'Good start option',
            'B': 'Decent start choice',
            'B-': 'Borderline start consideration',
            'C+': 'Risky start, better options likely available',
            'C': 'Avoid unless desperate',
            'D': 'Strong avoid recommendation',
            'F': 'Do not start under any circumstances'
        }
        
        base_analysis = grade_map.get(grade, 'Standard recommendation')
        
        if confidence_score >= 80:
            return f"{base_analysis} - Very high expert confidence"
        elif confidence_score >= 60:
            return f"{base_analysis} - Moderate expert confidence"
        else:
            return f"{base_analysis} - Low expert confidence"
    
    @staticmethod
    def _analyze_ecr_variance(weekly_ecr: float, season_ecr: float) -> str:
        """Analyze variance between weekly and season ECR."""
        variance = weekly_ecr - season_ecr
        if variance <= -5:
            return "Much better weekly outlook than season ranking"
        elif variance <= -2:
            return "Better weekly form than season average"
        elif variance <= 2:
            return "Weekly form matches season expectations"
        elif variance <= 5:
            return "Weekly outlook below season ranking"
        else:
            return "Much worse weekly outlook than season ranking"
    
    @staticmethod
    def _get_location_advantage(home_away: str, position: str) -> str:
        """Get location advantage analysis."""
        if home_away == 'Home':
            return "Home field advantage, crowd support"
        elif home_away == 'Away':
            return "Road game, potential crowd disadvantage"
        else:
            return "Neutral site"
    
    @staticmethod
    def _get_location_icon(home_away: str) -> str:
        """Get location icon."""
        if home_away == 'Home':
            return "🏠"
        elif home_away == 'Away':
            return "✈️"
        else:
            return "🏟️"
    
    @staticmethod
    def _get_detailed_matchup_analysis(difficulty: str, position: str, opponent: str = None) -> str:
        """Get detailed matchup analysis."""
        if difficulty == 'Easy':
            return f"Favorable matchup for {position} production - exploit opportunity"
        elif difficulty == 'Tough':
            return f"Challenging matchup may limit {position} ceiling - proceed carefully"
        elif difficulty == 'Moderate':
            return f"Neutral matchup for {position} - standard expectations"
        else:
            return f"Standard matchup expectations for {position}"
    
    @staticmethod
    def _generate_schedule_outlook(player_data: Dict) -> str:
        """Generate upcoming schedule outlook."""
        # This would require schedule data - placeholder for now
        return None
    
    @staticmethod
    def _get_detailed_ownership_analysis(ownership_pct: float, projected_points: float = None) -> str:
        """Get detailed ownership analysis."""
        ownership_tier = ContextFormatter._get_ownership_tier(ownership_pct)
        
        if ownership_pct < 25 and projected_points and projected_points >= 15:
            return f"{ownership_tier} - Potential value opportunity"
        elif ownership_pct > 75:
            return f"{ownership_tier} - Widely recognized value"
        else:
            return ownership_tier
    
    @staticmethod
    def _get_value_tier_analysis(value: float, position: str) -> str:
        """Get value tier analysis."""
        if value >= 15:
            return f"Premium {position} value"
        elif value >= 10:
            return f"Strong {position} value"
        elif value >= 5:
            return f"Solid {position} value"
        elif value >= 0:
            return f"Replacement-level {position}"
        else:
            return f"Below replacement-level {position}"
    
    @staticmethod
    def _get_detailed_opportunity_analysis(opportunity_score: float, ownership_pct: float = None) -> str:
        """Get detailed opportunity analysis."""
        base_rating = ContextFormatter._get_opportunity_rating(opportunity_score)
        
        if ownership_pct and ownership_pct < 25 and opportunity_score >= 20:
            return f"{base_rating} - Low ownership amplifies opportunity"
        else:
            return base_rating
    
    @staticmethod
    def _identify_dossier_market_inefficiency(ownership_pct: float = None, projected_points: float = None, ecr_overall: float = None) -> str:
        """Identify market inefficiencies for player dossier."""
        if ownership_pct is None or not projected_points or not ecr_overall:
            return None
        
        # Underowned stars
        if ownership_pct < 50 and ecr_overall < 30 and projected_points > 16:
            return f"Underowned elite player - Only {ownership_pct}% rostered despite top-30 ECR and {projected_points} projected points"
        
        # Overowned disappointments  
        if ownership_pct > 80 and projected_points < 12:
            return f"Potential overvalued player - {ownership_pct}% owned but only {projected_points} projected points"
        
        # Hidden gems
        if ownership_pct < 25 and projected_points > 15:
            return f"Potential waiver target - Strong {projected_points} projection with low {ownership_pct}% ownership"
        
        return None
    
    @staticmethod
    def _get_detailed_age_trajectory(age: int, age_category: str, position: str) -> str:
        """Get detailed age trajectory analysis."""
        if "Prime" in age_category or "Peak" in age_category:
            return f"In performance prime for {position} - optimal fantasy window"
        elif "Ascending" in age_category or "Development" in age_category:
            return f"Ascending trajectory for {position} - growth potential ahead"
        elif "Decline" in age_category or "Risk" in age_category:
            return f"Age-related concerns for {position} - monitor closely"
        else:
            return f"Standard age trajectory for {position}"
    
    @staticmethod
    def _get_detailed_experience_analysis(draft_year: int, position: str) -> str:
        """Get detailed experience analysis."""
        experience = ContextFormatter._calculate_experience_level(draft_year)
        
        if "Rookie" in experience:
            return f"{experience} - Learning curve expected"
        elif "Second-Year" in experience:
            return f"{experience} - Sophomore development phase"
        elif "Young Veteran" in experience:
            return f"{experience} - Prime development window"
        elif "Experienced Veteran" in experience:
            return f"{experience} - Peak performance window"
        else:
            return f"{experience} - Late career phase"
    
    @staticmethod
    def _get_career_stage_analysis(draft_year: int, age: int = None, position: str = None) -> str:
        """Get career stage analysis."""
        current_year = 2025
        years_exp = current_year - draft_year
        
        if years_exp <= 2:
            return "Early Career - Development phase with upside potential"
        elif years_exp <= 5:
            return "Prime Development - Peak growth window"
        elif years_exp <= 8:
            return "Peak Performance - Maximum value window"
        elif years_exp <= 12:
            return "Veteran Stage - Experience vs decline balance"
        else:
            return "Late Career - Decline risk considerations"
    
    @staticmethod
    def _generate_performance_trajectory(age: int = None, position: str = None, draft_year: int = None) -> str:
        """Generate performance trajectory model."""
        if not age or not position:
            return None
            
        if position == 'RB':
            if age <= 25:
                return "Prime RB years - expect peak performance"
            elif age <= 28:
                return "Good RB production window remaining"
            else:
                return "Age-related decline risk increasing"
        elif position == 'QB':
            if age <= 30:
                return "Ascending or peak QB performance window"
            elif age <= 35:
                return "Prime QB performance years"
            else:
                return "Experience vs physical decline balance"
        else:
            if age <= 27:
                return "Prime years ahead or current"
            elif age <= 32:
                return "Peak performance window"
            else:
                return "Age-related decline considerations"
    
    @staticmethod
    def _get_detailed_trend_analysis(rank_delta: float, ecr_overall: float = None) -> str:
        """Get detailed trend analysis."""
        if rank_delta <= -3:
            return "Strong upward momentum in expert rankings"
        elif rank_delta <= -1:
            return "Moderate upward trend in expert opinion"
        elif rank_delta <= 1:
            return "Stable ranking with minimal movement"
        elif rank_delta <= 3:
            return "Moderate downward trend in expert opinion"
        else:
            return "Strong downward momentum in expert rankings"
    
    @staticmethod
    def _get_momentum_indicator(rank_delta: float) -> str:
        """Get momentum indicator."""
        if rank_delta <= -2:
            return "📈 Rising"
        elif rank_delta >= 2:
            return "📉 Falling"
        else:
            return "➡️ Stable"
    
    @staticmethod
    def _analyze_trend_sustainability(rank_delta: float, sd_overall: float = None) -> str:
        """Analyze trend sustainability."""
        if not sd_overall:
            return "Monitor for trend continuation"
            
        if abs(rank_delta) >= 3 and sd_overall < 4:
            return "Strong trend with expert consensus - likely sustainable"
        elif abs(rank_delta) >= 3 and sd_overall >= 6:
            return "Strong trend but high disagreement - monitor closely"
        elif abs(rank_delta) <= 1:
            return "Stable ranking - minimal trend to sustain"
        else:
            return "Moderate trend - watch for continuation or reversal"
    
    @staticmethod
    def _generate_comprehensive_player_summary(player_data: Dict) -> str:
        """Generate overall player summary with key insights."""
        summary_elements = []
        
        # Tier summary
        ecr_overall = player_data.get('ecr_overall')
        if ecr_overall:
            if ecr_overall <= 24:
                summary_elements.append("Elite fantasy asset")
            elif ecr_overall <= 60:
                summary_elements.append("Solid roster contributor")
            else:
                summary_elements.append("Depth/speculative option")
        
        # Projection summary
        projected_points = player_data.get('projected_points')
        if projected_points:
            if projected_points >= 18:
                summary_elements.append("high weekly upside")
            elif projected_points >= 14:
                summary_elements.append("reliable weekly production")
            else:
                summary_elements.append("touchdown-dependent scoring")
        
        # Age summary
        age_category = player_data.get('age_category')
        if age_category:
            if "Prime" in age_category or "Peak" in age_category:
                summary_elements.append("in performance prime")
            elif "Ascending" in age_category or "Development" in age_category:
                summary_elements.append("ascending trajectory")
            elif "Decline" in age_category or "Risk" in age_category:
                summary_elements.append("age-related concerns")
        
        # Ownership summary
        weekly_ownership = player_data.get('weekly_ownership')
        if weekly_ownership is not None:
            if weekly_ownership < 50:
                summary_elements.append("potential market inefficiency")
            elif weekly_ownership > 90:
                summary_elements.append("widely recognized value")
        
        if summary_elements:
            return f"- **Overall Assessment**: {', '.join(summary_elements).capitalize()}"
        
        return None


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