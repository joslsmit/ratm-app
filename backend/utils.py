import re
import json
import pandas as pd
import google.generativeai as genai
from datetime import datetime

def normalize_player_name(name):
    """Normalizes player names for consistent matching."""
    if not name:
        return None
    # Remove common suffixes like Jr., Sr., III, IV, V
    name = re.sub(r'\s(Jr|Sr|[IVX]+)\.?$', '', name, flags=re.IGNORECASE).strip()
    # Remove non-alphanumeric characters except spaces
    name = re.sub(r'[^a-zA-Z0-9\s]', '', name).strip()
    return name.lower()

def fuzzy_find_player_key(name_to_search, key_dictionary):
    if not key_dictionary: return None
    normalized_search_name = normalize_player_name(name_to_search)
    if normalized_search_name in key_dictionary: return normalized_search_name
    
    # Fallback to partial match if exact normalized name not found
    for key in key_dictionary:
        if normalized_search_name and normalized_search_name in key: return key
    return None

def get_player_context(player_name, ecr_type_preference='overall', combined_player_data_cache=None, player_name_to_id=None, player_data_cache=None, static_ecr_overall_data=None, static_ecr_positional_data=None, static_ecr_rookie_data=None):
    sleeper_key = fuzzy_find_player_key(player_name, player_name_to_id)
    
    # Determine which static ECR data to use based on preference
    if ecr_type_preference == 'overall':
        static_ecr_source = static_ecr_overall_data
    elif ecr_type_preference == 'positional':
        static_ecr_source = static_ecr_positional_data
    elif ecr_type_preference == 'rookie':
        static_ecr_source = static_ecr_rookie_data
    else: # Default to overall if preference is unknown or not provided
        static_ecr_source = static_ecr_overall_data

    static_key = fuzzy_find_player_key(player_name, static_ecr_source)
    
    player_id = player_name_to_id.get(sleeper_key) if sleeper_key and player_name_to_id else None
    # Use combined_player_data_cache for all player context
    player_data = combined_player_data_cache.get(normalize_player_name(player_name), {})
    
    context_lines = []
    full_name = player_data.get('name', player_name)
    context_lines.append(f"- Player: {full_name} ({player_data.get('position', 'N/A')}, {player_data.get('team', 'N/A')})")
    
    # Get years_exp from combined_player_data_cache
    years_exp = player_data.get('years_exp')
    if years_exp is not None:
        context_lines.append(f"  - Experience: {int(years_exp)} years")
    else:
        context_lines.append(f"  - Experience: N/A years") # Indicate if data is missing

    # Add is_rookie status
    is_rookie_status = "Yes" if player_data.get('is_rookie') else "No"
    context_lines.append(f"  - Is Rookie: {is_rookie_status}")

    # Use the appropriate ECR and related stats based on preference
    ecr_label = f"{ecr_type_preference.title()} ECR"
    ecr_value = player_data.get(f'ecr_{ecr_type_preference}')
    ecr_display = f"{ecr_value:.1f}" if isinstance(ecr_value, (int, float)) else "N/A"
    context_lines.append(f"  - {ecr_label}: {ecr_display}")
    
    if sd := player_data.get(f'sd_{ecr_type_preference}'): context_lines.append(f"  - Std Dev: {sd:.2f}")
    if best := player_data.get(f'best_{ecr_type_preference}'): context_lines.append(f"  - Best Rank: {int(best)}")
    if worst := player_data.get(f'worst_{ecr_type_preference}'): context_lines.append(f"  - Worst Rank: {int(worst)}")
    if rank_delta := player_data.get(f'rank_delta_{ecr_type_preference}'): context_lines.append(f"  - Rank Delta (1W): {rank_delta:.1f}")
    if bye_week := player_data.get('bye_week'): context_lines.append(f"  - Bye Week: {int(bye_week)}")
    
    return "\n".join(context_lines)

def make_gemini_request(prompt, user_api_key):
    if not user_api_key: raise Exception("API key is missing from the request.")
    genai.configure(api_key=user_api_key)
    try:
        model = genai.GenerativeModel('gemini-2.5-flash-lite')
        response = model.generate_content(prompt)
    except Exception as e:
        print(f"DEBUG: Error during generate_content: {e}")
        raise e
    if not response.candidates:
        print("AI model did not return a valid response (no candidates).")
        return "The AI model did not return a valid response. The content may have been blocked due to safety settings."
    
    raw_response_text = response.text
    return raw_response_text

def process_ai_response(response_text):
    try:
        # Log the raw response for debugging
        with open('ai_response.log', 'a') as f:
            f.write(f"{datetime.now()} - Raw AI Response:\n{response_text}\n\n")
        
        # Attempt to find the JSON block more robustly
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            cleaned_text = json_match.group(0)
            try:
                data = json.loads(cleaned_text)
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
                # Return raw response as fallback
                return response_text.strip()
        else:
            # If no JSON block found, treat entire response as plain text
            return response_text.strip()

        raw_confidence = data.get('confidence', 'Medium')
        analysis_content = data.get('analysis', 'No analysis provided.')

        # Attempt to parse analysis_content if it's a string that looks like JSON
        if isinstance(analysis_content, str):
            try:
                # Try to load it as JSON. If successful, it's a dict.
                parsed_analysis = json.loads(analysis_content)
                if isinstance(parsed_analysis, dict):
                    analysis_content = parsed_analysis
            except json.JSONDecodeError:
                # If it's not a valid JSON string, keep it as is (string)
                pass

        if isinstance(raw_confidence, float):
            if raw_confidence >= 0.8:
                confidence = "High"
            elif raw_confidence >= 0.5:
                confidence = "Medium"
            else:
                confidence = "Low"
        elif isinstance(raw_confidence, str):
            confidence = raw_confidence.title()
        else: # Default if unexpected type
            confidence = "Medium"

        if isinstance(analysis_content, dict):
            formatted_analysis = []
            for key, value in analysis_content.items():
                display_key = key.replace('_', ' ').title()
                # Ensure value is a string before stripping
                formatted_analysis.append(f"**{display_key}:** {str(value).strip()}")
            analysis_text = "\n".join(formatted_analysis)
        else:
            analysis_text = str(analysis_content).strip() # Ensure content is a string before stripping

        # Further clean up multiple newlines
        analysis_text = re.sub(r'\n\s*\n', '\n\n', analysis_text) # Replace multiple newlines with just two
        analysis_text = re.sub(r'^\s*\n', '', analysis_text) # Remove leading newline if any
        analysis_text = re.sub(r'\n\s*$', '', analysis_text) # Remove trailing newline if any

        emoji_map = {'High': '✅', 'Medium': '🤔', 'Low': '⚠️'}
        confidence_badge = f"**Confidence: {emoji_map.get(confidence, '🤔')} {confidence}**"
        return f"{confidence_badge}\n\n---\n\n{analysis_text}"
    except Exception as e:
        print(f"Error processing AI response: {e}")
        traceback.print_exc()
        # Log the error for debugging
        with open('ai_response.log', 'a') as f:
            f.write(f"{datetime.now()} - Error processing AI response: {str(e)}\n\n")
        # Attempt to extract some meaningful content if possible
        if "confidence" in response_text.lower() and "analysis" in response_text.lower():
            return "There was an error processing the AI's response, but some content was returned. Please check the logs for the raw response."
        return "There was an error processing the AI's response. The format was invalid. Please try again."


def process_ai_response_v2(response_text, endpoint_name="unknown"):
    """
    Enhanced AI response processing with validation and fallback.
    Maintains compatibility with existing frontend expectations.
    """
    try:
        # Log for debugging (same as original)
        with open('ai_response.log', 'a') as f:
            f.write(f"{datetime.now()} - Enhanced Processing ({endpoint_name}):\n{response_text}\n\n")
        
        # Clean response text
        cleaned_response = response_text.strip()
        
        # Extract JSON block using same method as original
        start_idx = cleaned_response.find('{')
        end_idx = cleaned_response.rfind('}') + 1
        
        if start_idx == -1 or end_idx == 0:
            print(f"No JSON found in response for {endpoint_name}")
            return process_ai_response(response_text)  # Fallback to original
            
        json_str = cleaned_response[start_idx:end_idx]
        
        try:
            parsed_response = json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"JSON decode error for {endpoint_name}: {e}")
            return process_ai_response(response_text)  # Fallback to original
        
        # Validate required fields
        if 'confidence' not in parsed_response:
            print(f"Missing confidence field for {endpoint_name}")
            return process_ai_response(response_text)  # Fallback to original
            
        if 'analysis' not in parsed_response:
            print(f"Missing analysis field for {endpoint_name}")
            return process_ai_response(response_text)  # Fallback to original
        
        # Normalize confidence to ensure valid values
        raw_confidence = parsed_response['confidence']
        if raw_confidence not in ['High', 'Medium', 'Low']:
            # Handle legacy numeric confidence or invalid values
            if isinstance(raw_confidence, (int, float)):
                if raw_confidence >= 0.8:
                    confidence = 'High'
                elif raw_confidence >= 0.5:
                    confidence = 'Medium'
                else:
                    confidence = 'Low'
            else:
                confidence = 'Medium'  # Safe default
        else:
            confidence = raw_confidence
            
        # Get analysis text and ensure it's a string
        analysis_text = str(parsed_response['analysis']).strip()
        
        # Clean up analysis formatting (remove excessive newlines)
        analysis_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', analysis_text)
        analysis_text = re.sub(r'^\s*\n+', '', analysis_text)
        analysis_text = re.sub(r'\n+\s*$', '', analysis_text)
        
        # Format output exactly like original function for frontend compatibility
        emoji_map = {'High': '✅', 'Medium': '🤔', 'Low': '⚠️'}
        confidence_badge = f"**Confidence: {emoji_map.get(confidence, '🤔')} {confidence}**"
        
        return f"{confidence_badge}\n\n---\n\n{analysis_text}"
        
    except Exception as e:
        # Log error and fallback to original function - NEVER crash
        print(f"Enhanced processing failed for {endpoint_name}: {e}")
        with open('ai_response.log', 'a') as f:
            f.write(f"{datetime.now()} - Enhanced processing error ({endpoint_name}): {str(e)}\n\n")
        return process_ai_response(response_text)


# --- Enhanced Waiver Wire Analysis Utility Functions ---

def calculate_matchup_difficulty(opponent_team, position):
    """
    Calculate matchup difficulty rating based on opponent defensive strength.
    
    Args:
        opponent_team: Three-letter team code (e.g., 'BAL', 'CLE')
        position: Player position (QB, RB, WR, TE)
    
    Returns:
        String: 'Easy', 'Moderate', 'Tough', or 'Unknown'
    """
    
    # Defensive strength rankings by position (2025 season data)
    # These would be updated with current season defensive rankings
    defensive_rankings = {
        'QB': {
            'Easy': ['JAC', 'CAR', 'NE', 'NYG', 'LV', 'WAS', 'CHI', 'ARI'],
            'Tough': ['BAL', 'PIT', 'BUF', 'DEN', 'SF', 'DAL', 'NYJ', 'MIA']
        },
        'RB': {
            'Easy': ['DET', 'NO', 'IND', 'WAS', 'CAR', 'ARI', 'LAC', 'ATL'], 
            'Tough': ['BAL', 'SF', 'BUF', 'PIT', 'PHI', 'KC', 'LV', 'CHI']
        },
        'WR': {
            'Easy': ['ARI', 'WAS', 'JAC', 'CAR', 'LV', 'LAC', 'IND', 'ATL'],
            'Tough': ['BAL', 'BUF', 'SF', 'DAL', 'DEN', 'NYJ', 'PIT', 'MIA']
        },
        'TE': {
            'Easy': ['CAR', 'WAS', 'IND', 'JAC', 'ARI', 'ATL', 'LV', 'CHI'],
            'Tough': ['SF', 'BAL', 'BUF', 'PIT', 'DEN', 'NYJ', 'MIA', 'DAL']
        }
    }
    
    if not opponent_team or position not in defensive_rankings:
        return 'Unknown'
    
    position_rankings = defensive_rankings.get(position, {})
    
    if opponent_team in position_rankings.get('Easy', []):
        return 'Easy'
    elif opponent_team in position_rankings.get('Tough', []):
        return 'Tough'
    else:
        return 'Moderate'

def calculate_value_opportunity_score(projected_points, ownership_pct, confidence_score):
    """
    Calculate ownership arbitrage opportunity score.
    
    Purpose: Identify players with high projections but low ownership
    
    Args:
        projected_points: Weekly projected fantasy points
        ownership_pct: Platform ownership percentage (0-100)
        confidence_score: Start/sit grade confidence (30-95)
    
    Returns:
        Float: Opportunity score (higher = better value opportunity)
    """
    
    if not all([projected_points, ownership_pct is not None, confidence_score]):
        return 0.0
    
    try:
        # Base value from projected points
        base_value = float(projected_points)
        
        # Ownership factor (lower ownership = higher opportunity)
        # Scale: 0-25% ownership gets bonus, >75% gets penalty
        if ownership_pct < 25:
            ownership_multiplier = 1.5  # High opportunity
        elif ownership_pct > 75:
            ownership_multiplier = 0.7  # Low opportunity
        else:
            ownership_multiplier = 1.0  # Neutral
        
        # Confidence factor from expert grades
        confidence_multiplier = confidence_score / 100.0
        
        # Calculate final opportunity score
        opportunity_score = base_value * ownership_multiplier * confidence_multiplier
        
        return round(opportunity_score, 2)
        
    except (ValueError, TypeError):
        return 0.0

def calculate_age_category(age, position):
    """
    Calculate age-based player category for roster decisions.
    
    Args:
        age: Player age in years
        position: Player position
        
    Returns:
        String: Age category description
    """
    
    if not age:
        return 'Unknown'
    
    try:
        age_float = float(age)
        
        # Position-specific age curves
        if position in ['RB']:
            if age_float < 24:
                return 'Prime Ascending (Peak Years Ahead)'
            elif age_float < 27:
                return 'Peak Window (Maximum Value)'
            elif age_float < 30:
                return 'Decline Phase (Use Caution)'
            else:
                return 'High Risk (Age-Related Decline)'
                
        elif position in ['QB']:
            if age_float < 27:
                return 'Development Phase (Ascending)'
            elif age_float < 35:
                return 'Prime Years (Peak Performance)'
            else:
                return 'Veteran (Experience vs. Decline)'
                
        elif position in ['WR', 'TE']:
            if age_float < 25:
                return 'Early Career (Development)'
            elif age_float < 30:
                return 'Prime Years (Peak Performance)'
            elif age_float < 33:
                return 'Veteran (Experience Advantage)'
            else:
                return 'Late Career (Decline Risk)'
        else:
            # Generic age categories
            if age_float < 25:
                return 'Young Player'
            elif age_float < 30:
                return 'Prime Years'
            else:
                return 'Veteran'
                
    except (ValueError, TypeError):
        return 'Unknown'

def calculate_projection_confidence(start_sit_grade, ecr_overall, weekly_ecr):
    """
    Calculate overall projection confidence based on multiple factors.
    
    Args:
        start_sit_grade: Letter grade (A+, A, B, etc.)
        ecr_overall: Season-long ECR ranking
        weekly_ecr: Weekly ECR ranking
        
    Returns:
        String: Confidence level description
    """
    
    confidence_factors = []
    
    # Grade-based confidence
    if start_sit_grade:
        if start_sit_grade in ['A+', 'A']:
            confidence_factors.append('High')
        elif start_sit_grade in ['A-', 'B+', 'B']:
            confidence_factors.append('Medium')
        else:
            confidence_factors.append('Low')
    
    # ECR consistency check
    if ecr_overall and weekly_ecr:
        try:
            ecr_diff = abs(float(ecr_overall) - float(weekly_ecr))
            if ecr_diff < 5:
                confidence_factors.append('Consistent')
            elif ecr_diff > 15:
                confidence_factors.append('Volatile')
        except (ValueError, TypeError):
            pass
    
    # Determine overall confidence
    if 'High' in confidence_factors and 'Consistent' in confidence_factors:
        return 'Very High Confidence'
    elif 'High' in confidence_factors:
        return 'High Confidence'
    elif 'Medium' in confidence_factors:
        return 'Moderate Confidence'
    elif 'Volatile' in confidence_factors:
        return 'Low Confidence (Volatile)'
    else:
        return 'Standard Confidence'

def get_weekly_outlook(player_data, weeks_ahead=4):
    """
    Generate short-term outlook based on projections and schedule.
    
    Args:
        player_data: Enhanced player data dictionary
        weeks_ahead: Number of weeks to analyze
        
    Returns:
        String: Outlook description
    """
    
    outlook_factors = []
    
    # Projected points assessment
    projected_points = player_data.get('projected_points')
    if projected_points:
        if projected_points >= 20:
            outlook_factors.append('High Scoring Potential')
        elif projected_points >= 15:
            outlook_factors.append('Solid Production Expected')
        else:
            outlook_factors.append('Limited Upside')
    
    # Matchup assessment
    matchup_difficulty = player_data.get('matchup_difficulty')
    if matchup_difficulty == 'Easy':
        outlook_factors.append('Favorable Matchup')
    elif matchup_difficulty == 'Tough':
        outlook_factors.append('Challenging Matchup')
    
    # Confidence assessment
    grade_confidence = player_data.get('grade_confidence_score', 0)
    if grade_confidence >= 85:
        outlook_factors.append('Expert Confidence')
    
    # Combine factors into outlook
    if 'High Scoring Potential' in outlook_factors and 'Favorable Matchup' in outlook_factors:
        return 'Excellent Short-term Outlook'
    elif 'Solid Production Expected' in outlook_factors:
        return 'Favorable Short-term Outlook'
    elif 'Challenging Matchup' in outlook_factors:
        return 'Mixed Short-term Outlook'
    else:
        return 'Standard Short-term Outlook'
