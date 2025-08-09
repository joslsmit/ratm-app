from flask import Flask, request, jsonify, session, redirect
from flask_cors import CORS
from requests_oauthlib import OAuth2Session
from werkzeug.middleware.proxy_fix import ProxyFix # Import ProxyFix
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
from utils import normalize_player_name, fuzzy_find_player_key, get_player_context, make_gemini_request, process_ai_response, process_ai_response_v2
from prompt_templates import PromptBuilder
from few_shot_examples import ExampleLibrary
from chain_of_thought import ChainOfThoughtBuilder, ReasoningType
from context_formatters import ContextFormatter, AnalysisType

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
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_host=1, x_proto=1, x_port=1, x_prefix=1) # Apply ProxyFix
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY")
if not FLASK_SECRET_KEY:
    raise ValueError("FLASK_SECRET_KEY environment variable not set. This is required for Flask sessions.")
app.secret_key = FLASK_SECRET_KEY # Needed for Flask sessions
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:3000", "https://ratm-app-git-oauth-dev-joshua-smiths-projects-2dcfc522.vercel.app", "https://localhost:5000"]}}) # Updated ngrok URL in CORS

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

PROMPT_PREAMBLE = """You are 'The Analyst' - an expert fantasy football advisor specializing in data-driven analysis for the 2025 NFL season.

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
JSON_OUTPUT_INSTRUCTION = """RESPONSE FORMAT REQUIREMENTS:
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

# --- Data Loading and Initialization ---
def load_all_data():
    """Load all necessary data into memory."""
    global player_data_cache, player_name_to_id, static_ecr_overall_data, static_ecr_positional_data, static_ecr_rookie_data, player_values_cache, pick_values_cache, combined_player_data_cache
    
    try:
        import_data()  # Initial data import
        
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

    except Exception as e:
        print(f"❌ FATAL ERROR during application startup data loading: {e}")
        traceback.print_exc()

# Load data on application start
load_all_data()

# --- Background Scheduler for Data Refresh ---
scheduler = BackgroundScheduler()
scheduler.add_job(func=import_data, trigger="interval", hours=24)
scheduler.start()


# --- API Endpoints ---
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

        # --- Generate Enhanced AI Analysis (Phase 0B) ---
        # Create enhanced player context using Phase 0B context formatter
        enhanced_player_context = ContextFormatter.format_enhanced_player_context(
            combined_info, AnalysisType.PLAYER_DOSSIER
        )
        
        # Get few-shot examples for player analysis
        examples = ExampleLibrary.get_examples_for_analysis_type('player_analysis')
        
        # Get chain-of-thought reasoning questions
        reasoning_questions = ChainOfThoughtBuilder.get_reasoning_questions_list(ReasoningType.PLAYER_EVALUATION)
        
        # Build enhanced prompt with all Phase 0B components
        methodology_steps = [
            'Evaluate current role security and depth chart position within team context',
            'Compare Expert Consensus Ranking to projected fantasy performance and draft value',
            'Assess injury history, age factors, and other risk variables that could impact season',
            'Project 2025 season outlook considering all supporting factors and potential scenarios',
            'Synthesize analysis into clear, actionable draft recommendation with appropriate confidence'
        ]
        
        enhanced_prompt = PromptBuilder.build_enhanced_prompt(
            task_description='Comprehensive Player Analysis for Fantasy Football Drafting',
            player_data=enhanced_player_context,
            methodology_steps=methodology_steps,
            examples=examples[:1],  # Include one high-quality example
            chain_of_thought=reasoning_questions
        )
        
        response_text = make_gemini_request(enhanced_prompt, user_key)
        
        # --- Combine and Return ---
        return jsonify({
            'player_data': player_data_response,
            'analysis': process_ai_response_v2(response_text, 'player_dossier')
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
        
        # --- Enhanced Rookie Rankings (Phase 0B) ---
        
        # Build enhanced methodology for rookie evaluation  
        methodology_steps = [
            'Evaluate rookie draft capital and NFL team commitment as foundation for opportunity',
            'Assess college production, skillset translation, and NFL-readiness factors',
            'Analyze expert consensus patterns and uncertainty levels using standard deviation',
            'Consider team context, coaching fit, and projected role within offensive system',
            'Rank rookies balancing upside potential against rookie adjustment risk factors'
        ]
        
        rookie_reasoning = [
            'Which rookies have the highest draft capital and clearest path to early opportunity?',
            'How do college metrics and skillsets project to NFL success in 2025?',
            'Where do I see expert disagreement (high SD) suggesting value opportunities?',
            'What team situations and coaching systems best support rookie success?',
            'How should I balance ceiling potential against floor concerns for each rookie?'
        ]
        
        # Enhanced prompt with Phase 0B components
        enhanced_prompt = f"""{PromptBuilder.get_base_system_prompt()}

TASK: Advanced Rookie Rankings for 2025 Fantasy Football Season
Create strategic rookie rankings that balance opportunity, talent, and situation for fantasy success.

ANALYSIS METHODOLOGY:
{chr(10).join(f"{i}. {step}" for i, step in enumerate(methodology_steps, 1))}

STEP-BY-STEP THINKING PROCESS:
{chr(10).join(f"{i}. {step}" for i, step in enumerate(rookie_reasoning, 1))}

ROOKIE DATA FOR ANALYSIS:
{chr(10).join(rookie_list_for_prompt)}

RESPONSE FORMAT REQUIREMENTS:
Your response MUST be a single, valid JSON object with one top-level key: "rookies".
The "rookies" value MUST be a JSON array of the top 15 rookies.

Each rookie object MUST have these exact keys:
- "rank" (integer): 1-15 ranking
- "name" (string): Player name
- "position" (string): Position matching provided data  
- "team" (string): NFL team
- "ecr" (float or null): Expert consensus ranking
- "sd" (float or null): Standard deviation
- "best" (integer or null): Best expert ranking
- "worst" (integer or null): Worst expert ranking
- "rank_delta" (float or null): Recent ranking change
- "analysis" (string): 1-2 sentence evaluation focusing on opportunity and upside

CRITICAL: Use null for unavailable numeric data, ensure proper JSON syntax with quotes and commas."""
        response_text = make_gemini_request(enhanced_prompt, user_key)
        
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
        # --- Enhanced Keeper Evaluation (Phase 0B) ---
        # Build enhanced keeper analysis for each player
        keeper_contexts = []
        for k in keepers:
            player_name = k['name']
            keeper_round = int(k['round']) - 1  # Adjust for 0-indexing
            keeper_pick = keeper_round * 12 + 1
            
            # Get player data for enhanced context formatting
            normalized_name = normalize_player_name(player_name)
            player_data = combined_player_data_cache.get(normalized_name, {})
            
            # Enhanced context with keeper-specific information
            if player_data:
                enhanced_context = ContextFormatter.format_enhanced_player_context(
                    player_data, AnalysisType.KEEPER_EVALUATION, 
                    {'keeper_cost': f'Round {keeper_round + 1} pick (#{keeper_pick} overall)'}
                )
            else:
                # Fallback to basic context
                enhanced_context = f"**{player_name}** - No data available\n- Keeper Cost: Round {keeper_round + 1} pick (#{keeper_pick} overall)"
            
            # Add additional context if provided
            if k.get('context'):
                enhanced_context += f"\n- Additional Context: {k['context']}"
            
            keeper_contexts.append(enhanced_context)
        
        context_str = "\n\n".join(keeper_contexts)
        
        # Get keeper analysis examples and reasoning
        keeper_examples = ExampleLibrary.get_examples_for_analysis_type('keeper_analysis')
        value_reasoning = ChainOfThoughtBuilder.get_reasoning_questions_list(ReasoningType.VALUE_ASSESSMENT)
        
        # Build enhanced keeper evaluation prompt
        methodology_steps = [
            'Compare market value (ECR) to keeper cost for each player to calculate surplus value',
            'Assess age trajectory and multi-year value sustainability for keeper decisions',
            'Evaluate opportunity cost of keeper slots versus draft flexibility',
            'Consider bye week overlaps and roster construction implications',
            'Prioritize keeper recommendations based on total value and strategic fit'
        ]
        
        enhanced_prompt = PromptBuilder.build_enhanced_prompt(
            task_description='Comprehensive Keeper Evaluation for Fantasy Football',
            player_data=context_str,
            methodology_steps=methodology_steps,
            examples=keeper_examples[:1] if keeper_examples else None,
            chain_of_thought=value_reasoning
        )
        
        response_text = make_gemini_request(enhanced_prompt, user_key)
        return jsonify({'result': process_ai_response_v2(response_text, 'keeper_evaluator')})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/trade_analyzer', methods=['POST'])
def trade_analyzer():
    try:
        user_key = request.headers.get('X-API-Key')
        scoring_format = request.json.get('scoring_format', 'PPR')
        ecr_type_pref = request.json.get('ecr_type_preference', 'overall') # Default to overall
        # --- Enhanced Trade Analysis (Phase 0B) ---
        # Format assets for enhanced analysis
        my_assets_names = request.json.get('my_assets', [])
        partner_assets_names = request.json.get('partner_assets', [])
        
        my_assets_context = "\n".join([get_player_context(name, ecr_type_preference=ecr_type_pref, combined_player_data_cache=combined_player_data_cache, player_name_to_id=player_name_to_id, player_data_cache=player_data_cache, static_ecr_overall_data=static_ecr_overall_data, static_ecr_positional_data=static_ecr_positional_data, static_ecr_rookie_data=static_ecr_rookie_data) if "pick" not in name.lower() else f"- {name}" for name in my_assets_names])
        partner_assets_context = "\n".join([get_player_context(name, ecr_type_preference=ecr_type_pref, combined_player_data_cache=combined_player_data_cache, player_name_to_id=player_name_to_id, player_data_cache=player_data_cache, static_ecr_overall_data=static_ecr_overall_data, static_ecr_positional_data=static_ecr_positional_data, static_ecr_rookie_data=static_ecr_rookie_data) if "pick" not in name.lower() else f"- {name}" for name in partner_assets_names])
        
        # Get trade analysis examples and reasoning
        trade_examples = ExampleLibrary.get_examples_for_analysis_type('trade_analysis')
        trade_reasoning = ChainOfThoughtBuilder.get_reasoning_questions_list(ReasoningType.TRADE_ANALYSIS)
        
        # Enhanced trade context formatting
        league_context = f"{scoring_format} scoring format in 12-team league"
        
        # Build enhanced trade analysis prompt
        methodology_steps = [
            'Calculate raw fantasy value of each side using ECR and projected points',
            'Assess positional scarcity and replaceability for all positions involved',
            'Evaluate timing factors (bye weeks, playoff schedules, age curves)',
            'Consider roster construction and team-specific needs impact',
            'Declare clear winner with supporting reasoning and confidence assessment'
        ]
        
        enhanced_prompt = PromptBuilder.build_trade_analysis_prompt(
            my_assets=my_assets_context,
            their_assets=partner_assets_context,
            league_context=league_context
        )
        
        response_text = make_gemini_request(enhanced_prompt, user_key)
        return jsonify({'result': process_ai_response_v2(response_text, 'trade_analyzer')})
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
                    'ecr': clean_numeric_value(p_data.get('ecr')),
                    'sd': clean_numeric_value(p_data.get('sd')),
                    'best': clean_numeric_value(p_data.get('best')),
                    'worst': clean_numeric_value(p_data.get('worst')),
                    'rank_delta': clean_numeric_value(p_data.get('rank_delta'))
                })
        
        # --- Enhanced Tier Generation (Phase 0B) ---
        # Convert the list of dictionaries to a JSON string for the prompt
        player_list_str = json.dumps(player_list_for_tiers, indent=2)
        
        # Get tier analysis examples and reasoning
        tier_examples = ExampleLibrary.get_examples_for_analysis_type('tier_analysis')
        
        # Build enhanced tier generation prompt with methodology
        methodology_steps = [
            f'Analyze the {position} rankings using ECR and standard deviation to identify natural tier breaks',
            'Group players with similar ECR ranges and statistical profiles into meaningful tiers',
            'Consider expert consensus (lower SD = clearer tier placement) when setting tier boundaries', 
            'Create descriptive tier headers that capture each group\'s fantasy value and role',
            'Write concise summaries explaining what differentiates each tier from others'
        ]
        
        tier_reasoning = [
            f'Where are the natural breaks in {position} ECR that suggest tier separations?',
            'Which players have high expert consensus (low SD) vs high disagreement (high SD)?',
            'How should positional scarcity and draft strategy influence tier groupings?',
            'What tier names and descriptions best capture each group\'s fantasy value?'
        ]
        
        # Enhanced prompt with Phase 0B components
        enhanced_prompt = f"""{PromptBuilder.get_base_system_prompt()}

TASK: Advanced Tier Generation for {position} Position
Create strategic fantasy football tiers that group players by similar value and draft cost.

ANALYSIS METHODOLOGY:
{chr(10).join(f"{i}. {step}" for i, step in enumerate(methodology_steps, 1))}

STEP-BY-STEP THINKING PROCESS:
{chr(10).join(f"{i}. {step}" for i, step in enumerate(tier_reasoning, 1))}

PLAYER DATA:
{player_list_str}

RESPONSE FORMAT REQUIREMENTS:
Your response MUST be a single JSON object with one key 'tiers', whose value is a JSON array.
Each tier object requires: 'header' (descriptive name), 'summary' (1-sentence explanation), 'players' (array).
Each player object MUST have: 'name', 'position', 'team', 'ecr', 'sd', 'best', 'worst', 'rank_delta'.

EXAMPLE STRUCTURE:
```json
{{
  "tiers": [
    {{
      "header": "Tier 1: Elite {position}s",
      "summary": "These {position}s are top-tier with elite upside and minimal risk.",
      "players": [
        {{"name": "Player A", "position": "{position}", "team": "BUF", "ecr": 1.0, "sd": 1.5, "best": 1, "worst": 3, "rank_delta": 0.2}}
      ]
    }}
  ]
}}
```

CRITICAL: Ensure valid JSON syntax with proper quotes and commas."""
        
        response_text = make_gemini_request(enhanced_prompt, user_key)
        
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

        # --- Enhanced Market Inefficiency Analysis (Phase 0B) ---
        
        # Build enhanced methodology for market inefficiency detection
        methodology_steps = [
            'Analyze expert consensus patterns using standard deviation to identify disagreement',
            'Compare ECR ranking ranges (best vs worst) to find wide variances indicating uncertainty',
            'Evaluate recent ranking trends (rank_delta) for momentum and market shifts',
            'Assess rookie status and experience level for potential over/under-valuation',
            'Identify sleepers (undervalued with upside) and busts (overvalued with downside risk)'
        ]
        
        inefficiency_reasoning = [
            'Which players have high standard deviation indicating expert disagreement?',
            'Where do I see wide ECR ranges suggesting market uncertainty?',
            'What recent trends show players rising or falling in expert opinion?',
            'Are there rookie or veteran factors creating valuation inefficiencies?',
            'Which specific players represent clear sleeper or bust opportunities?'
        ]
        
        # Enhanced prompt with Phase 0B components
        enhanced_prompt = f"""{PromptBuilder.get_base_system_prompt()}

TASK: Advanced Market Inefficiency Detection for Fantasy Football
Identify undervalued players (sleepers) and overvalued players (busts) based on expert consensus patterns.

ANALYSIS METHODOLOGY:
{chr(10).join(f"{i}. {step}" for i, step in enumerate(methodology_steps, 1))}

STEP-BY-STEP THINKING PROCESS:
{chr(10).join(f"{i}. {step}" for i, step in enumerate(inefficiency_reasoning, 1))}

PLAYER ANALYSIS DATA:
{candidates_str}

RESPONSE FORMAT REQUIREMENTS:
Your response MUST be a single JSON object with two keys: "sleepers" and "busts".
Each key contains a JSON array of 3-5 player objects with these exact fields:
- "name" (string): Player name
- "justification" (string): Detailed reasoning for sleeper/bust designation
- "confidence" (string): 'High', 'Medium', or 'Low'
- "ecr" (float or null): Expert consensus ranking
- "sd" (float or null): Standard deviation
- "best" (integer or null): Best expert ranking
- "worst" (integer or null): Worst expert ranking  
- "rank_delta" (float or null): Recent ranking change
- "is_rookie" (boolean): true or false

CRITICAL: Use null for unavailable numeric data, true/false for is_rookie boolean."""
        
        response_text = make_gemini_request(enhanced_prompt, user_key)
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
        # --- Enhanced Draft Position Suggestion (Phase 0B) ---
        current_round = data.get('current_round', 1)
        draft_board = data.get('draft_board', {})
        
        draft_summary = "\n".join([f"{rnd}: Drafted {get_player_context(name, ecr_type_preference=ecr_type_pref, combined_player_data_cache=combined_player_data_cache, player_name_to_id=player_name_to_id, player_data_cache=player_data_cache, static_ecr_overall_data=static_ecr_overall_data, static_ecr_positional_data=static_ecr_positional_data, static_ecr_rookie_data=static_ecr_rookie_data)}" for rnd, name in draft_board.items() if name]) if draft_board else "No picks made yet."
        
        # Build enhanced draft assistance methodology
        methodology_steps = [
            'Analyze current roster composition and identify positional gaps or weaknesses',
            'Evaluate positional scarcity and value available in upcoming draft rounds',
            'Consider best player available (BPA) versus positional need strategy',
            'Assess bye week timing and roster construction balance requirements',
            'Recommend top 2 positions with strategic reasoning and timing considerations'
        ]
        
        draft_reasoning = [
            f'What positions are missing or weak in my current Round {current_round} roster?',
            'Which positions have the best value available in upcoming rounds?',
            'Should I prioritize best player available or fill specific positional needs?',
            'How do bye weeks and roster balance affect my positional priorities?',
            'What are the top 2 positions I should target and why?'
        ]
        
        # Enhanced prompt with Phase 0B components
        enhanced_prompt = f"""{PromptBuilder.get_base_system_prompt()}

TASK: Strategic Draft Position Recommendation for Round {current_round}
Provide the top 2 positions to target based on roster analysis and draft strategy.

ANALYSIS METHODOLOGY:
{chr(10).join(f"{i}. {step}" for i, step in enumerate(methodology_steps, 1))}

STEP-BY-STEP THINKING PROCESS:
{chr(10).join(f"{i}. {step}" for i, step in enumerate(draft_reasoning, 1))}

CURRENT DRAFT BOARD:
{draft_summary}

{PromptBuilder.get_json_instruction()}"""
        
        response_text = make_gemini_request(enhanced_prompt, user_key)
        return jsonify({'result': process_ai_response_v2(response_text, 'suggest_position')})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/pick_evaluator', methods=['POST'])
def pick_evaluator():
    try:
        user_key = request.headers.get('X-API-Key')
        data = request.json
        ecr_type_pref = data.get('ecr_type_preference', 'overall') # Default to overall
        # --- Enhanced Pick Evaluation (Phase 0B) ---
        current_round = data.get('current_round', 1)
        player_to_pick = data.get('player_to_pick', 'Unknown Player')
        draft_board = data.get('draft_board', {})
        
        draft_summary = "\n".join([f"{rnd}: Drafted {get_player_context(name, ecr_type_preference=ecr_type_pref, combined_player_data_cache=combined_player_data_cache, player_name_to_id=player_name_to_id, player_data_cache=player_data_cache, static_ecr_overall_data=static_ecr_overall_data, static_ecr_positional_data=static_ecr_positional_data, static_ecr_rookie_data=static_ecr_rookie_data)}" for rnd, name in draft_board.items() if name]) if draft_board else "This is my first pick."
        
        # Get enhanced player context for the pick being evaluated
        normalized_name = normalize_player_name(player_to_pick)
        player_data = combined_player_data_cache.get(normalized_name, {})
        
        if player_data:
            enhanced_player_context = ContextFormatter.format_enhanced_player_context(
                player_data, AnalysisType.DRAFT_ASSISTANCE, 
                {'pick_number': current_round * 12}  # Approximate pick number for 12-team league
            )
        else:
            enhanced_player_context = f"**{player_to_pick}** - No data available"
        
        # Build enhanced pick evaluation methodology
        methodology_steps = [
            f'Compare player\'s ECR to Round {current_round} draft value to assess if pick represents good value',
            'Analyze current roster composition and determine how this player fits positional needs',
            'Evaluate opportunity cost of this pick versus other players available in this round',
            'Consider player\'s risk profile, consistency, and upside relative to draft position',
            'Assign clear verdict: GOOD PICK (great value), SOLID PICK (fair value), or POOR PICK (poor value)'
        ]
        
        pick_reasoning = [
            f'Is this player\'s ECR significantly better than Round {current_round} draft position?',
            'How does this player address my current roster strengths and weaknesses?', 
            'What other players of similar or better value might be available?',
            'Does this player\'s risk/reward profile justify the draft investment?',
            'Based on value, fit, and alternatives, what\'s my verdict on this pick?'
        ]
        
        # Enhanced prompt with Phase 0B components
        enhanced_prompt = f"""{PromptBuilder.get_base_system_prompt()}

TASK: Comprehensive Draft Pick Evaluation for Round {current_round}
Analyze whether {player_to_pick} represents good draft value and roster fit.

ANALYSIS METHODOLOGY:
{chr(10).join(f"{i}. {step}" for i, step in enumerate(methodology_steps, 1))}

STEP-BY-STEP THINKING PROCESS:
{chr(10).join(f"{i}. {step}" for i, step in enumerate(pick_reasoning, 1))}

CURRENT ROSTER COMPOSITION:
{draft_summary}

PLAYER BEING EVALUATED:
{enhanced_player_context}

VERDICT REQUIREMENTS:
You must provide one of these exact verdicts in your analysis:
- **GOOD PICK**: Excellent value, ECR significantly better than round
- **SOLID PICK**: Fair value, reasonable pick for this round  
- **POOR PICK**: Poor value, much better options likely available

{PromptBuilder.get_json_instruction()}"""
        
        response_text = make_gemini_request(enhanced_prompt, user_key)
        return jsonify({'result': process_ai_response_v2(response_text, 'pick_evaluator')})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/roster_composition_analysis', methods=['POST'])
def roster_composition_analysis():
    try:
        user_key = request.headers.get('X-API-Key')
        data = request.json
        # --- Enhanced Roster Composition Analysis (Phase 0B) ---
        composition = data.get('composition', {})
        drafted_count = data.get('drafted_count', 0)
        
        # Calculate draft progress and remaining picks
        total_roster_spots = 16  # Typical fantasy roster size
        remaining_picks = total_roster_spots - drafted_count
        draft_progress = round((drafted_count / total_roster_spots) * 100)
        
        comp_str = ", ".join([f"{count} {pos}" for pos, count in composition.items() if count > 0])
        
        # Build enhanced roster analysis methodology
        methodology_steps = [
            f'Evaluate positional balance after {drafted_count} picks ({draft_progress}% complete)',
            'Identify critical gaps or over-drafting at specific positions relative to typical roster construction',
            'Assess remaining roster needs based on standard starting lineup requirements (1 QB, 2 RB, 2-3 WR, 1 TE, etc.)',
            f'Consider draft stage implications for remaining {remaining_picks} picks and available player quality',
            'Provide specific strategic guidance for addressing roster imbalances in upcoming rounds'
        ]
        
        roster_reasoning = [
            'Which positions am I over-drafted or under-drafted compared to typical roster construction?',
            'What are my most critical positional needs that must be addressed?',
            f'At {draft_progress}% completion, what positions should I prioritize in remaining picks?',
            'How does my current roster balance affect my draft strategy flexibility?',
            'What specific recommendations will improve my roster construction going forward?'
        ]
        
        # Enhanced prompt with Phase 0B components
        enhanced_prompt = f"""{PromptBuilder.get_base_system_prompt()}

TASK: Strategic Roster Composition Analysis
Evaluate roster balance and provide strategic guidance for remaining draft picks.

ANALYSIS METHODOLOGY:
{chr(10).join(f"{i}. {step}" for i, step in enumerate(methodology_steps, 1))}

STEP-BY-STEP THINKING PROCESS:
{chr(10).join(f"{i}. {step}" for i, step in enumerate(roster_reasoning, 1))}

CURRENT ROSTER COMPOSITION:
After {drafted_count} picks ({draft_progress}% complete): {comp_str}
Remaining picks: {remaining_picks}

ANALYSIS REQUIREMENTS:
Provide 2-3 sentence analysis focusing on:
- Most critical positional needs or imbalances
- Strategic priority for remaining {remaining_picks} picks
- Specific actionable recommendations for draft strategy adjustment

{PromptBuilder.get_json_instruction()}"""
        
        response_text = make_gemini_request(enhanced_prompt, user_key)
        return jsonify({'result': process_ai_response_v2(response_text, 'roster_composition')})
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
            'bye_week': cleaned_player_data.get('bye_week'), # Added missing field
            'ecr_overall': cleaned_player_data.get('ecr_overall'),
            'sd_overall': cleaned_player_data.get('sd_overall'), # Added missing field
            'best_overall': cleaned_player_data.get('best_overall'), # Added missing field
            'worst_overall': cleaned_player_data.get('worst_overall'), # Added missing field
            'rank_delta_overall': cleaned_player_data.get('rank_delta_overall'), # Added missing field
            'ecr_positional': cleaned_player_data.get('ecr_positional'),
            'sd_positional': cleaned_player_data.get('sd_positional'), # Added missing field
            'best_positional': cleaned_player_data.get('best_positional'), # Added missing field
            'worst_positional': cleaned_player_data.get('worst_positional'), # Added missing field
            'rank_delta_positional': cleaned_player_data.get('rank_delta_positional'), # Added missing field
            'ecr_rookie': cleaned_player_data.get('ecr_rookie'), # Added missing field
            'sd_rookie': cleaned_player_data.get('sd_rookie'), # Added missing field
            'best_rookie': cleaned_player_data.get('best_rookie'), # Added missing field
            'worst_rookie': cleaned_player_data.get('worst_rookie'), # Added missing field
            'rank_delta_rookie': cleaned_player_data.get('rank_delta_rookie'), # Added missing field
            'years_exp': cleaned_player_data.get('years_exp'),
            'is_rookie': cleaned_player_data.get('is_rookie') # Added missing field
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

        # Phase 0B: Enhanced waiver wire add/drop analysis prompting
        
        # Get enhanced context for the waiver candidate
        waiver_player_data = combined_player_data_cache.get(normalize_player_name(player_to_add), {})
        waiver_candidate_context = ContextFormatter.format_enhanced_player_context(
            waiver_player_data, AnalysisType.WAIVER_ANALYSIS
        )
        
        # Build roster context with enhanced formatting
        roster_analysis = []
        for pos, name in roster.items():
            if name:
                player_data = combined_player_data_cache.get(normalize_player_name(name), {})
                enhanced_context = ContextFormatter.format_enhanced_player_context(
                    player_data, AnalysisType.WAIVER_ANALYSIS
                )
                roster_analysis.append(f"**{pos.upper()}**: {enhanced_context}")
        roster_context = "\n\n".join(roster_analysis)
        
        # Get waiver decision examples (falls back to player analysis examples)
        waiver_examples = ExampleLibrary.get_examples_for_analysis_type('waiver_swap_analysis')
        
        # Build enhanced prompt with waiver wire methodology
        enhanced_prompt = PromptBuilder.build_enhanced_prompt(
            analysis_type="waiver_swap_analysis",
            context_data=f"CURRENT ROSTER:\n{roster_context}\n\nWAIVER WIRE CANDIDATE:\n{waiver_candidate_context}",
            specific_examples=waiver_examples,
            methodology_steps=[
                "1. WAIVER CANDIDATE VALUE ASSESSMENT",
                "   • Evaluate current ECR and recent trend momentum",
                "   • Assess role security and opportunity factors", 
                "   • Consider injury/bye week timing implications",
                "   • Determine upside potential vs floor outcomes",
                "",
                "2. ROSTER COMPOSITION ANALYSIS",
                "   • Identify positional strengths and weaknesses",
                "   • Evaluate depth at each position for drop candidates",
                "   • Consider bye week management implications",
                "   • Assess short-term needs vs long-term roster building",
                "",
                "3. DROP CANDIDATE EVALUATION",
                "   • Compare ECR values between waiver add and potential drops",
                "   • Evaluate declining players or role changes",
                "   • Consider positional replaceability on waiver wire",
                "   • Factor in remaining upside vs waiver candidate upside",
                "",
                "4. ADD/DROP DECISION FRAMEWORK",
                "   • Calculate net value improvement from the transaction",
                "   • Assess roster construction impact and flexibility",
                "   • Consider waiver priority cost vs expected benefit",
                "   • Evaluate timing urgency (other managers may target player)",
                "",
                "5. FINAL RECOMMENDATION SYNTHESIS",
                "   • Provide clear ADD or DO NOT ADD verdict with reasoning",
                "   • If ADD: specify exact player to DROP with justification",
                "   • Quantify expected improvement and confidence level",
                "   • Address any close-call factors or alternative scenarios"
            ]
        )
        
        response_text = make_gemini_request(enhanced_prompt, user_key)
        return jsonify({'result': process_ai_response_v2(response_text, 'waiver_swap')})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/waiver_wire_analysis', methods=['POST'])
def waiver_wire_analysis():
    try:
        user_key = request.headers.get('X-API-Key')
        team_roster = request.json.get('team_roster', []) # List of player names on user's team
        ecr_type_pref = request.json.get('ecr_type_preference', 'overall') # Default to overall
        
        # Phase 0B: Enhanced waiver wire analysis prompting
        
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

        # Build enhanced context for roster analysis
        roster_analysis = []
        for player_name in team_roster:
            player_data = combined_player_data_cache.get(normalize_player_name(player_name), {})
            enhanced_context = ContextFormatter.format_enhanced_player_context(
                player_data, AnalysisType.WAIVER_ANALYSIS
            )
            roster_analysis.append(f"- {enhanced_context}")
        roster_context = "\n".join(roster_analysis)
        
        # Build enhanced available players context
        available_players_analysis = []
        for p in sorted_available_players:
            player_data = combined_player_data_cache.get(normalize_player_name(p['name']), {})
            if player_data:
                enhanced_context = ContextFormatter.format_enhanced_player_context(
                    player_data, AnalysisType.WAIVER_ANALYSIS
                )
                available_players_analysis.append(f"- {enhanced_context}")
            else:
                # Fallback for players not in enhanced data
                available_players_analysis.append(f"- {p['name']} ({p['pos']}, {p['team']}) - ECR: {p['ecr'] or 'N/A'}")
        
        available_players_context = "\n".join(available_players_analysis[:25])  # Limit for prompt length
        
        # Get waiver wire examples (falls back to player analysis examples)
        waiver_examples = ExampleLibrary.get_examples_for_analysis_type('waiver_wire_analysis')
        
        # Build enhanced prompt with waiver wire methodology
        enhanced_prompt = PromptBuilder.build_enhanced_prompt(
            analysis_type="waiver_wire_analysis",
            context_data=f"CURRENT ROSTER:\n{roster_context}\n\nTOP AVAILABLE PLAYERS:\n{available_players_context}",
            specific_examples=waiver_examples,
            methodology_steps=[
                "1. ROSTER NEEDS ASSESSMENT",
                "   • Analyze current roster strengths and weaknesses by position",
                "   • Identify bye week vulnerabilities and depth concerns",
                "   • Assess injury risk and backup needs",
                "   • Consider positional scarcity and streaming requirements",
                "",
                "2. AVAILABLE PLAYER EVALUATION", 
                "   • Rank available players by value and opportunity",
                "   • Prioritize players with trending upward momentum",
                "   • Consider role security and target share trends",
                "   • Factor in schedule strength and matchup advantages",
                "",
                "3. WAIVER PRIORITY STRATEGY",
                "   • Recommend 3-5 players in order of priority",
                "   • Balance high-upside adds vs immediate-need fills", 
                "   • Consider waiver position cost vs expected benefit",
                "   • Account for league competition and likely claims",
                "",
                "4. DROP CANDIDATE IDENTIFICATION",
                "   • Identify 1-2 drop candidates if roster moves needed",
                "   • Prioritize players with declining roles or value",
                "   • Consider bye week timing for temporary drops",
                "   • Avoid dropping players with remaining upside potential",
                "",
                "5. RECOMMENDATION SYNTHESIS",
                "   • Provide clear add/drop recommendations with rationale",
                "   • Explain the strategic reasoning behind each move",
                "   • Consider both short-term and long-term roster construction",
                "   • Address any situational factors or timing considerations"
            ]
        )
        
        response_text = make_gemini_request(enhanced_prompt, user_key)
        return jsonify({'result': process_ai_response_v2(response_text, 'waiver_wire')})
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

# --- Yahoo API Endpoints ---
# Note: These are simplified for clarity. In a real app, you'd handle token
# storage, refresh, and error handling more robustly.

YAHOO_CLIENT_ID = os.getenv("YAHOO_CLIENT_ID")
YAHOO_CLIENT_SECRET = os.getenv("YAHOO_CLIENT_SECRET")
# Ensure this matches what you set in the Yahoo Developer Network app settings
YAHOO_REDIRECT_URI = 'https://localhost:5000/api/yahoo/callback' # <-- Make sure this is up-to-date with your ngrok URL for local dev
AUTHORIZATION_BASE_URL = 'https://api.login.yahoo.com/oauth2/request_auth'
TOKEN_URL = 'https://api.login.yahoo.com/oauth2/get_token'


@app.route('/api/yahoo/login')
def yahoo_login():
    """
    Redirects the user to Yahoo's authorization page.
    """
    if not YAHOO_CLIENT_ID or not YAHOO_CLIENT_SECRET:
        return "Yahoo client ID or secret not configured on the server.", 500

    yahoo = OAuth2Session(YAHOO_CLIENT_ID, redirect_uri=YAHOO_REDIRECT_URI)
    authorization_url, state = yahoo.authorization_url(AUTHORIZATION_BASE_URL)

    # Debug: Log the authorization URL and parameters for troubleshooting
    print(f"DEBUG: Yahoo OAuth Authorization URL: {authorization_url}")
    print(f"DEBUG: OAuth State: {state}")
    print(f"DEBUG: Redirect URI used: {YAHOO_REDIRECT_URI}")

    # State is used to prevent CSRF, keep this for later verification
    session['oauth_state'] = state
    return redirect(authorization_url)


@app.route('/api/yahoo/callback')
def yahoo_callback():
    """
    Handles the callback from Yahoo after the user has authorized the app.
    """
    if not YAHOO_CLIENT_ID or not YAHOO_CLIENT_SECRET:
        return "Yahoo client ID or secret not configured on the server.", 500

    # Use the state stored in the session to verify the request
    yahoo = OAuth2Session(YAHOO_CLIENT_ID, state=session.get('oauth_state'), redirect_uri=YAHOO_REDIRECT_URI)
    
    try:
        token = yahoo.fetch_token(
            TOKEN_URL,
            client_secret=YAHOO_CLIENT_SECRET,
            authorization_response=request.url
        )

        # For local development, pass the token to the frontend via URL.
        # In a production app, you would store this more securely (e.g., in a database).
        token_json = json.dumps(token)
        encoded_token = requests.utils.quote(token_json)

        return redirect(f'http://localhost:3000/#yahoo-leagues?token={encoded_token}')

    except Exception as e:
        print(f"Error fetching Yahoo token: {e}")
        if hasattr(e, 'response') and e.response is not None:
            print(f"Yahoo token error response: {e.response.text}")
        traceback.print_exc()
        return "Error fetching Yahoo token.", 500


@app.route('/api/yahoo/leagues')
def get_yahoo_leagues():
    """
    Fetches the user's fantasy football leagues from the Yahoo API.
    Expects the token in the Authorization header.
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        print("DEBUG: Authorization header missing or malformed.")
        return jsonify({"error": "Not authenticated with Yahoo. Authorization header missing."}), 401

    try:
        # Extract the access_token string from the Authorization header
        # The frontend now sends "Bearer <ACCESS_TOKEN_STRING>"
        access_token_string = auth_header.split(' ')[1]
        
        if not access_token_string:
            return jsonify({"error": "Invalid token format: access_token missing."}), 401

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Invalid token format in Authorization header."}), 401

    # Use the extracted access_token string to create the OAuth2Session
    yahoo = OAuth2Session(YAHOO_CLIENT_ID, token={'access_token': access_token_string})

    try:
        # The URL for fetching a user's games, then leagues for the NFL game (game_key=nfl)
        # We use 'use_login=1' to specify the logged-in user.
        url = 'https://fantasysports.yahooapis.com/fantasy/v2/users;use_login=1/games;game_keys=nfl/leagues;out=teams?format=json'
        
        response = yahoo.get(url)
        response.raise_for_status() # Raise an exception for bad status codes
        
        # Parse and transform the response using defensive JSON parsing
        return jsonify(parse_yahoo_leagues_response(response.json()))

    except requests.exceptions.RequestException as req_e:
        print(f"Error fetching Yahoo leagues (RequestException): {req_e}")
        if req_e.response is not None:
            print(f"Yahoo leagues error response content: {req_e.response.text}")
        traceback.print_exc()
        # This could be a token expiration error, you might need to handle token refresh here
        return jsonify({"error": "Failed to fetch leagues from Yahoo.", "details": str(req_e)}), 500
    except Exception as e:
        print(f"Error fetching Yahoo leagues (General Exception): {e}")
        traceback.print_exc()
        return jsonify({"error": "Failed to fetch leagues from Yahoo.", "details": str(e)}), 500

def parse_yahoo_leagues_response(data):
    """
    Parse Yahoo API leagues response with defensive JSON parsing.
    Returns a clean array of league objects or empty array on failure.
    """
    try:
        # Navigate the complex JSON structure using defensive .get() calls
        fantasy_content = data.get('fantasy_content', {})
        users = fantasy_content.get('users', {})
        
        # Get the first user (index "0")
        user_data = users.get('0', {})
        user_info = user_data.get('user', [])
        
        # User info is typically an array where [1] contains the games
        if not isinstance(user_info, list) or len(user_info) < 2:
            print("DEBUG: User info structure unexpected")
            return []
        
        games = user_info[1].get('games', {})
        
        # Get the NFL game (index "0" typically)
        game_data = games.get('0', {})
        game_info = game_data.get('game', [])
        
        # Game info is typically an array where [1] contains the leagues
        if not isinstance(game_info, list) or len(game_info) < 2:
            print("DEBUG: Game info structure unexpected")
            return []
        
        leagues_data = game_info[1].get('leagues', {})
        
        # Parse leagues - could be a dict with numbered keys or direct list
        leagues = []
        
        # Handle case where leagues is a dict with numbered keys
        if isinstance(leagues_data, dict):
            for key, league_container in leagues_data.items():
                if key.isdigit():  # Skip non-numeric keys like "count"
                    league_info = league_container.get('league', [])
                    
                    # League info is typically an array where [0] has basic info and [1] has teams
                    if isinstance(league_info, list) and len(league_info) >= 1:
                        basic_info = league_info[0]
                        
                        # Extract basic league information
                        league_key = basic_info.get('league_key', '')
                        league_name = basic_info.get('name', 'Unknown League')
                        
                        # Extract team_key from teams data if available
                        team_key = ''
                        if len(league_info) > 1:
                            teams_data = league_info[1].get('teams', {})
                            # Get the first team (user's team)
                            first_team = teams_data.get('0', {})
                            team_info = first_team.get('team', [])
                            if isinstance(team_info, list) and len(team_info) >= 1:
                                # team_info is a nested list: [[{team_key: ...}, {team_id: ...}, ...]]
                                team_data_list = team_info[0]
                                if isinstance(team_data_list, list) and len(team_data_list) >= 1:
                                    team_key = team_data_list[0].get('team_key', '')
                        
                        if league_key:  # Only add if we have a valid league_key
                            leagues.append({
                                'league_key': league_key,
                                'league_name': league_name,
                                'team_key': team_key
                            })
        
        # Successfully parsed leagues
        return leagues
        
    except Exception as e:
        print(f"ERROR: Failed to parse Yahoo leagues response: {e}")
        traceback.print_exc()
        return []

@app.route('/api/test/roster')
def test_roster_parser():
    """
    Test endpoint to debug roster parsing logic with mock Yahoo data.
    """
    # Mock Yahoo API response structure based on what we've learned
    mock_response = {
        "fantasy_content": {
            "xml:lang": "en-US",
            "yahoo:uri": "/fantasy/v2/team/461.l.42889.t.8/roster",
            "team": [
                {
                    "team_key": "461.l.42889.t.8",
                    "team_id": "8",
                    "name": "Test Team"
                },
                {
                    "roster": {
                        "coverage_type": "week",
                        "week": "17",
                        "players": {
                            "0": {
                                "player": [
                                    {
                                        "player_key": "461.p.31000",
                                        "player_id": "31000",
                                        "name": {
                                            "full": "Patrick Mahomes",
                                            "first": "Patrick",
                                            "last": "Mahomes"
                                        },
                                        "selected_position": {
                                            "coverage_type": "week",
                                            "week": "17",
                                            "position": "QB"
                                        },
                                        "eligible_positions": [
                                            {"position": "QB"}
                                        ],
                                        "status": "Healthy"
                                    }
                                ]
                            },
                            "1": {
                                "player": [
                                    {
                                        "player_key": "461.p.32000",
                                        "player_id": "32000",
                                        "name": {
                                            "full": "Derrick Henry",
                                            "first": "Derrick", 
                                            "last": "Henry"
                                        },
                                        "selected_position": {
                                            "coverage_type": "week",
                                            "week": "17",
                                            "position": "RB"
                                        },
                                        "eligible_positions": [
                                            {"position": "RB"}
                                        ],
                                        "status": "Healthy"
                                    }
                                ]
                            },
                            "count": 2
                        }
                    }
                }
            ],
            "time": "33.649963378906ms",
            "copyright": "Data provided by Yahoo! and STATS, LLC",
            "refresh_rate": "60"
        }
    }
    
    # Test the parser with mock data
    result = parse_yahoo_roster_response(mock_response)
    return jsonify(result)

@app.route('/api/yahoo/roster')
def get_yahoo_roster():
    """
    Fetches the user's fantasy team roster from the Yahoo API.
    Expects team_key as query parameter and token in Authorization header.
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Not authenticated with Yahoo. Authorization header missing."}), 401
    
    # Get and validate team_key parameter
    team_key = request.args.get('team_key')
    if not team_key:
        return jsonify({"error": "team_key parameter is required."}), 400
    
    # Optional week parameter for NFL
    week = request.args.get('week')
    
    try:
        # Extract the access_token string from the Authorization header
        access_token_string = auth_header.split(' ')[1]
        
        if not access_token_string:
            return jsonify({"error": "Invalid token format: access_token missing."}), 401

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": "Invalid token format in Authorization header."}), 401

    # Use the extracted access_token string to create the OAuth2Session
    yahoo = OAuth2Session(YAHOO_CLIENT_ID, token={'access_token': access_token_string})

    try:
        # Build URL with optional week parameter
        if week:
            url = f'https://fantasysports.yahooapis.com/fantasy/v2/team/{team_key}/roster;week={week}?format=json'
        else:
            url = f'https://fantasysports.yahooapis.com/fantasy/v2/team/{team_key}/roster?format=json'
        
        response = yahoo.get(url)
        response.raise_for_status()
        
        # Parse and transform the response using defensive JSON parsing
        return jsonify(parse_yahoo_roster_response(response.json()))

    except requests.exceptions.RequestException as req_e:
        print(f"Error fetching Yahoo roster: {req_e}")
        if req_e.response is not None:
            print(f"Yahoo roster error response content: {req_e.response.text}")
        traceback.print_exc()
        return jsonify({"error": "Failed to fetch roster from Yahoo.", "details": str(req_e)}), 500
    except Exception as e:
        print(f"Error processing Yahoo roster: {e}")
        traceback.print_exc()
        return jsonify({"error": "Failed to process roster data.", "details": str(e)}), 500

def parse_yahoo_roster_response(data):
    """
    Parse Yahoo API roster response with defensive JSON parsing.
    Returns a clean array of player objects or empty array on failure.
    """
    try:
        # DEBUG: Log the raw response structure to understand what we're getting
        print(f"DEBUG: Raw Yahoo roster response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
        if isinstance(data, dict) and 'fantasy_content' in data:
            print(f"DEBUG: fantasy_content keys: {list(data['fantasy_content'].keys())}")
        
        # Navigate the complex JSON structure using defensive .get() calls
        fantasy_content = data.get('fantasy_content', {})
        
        # Team data is typically an array where [1] contains roster
        team_data = fantasy_content.get('team', [])
        print(f"DEBUG: team_data type: {type(team_data)}")
        print(f"DEBUG: team_data keys/length: {list(team_data.keys()) if isinstance(team_data, dict) else len(team_data) if isinstance(team_data, list) else 'Neither dict nor list'}")
        
        if not isinstance(team_data, list) or len(team_data) < 2:
            print("DEBUG: Team data structure unexpected - checking if it's a dict instead")
            if isinstance(team_data, dict):
                print(f"DEBUG: team_data is dict with keys: {list(team_data.keys())}")
            return []
        
        roster_container = team_data[1].get('roster', {})
        players_data = roster_container.get('players', {})
        
        # Parse players - dict with numbered keys
        players = []
        
        if isinstance(players_data, dict):
            for key, player_container in players_data.items():
                if key.isdigit():  # Skip non-numeric keys like "count"
                    player_info = player_container.get('player', [])
                    
                    # Player info is typically an array where [0] has player data
                    if isinstance(player_info, list) and len(player_info) >= 1:
                        player_data = player_info[0]
                        
                        # Extract player information with defensive parsing
                        player_key = player_data.get('player_key', '')
                        player_id = player_data.get('player_id', '')
                        
                        # Handle name structure (could be nested)
                        name_data = player_data.get('name', {})
                        if isinstance(name_data, dict):
                            full_name = name_data.get('full', '')
                        else:
                            full_name = str(name_data) if name_data else ''
                        
                        # Handle position data
                        selected_pos_data = player_data.get('selected_position', {})
                        if isinstance(selected_pos_data, dict):
                            selected_position = selected_pos_data.get('position', '')
                        else:
                            selected_position = str(selected_pos_data) if selected_pos_data else ''
                        
                        eligible_positions = player_data.get('eligible_positions', [])
                        if not isinstance(eligible_positions, list):
                            eligible_positions = [str(eligible_positions)] if eligible_positions else []
                        
                        status = player_data.get('status', '')
                        
                        if player_key and full_name:  # Only add if we have key data
                            players.append({
                                'player_key': player_key,
                                'player_id': player_id,
                                'name': full_name,
                                'selected_position': selected_position,
                                'eligible_positions': eligible_positions,
                                'status': status
                            })
        
        # Enrich players with local data
        if players:
            players = enrich_roster_players(players)
        
        return players
        
    except Exception as e:
        print(f"ERROR: Failed to parse Yahoo roster response: {e}")
        traceback.print_exc()
        return []

def enrich_roster_players(yahoo_players):
    """
    Enrich Yahoo roster players with local ECR and analysis data.
    """
    enriched_players = []
    
    for player in yahoo_players:
        try:
            # Normalize player name for matching
            normalized_name = normalize_player_name(player['name'])
            
            # Get combined player data for additional info
            combined_info = combined_player_data_cache.get(normalized_name, {})
            
            # Merge Yahoo data with local data
            enriched_player = {
                # Yahoo roster data
                'player_key': player['player_key'],
                'player_id': player['player_id'],
                'name': player['name'],
                'selected_position': player['selected_position'],
                'eligible_positions': player['eligible_positions'],
                'status': player['status'],
                
                # Local enrichment data
                'team': combined_info.get('team', 'N/A'),
                'position': combined_info.get('position', player['selected_position']),
                'bye_week': combined_info.get('bye_week'),
                'ecr_overall': combined_info.get('ecr_overall'),
                'sd_overall': combined_info.get('sd_overall'),
                'best_overall': combined_info.get('best_overall'),
                'worst_overall': combined_info.get('worst_overall'),
                'rank_delta_overall': combined_info.get('rank_delta_overall'),
                'years_exp': combined_info.get('years_exp'),
                'is_rookie': combined_info.get('is_rookie', False)
            }
            
            enriched_players.append(enriched_player)
            
        except Exception as e:
            print(f"Error enriching player {player.get('name', 'Unknown')}: {e}")
            # Include player even if enrichment fails
            enriched_players.append(player)
    
    return enriched_players

if __name__ == '__main__':
    # This block is for local development only.
    # When deployed on Render with Gunicorn, this block is not executed.
    # Data loading is handled by the `load_all_data()` call at the top level.
    if static_ecr_overall_data and player_data_cache is not None:
        # Use SSL context for HTTPS
        app.run(debug=True, host='0.0.0.0', port=5000, ssl_context=('certs/localhost.pem', 'certs/localhost-key.pem'))
    else:
        print("Application will not start because essential data failed to load.")
