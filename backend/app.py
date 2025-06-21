from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import os
import pandas as pd
import re
import json
from dotenv import load_dotenv
import google.generativeai as genai
import traceback
import logging # Import logging module
from datetime import datetime # Import datetime class
from apscheduler.schedulers.background import BackgroundScheduler
from data_importer import import_data

# Get the absolute path of the directory where this file is located
basedir = os.path.abspath(os.path.dirname(__file__))

# Define log file path (no longer configuring logging.basicConfig here)
log_file_path = os.path.join(basedir, 'ai_response.log')
# Initial log message (optional, as direct writes will handle main debugging)
try:
    with open(log_file_path, 'a') as f:
        f.write(f"{datetime.now()} - --- Backend Server Started ---\n")
except Exception as e:
    pass # Suppress error if logging fails

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey") # Needed for Flask sessions
CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})

# --- Configuration (API key will be passed per request) ---
# Using the latest available preview model as requested
model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-06-17')


# --- Data Caching ---
player_data_cache, player_name_to_id, static_ecr_overall_data, static_ecr_positional_data, static_ecr_rookie_data, player_values_cache, pick_values_cache, combined_player_data_cache = None, None, {}, {}, {}, None, None, None

# --- Data Loading & Helper Functions ---
def load_values_from_csv(file_path):
    try:
        df = pd.read_csv(file_path)
        # Replace NaN with None for JSON compatibility
        df = df.where(pd.notna(df), None)
        # Dynamically find the player name column
        player_col = next((col for col in ['player_name', 'player', 'full_name', 'pick'] if col in df.columns), None)
        if not player_col:
            print(f"❌ FATAL ERROR: Could not find a player name column in {file_path}")
            return None
        
        # Convert DataFrame to dictionary and clean NaN values
        values_dict = {}
        for index, row in df.iterrows():
            player_name = row[player_col]
            player_data = row.to_dict()
            for key, value in player_data.items():
                if pd.isna(value):
                    player_data[key] = None
            values_dict[player_name] = player_data

        print(f"✅ Successfully loaded {len(values_dict)} values from {file_path}.")
        return values_dict
    except FileNotFoundError:
        print(f"❌ FATAL ERROR: The CSV file was not found at '{file_path}'.")
        return None
    except Exception as e:
        print(f"❌ FATAL ERROR loading CSV: {e}")
        traceback.print_exc()
        return None

def load_ecr_data_from_csv(file_path):
    try:
        df = pd.read_csv(file_path)
        print(f"Total rows in {file_path}: {len(df)}")
        if 'ecr_type' not in df.columns:
            print(f"❌ FATAL ERROR: 'ecr_type' column not found in {file_path}. Cannot categorize ECR data.")
            return None, None, None # Return None for all caches if critical column is missing

        print(f"Unique ecr_type values: {df['ecr_type'].unique()}")

        # Convert all NaN values in the DataFrame to None at this stage
        df = df.where(pd.notna(df), None)
        print(f"df head after NaN to None conversion:\n{df.head()}")

        player_col = next((col for col in ['player', 'player_name', 'full_name'] if col in df.columns), None)
        if not player_col:
            print(f"❌ FATAL ERROR: Could not find a player name column (e.g., 'player', 'player_name', 'full_name') in {file_path}")
            return None, None, None
        print(f"Identified player column: '{player_col}'")

        # Helper to create a dictionary from a filtered DataFrame
        def create_ecr_dict(filtered_df):
            ecr_dict = {}
            for index, row in filtered_df.iterrows():
                player_name = row[player_col]
                if player_name is None or str(player_name).lower().strip() == 'nan' or str(player_name).strip() == '':
                    continue # Skip rows with invalid player names

                cleaned_name = normalize_player_name(str(player_name))
                
                if not cleaned_name:
                    continue # Skip if name becomes empty after cleaning

                ecr_dict[cleaned_name] = {
                    'original_name': str(player_name), # Store the original name from CSV
                    'ecr': row.get('ecr'),
                    'sd': row.get('sd'),
                    'best': row.get('best'),
                    'worst': row.get('worst'),
                    'rank_delta': row.get('rank_delta'),
                    'pos': row.get('pos'),
                    'bye': row.get('bye'),
                    'team': row.get('team'),
                    'ecr_type': row.get('ecr_type') # Include ecr_type for debugging/context
                }
            return ecr_dict

        # Filter and create dictionaries for each type
        overall_df = df[df['ecr_type'] == 'bo'].copy()
        positional_df = df[df['ecr_type'] == 'bp'].copy()
        rookie_df = df[df['ecr_type'] == 'drk'].copy() # For rookie rankings

        overall_ecr_dict = create_ecr_dict(overall_df)
        positional_ecr_dict = create_ecr_dict(positional_df)
        rookie_ecr_dict = create_ecr_dict(rookie_df)

        print(f"✅ Successfully loaded {len(overall_ecr_dict)} overall ECR entries (bo).")
        print(f"✅ Successfully loaded {len(positional_ecr_dict)} positional ECR entries (bp).")
        print(f"✅ Successfully loaded {len(rookie_ecr_dict)} rookie ECR entries (drk).")

        return overall_ecr_dict, positional_ecr_dict, rookie_ecr_dict

    except FileNotFoundError:
        print(f"❌ FATAL ERROR: The CSV file was not found at '{file_path}'. Make sure it's in your GitHub repository.")
        return None, None, None
    except Exception as e:
        print(f"❌ FATAL ERROR loading ECR data CSV: {e}")
        traceback.print_exc()
        return None, None, None
    except FileNotFoundError:
        print(f"❌ FATAL ERROR: The CSV file was not found at '{file_path}'. Make sure it's in your GitHub repository.")
        return None
    except Exception as e:
        print(f"❌ FATAL ERROR loading CSV: {e}")
        traceback.print_exc()
        return None

def get_all_players():
    global player_data_cache, player_name_to_id
    if player_data_cache is not None: return
    url = "https://api.sleeper.app/v1/players/nfl"
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        player_data_cache = response.json()


        # Normalize Sleeper player names for consistent keys
        player_name_to_id = { normalize_player_name(p['full_name']): p_id for p_id, p in player_data_cache.items() if p.get('full_name') }
        print(f"✅ Successfully loaded {len(player_data_cache)} players from Sleeper API.")
    except Exception as e:
        print(f"❌ FATAL ERROR fetching players from Sleeper API: {e}")
        traceback.print_exc()
        player_data_cache, player_name_to_id = {}, {}

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

def create_combined_player_data_cache():
    global combined_player_data_cache, static_ecr_overall_data, static_ecr_positional_data, static_ecr_rookie_data
    if not static_ecr_overall_data and not static_ecr_positional_data and not static_ecr_rookie_data:
        print("❌ Cannot create combined player data cache: No ECR data is loaded.")
        return

    temp_combined_data = {}
    
    # Combine data from all ECR sources, prioritizing overall for base ECR if multiple exist
    all_ecr_keys = set(static_ecr_overall_data.keys()) | set(static_ecr_positional_data.keys()) | set(static_ecr_rookie_data.keys())

    for name_key in all_ecr_keys:
        overall_data = static_ecr_overall_data.get(name_key, {})
        positional_data = static_ecr_positional_data.get(name_key, {})
        rookie_data = static_ecr_rookie_data.get(name_key, {})

        # Prioritize overall ECR for the main 'ecr' field, but include both
        # Use overall_data for general player info if available, otherwise positional or rookie
        primary_data_source = overall_data or positional_data or rookie_data

        # Ensure bye_week is an integer or None
        bye_week_val = primary_data_source.get('bye')
        if bye_week_val is not None:
            try:
                bye_week_val = int(bye_week_val)
            except (ValueError, TypeError):
                bye_week_val = None # Set to None if conversion fails

def clean_numeric_value(value):
    if isinstance(value, float) and pd.isna(value):
        return None
    return value

def create_combined_player_data_cache():
    global combined_player_data_cache, static_ecr_overall_data, static_ecr_positional_data, static_ecr_rookie_data
    if not static_ecr_overall_data and not static_ecr_positional_data and not static_ecr_rookie_data:
        print("❌ Cannot create combined player data cache: No ECR data is loaded.")
        return

    temp_combined_data = {}
    
    # Combine data from all ECR sources, prioritizing overall for base ECR if multiple exist
    all_ecr_keys = set(static_ecr_overall_data.keys()) | set(static_ecr_positional_data.keys()) | set(static_ecr_rookie_data.keys())

    for name_key in all_ecr_keys:
        overall_data = static_ecr_overall_data.get(name_key, {})
        positional_data = static_ecr_positional_data.get(name_key, {})
        rookie_data = static_ecr_rookie_data.get(name_key, {})

        # Prioritize overall ECR for the main 'ecr' field, but include both
        # Use overall_data for general player info if available, otherwise positional or rookie
        primary_data_source = overall_data or positional_data or rookie_data

        # Ensure bye_week is an integer or None
        bye_week_val = primary_data_source.get('bye')
        if bye_week_val is not None:
            try:
                bye_week_val = int(bye_week_val)
            except (ValueError, TypeError):
                bye_week_val = None # Set to None if conversion fails

        # Get Sleeper data for years_exp
        sleeper_player_id = player_name_to_id.get(name_key)
        sleeper_info = player_data_cache.get(sleeper_player_id, {}) if sleeper_player_id else {}
        
        # Determine the display name: prioritize original_name from ECR, then Sleeper's full_name, then normalized name
        display_name = primary_data_source.get('original_name') or \
                       sleeper_info.get('full_name') or \
                       primary_data_source.get('name', name_key.title())

        temp_combined_data[name_key] = {
            'name': primary_data_source.get('name', name_key.title()), # Keep this for internal consistency if needed
            'display_name': display_name, # New field for user-facing display
            'team': primary_data_source.get('team', sleeper_info.get('team', 'N/A')),
            'position': primary_data_source.get('pos', sleeper_info.get('position', 'N/A')),
            'bye_week': bye_week_val,
            'years_exp': clean_numeric_value(sleeper_info.get('years_exp')),
            'ecr_overall': clean_numeric_value(overall_data.get('ecr')),
            'sd_overall': clean_numeric_value(overall_data.get('sd')),
            'best_overall': clean_numeric_value(overall_data.get('best')),
            'worst_overall': clean_numeric_value(overall_data.get('worst')),
            'rank_delta_overall': clean_numeric_value(overall_data.get('rank_delta')),
            'ecr_positional': clean_numeric_value(positional_data.get('ecr')),
            'sd_positional': clean_numeric_value(positional_data.get('sd')),
            'best_positional': clean_numeric_value(positional_data.get('best')),
            'worst_positional': clean_numeric_value(positional_data.get('worst')),
            'rank_delta_positional': clean_numeric_value(positional_data.get('rank_delta')),
            'ecr_rookie': clean_numeric_value(rookie_data.get('ecr')),
            'sd_rookie': clean_numeric_value(rookie_data.get('sd')),
            'best_rookie': clean_numeric_value(rookie_data.get('best')),
            'worst_rookie': clean_numeric_value(rookie_data.get('worst')),
            'rank_delta_rookie': clean_numeric_value(rookie_data.get('rank_delta')),
            'is_rookie': name_key in static_ecr_rookie_data # New field: True if player is in rookie ECR data
        }
    
    combined_player_data_cache = temp_combined_data
    print(f"✅ Successfully created combined_player_data_cache with {len(combined_player_data_cache)} players.")

def get_player_context(player_name, ecr_type_preference='overall'):
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
        else:
            # Fallback to original cleaning if no curly braces found
            cleaned_text = re.sub(r'^```json\s*|```\s*$', '', response_text.strip(), flags=re.MULTILINE)
        
        data = json.loads(cleaned_text)
        raw_confidence = data.get('confidence', 'Medium')
        analysis_content = data.get('analysis', 'No analysis provided.')

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
                formatted_analysis.append(f"**{display_key}:** {value.strip()}") # Strip whitespace from value
            analysis_text = "\n".join(formatted_analysis) # Use single newline
        else:
            analysis_text = analysis_content.strip() # Strip whitespace from overall content

        # Further clean up multiple newlines
        analysis_text = re.sub(r'\n\s*\n', '\n\n', analysis_text) # Replace multiple newlines with just two
        analysis_text = re.sub(r'^\s*\n', '', analysis_text) # Remove leading newline if any
        analysis_text = re.sub(r'\n\s*$', '', analysis_text) # Remove trailing newline if any

        emoji_map = {'High': '✅', 'Medium': '🤔', 'Low': '⚠️'}
        confidence_badge = f"**Confidence: {emoji_map.get(confidence, '🤔')} {confidence}**"
        return f"{confidence_badge}\n\n---\n\n{analysis_text}"
    except (json.JSONDecodeError, AttributeError) as e:
        print(f"Error processing AI response: {e}")
        traceback.print_exc()
        # Log the error for debugging
        with open('ai_response.log', 'a') as f:
            f.write(f"{datetime.now()} - Error processing AI response: {str(e)}\n\n")
        # Attempt to extract some meaningful content if possible
        if "confidence" in response_text.lower() and "analysis" in response_text.lower():
            return "There was an error processing the AI's response, but some content was returned. Please check the logs for the raw response."
        return "There was an error processing the AI's response. The format was invalid. Please try again."

PROMPT_PREAMBLE = "You are 'The Analyst,' a data-driven, no-nonsense fantasy football expert providing advice for the upcoming 2025 NFL season. All analysis is for a 12-team, PPR league with standard Yahoo scoring rules..."
JSON_OUTPUT_INSTRUCTION = "Your response MUST be a JSON object with two keys: \"confidence\" and \"analysis\"..."

# --- Existing API Endpoints (modified to pass user_key) ---
@app.route('/api/player_dossier', methods=['POST'])
def player_dossier():
    try:
        user_key = request.headers.get('X-API-Key')
        player_name = request.json.get('player_name')
        ecr_type_pref = request.json.get('ecr_type_preference', 'overall') # Default to overall

        # --- Get Player Static Data ---
        sleeper_key = fuzzy_find_player_key(player_name, player_name_to_id)
        player_id = player_name_to_id.get(sleeper_key) if sleeper_key and player_name_to_id else {}
        player_info_live = player_data_cache.get(player_id, {}) if player_id and player_data_cache else {}
        
        # Get data from combined cache using the normalized player name
        combined_info = combined_player_data_cache.get(normalize_player_name(player_name), {})

        player_data_response = {
            "name": combined_info.get('display_name', player_name.title()), # Use display_name for the dossier header
            "team": combined_info.get('team', 'N/A'),
            "position": combined_info.get('position', 'N/A'),
            "bye_week": combined_info.get('bye_week'),
            "ecr_overall": combined_info.get('ecr_overall'),
            "sd_overall": combined_info.get('sd_overall'),
            "best_overall": combined_info.get('best_overall'),
            "worst_overall": combined_info.get('worst_overall'),
            "rank_delta_overall": combined_info.get('rank_delta_overall'),
            "ecr_positional": combined_info.get('ecr_positional'),
            "sd_positional": combined_info.get('sd_positional'),
            "best_positional": combined_info.get('best_positional'),
            "worst_positional": combined_info.get('worst_positional'),
            "rank_delta_positional": combined_info.get('rank_delta_positional'),
            "ecr_rookie": combined_info.get('ecr_rookie'),
            "sd_rookie": combined_info.get('sd_rookie'),
            "best_rookie": combined_info.get('best_rookie'),
            "worst_rookie": combined_info.get('worst_rookie'),
            "rank_delta_rookie": combined_info.get('rank_delta_rookie'),
        }

        # --- Generate AI Analysis ---
        # Pass the preferred ECR type to get_player_context for AI prompt generation
        prompt = f"{PROMPT_PREAMBLE}\n\n**Task:** First, create a detailed markdown report for the player with headers: ### Depth Chart Role, ### Value Analysis, ### Risk Factors, ### 2025 Outlook, and ### Final Verdict. Then, wrap this entire markdown report inside the 'analysis' key of your JSON output.\n\n**Player Data:**\n{get_player_context(player_name, ecr_type_preference=ecr_type_pref)}\n\n{JSON_OUTPUT_INSTRUCTION}"
        response_text = make_gemini_request(prompt, user_key)
        
        # --- Combine and Return ---
        return jsonify({
            'player_data': player_data_response,
            'analysis': process_ai_response(response_text)
        })
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/rookie_rankings', methods=['POST'])
def rookie_rankings():
    try:
        user_key = request.headers.get('X-API-Key')
        position_filter = request.json.get('position', 'all')
        
        # Filter combined_player_data_cache for rookies based on years_exp
        rookies_for_ranking = []
        for name_key, player_data in combined_player_data_cache.items():
            # A player is considered a rookie if years_exp is 0 (true rookie)
            # and they are present in the static_ecr_rookie_data (drk)
            is_rookie_by_exp = player_data.get('years_exp') is not None and (player_data['years_exp'] == 0)
            is_in_rookie_ecr = name_key in static_ecr_rookie_data # Check if they are in the DRK ECR

            # Only include players if they are explicitly in the rookie ECR data AND have 0 years experience
            if is_in_rookie_ecr and is_rookie_by_exp:
                if position_filter == 'all' or player_data.get('position') == position_filter:
                    rookies_for_ranking.append({
                        'name': player_data.get('display_name', player_data.get('name')), # Prefer display_name
                        'position': player_data.get('position'),
                        'team': player_data.get('team'),
                        'ecr': player_data.get('ecr_rookie'),
                        'sd': player_data.get('sd_rookie'),
                        'best': player_data.get('best_rookie'),
                        'worst': player_data.get('worst_rookie'),
                        'rank_delta': player_data.get('rank_delta_rookie')
                    })
        
        # Sort rookies by their rookie ECR
        sorted_rookies = sorted(rookies_for_ranking, key=lambda x: x.get('ecr') if x.get('ecr') is not None else 999)
        
        rookie_list_for_prompt = [f"- {r['name']} ({r['position']}, {r['team']}) - ECR: {r.get('ecr')}, SD: {r.get('sd')}, Best: {r.get('best')}, Worst: {r.get('worst')}, RankDelta: {r.get('rank_delta')}" for r in sorted_rookies[:50]]
        
        prompt = f"{PROMPT_PREAMBLE}\n\n**Task:** From the provided Rookie Data, create a ranked list of the top 15 rookies. Ensure that the 'position' field in your output matches the position of the player in the provided data. If a position filter was applied, only include players matching that filter.\n\n**Rookie Data:**\n{chr(10).join(rookie_list_for_prompt)}\n\n**Instructions:** Your response MUST be a single, valid JSON object. This object must have one top-level key: \"rookies\". The value of \"rookies\" MUST be a JSON array. Each element in this array MUST be a JSON object representing a rookie. Each rookie object MUST have the following keys, in this exact order, with correctly formatted JSON values: \"rank\" (integer), \"name\" (string), \"position\" (string), \"team\" (string), \"ecr\" (float or null), \"sd\" (float or null), \"best\" (integer or null), \"worst\" (integer or null), \"rank_delta\" (float or null), and \"analysis\" (string, 1-2 sentences). For any numeric field where data is not available, use `null` instead of \"N/A\" or any other string. Ensure all strings are properly quoted and all necessary commas are included between key-value pairs and between objects in the array. Do not include any text or formatting outside of this single JSON object."
        response_text = make_gemini_request(prompt, user_key)
        
        # Use a more robust method to extract the JSON block
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            cleaned_text = json_match.group(0)
        else:
            # Fallback to original cleaning if no curly braces found, though less reliable
            cleaned_text = re.sub(r'^```json\s*|```\s*$', '', response_text.strip(), flags=re.MULTILINE)
        
        try:
            return jsonify(json.loads(cleaned_text).get('rookies', []))
        except json.JSONDecodeError as e:
            error_message = f"Failed to parse AI response for rookies: {e}. Raw response might be malformed."
            print(f"❌ JSON decoding error in rookie_rankings: {e}")
            print(f"Raw response_text: {response_text}")
            print(f"Cleaned_text attempting to parse: {cleaned_text}")
            # Log the error for debugging
            with open('ai_response.log', 'a') as f:
                f.write(f"{datetime.now()} - JSON Decoding Error in rookie_rankings: {str(e)}\n")
                f.write(f"Raw AI Response:\n{response_text}\n\n")
                f.write(f"Cleaned Text Attempted to Parse:\n{cleaned_text}\n\n")
            return jsonify({"error": error_message}), 500
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Failed to generate AI analysis for rookies: {e}"}), 500

@app.route('/api/keeper_evaluation', methods=['POST'])
def keeper_evaluation():
    try:
        user_key = request.headers.get('X-API-Key')
        keepers = request.json.get('keepers')
        ecr_type_pref = request.json.get('ecr_type_preference', 'overall') # Default to overall
        context_str = "\n".join([f"{get_player_context(k['name'], ecr_type_preference=ecr_type_pref)}\n  - Keeper Cost: A round {int(k['round']) - 1} pick\n" + (f"  - Additional Context: {k.get('context') or ''}\n") for k in keepers])
        prompt = f"{PROMPT_PREAMBLE}\n\n**Task:** Analyze these keepers. Compare Cost to ECR. Note bye week overlaps. Prioritize recommendations.\n\n**Data:**\n{context_str}\n\n{JSON_OUTPUT_INSTRUCTION}\n\n**Important:** Ensure your response is a valid JSON object with exactly two keys: 'confidence' (string: 'High', 'Medium', or 'Low') and 'analysis' (string or object). Do not include any text outside the JSON structure."
        response_text = make_gemini_request(prompt, user_key)
        return jsonify({'result': process_ai_response(response_text)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/trade_analyzer', methods=['POST'])
def trade_analyzer():
    try:
        user_key = request.headers.get('X-API-Key')
        scoring_format = request.json.get('scoring_format', 'PPR')
        ecr_type_pref = request.json.get('ecr_type_preference', 'overall') # Default to overall
        my_assets_context = "\n".join([get_player_context(name, ecr_type_preference=ecr_type_pref) if "pick" not in name.lower() else f"- {name}" for name in request.json.get('my_assets', [])])
        partner_assets_context = "\n".join([get_player_context(name, ecr_type_preference=ecr_type_pref) if "pick" not in name.lower() else f"- {name}" for name in request.json.get('partner_assets', [])])
        prompt = f"{PROMPT_PREAMBLE.replace('PPR', scoring_format)}\n\n**Task:** Analyze this trade from the perspective of 'My Team'. Declare a winner or if it is fair. Justify your answer, consistently referring to the sides as 'My Team' and 'The Other Team'.\n\n**Assets My Team Receives:**\n{my_assets_context}\n\n**Assets The Other Team Receives:**\n{partner_assets_context}\n\n{JSON_OUTPUT_INSTRUCTION}"
        response_text = make_gemini_request(prompt, user_key)
        return jsonify({'result': process_ai_response(response_text)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate_tiers', methods=['POST'])
def generate_tiers():
    try:
        user_key = request.headers.get('X-API-Key')
        position = request.json.get('position')
        ecr_type_pref = request.json.get('ecr_type_preference', 'overall') # Default to overall

        # Determine which static ECR data to use based on preference
        if ecr_type_pref == 'overall':
            ecr_source = static_ecr_overall_data
        elif ecr_type_pref == 'positional':
            ecr_source = static_ecr_positional_data
        else:
            ecr_source = static_ecr_overall_data # Fallback

        # Filter ECR data for the specified position and sort by ECR
        player_list_for_tiers = []
        for name, p_data in sorted(ecr_source.items(), key=lambda item: item[1].get('ecr') if item[1].get('ecr') is not None else 999):
            if p_data.get('pos') == position:
                # Get team from combined_player_data_cache for consistency
                combined_info = combined_player_data_cache.get(normalize_player_name(name), {})
                player_list_for_tiers.append({
                    'name': combined_info.get('display_name', name.title()),
                    'position': p_data['pos'],
                    'team': combined_info.get('team', 'N/A'),
                    'ecr': p_data.get('ecr'),
                    'sd': p_data.get('sd'),
                    'best': p_data.get('best'),
                    'worst': p_data.get('worst'),
                    'rank_delta': p_data.get('rank_delta')
                })
        
        # Convert the list of dictionaries to a JSON string for the prompt
        player_list_str = json.dumps(player_list_for_tiers, indent=2)
        
        prompt = f"{PROMPT_PREAMBLE}\n\n**Task:** Group the following {position}s into Tiers. Your response MUST be a single JSON object with one key, 'tiers', whose value is a JSON array. Each object in the 'tiers' array should represent a tier and have the following keys: 'header' (string, e.g., 'Tier 1: Elite Quarterbacks'), 'summary' (string, a 1-sentence summary), and 'players' (JSON array of player objects. Each player object MUST have 'name', 'position', 'team', 'ecr', 'sd', 'best', 'worst', 'rank_delta' keys).\n\n**Example Desired JSON Structure:**\n```json\n{{\n  \"tiers\": [\n    {{\n      \"header\": \"Tier 1: Elite Quarterbacks\",\n      \"summary\": \"These QBs are top-tier.\",\n      \"players\": [\n        {{\"name\": \"Player A\", \"position\": \"QB\", \"team\": \"BUF\", \"ecr\": 1.0, \"sd\": 1.5, \"best\": 1, \"worst\": 3, \"rank_delta\": 0.2}},\n        {{\"name\": \"Player B\", \"position\": \"QB\", \"team\": \"KC\", \"ecr\": 2.0, \"sd\": 1.2, \"best\": 1, \"worst\": 4, \"rank_delta\": -0.1}}\n      ]\n    }}\n  ]\n}}\n```\n\n**Player List for Tiers (JSON Array):**\n{player_list_str}"
        response_text = make_gemini_request(prompt, user_key)
        
        try:
            cleaned_text = re.sub(r'^```json\s*|```\s*$', '', response_text.strip(), flags=re.MULTILINE)
            data = json.loads(cleaned_text)
            tiers_data = data.get('tiers', [])
            return jsonify({'result': tiers_data})
        except (json.JSONDecodeError, AttributeError) as e:
            print(f"Error processing AI response for tiers: {e}")
            return jsonify({'error': f"Failed to parse AI response for tiers: {e}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/find_market_inefficiencies', methods=['POST'])
def find_market_inefficiencies():
    try:
        user_key = request.headers.get('X-API-Key')
        position = request.json.get('position', 'all')
        ecr_type_pref = request.json.get('ecr_type_preference', 'overall') # Default to overall
        
        # Determine which static ECR data to use based on preference
        if ecr_type_pref == 'overall':
            ecr_source = static_ecr_overall_data
        elif ecr_type_pref == 'positional':
            ecr_source = static_ecr_positional_data
        else:
            ecr_source = static_ecr_overall_data # Fallback

        candidates_list = [] # Change to a list of dictionaries to build the data
        # Iterate through the chosen ECR data, sorted by ECR
        for name, ecr_data in sorted(ecr_source.items(), key=lambda item: item[1].get('ecr') if item[1].get('ecr') is not None else 999):
            if position != 'all' and not ecr_data.get('pos', '').startswith(position): continue
            
            # Initialize sleeper_info to an empty dictionary at the start of each iteration
            sleeper_info = {}
            
            # Use combined_player_data_cache to get all relevant ECR data
            combined_info = combined_player_data_cache.get(normalize_player_name(name), {})
            
            # Get sleeper_info if player_id exists
            sleeper_id = player_name_to_id.get(normalize_player_name(name))
            if sleeper_id:
                sleeper_info = player_data_cache.get(sleeper_id, {})

            # Construct a dictionary for each player
            player_context_data = {
                'name': combined_info.get('display_name', name.title()),
                'position': combined_info.get('position', 'N/A'),
                'team': combined_info.get('team', 'N/A'),
                'ecr': combined_info.get(f'ecr_{ecr_type_pref}'),
                'sd': combined_info.get(f'sd_{ecr_type_pref}'),
                'best': combined_info.get(f'best_{ecr_type_pref}'),
                'worst': combined_info.get(f'worst_{ecr_type_pref}'),
                'rank_delta': combined_info.get(f'rank_delta_{ecr_type_pref}'),
                'status': sleeper_info.get('status', 'N/A')
            }
            
            # Convert numeric values to appropriate types or None
            for key in ['ecr', 'sd', 'best', 'worst', 'rank_delta']:
                if isinstance(player_context_data[key], (float, int)):
                    pass # Keep as is
                else:
                    player_context_data[key] = None # Set to None if not numeric

            candidates_list.append(player_context_data)
            if len(candidates_list) >= 150: break
        
        # Convert the list of dictionaries to a formatted string for the prompt
        candidates_str = "\n".join([
            f"- {p['name']} ({p['position']}, {p['team']}): ECR={p['ecr'] or 'N/A'}, SD={p['sd'] or 'N/A'}, Best={p['best'] or 'N/A'}, Worst={p['worst'] or 'N/A'}, RankDelta={p['rank_delta'] or 'N/A'}, Is Rookie: {'Yes' if combined_player_data_cache.get(normalize_player_name(p['name']), {}).get('is_rookie') else 'No'}, Status={p['status'] or 'N/A'}"
            for p in candidates_list
        ])

        prompt = f"{PROMPT_PREAMBLE}\n\n**Task:** Find market inefficiencies. Your response MUST be a single JSON object with two keys: \"sleepers\" and \"busts\". Each key must contain a JSON array of 3-5 player objects. Each player object MUST have the following keys: \"name\" (string), \"justification\" (string), \"confidence\" (string: 'High', 'Medium', or 'Low'), \"ecr\" (float or null), \"sd\" (float or null), \"best\" (integer or null), \"worst\" (integer or null), \"rank_delta\" (float or null), and \"is_rookie\" (boolean). For any numeric field where data is not available, use `null`. For the \"is_rookie\" field, use `true` or `false`.\n\n**Data:**\n{candidates_str}"
        response_text = make_gemini_request(prompt, user_key)
        cleaned_text = re.sub(r'^```json\s*|```\s*$', '', response_text.strip(), flags=re.MULTILINE)
        return jsonify(json.loads(cleaned_text))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/suggest_position', methods=['POST'])
def suggest_position():
    try:
        user_key = request.headers.get('X-API-Key')
        data = request.json
        ecr_type_pref = data.get('ecr_type_preference', 'overall') # Default to overall
        draft_summary = "\n".join([f"{rnd}: Drafted {get_player_context(name, ecr_type_preference=ecr_type_pref)}" for rnd, name in data.get('draft_board', {}).items() if name]) if data.get('draft_board') else "No picks made yet."
        prompt = f"{PROMPT_PREAMBLE}\n\n**Task:** It is Round {data.get('current_round')}. Based on my detailed roster below, what are the top 2 positions I should target? Justify.\n\n**My Draft So Far:**\n{draft_summary}"
        response_text = make_gemini_request(prompt, user_key)
        return jsonify({'result': response_text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/pick_evaluator', methods=['POST'])
def pick_evaluator():
    try:
        user_key = request.headers.get('X-API-Key')
        data = request.json
        ecr_type_pref = data.get('ecr_type_preference', 'overall') # Default to overall
        draft_summary = "\n".join([f"{rnd}: Drafted {get_player_context(name, ecr_type_preference=ecr_type_pref)}" for rnd, name in data.get('draft_board', {}).items() if name]) if data.get('draft_board') else "This is my first pick."
        player_context = get_player_context(data.get('player_to_pick'), ecr_type_preference=ecr_type_pref)
        prompt = f"{PROMPT_PREAMBLE}\n\n**Task:** Analyze if this is a good pick for me in Round {data.get('current_round')}. Compare ECR to the round and evaluate roster fit. Give a 'GOOD PICK', 'SOLID PICK,' or 'POOR PICK' verdict.\n\n**My Draft So Far:**\n{draft_summary}\n\n**Player Being Considered:**\n{player_context}\n\n{JSON_OUTPUT_INSTRUCTION}"
        response_text = make_gemini_request(prompt, user_key)
        return jsonify({'result': process_ai_response(response_text)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/roster_composition_analysis', methods=['POST'])
def roster_composition_analysis():
    try:
        user_key = request.headers.get('X-API-Key')
        composition = request.json.get('composition')
        comp_str = ", ".join([f"{count} {pos}" for pos, count in composition.items()])
        prompt = f"{PROMPT_PREAMBLE}\n\n**Task:** Provide a brief, 2-3 sentence analysis of my roster balance based on these position counts.\n\n**Composition:**\n{comp_str}"
        response_text = make_gemini_request(prompt, user_key)
        return jsonify({'result': process_ai_response(response_text)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/dynasty_player_values')
def dynasty_player_values():
    if not player_values_cache:
        return jsonify([])
    return jsonify(list(player_values_cache.values()))

@app.route('/api/dynasty_pick_values')
def dynasty_pick_values():
    if not pick_values_cache:
        return jsonify([])
    return jsonify(list(pick_values_cache.values()))

@app.route('/api/last_update_date')
def get_last_update_date():
    try:
        file_path = os.path.join(basedir, 'values-players.csv')
        if os.path.exists(file_path):
            timestamp = os.path.getmtime(file_path)
            dt_object = datetime.fromtimestamp(timestamp)
            # Format as "Month Day, Year" e.g., "June 15, 2025"
            formatted_date = dt_object.strftime("%B %d, %Y")
            return jsonify({"last_update": formatted_date})
        else:
            return jsonify({"error": "File not found"}), 404
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/search_players')
def search_players():
    query = request.args.get('query', '').lower()
    if not query:
        return jsonify([])

    # Filter combined_player_data_cache based on query
    # combined_player_data_cache stores data with cleaned names as keys
    # We need to search by the 'name' field within the dictionary values
    results = []
    for player_key, player_data in combined_player_data_cache.items():
        if query in player_data.get('name', '').lower():
            results.append({
                'id': player_key, # Using the cleaned name as ID for simplicity
                'name': player_data.get('name'),
                'position': player_data.get('position'),
                'team': player_data.get('team')
            })
    
    # Limit results to a reasonable number, e.g., 10
    return jsonify(results[:10])

@app.route('/api/all_player_names_with_data')
def all_player_names_with_data():
    if not combined_player_data_cache:
        return jsonify({"error": "Combined player data cache not available."}), 500
    
    # Convert the dictionary of players into a list of players
    player_list = []
    for player_data in combined_player_data_cache.values():
        # Ensure all values are JSON-serializable (None for NaN)
        cleaned_player_data = {k: (None if isinstance(v, float) and pd.isna(v) else v) for k, v in player_data.items()}
        # For autocomplete, we will provide a specific 'autocomplete_name' field
        player_list.append({
            'name': cleaned_player_data.get('name'), # This is the normalized name, used for staticData keying
            'display_name': cleaned_player_data.get('display_name'), # The full name for display
            'autocomplete_name': cleaned_player_data.get('display_name', cleaned_player_data.get('name')), # The name to be used by autocomplete.js
            'position': cleaned_player_data.get('position'),
            'team': cleaned_player_data.get('team'),
            'ecr_overall': cleaned_player_data.get('ecr_overall'),
            'ecr_positional': cleaned_player_data.get('ecr_positional'),
            'years_exp': cleaned_player_data.get('years_exp')
        })
    
    # Debugging: Print a sample of the data being sent to the frontend
    if player_list:
        print(f"Sample of player_list sent to frontend (first entry):\n{player_list[0]}")
    
    return jsonify(player_list)

@app.route('/api/trending_players')
def trending_players():
    try:
        url = "https://api.sleeper.app/v1/players/nfl/trending/add?lookback_hours=48&limit=25"
        print(f"DEBUG: Fetching trending players from: {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        sleeper_trending_data = response.json()
        print(f"DEBUG: Received {len(sleeper_trending_data)} trending players from Sleeper API.")
        
        detailed_list = []
        for player in sleeper_trending_data:
            if player_id := player.get('player_id'):
                player_details = player_data_cache.get(player_id)
                if player_details and player_details.get('full_name'):
                    cleaned_name = normalize_player_name(player_details.get('full_name')) # Use normalize_player_name
                    # Use overall ECR for trending players by default
                    static_info = static_ecr_overall_data.get(cleaned_name, {}) 
                    detailed_list.append({
                        'name': player_details.get('full_name'),
                        'team': player_details.get('team', 'N/A'),
                        'position': player_details.get('position', 'N/A'),
                        'adds': player.get('count', 0),
                        'ecr': clean_numeric_value(static_info.get('ecr')), 
                        'sd': clean_numeric_value(static_info.get('sd')),
                        'best': clean_numeric_value(static_info.get('best')),
                        'worst': clean_numeric_value(static_info.get('worst')),
                        'rank_delta': clean_numeric_value(static_info.get('rank_delta'))
                    })
        print(f"DEBUG: Returning {len(detailed_list)} detailed trending players.")
        return jsonify(detailed_list)
    except requests.exceptions.RequestException as req_e:
        print(f"ERROR: Request to Sleeper API failed: {req_e}")
        traceback.print_exc()
        return jsonify({"error": f"Failed to fetch trending data from Sleeper API: {req_e}"}), 500
    except Exception as e:
        print(f"ERROR: An unexpected error occurred in trending_players: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/waiver_swap_analysis', methods=['POST'])
def waiver_swap_analysis():
    try:
        user_key = request.headers.get('X-API-Key')
        data = request.json
        roster = data.get('roster', {})
        player_to_add = data.get('player_to_add')
        ecr_type_pref = data.get('ecr_type_preference', 'overall') # Default to overall

        if not roster or not player_to_add:
            return jsonify({"error": "Roster and player_to_add are required."}), 400

        roster_context = "\n".join([f"({pos}) {get_player_context(name, ecr_type_preference=ecr_type_pref)}" for pos, name in roster.items() if name])
        waiver_player_context = get_player_context(player_to_add, ecr_type_preference=ecr_type_pref)

        prompt = f"""
{PROMPT_PREAMBLE}

**Task:** You are tasked with evaluating a potential waiver wire transaction. A user wants to pick up a specific player and needs to know if it's a good move and, if so, who to drop from their current roster.

1.  **Analyze the Waiver Candidate:** Evaluate the player to be added based on their current performance, role, and future outlook for the 2025 season.
2.  **Analyze the User's Roster:** Examine the user's current roster to identify strengths, weaknesses, and potential players who could be dropped. Pay close attention to underperforming players, players with difficult upcoming schedules, or positions where the user has a surplus.
3.  **Formulate a Recommendation:**
    *   Provide a clear "verdict" on whether to **ADD** the player or **DO NOT ADD** the player.
    *   If the verdict is to ADD the player, you MUST recommend a specific player to **DROP**.
    *   Justify your recommendation with a detailed analysis, comparing the waiver candidate directly to the suggested drop candidate. Consider factors like positional need, bye weeks, short-term vs. long-term value, and overall impact on the team's strength.

**My Current Roster:**
{roster_context}

**Waiver Wire Player to Consider Adding:**
{waiver_player_context}

{JSON_OUTPUT_INSTRUCTION}
"""
        response_text = make_gemini_request(prompt, user_key)
        return jsonify({'result': process_ai_response(response_text)})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/waiver_wire_analysis', methods=['POST'])
def waiver_wire_analysis():
    try:
        user_key = request.headers.get('X-API-Key')
        team_roster = request.json.get('team_roster', []) # List of player names on user's team
        ecr_type_pref = request.json.get('ecr_type_preference', 'overall') # Default to overall
        
        # Determine which static ECR data to use for available players
        if ecr_type_pref == 'overall':
            ecr_source = static_ecr_overall_data
        elif ecr_type_pref == 'positional':
            ecr_source = static_ecr_positional_data
        else:
            ecr_source = static_ecr_overall_data # Fallback

        all_players_data = []
        for name, data in ecr_source.items(): 
            player_info = player_data_cache.get(player_name_to_id.get(name, ''), {})
            if player_info.get('full_name') and player_info.get('full_name').lower().strip() not in [p.lower().strip() for p in team_roster]:
                all_players_data.append({
                    'name': player_info.get('full_name'),
                    'pos': data.get('pos', 'N/A'), 
                    'ecr': data.get('ecr'), 
                    'sd': data.get('sd'),
                    'best': data.get('best'),
                    'worst': data.get('worst'),
                    'rank_delta': data.get('rank_delta'),
                    'bye_week': data.get('bye'), 
                    'team': data.get('team', 'N/A'), 
                })
        
        # Sort available players by ECR
        sorted_available_players = sorted(all_players_data, key=lambda x: x.get('ecr') if x.get('ecr') is not None else 999)[:50] # Top 50 available

        roster_context = "\n".join([get_player_context(player_name, ecr_type_preference=ecr_type_pref) for player_name in team_roster])
        available_players_context = "\n".join([
            f"- {p['name']} ({p['pos']}, {p['team']}) - ECR: {p['ecr'] or 'N/A'}, SD: {p['sd'] or 'N/A'}, Best: {p['best'] or 'N/A'}, Worst: {p['worst'] or 'N/A'}, RankDelta: {p['rank_delta'] or 'N/A'}"
            for p in sorted_available_players
        ])

        prompt = f"{PROMPT_PREAMBLE}\n\n**Task:** Analyze my current roster and the top available waiver wire players. Recommend 3-5 players to add, justifying each recommendation based on Yahoo PPR scoring, current performance, and potential upside. Also, suggest 1-2 players to drop if necessary.\n\n**My Current Roster:**\n{roster_context}\n\n**Top Available Waiver Wire Players:**\n{available_players_context}\n\n{JSON_OUTPUT_INSTRUCTION}"
        response_text = make_gemini_request(prompt, user_key)
        return jsonify({'result': process_ai_response(response_text)})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/debug_rookie_ecr_data', methods=['GET'])
def debug_rookie_ecr_data():
    if not static_ecr_rookie_data:
        return jsonify({"error": "Rookie ECR data not loaded."}), 500
    
    # Return all rookie ECR data
    all_rookie_data = []
    for player_name, data in static_ecr_rookie_data.items():
        all_rookie_data.append(data)
    return jsonify(all_rookie_data)

@app.route('/api/debug_all_player_sd_data', methods=['GET'])
def debug_all_player_sd_data():
    if not combined_player_data_cache:
        return jsonify({"error": "Combined player data cache not loaded."}), 500
    
    all_sd_data = []
    for player_key, player_data in combined_player_data_cache.items():
        all_sd_data.append({
            'name': player_data.get('display_name', player_data.get('name')),
            'sd_overall': player_data.get('sd_overall'),
            'sd_positional': player_data.get('sd_positional')
        })
    return jsonify(all_sd_data)

@app.route('/api/debug_player_cache/<player_name>', methods=['GET'])
def debug_player_cache(player_name):
    global player_data_cache, player_name_to_id
    if player_data_cache is None:
        get_all_players() # Attempt to load if not already loaded

    if player_data_cache:
        normalized_search_name = normalize_player_name(player_name)
        
        # Try to find by normalized name first
        player_id = player_name_to_id.get(normalized_search_name)
        if player_id:
            return jsonify(player_data_cache.get(player_id))
        
        # If not found by normalized name, try fuzzy match on original full_name
        for p_id, p_data in player_data_cache.items():
            if p_data.get('full_name'):
                if normalized_search_name in normalize_player_name(p_data['full_name']):
                    return jsonify(p_data) # Return first fuzzy match based on normalized names
        
        # If still not found, return a sample of player_name_to_id for debugging
        sample_keys = list(player_name_to_id.keys())[:20] # Get first 20 keys
        return jsonify({
            "message": f"Player '{player_name}' (normalized: '{normalized_search_name}') not found in cache.",
            "debug_info": {
                "sample_player_name_to_id_keys": sample_keys,
                "total_player_name_to_id_keys": len(player_name_to_id)
            }
        }), 404
    return jsonify({"message": "Player data cache not loaded"}), 500

if __name__ == '__main__':
    try:
        import_data()  # Initial data import
        scheduler = BackgroundScheduler()
        scheduler.add_job(func=import_data, trigger="interval", hours=24)
        scheduler.start()

        get_all_players()
        csv_file_path = os.path.join(basedir, 'db_fpecr_latest.csv')
        
        # Load different ECR types into their respective caches
        static_ecr_overall_data, static_ecr_positional_data, static_ecr_rookie_data = load_ecr_data_from_csv(csv_file_path)
        
        player_values_cache = load_values_from_csv(os.path.join(basedir, 'values-players.csv'))
        pick_values_cache = load_values_from_csv(os.path.join(basedir, 'values-picks.csv'))

        # Create the combined player data cache at startup
        create_combined_player_data_cache()

        print(f"Player data cache size: {len(player_data_cache) if player_data_cache else 0}")
        print(f"Static Overall ECR data size: {len(static_ecr_overall_data) if static_ecr_overall_data else 0}")
        print(f"Static Positional ECR data size: {len(static_ecr_positional_data) if static_ecr_positional_data else 0}")
        print(f"Static Rookie ECR data size: {len(static_ecr_rookie_data) if static_ecr_rookie_data else 0}")

        if static_ecr_overall_data and player_data_cache is not None: # Check if at least overall ECR is loaded
            app.run(debug=True, host='0.0.0.0', port=5001) # Bind to 0.0.0.0 for Render deployment
        else:
            print("Application will not start because essential data failed to load.")
            # sys.exit(1) # Uncomment to force exit if data loading fails
    except Exception as e:
        print(f"❌ FATAL ERROR during application startup: {e}")
        traceback.print_exc()
