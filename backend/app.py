from flask import Flask, request, jsonify, redirect, url_for, session
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

print("--- APP.PY VERSION 3.0 LOADED ---") # Unique identifier for debugging

# Get the absolute path of the directory where this file is located
basedir = os.path.abspath(os.path.dirname(__file__))

# Define log file path (no longer configuring logging.basicConfig here)
log_file_path = os.path.join(basedir, 'ai_response.log')
# Initial log message (optional, as direct writes will handle main debugging)
try:
    with open(log_file_path, 'a') as f:
        f.write(f"{datetime.now()} - --- Backend Server Started ---\n")
except Exception as e:
    print(f"Error writing initial log message: {e}")

load_dotenv()
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "supersecretkey") # Needed for Flask sessions
CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}})

# --- Configuration (API key will be passed per request) ---
# Using the latest available preview model as requested
model = genai.GenerativeModel('gemini-1.5-flash')

# --- Yahoo OAuth 2.0 Configuration ---
YAHOO_CLIENT_ID = os.getenv("YAHOO_CLIENT_ID")
YAHOO_CLIENT_SECRET = os.getenv("YAHOO_CLIENT_SECRET")
# This must match the redirect URI in your Yahoo Developer App settings
YAHOO_REDIRECT_URI = os.getenv("YAHOO_REDIRECT_URI", "http://localhost:5001/auth/yahoo/callback") 

# Yahoo OAuth 2.0 URLs
AUTHORIZATION_URL = "https://api.login.yahoo.com/oauth2/request_auth"
TOKEN_URL = "https://api.login.yahoo.com/oauth2/get_token"
PROFILE_URL = "https://social.yahooapis.com/v1/user/me/profile?format=json" # Example API endpoint
# Using Flask's session to store tokens. A server-side session would be more secure,
# but for ease of use for a novice, the default client-side session is a good starting point.
# Ensure FLASK_SECRET_KEY is strong and kept secret in production.

# --- Data Caching ---
player_data_cache, player_name_to_id, static_adp_data, player_values_cache, pick_values_cache, weekly_data_cache = None, None, {}, None, None, None

# --- Data Loading & Helper Functions ---
def load_weekly_data_from_csv(file_path):
    try:
        df = pd.read_csv(file_path)
        # Corrected column names for weekly data
        weekly_dict = {row['player_name'].lower().strip(): row.to_dict() for index, row in df.iterrows() if 'player_name' in df.columns}
        print(f"✅ Successfully loaded {len(weekly_dict)} weekly data entries from {file_path}.")
        return weekly_dict
    except FileNotFoundError:
        print(f"❌ FATAL ERROR: The weekly data CSV file was not found at '{file_path}'.")
        return None
    except Exception as e:
        print(f"❌ FATAL ERROR loading weekly data CSV: {e}")
        traceback.print_exc()
        return None

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

def load_adp_from_csv(file_path):
    try:
        df = pd.read_csv(file_path)
        # Dynamically find the player name column, including 'player'
        player_col = next((col for col in ['Player', 'player_name', 'full_name', 'player'] if col in df.columns), None)
        if not player_col:
            print(f"❌ FATAL ERROR: Could not find a player name column in {file_path}")
            return None

        df_processed = df[[player_col, 'pos', 'ecr']].copy() # Changed 'adp' to 'ecr' based on db_fpecr_latest.csv
        def clean_player_name(player_name):
            return re.sub(r'\s[A-Z]{2,4}$', '', str(player_name)).lower().strip()
        df_processed['Player_Clean'] = df_processed[player_col].apply(clean_player_name)
        adp_dict = {row['Player_Clean']: {'adp': row['ecr'], 'pos_rank': row['pos']} for index, row in df_processed.iterrows() if row['Player_Clean'] and row['Player_Clean'] != 'nan'}
        print(f"✅ Successfully loaded {len(adp_dict)} players from {file_path}.")
        return adp_dict
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
        player_name_to_id = { p['full_name'].lower().strip(): p_id for p_id, p in player_data_cache.items() if p.get('full_name') }
        print(f"✅ Successfully loaded {len(player_data_cache)} players from Sleeper API.")
    except Exception as e:
        print(f"❌ FATAL ERROR fetching players from Sleeper API: {e}")
        traceback.print_exc()
        player_data_cache, player_name_to_id = {}, {}

def fuzzy_find_player_key(name_to_search, key_dictionary):
    if not key_dictionary: return None
    lower_name = name_to_search.lower().strip()
    if lower_name in key_dictionary: return lower_name
    for key in key_dictionary:
        if lower_name in key: return key
    return None

def get_player_context(player_name):
    sleeper_key = fuzzy_find_player_key(player_name, player_name_to_id)
    static_key = fuzzy_find_player_key(player_name, static_adp_data)
    player_id = player_name_to_id.get(sleeper_key) if sleeper_key and player_name_to_id else None
    player_info_live = player_data_cache.get(player_id, {}) if player_id and player_data_cache else {}
    player_info_static = static_adp_data.get(static_key, {}) if static_key and static_adp_data else {}
    context_lines = []
    full_name = player_info_live.get('full_name', player_name)
    context_lines.append(f"- Player: {full_name} ({player_info_live.get('position', 'N/A')}, {player_info_live.get('team', 'N/A')})")
    context_lines.append(f"  - Status: {player_info_live.get('status', 'N/A')}")
    context_lines.append(f"  - Age: {player_info_live.get('age', 'N/A')}, Experience: {player_info_live.get('years_exp', 'N/A')} years")
    if bye_week := player_info_live.get('bye_week'): context_lines.append(f"  - Bye Week: {bye_week}")
    pos_rank = player_info_static.get('pos_rank', 'N/A')
    adp = player_info_static.get('adp')
    adp_display = f"{adp:.1f}" if adp else "N/A"
    context_lines.append(f"  - Consensus Positional Rank: {pos_rank}")
    context_lines.append(f"  - Consensus Market ADP: {adp_display}")
    return "\n".join(context_lines)

def make_gemini_request(prompt, user_api_key):
    if not user_api_key: raise Exception("API key is missing from the request.")
    genai.configure(api_key=user_api_key)
    response = model.generate_content(prompt)
    if not response.candidates:
        print("AI model did not return a valid response (no candidates).")
        return "The AI model did not return a valid response. The content may have been blocked due to safety settings."
    
    raw_response_text = response.text
    # Directly write to log file for robust debugging
    try:
        with open(log_file_path, 'a') as f: # 'a' for append mode
            f.write("\n" + "="*50 + "\n")
            f.write("--- RAW AI RESPONSE (FOR DEBUGGING) ---\n")
            f.write(raw_response_text + "\n")
            f.write("="*50 + "\n\n")
    except Exception as log_e:
        print(f"Error writing to log file: {log_e}")
    return raw_response_text

def process_ai_response(response_text):
    try:
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
                formatted_analysis.append(f"**{display_key}:** {value}")
            analysis_text = "\n\n".join(formatted_analysis)
        else:
            analysis_text = analysis_content

        emoji_map = {'High': '✅', 'Medium': '🤔', 'Low': '⚠️'}
        confidence_badge = f"**Confidence: {emoji_map.get(confidence, '🤔')} {confidence}**"
        return f"{confidence_badge}\n\n---\n\n{analysis_text}"
    except (json.JSONDecodeError, AttributeError) as e:
        print(f"Error processing AI response: {e}")
        traceback.print_exc()
        return response_text

PROMPT_PREAMBLE = "You are 'The Analyst,' a data-driven, no-nonsense fantasy football expert providing advice for the upcoming 2025 NFL season. All analysis is for a 12-team, PPR league with standard Yahoo scoring rules..."
JSON_OUTPUT_INSTRUCTION = "Your response MUST be a JSON object with two keys: \"confidence\" and \"analysis\"..."

# --- Existing API Endpoints (modified to pass user_key) ---
@app.route('/api/player_dossier', methods=['POST'])
def player_dossier():
    try:
        user_key = request.headers.get('X-API-Key')
        player_name = request.json.get('player_name')

        # --- Get Player Static Data ---
        sleeper_key = fuzzy_find_player_key(player_name, player_name_to_id)
        static_key = fuzzy_find_player_key(player_name, static_adp_data)
        player_id = player_name_to_id.get(sleeper_key) if sleeper_key and player_name_to_id else None
        player_info_live = player_data_cache.get(player_id, {}) if player_id and player_data_cache else {}
        player_info_static = static_adp_data.get(static_key, {}) if static_key and static_adp_data else {}
        
        player_data_response = {
            "name": player_info_live.get('full_name', player_name.title()),
            "team": player_info_live.get('team', 'N/A'),
            "position": player_info_live.get('position', 'N/A'),
            "pos_rank": player_info_static.get('pos_rank', 'N/A'),
            "adp": player_info_static.get('adp'),
            "bye_week": player_info_live.get('bye_week')
        }

        # --- Generate AI Analysis ---
        prompt = f"{PROMPT_PREAMBLE}\n\n**Task:** First, create a detailed markdown report for the player with headers: ### Depth Chart Role, ### Value Analysis, ### Risk Factors, ### 2025 Outlook, and ### Final Verdict. Then, wrap this entire markdown report inside the 'analysis' key of your JSON output.\n\n**Player Data:**\n{get_player_context(player_name)}\n\n{JSON_OUTPUT_INSTRUCTION}"
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
        rookies = [
            {'name': p.get('full_name'),'position': p.get('position'),'team': p.get('team'), **static_adp_data.get(p.get('full_name', '').lower().strip(), {})}
            for p_id, p in player_data_cache.items() if p.get('years_exp') == 0 and (position_filter == 'all' or p.get('position') == position_filter) and p.get('full_name')
        ]
        sorted_rookies = sorted(rookies, key=lambda x: x.get('adp') or 999)
        rookie_list_for_prompt = [f"- {r['name']} ({r['position']}, {r['team']}) - ADP: {r.get('adp') or 'N/A'}" for r in sorted_rookies[:50]]
        prompt = f"{PROMPT_PREAMBLE}\n\n**Task:** Create a ranked list of rookies.\n\n**Rookie Data:**\n{chr(10).join(rookie_list_for_prompt)}\n\n**Instructions:** Your response MUST be a single JSON object with one key: \"rookies\". The value must be a JSON array of objects. For each of the top 15 rookies, create an object with these keys: \"rank\", \"name\", \"position\", \"team\", \"adp\" (string or \"N/A\"), \"pos_rank\", and \"analysis\" (a 1-2 sentence summary of their outlook)."
        response_text = make_gemini_request(prompt, user_key)
        cleaned_text = re.sub(r'^```json\s*|```\s*$', '', response_text.strip(), flags=re.MULTILINE)
        return jsonify(json.loads(cleaned_text).get('rookies', []))
    except Exception as e:
        return jsonify({"error": f"Failed to generate AI analysis for rookies: {e}"}), 500

@app.route('/api/keeper_evaluation', methods=['POST'])
def keeper_evaluation():
    try:
        user_key = request.headers.get('X-API-Key')
        keepers = request.json.get('keepers')
        context_str = "\n".join([f"{get_player_context(k['name'])}\n  - Keeper Cost: A round {int(k['round']) - 1} pick\n" for k in keepers])
        prompt = f"{PROMPT_PREAMBLE}\n\n**Task:** Analyze these keepers. Compare Cost to ADP. Note bye week overlaps. Prioritize recommendations.\n\n**Data:**\n{context_str}\n\n{JSON_OUTPUT_INSTRUCTION}"
        response_text = make_gemini_request(prompt, user_key)
        return jsonify({'result': process_ai_response(response_text)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/trade_analyzer', methods=['POST'])
def trade_analyzer():
    try:
        user_key = request.headers.get('X-API-Key')
        my_assets_context = "\n".join([get_player_context(name) if "pick" not in name.lower() else f"- {name}" for name in request.json.get('my_assets', [])])
        partner_assets_context = "\n".join([get_player_context(name) if "pick" not in name.lower() else f"- {name}" for name in request.json.get('partner_assets', [])])
        prompt = f"{PROMPT_PREAMBLE}\n\n**Task:** Analyze this trade. Declare a winner or if it is fair. Justify your answer.\n\n**Assets My Team Receives:**\n{my_assets_context}\n\n**Assets My Partner Receives:**\n{partner_assets_context}\n\n{JSON_OUTPUT_INSTRUCTION}"
        response_text = make_gemini_request(prompt, user_key)
        return jsonify({'result': process_ai_response(response_text)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate_tiers', methods=['POST'])
def generate_tiers():
    try:
        user_key = request.headers.get('X-API-Key')
        position = request.json.get('position')
        player_list_str = "\n".join([f"- {name.title()} ({p_data['pos_rank']}, {player_data_cache.get(player_name_to_id.get(name), {}).get('team', 'N/A')}) - ADP: {p_data['adp']}" for name, p_data in sorted(static_adp_data.items(), key=lambda item: item[1]['adp']) if p_data.get('pos_rank', '').startswith(position)])
        prompt = f"{PROMPT_PREAMBLE}\n\n**Task:** Group the following {position}s into Tiers. Your response MUST be a single JSON object with one key, 'tiers', whose value is a JSON array. Each object in the 'tiers' array should represent a tier and have the following keys: 'header' (string, e.g., 'Tier 1: Elite Quarterbacks'), 'summary' (string, a 1-sentence summary), and 'players' (JSON array of player names as strings).\n\n**Example Desired JSON Structure:**\n```json\n{{\n  \"tiers\": [\n    {{\n      \"header\": \"Tier 1: Elite Quarterbacks\",\n      \"summary\": \"These QBs are top-tier.\",\n      \"players\": [\"Player A\", \"Player B\"]\n    }},\n    {{\n      \"header\": \"Tier 2: High-Upside Quarterbacks\",\n      \"summary\": \"These QBs have potential.\",\n      \"players\": [\"Player C\", \"Player D\"]\n    }}\n  ]\n}}\n```\n\n**Player List for Tiers:**\n{player_list_str}"
        response_text = make_gemini_request(prompt, user_key)
        
        try:
            cleaned_text = re.sub(r'^```json\s*|```\s*$', '', response_text.strip(), flags=re.MULTILINE)
            data = json.loads(cleaned_text)
            tiers_data = data.get('tiers', [])
            
            markdown_output = []
            for tier in tiers_data:
                header = tier.get('header', 'Untitled Tier')
                summary = tier.get('summary', 'No summary provided.')
                players = tier.get('players', [])
                
                markdown_output.append(f"## {header}")
                markdown_output.append(f"{summary}")
                for player in players:
                    markdown_output.append(f"* {player}")
                markdown_output.append("") # Add a blank line between tiers
            
            return jsonify({'result': "\n".join(markdown_output).strip()})
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
        candidates_str = ""
        for name, adp_data in sorted(static_adp_data.items(), key=lambda item: item[1].get('adp') or 999):
            if position != 'all' and not adp_data.get('pos_rank', '').startswith(position): continue
            if player_id := player_name_to_id.get(name):
                sleeper_info = player_data_cache.get(player_id, {})
                candidates_str += f"- {name.title()} ({adp_data.get('pos_rank', 'N/A')}, {sleeper_info.get('team', 'N/A')}): ADP={adp_data.get('adp')}, SleeperRank={sleeper_info.get('rank_ppr')}, Status={sleeper_info.get('status')}\n"
                if len(candidates_str.splitlines()) >= 150: break
        prompt = f"{PROMPT_PREAMBLE}\n\n**Task:** Find market inefficiencies. Your response MUST be a single JSON object with two keys: \"sleepers\" and \"busts\". Each key must contain a JSON array of 3-5 player objects. Each player object must have three keys: \"name\", \"justification\", and \"confidence\" (High, Medium, or Low).\n\n**Data:**\n{candidates_str}"
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
        draft_summary = "\n".join([f"{rnd}: Drafted {get_player_context(name)}" for rnd, name in data.get('draft_board', {}).items() if name]) if data.get('draft_board') else "No picks made yet."
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
        draft_summary = "\n".join([f"{rnd}: Drafted {get_player_context(name)}" for rnd, name in data.get('draft_board', {}).items() if name]) if data.get('draft_board') else "This is my first pick."
        player_context = get_player_context(data.get('player_to_pick'))
        prompt = f"{PROMPT_PREAMBLE}\n\n**Task:** Analyze if this is a good pick for me in Round {data.get('current_round')}. Compare ADP to the round and evaluate roster fit. Give a 'GOOD PICK', 'SOLID PICK,' or 'POOR PICK' verdict.\n\n**My Draft So Far:**\n{draft_summary}\n\n**Player Being Considered:**\n{player_context}\n\n{JSON_OUTPUT_INSTRUCTION}"
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

@app.route('/api/all_player_names_with_data')
def all_player_names_with_data():
    if not static_adp_data or not player_data_cache:
        return jsonify([])

    sleeper_data_by_name = {
        p['full_name'].lower().strip(): {
            'bye_week': p.get('bye_week', 'N/A'),
            'team': p.get('team', 'N/A'),
            'position': p.get('position', 'N/A')
        }
        for p_id, p in player_data_cache.items() if p.get('full_name')
    }

    combined_data = []
    for name, data in static_adp_data.items():
        player_info = sleeper_data_by_name.get(name.lower().strip(), {})
        combined_data.append({
            'name': name.title(),
            'pos_rank': data.get('pos_rank', 'N/A'),
            'adp': data.get('adp'),
            'bye_week': player_info.get('bye_week', 'N/A'),
            'team': player_info.get('team', 'N/A'),
            'position': player_info.get('position', 'N/A')
        })
        
    return jsonify(combined_data)

@app.route('/api/trending_players')
def trending_players():
    try:
        url = "https://api.sleeper.app/v1/players/nfl/trending/add?lookback_hours=48&limit=25"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        detailed_list = []
        for player in response.json():
            if player_id := player.get('player_id'):
                player_details = player_data_cache.get(player_id)
                if player_details and player_details.get('full_name'):
                    cleaned_name = player_details.get('full_name').lower().strip()
                    static_info = static_adp_data.get(cleaned_name, {})
                    detailed_list.append({'name': player_details.get('full_name'), 'team': player_details.get('team', 'N/A'), 'position': player_details.get('position', 'N/A'), 'adds': player.get('count', 0), 'pos_rank': static_info.get('pos_rank', 'N/A')})
        return jsonify(detailed_list)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/waiver_wire_analysis', methods=['POST'])
def waiver_wire_analysis():
    try:
        user_key = request.headers.get('X-API-Key')
        team_roster = request.json.get('team_roster', []) # List of player names on user's team
        
        # Get available players (e.g., from Sleeper API or a combined data source)
        # For now, let's consider all players not on the user's roster as available
        all_players_data = []
        for name, data in static_adp_data.items():
            player_info = player_data_cache.get(player_name_to_id.get(name, ''), {})
            if player_info.get('full_name') and player_info.get('full_name').lower().strip() not in [p.lower().strip() for p in team_roster]:
                all_players_data.append({
                    'name': player_info.get('full_name'),
                    'pos_rank': data.get('pos_rank', 'N/A'),
                    'adp': data.get('adp'),
                    'bye_week': player_info.get('bye_week', 'N/A'),
                    'team': player_info.get('team', 'N/A'),
                    'position': player_info.get('position', 'N/A'),
                    'weekly_rank': weekly_data_cache.get(player_info.get('full_name', '').lower().strip(), {}).get('overall_rank', 'N/A')
                })
        
        # Sort available players by weekly rank or ADP for the prompt
        sorted_available_players = sorted(all_players_data, key=lambda x: x.get('weekly_rank') if isinstance(x.get('weekly_rank'), (int, float)) else (x.get('adp') if isinstance(x.get('adp'), (int, float)) else 999))[:50] # Top 50 available

        roster_context = "\n".join([get_player_context(player_name) for player_name in team_roster])
        available_players_context = "\n".join([
            f"- {p['name']} ({p['position']}, {p['team']}) - Weekly Rank: {p['weekly_rank']}, ADP: {p['adp']}"
            for p in sorted_available_players
        ])

        prompt = f"{PROMPT_PREAMBLE}\n\n**Task:** Analyze my current roster and the top available waiver wire players. Recommend 3-5 players to add, justifying each recommendation based on Yahoo PPR scoring, current performance, and potential upside. Also, suggest 1-2 players to drop if necessary.\n\n**My Current Roster:**\n{roster_context}\n\n**Top Available Waiver Wire Players:**\n{available_players_context}\n\n{JSON_OUTPUT_INSTRUCTION}"
        response_text = make_gemini_request(prompt, user_key)
        return jsonify({'result': process_ai_response(response_text)})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    try:
        import_data()  # Initial data import
        scheduler = BackgroundScheduler()
        scheduler.add_job(func=import_data, trigger="interval", hours=24)
        scheduler.start()

        # No longer need to load API key globally here
        get_all_players()
        csv_file_path = os.path.join(basedir, 'db_fpecr_latest.csv')
        static_adp_data = load_adp_from_csv(csv_file_path)
        player_values_cache = load_values_from_csv(os.path.join(basedir, 'values-players.csv'))
        pick_values_cache = load_values_from_csv(os.path.join(basedir, 'values-picks.csv'))
        weekly_data_cache = load_weekly_data_from_csv(os.path.join(basedir, 'fp_latest_weekly.csv'))

        if static_adp_data and player_data_cache is not None and weekly_data_cache is not None:
            app.run(debug=True, host='0.0.0.0', port=5001) # Bind to 0.0.0.0 for Render deployment
        else:
            print("Application will not start because essential data failed to load.")
    except Exception as e:
        print(f"❌ FATAL ERROR during application startup: {e}")
        traceback.print_exc() # Print full traceback
