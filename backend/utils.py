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
        model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-06-17')
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
