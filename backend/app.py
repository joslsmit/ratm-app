from flask import Flask, request, jsonify
from flask_cors import CORS # Import CORS
import requests
import os
import pandas as pd
import re
import json
from dotenv import load_dotenv
import google.generativeai as genai
import traceback # Import traceback for detailed error logging

# Get the absolute path of the directory where this file is located
basedir = os.path.abspath(os.path.dirname(__file__))

load_dotenv()
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:3000"}}) # Enable CORS for /api routes from frontend origin

# --- Configuration ---
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    raise ValueError("FATAL ERROR: GOOGLE_API_KEY not found in environment. The application cannot start.")
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.0-flash') 

# --- Data Caching ---
player_data_cache, player_name_to_id, static_adp_data = None, None, {}

# --- Data Loading & Helper Functions ---
def load_adp_from_csv(file_path):
    try:
        df = pd.read_csv(file_path)
        df_processed = df[['Player', 'POS', 'AVG']].copy()
        def clean_player_name(player_name):
            return re.sub(r'\s[A-Z]{2,4}$', '', str(player_name)).lower().strip()
        df_processed['Player_Clean'] = df_processed['Player'].apply(clean_player_name)
        adp_dict = {row['Player_Clean']: {'adp': row['AVG'], 'pos_rank': row['POS']} for index, row in df_processed.iterrows() if row['Player_Clean'] and row['Player_Clean'] != 'nan'}
        print(f"✅ Successfully loaded {len(adp_dict)} players from {file_path}.")
        return adp_dict
    except FileNotFoundError:
        print(f"❌ FATAL ERROR: The CSV file was not found at '{file_path}'. Make sure it's in your GitHub repository.")
        return None
    except Exception as e:
        print(f"❌ FATAL ERROR loading CSV: {e}")
        traceback.print_exc() # Print full traceback
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
        traceback.print_exc() # Print full traceback
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

def make_gemini_request(prompt): # Removed user_api_key as it's now configured globally
    if not api_key: raise Exception("API key is missing from the request.")
    response = model.generate_content(prompt)
    if not response.candidates:
        return "The AI model did not return a valid response. The content may have been blocked due to safety settings."
    return response.text

def process_ai_response(response_text):
    try:
        cleaned_text = re.sub(r'^```json\s*|```\s*$', '', response_text.strip(), flags=re.MULTILINE)
        data = json.loads(cleaned_text)
        confidence = data.get('confidence', 'Medium').title()
        analysis_content = data.get('analysis', 'No analysis provided.')

        # If analysis_content is a dictionary, format it into a Markdown string
        if isinstance(analysis_content, dict):
            formatted_analysis = []
            for key, value in analysis_content.items():
                # Capitalize key for display, replace underscores with spaces
                display_key = key.replace('_', ' ').title()
                formatted_analysis.append(f"**{display_key}:** {value}")
            analysis_text = "\n\n".join(formatted_analysis)
        else:
            analysis_text = analysis_content # Assume it's already a string

        emoji_map = {'High': '✅', 'Medium': '🤔', 'Low': '⚠️'}
        confidence_badge = f"**Confidence: {emoji_map.get(confidence, '🤔')} {confidence}**"
        return f"{confidence_badge}\n\n---\n\n{analysis_text}"
    except (json.JSONDecodeError, AttributeError) as e:
        print(f"Error processing AI response: {e}")
        traceback.print_exc()
        return response_text

PROMPT_PREAMBLE = "You are 'The Analyst,' a data-driven, no-nonsense fantasy football expert providing advice for the upcoming 2025 NFL season. All analysis is for a 12-team, PPR league with standard Yahoo scoring rules..."
JSON_OUTPUT_INSTRUCTION = "Your response MUST be a JSON object with two keys: \"confidence\" and \"analysis\"..."

@app.route('/api/player_dossier', methods=['POST'])
def player_dossier():
    try:
        player_name = request.json.get('player_name')
        prompt = f"{PROMPT_PREAMBLE}\n\n**Task:** First, create a detailed markdown report for the player with headers: ### Depth Chart Role, ### Value Analysis, ### Risk Factors, ### 2025 Outlook, and ### Final Verdict. Then, wrap this entire markdown report inside the 'analysis' key of your JSON output.\n\n**Player Data:**\n{get_player_context(player_name)}\n\n{JSON_OUTPUT_INSTRUCTION}"
        response_text = make_gemini_request(prompt) # Use the new make_gemini_request
        return jsonify({'result': process_ai_response(response_text)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/rookie_rankings', methods=['POST'])
def rookie_rankings():
    try:
        position_filter = request.json.get('position', 'all')
        rookies = [
            {'name': p.get('full_name'),'position': p.get('position'),'team': p.get('team'), **static_adp_data.get(p.get('full_name', '').lower().strip(), {})}
            for p_id, p in player_data_cache.items() if p.get('years_exp') == 0 and (position_filter == 'all' or p.get('position') == position_filter) and p.get('full_name')
        ]
        sorted_rookies = sorted(rookies, key=lambda x: x.get('adp') or 999)
        rookie_list_for_prompt = [f"- {r['name']} ({r['position']}, {r['team']}) - ADP: {r.get('adp') or 'N/A'}" for r in sorted_rookies[:50]]
        prompt = f"{PROMPT_PREAMBLE}\n\n**Task:** Create a ranked list of rookies.\n\n**Rookie Data:**\n{chr(10).join(rookie_list_for_prompt)}\n\n**Instructions:** Your response MUST be a single JSON object with one key: \"rookies\". The value must be a JSON array of objects. For each of the top 15 rookies, create an object with these keys: \"rank\", \"name\", \"position\", \"team\", \"adp\" (string or \"N/A\"), \"pos_rank\", and \"analysis\" (a 1-2 sentence summary of their outlook)."
        response_text = make_gemini_request(prompt)
        cleaned_text = re.sub(r'^```json\s*|```\s*$', '', response_text.strip(), flags=re.MULTILINE)
        return jsonify(json.loads(cleaned_text).get('rookies', []))
    except Exception as e:
        return jsonify({"error": f"Failed to generate AI analysis for rookies: {e}"}), 500

@app.route('/api/keeper_evaluation', methods=['POST'])
def keeper_evaluation():
    try:
        keepers = request.json.get('keepers')
        context_str = "\n".join([f"{get_player_context(k['name'])}\n  - Keeper Cost: A round {int(k['round']) - 1} pick\n" for k in keepers])
        prompt = f"{PROMPT_PREAMBLE}\n\n**Task:** Analyze these keepers. Compare Cost to ADP. Note bye week overlaps. Prioritize recommendations.\n\n**Data:**\n{context_str}\n\n{JSON_OUTPUT_INSTRUCTION}"
        response_text = make_gemini_request(prompt)
        return jsonify({'result': process_ai_response(response_text)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/trade_analyzer', methods=['POST'])
def trade_analyzer():
    try:
        my_assets_context = "\n".join([get_player_context(name) if "pick" not in name.lower() else f"- {name}" for name in request.json.get('my_assets', [])])
        partner_assets_context = "\n".join([get_player_context(name) if "pick" not in name.lower() else f"- {name}" for name in request.json.get('partner_assets', [])])
        prompt = f"{PROMPT_PREAMBLE}\n\n**Task:** Analyze this trade. Declare a winner or if it is fair. Justify your answer.\n\n**Assets My Team Receives:**\n{my_assets_context}\n\n**Assets My Partner Receives:**\n{partner_assets_context}\n\n{JSON_OUTPUT_INSTRUCTION}"
        response_text = make_gemini_request(prompt)
        return jsonify({'result': process_ai_response(response_text)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/generate_tiers', methods=['POST'])
def generate_tiers():
    try:
        position = request.json.get('position')
        player_list_str = "\n".join([f"- {name.title()} ({p_data['pos_rank']}, {player_data_cache.get(player_name_to_id.get(name), {}).get('team', 'N/A')}) - ADP: {p_data['adp']}" for name, p_data in sorted(static_adp_data.items(), key=lambda item: item[1]['adp']) if p_data.get('pos_rank', '').startswith(position)])
        prompt = f"{PROMPT_PREAMBLE}\n\n**Task:** Group the following {position}s into Tiers. For each tier, give a header, a 1-sentence summary, and a bulleted list of players.\n\n**Player List:**\n{player_list_str}\n\n{JSON_OUTPUT_INSTRUCTION}"
        response_text = make_gemini_request(prompt)
        return jsonify({'result': process_ai_response(response_text)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/find_market_inefficiencies', methods=['POST'])
def find_market_inefficiencies():
    try:
        position = request.json.get('position', 'all')
        candidates_str = ""
        for name, adp_data in sorted(static_adp_data.items(), key=lambda item: item[1].get('adp') or 999):
            if position != 'all' and not adp_data.get('pos_rank', '').startswith(position): continue
            if player_id := player_name_to_id.get(name):
                sleeper_info = player_data_cache.get(player_id, {})
                candidates_str += f"- {name.title()} ({adp_data.get('pos_rank', 'N/A')}, {sleeper_info.get('team', 'N/A')}): ADP={adp_data.get('adp')}, SleeperRank={sleeper_info.get('rank_ppr')}, Status={sleeper_info.get('status')}\n"
                if len(candidates_str.splitlines()) >= 150: break
        prompt = f"{PROMPT_PREAMBLE}\n\n**Task:** Find market inefficiencies. Your response MUST be a single JSON object with two keys: \"sleepers\" and \"busts\". Each key must contain a JSON array of 3-5 player objects. Each player object must have two keys: \"name\" and \"justification\".\n\n**Data:**\n{candidates_str}"
        response_text = make_gemini_request(prompt)
        cleaned_text = re.sub(r'^```json\s*|```\s*$', '', response_text.strip(), flags=re.MULTILINE)
        return jsonify(json.loads(cleaned_text))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/suggest_position', methods=['POST'])
def suggest_position():
    try:
        data = request.json
        draft_summary = "\n".join([f"{rnd}: Drafted {get_player_context(name)}" for rnd, name in data.get('draft_board', {}).items() if name]) if data.get('draft_board') else "No picks made yet."
        prompt = f"{PROMPT_PREAMBLE}\n\n**Task:** It is Round {data.get('current_round')}. Based on my detailed roster below, what are the top 2 positions I should target? Justify.\n\n**My Draft So Far:**\n{draft_summary}"
        response_text = make_gemini_request(prompt)
        return jsonify({'result': response_text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/pick_evaluator', methods=['POST'])
def pick_evaluator():
    try:
        data = request.json
        draft_summary = "\n".join([f"{rnd}: Drafted {get_player_context(name)}" for rnd, name in data.get('draft_board', {}).items() if name]) if data.get('draft_board') else "This is my first pick."
        player_context = get_player_context(data.get('player_to_pick'))
        prompt = f"{PROMPT_PREAMBLE}\n\n**Task:** Analyze if this is a good pick for me in Round {data.get('current_round')}. Compare ADP to the round and evaluate roster fit. Give a 'GOOD PICK', 'SOLID PICK,' or 'POOR PICK' verdict.\n\n**My Draft So Far:**\n{draft_summary}\n\n**Player Being Considered:**\n{player_context}\n\n{JSON_OUTPUT_INSTRUCTION}"
        response_text = make_gemini_request(prompt)
        return jsonify({'result': process_ai_response(response_text)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/roster_composition_analysis', methods=['POST'])
def roster_composition_analysis():
    try:
        composition = request.json.get('composition')
        comp_str = ", ".join([f"{count} {pos}" for pos, count in composition.items()])
        prompt = f"{PROMPT_PREAMBLE}\n\n**Task:** Provide a brief, 2-3 sentence analysis of my roster balance based on these position counts.\n\n**Composition:**\n{comp_str}"
        response_text = make_gemini_request(prompt)
        return jsonify({'result': response_text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/api/all_player_names_with_data')
def all_player_names_with_data():
    if not static_adp_data: return jsonify([])
    return jsonify([{'name': name.title(), 'pos_rank': data.get('pos_rank', 'N/A')} for name, data in static_adp_data.items()])

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

if __name__ == '__main__':
    try:
        get_all_players()
        csv_file_path = os.path.join(basedir, 'FantasyPros_2025_Overall_ADP_Rankings.csv')
        static_adp_data = load_adp_from_csv(csv_file_path)
        if static_adp_data and player_data_cache is not None:
            app.run(debug=True, port=5001) # Run on a different port to avoid conflict with potential frontend dev server
        else:
            print("Application will not start because essential data failed to load.")
    except Exception as e:
        print(f"❌ FATAL ERROR during application startup: {e}")
        traceback.print_exc() # Print full traceback
