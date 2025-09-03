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
from typing import Optional
import math

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
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:3000", "https://ratm-app-git-oauth-dev-joshua-smiths-projects-2dcfc522.vercel.app", "https://localhost:5000", "https://ratm-app.vercel.app"]}}) # Updated ngrok URL in CORS

# --- Configuration (API key will be passed per request) ---
# Using the latest available preview model as requested
model = genai.GenerativeModel('gemini-2.5-flash-lite-preview-06-17')


# --- Data Caching ---
player_data_cache, player_name_to_id, static_ecr_overall_data, static_ecr_positional_data, static_ecr_rookie_data, player_values_cache, pick_values_cache, weekly_projections_cache, combined_player_data_cache = None, None, {}, {}, {}, None, None, {}, None
yahoo_id_to_key = {}
name_aliases = {}

# --- Name Aliases (optional file: backend/name_aliases.json) ---
def load_name_aliases():
    """Load name alias map to improve CSV enrichment matching.

    Expected JSON format: { "normalized_name": "normalized_alias", ... }
    """
    global name_aliases
    try:
        alias_path = os.path.join(basedir, 'name_aliases.json')
        if os.path.exists(alias_path):
            with open(alias_path, 'r') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    name_aliases = {str(k): str(v) for k, v in data.items()}
                    print(f"Loaded {len(name_aliases)} name aliases")
                else:
                    name_aliases = {}
        else:
            name_aliases = {}
    except Exception as e:
        print(f"WARN: Failed to load name aliases: {e}")
        name_aliases = {}

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
            if player_name:  # Ensure player name exists
                # Normalize player name for consistent keying across all data sources
                normalized_name = normalize_player_name(player_name)
                player_data = row.to_dict()
                for key, value in player_data.items():
                    if pd.isna(value):
                        player_data[key] = None
                # Store original name for display purposes
                player_data['original_name'] = player_name
                values_dict[normalized_name] = player_data

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
                    'yahoo_id': row.get('yahoo_id'),
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

def load_weekly_projections_data(file_path):
    """
    Load and process weekly fantasy projections data.
    
    Purpose: Integrate projected points, grades, matchups, and ownership
    Returns: weekly_projections_cache dictionary keyed by normalized names
    """
    
    try:
        df = pd.read_csv(file_path)
        print(f"Loading weekly projections from {file_path}: {len(df)} players")
        
        # Defensive NaN handling
        df = df.where(pd.notna(df), None)
        
        # Dynamic column detection
        player_col = next((col for col in ['player_name', 'player', 'full_name'] 
                          if col in df.columns), None)
        
        if not player_col:
            print(f"❌ ERROR: Could not find player name column in {file_path}")
            return {}
        
        projections_cache = {}
        
        for index, row in df.iterrows():
            player_name = row.get(player_col)
            if not player_name or str(player_name).strip() == '':
                continue
                
            normalized_key = normalize_player_name(str(player_name))
            if not normalized_key:
                continue
            
            # Parse matchup data
            opponent_info = parse_matchup_string(row.get('player_opponent', ''))
            
            # Convert grades to confidence scores
            grade_score = convert_start_sit_grade(row.get('start_sit_grade', 'C'))
            
            projections_cache[normalized_key] = {
                'projected_points': clean_numeric_value(row.get('r2p_pts')),
                'start_sit_grade': row.get('start_sit_grade', 'C'),
                'grade_confidence_score': grade_score,
                'opponent': opponent_info['opponent'],
                'home_away': opponent_info['home_away'],
                'weekly_ownership': clean_numeric_value(row.get('player_owned_avg')),
                'weekly_pos_rank': row.get('pos_rank', ''),
                'weekly_ecr': clean_numeric_value(row.get('ecr')),
                'projection_date': row.get('scrape_date')
            }
        
        print(f"✅ Successfully loaded weekly projections for {len(projections_cache)} players")
        return projections_cache
        
    except Exception as e:
        print(f"❌ ERROR loading weekly projections: {e}")
        traceback.print_exc()
        return {}

def parse_matchup_string(matchup_str):
    """Parse matchup strings like 'vs. CLE' or 'at PIT'"""
    if not matchup_str:
        return {'opponent': 'N/A', 'home_away': 'Unknown'}
    
    matchup_str = str(matchup_str).strip()
    if matchup_str.startswith('vs.'):
        opponent = matchup_str.split('vs. ')[1] if 'vs. ' in matchup_str else matchup_str[3:].strip()
        return {'opponent': opponent, 'home_away': 'Home'}
    elif matchup_str.startswith('at '):
        opponent = matchup_str.split('at ')[1] if 'at ' in matchup_str else matchup_str[3:].strip()
        return {'opponent': opponent, 'home_away': 'Away'}
    else:
        return {'opponent': matchup_str, 'home_away': 'Neutral'}

def convert_start_sit_grade(grade):
    """Convert letter grades to numeric confidence scores"""
    if not grade:
        return 60  # Default C grade
    
    grade = str(grade).strip().upper()
    grade_mapping = {
        'A+': 95, 'A': 90, 'A-': 85,
        'B+': 80, 'B': 75, 'B-': 70,
        'C+': 65, 'C': 60, 'C-': 55,
        'D+': 50, 'D': 45, 'D-': 40,
        'F': 30
    }
    return grade_mapping.get(grade, 60)  # Default to C grade

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

def clean_numeric_value(value):
    """Attempt to coerce to float; return None for missing/NaN/non-numeric."""
    if value is None:
        return None
    try:
        f = float(value)
        if pd.isna(f):
            return None
        return f
    except (ValueError, TypeError):
        return None

def create_enhanced_combined_player_data_cache():
    """
    Enhanced version integrating ECR + Weekly Projections + Player Values
    
    Purpose: Create unified player data cache with all available metrics
    Dependencies: static_ecr_data, weekly_projections_cache, player_values_cache
    """
    
    global combined_player_data_cache, static_ecr_overall_data, static_ecr_positional_data
    global static_ecr_rookie_data, weekly_projections_cache, player_values_cache, yahoo_id_to_key
    
    # Validation checks
    if not any([static_ecr_overall_data, static_ecr_positional_data, static_ecr_rookie_data]):
        print("❌ Cannot create cache: No ECR data loaded")
        return
    
    temp_combined_data = {}
    yahoo_id_to_key = {}
    
    # Get all unique player keys from all data sources
    all_player_keys = (set(static_ecr_overall_data.keys()) | 
                      set(static_ecr_positional_data.keys()) | 
                      set(static_ecr_rookie_data.keys()) |
                      set(weekly_projections_cache.keys()) |
                      set(player_values_cache.keys() if player_values_cache else []))
    
    for name_key in all_player_keys:
        # Existing ECR data integration (unchanged)
        overall_data = static_ecr_overall_data.get(name_key, {})
        positional_data = static_ecr_positional_data.get(name_key, {})
        rookie_data = static_ecr_rookie_data.get(name_key, {})
        
        # Use overall_data for general player info if available, otherwise positional or rookie
        primary_data_source = overall_data or positional_data or rookie_data
        
        # Ensure bye_week is an integer or None
        bye_week_val = primary_data_source.get('bye')
        if bye_week_val is not None:
            try:
                bye_week_val = int(bye_week_val)
            except (ValueError, TypeError):
                bye_week_val = None
        
        # Get Sleeper data for years_exp
        sleeper_player_id = player_name_to_id.get(name_key)
        sleeper_info = player_data_cache.get(sleeper_player_id, {}) if sleeper_player_id else {}
        
        # Determine display name
        display_name = primary_data_source.get('original_name') or \
                       sleeper_info.get('full_name') or \
                       primary_data_source.get('name', name_key.title())
        
        # NEW: Weekly projections integration
        weekly_data = weekly_projections_cache.get(name_key, {})
        
        # NEW: Player values integration  
        values_data = player_values_cache.get(name_key, {}) if player_values_cache else {}
        
        # Enhanced player data structure
        # Stitch yahoo_id if available
        yahoo_id = (overall_data.get('yahoo_id') if overall_data else None) or \
                   (positional_data.get('yahoo_id') if positional_data else None) or \
                   (rookie_data.get('yahoo_id') if rookie_data else None)

        temp_combined_data[name_key] = {
            # Existing ECR fields (unchanged)
            'name': primary_data_source.get('name', name_key.title()),
            'display_name': display_name,
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
            'is_rookie': name_key in static_ecr_rookie_data,
            
            # NEW: Weekly projection fields
            'projected_points': weekly_data.get('projected_points'),
            'start_sit_grade': weekly_data.get('start_sit_grade'),
            'grade_confidence_score': weekly_data.get('grade_confidence_score'),
            'opponent': weekly_data.get('opponent'),
            'home_away': weekly_data.get('home_away'),
            'weekly_ownership': weekly_data.get('weekly_ownership'),
            'weekly_pos_rank': weekly_data.get('weekly_pos_rank'),
            'weekly_ecr': weekly_data.get('weekly_ecr'),
            
            # NEW: Player value fields
            'age': values_data.get('age'),
            'draft_year': values_data.get('draft_year'),
            'value_1qb': clean_numeric_value(values_data.get('value_1qb')),
            'value_2qb': clean_numeric_value(values_data.get('value_2qb')),
            
            # NEW: Calculated enhancement fields (to be post-processed)
            'matchup_difficulty': None,
            'value_opportunity_score': None,
            'age_category': None,
            'projection_confidence': None,
            # IDs
            'yahoo_id': yahoo_id,
        }
    
    # Post-process calculated fields using utility functions
    from utils import calculate_matchup_difficulty, calculate_value_opportunity_score, calculate_age_category, calculate_projection_confidence
    
    for name_key, player_data in temp_combined_data.items():
        # Calculate matchup difficulty
        player_data['matchup_difficulty'] = calculate_matchup_difficulty(
            player_data.get('opponent'), 
            player_data.get('position')
        )
        
        # Calculate value opportunity score
        player_data['value_opportunity_score'] = calculate_value_opportunity_score(
            player_data.get('projected_points'),
            player_data.get('weekly_ownership'),
            player_data.get('grade_confidence_score')
        )
        
        # Calculate age category
        player_data['age_category'] = calculate_age_category(
            player_data.get('age'),
            player_data.get('position')
        )
        
        # Calculate projection confidence
        player_data['projection_confidence'] = calculate_projection_confidence(
            player_data.get('start_sit_grade'),
            player_data.get('ecr_overall'),
            player_data.get('weekly_ecr')
        )
    
        if yahoo_id and str(yahoo_id).lower() not in ('na', 'nan', ''):
            yahoo_id_to_key[str(yahoo_id)] = name_key

    combined_player_data_cache = temp_combined_data
    print(f"✅ Enhanced cache created with {len(combined_player_data_cache)} players")

# Maintain backward compatibility
def create_combined_player_data_cache():
    """Backward compatibility wrapper for enhanced cache creation."""
    create_enhanced_combined_player_data_cache()

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
    global player_data_cache, player_name_to_id, static_ecr_overall_data, static_ecr_positional_data, static_ecr_rookie_data, player_values_cache, pick_values_cache, weekly_projections_cache, combined_player_data_cache
    
    try:
        import_data()  # Initial data import
        
        get_all_players()
        csv_file_path = os.path.join(basedir, 'db_fpecr_latest.csv')
        
        # Load different ECR types into their respective caches
        static_ecr_overall_data, static_ecr_positional_data, static_ecr_rookie_data = load_ecr_data_from_csv(csv_file_path)
        
        player_values_cache = load_values_from_csv(os.path.join(basedir, 'values-players.csv'))
        pick_values_cache = load_values_from_csv(os.path.join(basedir, 'values-picks.csv'))
        
        # Load weekly projections data
        weekly_projections_path = os.path.join(basedir, 'fp_latest_weekly.csv')
        weekly_projections_cache = load_weekly_projections_data(weekly_projections_path)

        # Create the combined player data cache at startup
        create_combined_player_data_cache()
        # Load optional name aliases
        try:
            load_name_aliases()
        except Exception as _e:
            print(f"WARN: load_name_aliases failed: {_e}")

        print(f"Player data cache size: {len(player_data_cache) if player_data_cache else 0}")
        print(f"Static Overall ECR data size: {len(static_ecr_overall_data) if static_ecr_overall_data else 0}")
        print(f"Static Positional ECR data size: {len(static_ecr_positional_data) if static_ecr_positional_data else 0}")
        print(f"Static Rookie ECR data size: {len(static_ecr_rookie_data) if static_ecr_rookie_data else 0}")
        print(f"Weekly projections cache size: {len(weekly_projections_cache) if weekly_projections_cache else 0}")

    except Exception as e:
        print(f"❌ FATAL ERROR during application startup data loading: {e}")
        traceback.print_exc()

# Load data on application start
load_all_data()

# --- Background Scheduler for Data Refresh ---
def refresh_external_data():
    """Download latest CSVs and rebuild combined caches."""
    try:
        print("DEBUG: Refreshing external data (CSV download + cache rebuild)")
        import_data()
        # Reload CSV-derived caches and rebuild combined cache
        global static_ecr_overall_data, static_ecr_positional_data, static_ecr_rookie_data
        global player_values_cache, pick_values_cache, weekly_projections_cache
        csv_file_path = os.path.join(basedir, 'db_fpecr_latest.csv')
        static_ecr_overall_data, static_ecr_positional_data, static_ecr_rookie_data = load_ecr_data_from_csv(csv_file_path)
        player_values_cache = load_values_from_csv(os.path.join(basedir, 'values-players.csv'))
        pick_values_cache = load_values_from_csv(os.path.join(basedir, 'values-picks.csv'))
        weekly_projections_cache = load_weekly_projections_data(os.path.join(basedir, 'fp_latest_weekly.csv'))
        create_combined_player_data_cache()
        try:
            load_name_aliases()
        except Exception as _e:
            print(f"WARN: load_name_aliases failed (refresh): {_e}")
        print("DEBUG: External data refresh complete")
    except Exception as e:
        print(f"ERROR: External data refresh failed: {e}")
        traceback.print_exc()

scheduler = BackgroundScheduler()
# Run once every 24 hours
scheduler.add_job(func=refresh_external_data, trigger="interval", hours=24)
scheduler.start()

@app.route('/api/admin/refresh_data', methods=['POST'])
def admin_refresh_data():
    """Force a data refresh from DynastyProcess GitHub (dev convenience).

    Triggers CSV downloads and cache rebuild. Returns basic stats.
    """
    try:
        refresh_external_data()
        # Summarize file sizes
        files = [
            ('db_fpecr_latest.csv', os.path.join(basedir, 'db_fpecr_latest.csv')),
            ('values-players.csv', os.path.join(basedir, 'values-players.csv')),
            ('values-picks.csv', os.path.join(basedir, 'values-picks.csv')),
            ('fp_latest_weekly.csv', os.path.join(basedir, 'fp_latest_weekly.csv')),
        ]
        stats = {}
        for name, path in files:
            try:
                size = os.path.getsize(path)
                mtime = os.path.getmtime(path)
                stats[name] = {
                    'exists': True,
                    'bytes': size,
                    'modified': datetime.fromtimestamp(mtime).isoformat()
                }
            except Exception:
                stats[name] = {'exists': False}
        return jsonify({'status': 'ok', 'files': stats}), 200
    except Exception as e:
        print(f"ERROR: admin_refresh_data failed: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# --- Name Aliases (optional file: backend/name_aliases.json) ---
def load_name_aliases():
    global name_aliases
    try:
        alias_path = os.path.join(basedir, 'name_aliases.json')
        if os.path.exists(alias_path):
            with open(alias_path, 'r') as f:
                data = json.load(f)
                if isinstance(data, dict):
                    # Expect mapping from normalized_name -> normalized_alias
                    name_aliases = {str(k): str(v) for k, v in data.items()}
                    print(f"Loaded {len(name_aliases)} name aliases")
                else:
                    name_aliases = {}
        else:
            name_aliases = {}
    except Exception as e:
        print(f"WARN: Failed to load name aliases: {e}")
        name_aliases = {}


# --- Position Validation Helpers ---
def is_valid_player_for_position(player_data, position_slot):
    """
    Validate if a player can be placed in a specific roster position.
    Handles flexible positions like W/T and W/R/T.
    
    Args:
        player_data: Player data dictionary from combined_player_data_cache
        position_slot: Position slot like 'QB', 'W/T', 'W/R/T', etc.
    
    Returns:
        bool: True if valid placement, False otherwise
    """
    if not player_data or not position_slot:
        return True  # Allow empty positions
    
    player_position = player_data.get('position', '').upper()
    position_slot_upper = position_slot.upper()
    
    # Handle flexible positions
    if position_slot_upper == 'W/T':
        return player_position in ['WR', 'TE']
    elif position_slot_upper == 'W/R/T':
        return player_position in ['WR', 'RB', 'TE']
    elif position_slot_upper.startswith('IR'):
        return True  # IR can hold any position
    elif position_slot_upper.startswith('BN'):
        return True  # Bench can hold any position
    else:
        # Standard positions (QB, RB1, WR1, etc.)
        expected_pos = position_slot_upper.rstrip('123456789')  # Remove numbers
        return player_position == expected_pos or expected_pos == 'DEF' and player_position == 'DST'

def get_position_flexibility_info(position_slot):
    """
    Get information about position flexibility for user guidance.
    
    Args:
        position_slot: Position slot like 'W/T', 'W/R/T', etc.
    
    Returns:
        dict: Position flexibility information
    """
    position_upper = position_slot.upper()
    
    if position_upper == 'W/T':
        return {'allowed_positions': ['WR', 'TE'], 'description': 'Wide Receiver or Tight End'}
    elif position_upper == 'W/R/T':
        return {'allowed_positions': ['WR', 'RB', 'TE'], 'description': 'Wide Receiver, Running Back, or Tight End'}
    elif position_upper.startswith('IR'):
        return {'allowed_positions': ['QB', 'WR', 'RB', 'TE', 'K', 'DST'], 'description': 'Injury Reserve (any position)'}
    elif position_upper.startswith('BN'):
        return {'allowed_positions': ['QB', 'WR', 'RB', 'TE', 'K', 'DST'], 'description': 'Bench (any position)'}
    else:
        expected_pos = position_upper.rstrip('123456789')
        return {'allowed_positions': [expected_pos], 'description': f'{expected_pos} only'}

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

        # Enhanced player data response with comprehensive metadata for frontend
        player_data_response = {
            # Core player information
            "name": combined_info.get('display_name', player_name.title()), # Use display_name for the dossier header
            "team": combined_info.get('team', 'N/A'),
            "position": combined_info.get('position', 'N/A'),
            "bye_week": combined_info.get('bye_week'),
            
            # ECR and consensus data
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
            
            # Weekly projection and outlook data (NEW)
            "projected_points": combined_info.get('projected_points'),
            "start_sit_grade": combined_info.get('start_sit_grade'),
            "grade_confidence_score": combined_info.get('grade_confidence_score'),
            "projection_confidence": combined_info.get('projection_confidence'),
            "weekly_ecr": combined_info.get('weekly_ecr'),
            
            # Matchup and schedule data (NEW)
            "opponent": combined_info.get('opponent'),
            "matchup_difficulty": combined_info.get('matchup_difficulty'),
            "home_away": combined_info.get('home_away'),
            "schedule_outlook": combined_info.get('schedule_outlook'),
            
            # Market value and ownership data (NEW)
            "weekly_ownership": combined_info.get('weekly_ownership'),
            "value_opportunity_score": combined_info.get('value_opportunity_score'),
            "value_1qb": combined_info.get('value_1qb'),
            "value_2qb": combined_info.get('value_2qb'),
            
            # Age and development data (NEW)
            "age": combined_info.get('age'),
            "age_category": combined_info.get('age_category'),
            "draft_year": combined_info.get('draft_year'),
            "years_exp": combined_info.get('years_exp'),
            "is_rookie": combined_info.get('is_rookie'),
            
            # Additional metadata for comprehensive analysis (NEW)
            "injury_status": combined_info.get('injury_status'),
            "depth_chart_position": combined_info.get('depth_chart_position'),
            "target_share": combined_info.get('target_share'),
            "snap_percentage": combined_info.get('snap_percentage'),
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
        
        # Build enhanced prompt with all Phase 0B components - COMPREHENSIVE 6-STEP METHODOLOGY
        methodology_steps = [
            "1. FANTASY VALUE ASSESSMENT (Enhanced Multi-Source)",
            "   • Analyze ECR consensus and expert agreement levels",
            "   • Integrate weekly projection data with season-long outlook", 
            "   • Compare positional tier with weekly scoring potential",
            "   • Factor expert confidence grades and projection reliability",
            "   • Identify ranking volatility and consistency patterns",
            "",
            "2. WEEKLY OUTLOOK AND MATCHUP ANALYSIS",
            "   • Evaluate current week projection and expert grade confidence",
            "   • Assess matchup difficulty and historical performance vs opponent type",
            "   • Consider home/away factors and travel implications",
            "   • Analyze upcoming schedule strength (2-4 weeks)",
            "   • Identify favorable and challenging matchup windows",
            "",
            "3. MARKET POSITIONING AND OWNERSHIP ANALYSIS", 
            "   • Evaluate current ownership vs projected production",
            "   • Identify potential market inefficiencies (over/under valued)",
            "   • Assess acquisition opportunity and roster availability",
            "   • Compare platform-specific ownership differences",
            "   • Highlight arbitrage opportunities for astute managers",
            "",
            "4. AGE TRAJECTORY AND DEVELOPMENT CURVE",
            "   • Analyze age-related performance expectations by position",
            "   • Evaluate career stage (ascending, prime, declining)",
            "   • Consider experience level and development potential",
            "   • Assess long-term vs short-term roster value",
            "   • Factor position-specific aging curves and decline patterns",
            "",
            "5. TREND ANALYSIS AND MOMENTUM EVALUATION",
            "   • Examine recent ranking trends and expert consensus shifts",
            "   • Evaluate trend sustainability vs temporary fluctuation",
            "   • Assess injury impact, role changes, and team context",
            "   • Identify potential breakout or decline indicators",
            "   • Consider coaching changes and system fit implications",
            "",
            "6. COMPREHENSIVE STRATEGIC RECOMMENDATIONS",
            "   • Provide clear DRAFT/TRADE FOR/HOLD/SELL guidance",
            "   • Identify optimal usage scenarios (start/sit strategy)",
            "   • Suggest complementary players and roster construction",
            "   • Highlight key weeks to target (favorable matchups)",
            "   • Address risk factors and contingency planning",
            "   • Include confidence levels and timeline expectations"
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
            # Handle keeper cost calculation with Round 1 edge case
            draft_round = int(k['round'])
            if draft_round == 1:
                # Round 1 picks cannot be kept for cheaper, remain Round 1
                keeper_round = 0  # 0-indexed Round 1
                keeper_pick = 1
            else:
                # Normal case: one round better, adjusted for 0-indexing
                keeper_round = draft_round - 2  # -1 for keeper rule, -1 for 0-indexing
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
            'Compare market value (ECR) to keeper cost for each player to calculate surplus value in rounds saved',
            'Assign systematic risk ratings (Low/Medium/High) based on injury history, role security, and team context',
            'Assess age trajectory and multi-year value sustainability for keeper decisions',
            'Evaluate opportunity cost of keeper slots versus draft flexibility and positional scarcity',
            'Consider bye week overlaps and roster construction implications across all keepers',
            'Analyze all potential keepers comparatively with direct position group comparisons',
            'Present results in concise, scannable format: Executive Summary Table + Brief Individual Analysis',
            'Rank keepers from best to worst value with clear tier separations and value explanations',
            'Recommend 2-3 optimal keeper combinations for balanced roster construction',
            'Provide individual keep/pass recommendation for each player with risk-adjusted reasoning',
            'Include draft strategy guidance: which positions to prioritize in early rounds after keeper selections'
        ]
        
        enhanced_prompt = PromptBuilder.build_enhanced_prompt(
            task_description='Strategic Keeper Analysis with Risk Assessment - Provide concise, actionable keeper recommendations with optimal combinations and draft strategy',
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

# ============================================================================
# WAIVER WIRE BENCH ANALYSIS ENHANCEMENT - Helper Functions
# ============================================================================

def build_complete_roster_context(filled_positions, empty_positions, waiver_candidate_data):
    """
    Build comprehensive roster context including bench depth analysis.
    
    Args:
        filled_positions: dict - {position: player_name}
        empty_positions: list - [position, position, ...]
        waiver_candidate_data: dict - player data for waiver candidate
        
    Returns:
        dict: {
            'roster_context': str,  # Full roster description
            'bench_analysis': str,  # Bench depth analysis
            'drop_candidates': list,  # Potential players to drop
            'positional_needs': str,  # Position-specific analysis
            'empty_spots': list     # Available roster spots
        }
    """
    try:
        roster_context_parts = []
        bench_players = []
        starter_players = []
        drop_candidates = []
        
        # Standard roster positions for validation
        STANDARD_ROSTER_POSITIONS = ['QB', 'WR1', 'WR2', 'RB1', 'RB2', 'W/T', 'W/R/T', 'DEF', 
                                   'BN1', 'BN2', 'BN3', 'BN4', 'BN5', 'BN6', 'IR1', 'IR2']
        
        # Categorize positions
        bench_positions = [pos for pos in STANDARD_ROSTER_POSITIONS if pos.startswith('BN')]
        starter_positions = [pos for pos in STANDARD_ROSTER_POSITIONS if not pos.startswith('BN') and not pos.startswith('IR')]
        ir_positions = [pos for pos in STANDARD_ROSTER_POSITIONS if pos.startswith('IR')]
        
        # Build context for filled positions
        for pos, player_name in filled_positions.items():
            if not player_name.strip():
                continue
                
            player_data = combined_player_data_cache.get(normalize_player_name(player_name), {})
            enhanced_context = ContextFormatter.format_enhanced_player_context(
                player_data, AnalysisType.WAIVER_ANALYSIS
            )
            
            # Categorize players
            if pos in bench_positions:
                bench_players.append({
                    'position': pos,
                    'name': player_name,
                    'context': enhanced_context,
                    'data': player_data
                })
            elif pos in starter_positions:
                starter_players.append({
                    'position': pos,
                    'name': player_name, 
                    'context': enhanced_context,
                    'data': player_data
                })
            
            roster_context_parts.append(f"**{pos.upper()}**: {enhanced_context}")
        
        # Add empty positions to context
        empty_starters = [pos for pos in empty_positions if pos in starter_positions]
        empty_bench = [pos for pos in empty_positions if pos in bench_positions]
        empty_ir = [pos for pos in empty_positions if pos in ir_positions]
        
        for pos in empty_starters:
            roster_context_parts.append(f"**{pos.upper()}**: [EMPTY STARTER SPOT]")
        
        for pos in empty_bench:
            roster_context_parts.append(f"**{pos.upper()}**: [EMPTY BENCH SPOT]")
            
        for pos in empty_ir:
            roster_context_parts.append(f"**{pos.upper()}**: [EMPTY IR SPOT]")
        
        # Build comprehensive context strings
        roster_context = "\n\n".join(roster_context_parts)
        
        # Analyze bench depth
        bench_analysis_parts = []
        if bench_players:
            bench_analysis_parts.append(f"BENCH PLAYERS ({len(bench_players)} filled):")
            for player in bench_players:
                tier_info = get_player_tier_info(player['data'])
                bench_analysis_parts.append(f"  • {player['name']} ({player['position']}) - {tier_info}")
        
        if empty_bench:
            bench_analysis_parts.append(f"EMPTY BENCH SPOTS ({len(empty_bench)}): {', '.join(empty_bench)}")
        
        bench_analysis = "\n".join(bench_analysis_parts) if bench_analysis_parts else "No bench analysis available"
        
        # Rank drop candidates (bench players first, then worst starters)
        drop_candidates = rank_drop_candidates(filled_positions, waiver_candidate_data)
        
        # Analyze positional needs
        positional_needs = analyze_positional_needs(starter_players, bench_players, waiver_candidate_data)
        
        return {
            'roster_context': roster_context,
            'bench_analysis': bench_analysis,
            'drop_candidates': drop_candidates,
            'positional_needs': positional_needs,
            'empty_spots': empty_positions,
            'bench_spots_available': len(empty_bench),
            'starter_spots_available': len(empty_starters)
        }
        
    except Exception as e:
        print(f"ERROR in build_complete_roster_context: {e}")
        # Return minimal context if error occurs
        return {
            'roster_context': "\n\n".join([f"**{pos.upper()}**: {name}" for pos, name in filled_positions.items()]),
            'bench_analysis': "Bench analysis unavailable due to error",
            'drop_candidates': [],
            'positional_needs': "Positional analysis unavailable",
            'empty_spots': empty_positions,
            'bench_spots_available': 0,
            'starter_spots_available': 0
        }

def get_player_tier_info(player_data):
    """Get tier information for a player (QB1, RB2, etc.)."""
    try:
        position = player_data.get('position', 'UNK')
        
        # Try multiple ECR field names (ecr_overall is primary field in combined cache)
        ecr = (player_data.get('ecr_overall') or 
               player_data.get('ecr') or 
               player_data.get('ecr_positional') or 
               player_data.get('weekly_ecr'))
        
        if not ecr:
            return f"{position}? (No ECR)"
        
        ecr_val = float(ecr)
        
        # Position tier thresholds
        tier_thresholds = {
            'QB': [12, 24],  # QB1 (1-12), QB2 (13-24), QB3+ (25+)
            'RB': [24, 36],  # RB1 (1-24), RB2 (25-36), RB3+ (37+)
            'WR': [36, 48],  # WR1 (1-36), WR2 (37-48), WR3+ (49+)
            'TE': [12, 24],  # TE1 (1-12), TE2 (13-24), TE3+ (25+)
            'DST': [12, 24], # DST1 (1-12), DST2 (13-24), DST3+ (25+)
        }
        
        thresholds = tier_thresholds.get(position, [24, 36])  # Default thresholds
        
        if ecr_val <= thresholds[0]:
            tier = f"{position}1"
        elif ecr_val <= thresholds[1]:
            tier = f"{position}2"
        else:
            tier = f"{position}3+"
            
        return f"{tier}, ECR: {ecr_val}"
        
    except Exception as e:
        return f"{player_data.get('position', 'UNK')}? (Error: {e})"

def rank_drop_candidates(filled_positions, waiver_candidate_data):
    """
    Rank all rostered players by drop priority.
    
    Ranking Factors:
    1. Position type priority (bench > flex > starter)
    2. Player tier level (QB2 > QB1, RB3 > RB1)
    3. Positional depth (deep position > shallow position)
    4. Age and injury considerations
    5. Bye week conflicts
    
    Returns:
        list: [(player_name, position, drop_score, reasoning), ...]
    """
    try:
        candidates = []
        
        # Standard position categories
        bench_positions = ['BN1', 'BN2', 'BN3', 'BN4', 'BN5', 'BN6']
        flex_positions = ['W/T', 'W/R/T']
        core_starters = ['QB', 'WR1', 'WR2', 'RB1', 'RB2', 'DEF']
        
        for pos, player_name in filled_positions.items():
            if not player_name.strip():
                continue
                
            player_data = combined_player_data_cache.get(normalize_player_name(player_name), {})
            drop_score = calculate_drop_priority_score(pos, player_data, waiver_candidate_data)
            reasoning = get_drop_reasoning(pos, player_data, drop_score)
            
            candidates.append({
                'name': player_name,
                'position': pos,
                'drop_score': drop_score,
                'reasoning': reasoning,
                'tier_info': get_player_tier_info(player_data)
            })
        
        # Sort by drop score (higher = more droppable)
        candidates.sort(key=lambda x: x['drop_score'], reverse=True)
        
        return candidates[:5]  # Return top 5 drop candidates
        
    except Exception as e:
        print(f"ERROR in rank_drop_candidates: {e}")
        return []

def calculate_drop_priority_score(position, player_data, waiver_candidate_data):
    """Calculate numerical drop priority score (higher = more droppable)."""
    try:
        score = 0
        
        # Position type scoring (bench > flex > starter)
        if position.startswith('BN'):
            score += 100  # Bench players are most droppable
        elif position in ['W/T', 'W/R/T']:
            score += 50   # Flex players moderately droppable
        elif position in ['IR1', 'IR2']:
            score += 25   # IR players only if healthy
        else:
            score += 10   # Core starters least droppable
        
        # ECR-based scoring (higher ECR = more droppable)
        ecr = player_data.get('ecr')
        if ecr:
            try:
                ecr_val = float(ecr)
                if ecr_val > 100:
                    score += 50  # Very droppable
                elif ecr_val > 60:
                    score += 30  # Moderately droppable
                elif ecr_val > 36:
                    score += 15  # Somewhat droppable
                # Players with ECR < 36 get no penalty (elite players)
            except:
                score += 20  # Unknown ECR adds moderate penalty
        else:
            score += 20  # No ECR data adds moderate penalty
        
        # Position scarcity considerations
        player_pos = player_data.get('position', '')
        if player_pos in ['QB', 'TE', 'DST']:
            score += 10  # These positions have less depth, more droppable
        elif player_pos in ['RB', 'WR']:
            score += 5   # Skill positions have more depth
        
        return score
        
    except Exception as e:
        print(f"ERROR calculating drop score: {e}")
        return 50  # Default moderate score

def get_drop_reasoning(position, player_data, drop_score):
    """Generate human-readable reasoning for drop candidate."""
    try:
        reasons = []
        
        if position.startswith('BN'):
            reasons.append("bench player")
        elif position in ['W/T', 'W/R/T']:
            reasons.append("flex position")
            
        ecr = player_data.get('ecr')
        if ecr:
            try:
                ecr_val = float(ecr)
                if ecr_val > 100:
                    reasons.append("very low ECR")
                elif ecr_val > 60:
                    reasons.append("low ECR")
            except:
                pass
        
        tier_info = get_player_tier_info(player_data)
        if any(x in tier_info for x in ['3+', '?']):
            reasons.append("lower tier")
            
        if not reasons:
            reasons.append("available for drop")
            
        return ", ".join(reasons)
        
    except Exception as e:
        return "drop candidate"

def analyze_positional_needs(starter_players, bench_players, waiver_candidate_data):
    """Analyze positional depth and needs."""
    try:
        position_counts = {}
        
        # Count players by position
        all_players = starter_players + bench_players
        for player in all_players:
            pos = player['data'].get('position', 'UNK')
            position_counts[pos] = position_counts.get(pos, 0) + 1
        
        # Analyze depth
        waiver_pos = waiver_candidate_data.get('position', 'UNK')
        current_depth = position_counts.get(waiver_pos, 0)
        
        analysis_parts = []
        analysis_parts.append(f"ADDING: {waiver_pos} (current depth: {current_depth})")
        
        if current_depth == 0:
            analysis_parts.append(f"  • Adding {waiver_pos} fills positional need")
        elif current_depth == 1:
            analysis_parts.append(f"  • Adding {waiver_pos} provides depth")
        else:
            analysis_parts.append(f"  • Adding {waiver_pos} increases depth (consider drops)")
        
        # Position depth summary
        depth_summary = []
        for pos, count in sorted(position_counts.items()):
            if count == 1:
                depth_summary.append(f"{pos}: shallow")
            elif count >= 3:
                depth_summary.append(f"{pos}: deep")
            else:
                depth_summary.append(f"{pos}: adequate")
        
        analysis_parts.append("DEPTH: " + ", ".join(depth_summary))
        
        return "\n".join(analysis_parts)
        
    except Exception as e:
        return f"Positional analysis error: {e}"

def parse_drop_recommendation(ai_response):
    """
    Parse AI response to extract structured drop recommendations.
    
    Patterns to detect:
    - "ADD: [Player], DROP: [Player]"
    - "ADD: [Player], OPEN SPOT: [Position]" 
    - "DO NOT ADD: [Reason]"
    
    Returns:
        dict: {
            'action': 'add' | 'reject',
            'add_player': str,
            'drop_player': str | None,
            'open_spot': str | None,
            'reasoning': str,
            'confidence': str
        }
    """
    try:
        if not ai_response:
            return None
            
        response_text = ai_response.lower()
        
        # Check for rejection patterns
        if any(phrase in response_text for phrase in ['do not add', 'don\'t add', 'avoid adding', 'pass on']):
            return {
                'action': 'reject',
                'add_player': None,
                'drop_player': None,
                'open_spot': None,
                'reasoning': 'AI recommends not adding this player',
                'confidence': 'medium'
            }
        
        # Look for ADD patterns
        import re
        
        # Pattern: ADD: [Player], DROP: [Player]
        add_drop_pattern = r'add[:\s]+([^,]+),?\s*drop[:\s]+([^,\n]+)'
        match = re.search(add_drop_pattern, response_text, re.IGNORECASE)
        
        if match:
            return {
                'action': 'add',
                'add_player': match.group(1).strip(),
                'drop_player': match.group(2).strip(),
                'open_spot': None,
                'reasoning': 'Upgrade opportunity identified',
                'confidence': 'high'
            }
        
        # Pattern: ADD: [Player], OPEN SPOT
        add_open_pattern = r'add[:\s]+([^,]+),?\s*open\s+spot'
        match = re.search(add_open_pattern, response_text, re.IGNORECASE)
        
        if match:
            return {
                'action': 'add',
                'add_player': match.group(1).strip(),
                'drop_player': None,
                'open_spot': 'available',
                'reasoning': 'Open roster spot available',
                'confidence': 'high'
            }
        
        # Default to add if no clear pattern found
        return {
            'action': 'add',
            'add_player': 'player',
            'drop_player': None,
            'open_spot': None,
            'reasoning': 'Analysis provided',
            'confidence': 'low'
        }
        
    except Exception as e:
        print(f"ERROR parsing drop recommendation: {e}")
        return None

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
        
        # Build roster context with enhanced formatting and position validation
        roster_analysis = []
        position_warnings = []
        
        for pos, name in roster.items():
            if name:
                player_data = combined_player_data_cache.get(normalize_player_name(name), {})
                
                # Validate position compatibility
                if not is_valid_player_for_position(player_data, pos):
                    player_pos = player_data.get('position', 'Unknown')
                    flex_info = get_position_flexibility_info(pos)
                    allowed_positions = ', '.join(flex_info['allowed_positions'])
                    position_warnings.append(
                        f"⚠️ {name} ({player_pos}) may not be valid for {pos} position (allows: {allowed_positions})"
                    )
                
                enhanced_context = ContextFormatter.format_enhanced_player_context(
                    player_data, AnalysisType.WAIVER_ANALYSIS
                )
                
                # Add position flexibility info for flex positions
                flex_info = get_position_flexibility_info(pos)
                if len(flex_info['allowed_positions']) > 1:
                    enhanced_context += f"\n- Position Slot: {pos} ({flex_info['description']})"
                
                roster_analysis.append(f"**{pos.upper()}**: {enhanced_context}")
        
        roster_context = "\n\n".join(roster_analysis)
        
        # Add position warnings to context if any
        if position_warnings:
            roster_context += "\n\n**POSITION COMPATIBILITY NOTES:**\n" + "\n".join(position_warnings)
        
        # Get waiver decision examples (falls back to player analysis examples)
        waiver_examples = ExampleLibrary.get_examples_for_analysis_type('waiver_swap_analysis')
        
        # Build enhanced prompt with waiver wire methodology
        enhanced_prompt = PromptBuilder.build_enhanced_prompt(
            task_description="Tier-Based Waiver Swap Analysis - CRITICAL: Use tier classifications (QB1 vs QB2, RB1 vs RB2, etc.) to evaluate upgrades. QB1 players should almost always be prioritized over QB2 players.",
            player_data=f"CURRENT ROSTER:\n{roster_context}\n\nWAIVER WIRE CANDIDATE:\n{waiver_candidate_context}",
            examples=waiver_examples,
            methodology_steps=[
                "1. TIER-BASED VALUE ASSESSMENT",
                "   • CRITICAL: Identify player tiers (QB1 vs QB2, RB1 vs RB2, etc.)",
                "   • QB1 (top 12) >> QB2 (13-24) is almost always an upgrade worth making",
                "   • Elite players (top 5 at position) should almost always be added",
                "   • Evaluate ECR and positional ranking with clear tier context",
                "   • Consider recent trend momentum and role security",
                "",
                "2. POSITIONAL UPGRADE ANALYSIS",
                "   • Compare current roster player tier vs waiver candidate tier",
                "   • RULE: Moving from QB2 to QB1 is a high-priority upgrade",
                "   • RULE: Any tier upgrade (QB2→QB1, RB2→RB1) is valuable",
                "   • Consider positional scarcity (QB depth vs RB/WR depth)",
                "   • Assess starter vs bench player impact on weekly lineup",
                "",
                "3. ROSTER COMPOSITION IMPACT",
                "   • Identify which current player would be replaced/dropped",
                "   • Compare tiers: is this a clear upgrade, lateral move, or downgrade?",
                "   • Consider bye week management and roster flexibility",
                "   • Evaluate bench depth at position after potential move",
                "",
                "4. TIER-BASED DECISION FRAMEWORK",
                "   • ADD if upgrading tiers (QB2→QB1 = clear add)",
                "   • ADD if acquiring elite player (top 5 at position)",
                "   • CONSIDER if lateral move within same tier",
                "   • DO NOT ADD if downgrading tiers",
                "   • Factor timing urgency for elite/tier-upgrade opportunities",
                "",
                "5. CLEAR RECOMMENDATION WITH TIER LOGIC",
                "   • State explicit ADD/DO NOT ADD with tier-based reasoning",
                "   • Example: 'ADD - Clear upgrade from QB2 to elite QB1'",
                "   • Include confidence level: High (tier upgrades), Medium (lateral), Low (downgrades)",
                "   • If ADD: specify exact player to DROP with justification",
                "   • Quantify expected improvement and confidence level",
                "   • Address any close-call factors or alternative scenarios"
            ]
        )
        
        response_text = make_gemini_request(enhanced_prompt, user_key)
        result = process_ai_response_v2(response_text, 'waiver_swap')
        
        # Include position warnings in response if any
        if position_warnings:
            result += "\n\n---\n**Position Compatibility Warnings:**\n" + "\n".join(position_warnings)
        
        return jsonify({'result': result})
    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/waiver_swap_analysis_enhanced', methods=['POST'])
def waiver_swap_analysis_enhanced():
    """
    Enhanced waiver swap analysis with comprehensive bench analysis.
    Accepts complete roster data including empty positions.
    """
    try:
        user_key = request.headers.get('X-API-Key')
        data = request.json
        
        # Enhanced data structure - accepts both formats for compatibility
        roster_data = data.get('roster_data', {})
        filled_positions = roster_data.get('filled_positions', data.get('roster', {}))
        empty_positions = roster_data.get('empty_positions', [])
        player_to_add = data.get('player_to_add')
        ecr_type_pref = data.get('ecr_type_preference', 'overall')

        if not filled_positions and not empty_positions:
            # Fallback to traditional format
            roster = data.get('roster', {})
            if not roster:
                return jsonify({"error": "Roster data is required."}), 400
            filled_positions = roster
            empty_positions = []
            
        if not player_to_add:
            return jsonify({"error": "player_to_add is required."}), 400

        print(f"DEBUG: Enhanced waiver analysis for {player_to_add}")
        print(f"DEBUG: Filled positions: {len(filled_positions)}, Empty positions: {len(empty_positions)}")

        # Get enhanced context for the waiver candidate
        waiver_player_data = combined_player_data_cache.get(normalize_player_name(player_to_add), {})
        waiver_candidate_context = ContextFormatter.format_enhanced_player_context(
            waiver_player_data, AnalysisType.WAIVER_ANALYSIS
        )
        
        # Build comprehensive roster context using helper functions
        roster_analysis = build_complete_roster_context(
            filled_positions, empty_positions, waiver_player_data
        )
        
        # Build position warnings if any
        position_warnings = []
        for pos, name in filled_positions.items():
            if name and name.strip():
                player_data = combined_player_data_cache.get(normalize_player_name(name), {})
                if not is_valid_player_for_position(player_data, pos):
                    player_pos = player_data.get('position', 'Unknown')
                    flex_info = get_position_flexibility_info(pos)
                    allowed_positions = ', '.join(flex_info['allowed_positions'])
                    position_warnings.append(
                        f"⚠️ {name} ({player_pos}) may not be valid for {pos} position (allows: {allowed_positions})"
                    )
        
        # Get waiver decision examples
        waiver_examples = ExampleLibrary.get_examples_for_analysis_type('waiver_swap_analysis')
        
        # Build enhanced prompt with comprehensive bench analysis methodology
        enhanced_prompt = PromptBuilder.build_enhanced_prompt(
            task_description="Balanced Waiver Analysis with EMPTY SPOT PRIORITY - CRITICAL: Provide helpful analysis in 6-8 sentences. If ANY bench spots are empty, use them instead of dropping players.",
            player_data=f"🚨 EMPTY BENCH SPOTS AVAILABLE: {roster_analysis['bench_spots_available']} spots\n\n{'⚠️ CRITICAL: USE EMPTY SPOTS FIRST - DO NOT DROP ANYONE!' if roster_analysis['bench_spots_available'] > 0 else 'ℹ️ Roster completely full - analyze drop candidates'}\n\nCURRENT ROSTER:\n{roster_analysis['roster_context']}\n\nBENCH ANALYSIS:\n{roster_analysis['bench_analysis']}\n\nPOSITIONAL NEEDS:\n{roster_analysis['positional_needs']}\n\nWAIVER WIRE CANDIDATE:\n{waiver_candidate_context}",
            examples=waiver_examples,
            methodology_steps=[
                "1. TIER-BASED VALUE ASSESSMENT",
                "   • CRITICAL: Identify player tiers (QB1 vs QB2, RB1 vs RB2, etc.)",
                "   • QB1 (top 12) >> QB2 (13-24) is almost always an upgrade worth making",
                "   • Elite players (top 5 at position) should almost always be added",
                "   • Evaluate ECR and positional ranking with clear tier context",
                "   • Consider recent trend momentum and role security",
                "",
                "2. POSITIONAL UPGRADE ANALYSIS",
                "   • Compare current roster player tier vs waiver candidate tier",
                "   • RULE: Moving from QB2 to QB1 is a high-priority upgrade",
                "   • RULE: Any tier upgrade (QB2→QB1, RB2→RB1) is valuable",
                "   • Consider positional scarcity (QB depth vs RB/WR depth)",
                "   • Assess starter vs bench player impact on weekly lineup",
                "",
                "3. ROSTER COMPOSITION IMPACT",
                "   • Identify which current player would be replaced/dropped",
                "   • Compare tiers: is this a clear upgrade, lateral move, or downgrade?",
                "   • Consider bye week management and roster flexibility",
                "   • Evaluate bench depth at position after potential move",
                "",
                "4. TIER-BASED DECISION FRAMEWORK",
                "   • ADD if upgrading tiers (QB2→QB1 = clear add)",
                "   • ADD if acquiring elite player (top 5 at position)",
                "   • CONSIDER if lateral move within same tier",
                "   • DO NOT ADD if downgrading tiers",
                "   • Factor timing urgency for elite/tier-upgrade opportunities",
                "",
                "5. CLEAR RECOMMENDATION WITH TIER LOGIC",
                "   • State explicit ADD/DO NOT ADD with tier-based reasoning",
                "   • Example: 'ADD - Clear upgrade from QB2 to elite QB1'",
                "   • Include confidence level: High (tier upgrades), Medium (lateral), Low (downgrades)",
                "   • If ADD: specify exact player to DROP with justification",
                "   • Quantify expected improvement and confidence level",
                "   • Address any close-call factors or alternative scenarios",
                "",
                "6. EMPTY BENCH SPOT PRIORITY CHECK - **CRITICAL FIRST STEP**",
                "   • **MANDATORY**: Check if any bench spots (BN1-BN6) are empty",
                "   • **IF EMPTY SPOTS EXIST**: Use empty spot, DO NOT consider any drops",
                "   • **RULE**: Empty spots always take priority over any drop decision",
                "   • **FORMAT**: 'RECOMMENDATION: ADD [Player], OPEN SPOT: [Position], REASON: Empty bench spot available'",
                "   • **STOP HERE** if empty spots available - do not analyze drops",
                "",
                "7. COMPREHENSIVE ROSTER ANALYSIS (Only if NO empty spots)",
                "   • SCAN ALL POSITIONS: Analyze starters, flex, and bench players",
                "   • BENCH DEPTH ASSESSMENT: Identify weakest bench players by tier",
                "   • POSITIONAL FLEXIBILITY: Consider W/T and W/R/T slot optimization",
                "   • **ONLY PROCEED** if all 16 roster spots are completely filled",
                "",
                "8. SYSTEMATIC DROP CANDIDATE EVALUATION (Only if roster completely full)", 
                "   • BENCH FIRST RULE: Always consider bench players before starters",
                "   • CROSS-POSITION DROPS: Drop weak bench RB for strong waiver WR",
                "   • TIER-BASED RANKING: Drop QB3 before QB2, RB4 before RB2",
                "   • DEPTH CONSIDERATION: Keep shallow positions, drop deep positions",
                "",
                "9. BALANCED OUTPUT FORMAT - **HELPFUL BUT NOT VERBOSE**",
                "   • **AIM FOR 6-8 SENTENCES TOTAL** - Informative but concise",
                "   • **CLEAR RECOMMENDATION FIRST**: Start with bold recommendation",
                "   • **PLAYER COMPARISON**: 2-3 sentences comparing waiver candidate vs current players",
                "   • **REASONING**: 2-3 sentences explaining the decision with tier/ECR context",
                "   • **NO REPETITION**: Avoid repeating the same points multiple times",
                "",
                "10. STRUCTURED RECOMMENDATION OUTPUT",
                "   • **PRIMARY FORMAT** (if empty spots): '✅ **RECOMMENDATION: ADD [Player] to OPEN BENCH SPOT ([BN#])**'",
                "   • **SECONDARY FORMAT** (if full roster): '✅ **RECOMMENDATION: ADD [Player], DROP [Player]**'", 
                "   • **REJECTION FORMAT**: '❌ **RECOMMENDATION: DO NOT ADD [Player]**'",
                "   • **FOLLOW WITH**: Brief 1-2 sentence explanation only",
                "   • **CRITICAL**: Be concise, actionable, and avoid verbose analysis"
            ]
        )
        
        # Make AI request
        response_text = make_gemini_request(enhanced_prompt, user_key)
        result = process_ai_response_v2(response_text, 'waiver_swap_enhanced')
        
        # Include position warnings in response if any
        if position_warnings:
            result += "\n\n---\n**Position Compatibility Warnings:**\n" + "\n".join(position_warnings)
        
        # Phase D: Smart Drop Summary Logic
        bench_spots = roster_analysis['bench_spots_available']
        drop_candidates = roster_analysis['drop_candidates']
        
        # Only show additional context when truly needed
        if bench_spots > 0:
            # Scenario: Empty spots available
            # AI should handle this, but add reminder if AI missed it
            if 'open' not in result.lower() and 'empty' not in result.lower() and 'spot' not in result.lower():
                result += f"\n\n💡 **Note**: {bench_spots} open bench spots available - consider using instead of dropping players."
        
        elif bench_spots == 0 and drop_candidates:
            # Scenario: Roster completely full, may need drop guidance
            ai_mentioned_drops = any(word in result.lower() for word in ['drop', 'release', 'cut'])
            
            if not ai_mentioned_drops:
                # AI didn't suggest specific drops, provide helpful summary
                top_drops = drop_candidates[:2]  # Show top 2 only
                drop_names = [f"{c['name']} ({c['tier_info'].split(',')[0]})" for c in top_drops]
                result += f"\n\n**💡 Consider dropping:** {' or '.join(drop_names)}"
            
            # If roster is full but AI still said to use open spot, that's an error - correct it
            if any(phrase in result.lower() for phrase in ['open spot', 'empty spot', 'bench spot']):
                result += f"\n\n**⚠️ Note**: Roster is actually full ({16 - bench_spots}/16 spots filled) - drops required for additions."
        
        return jsonify({
            'result': result,
            'roster_analysis': roster_analysis,
            'drop_recommendation': parse_drop_recommendation(result),
            'enhanced': True
        })
        
    except Exception as e:
        print(f"ERROR: Enhanced waiver analysis failed: {e}")
        traceback.print_exc()
        
        # Fallback to traditional analysis if enhanced fails
        try:
            print("INFO: Falling back to traditional waiver analysis")
            fallback_data = {
                'roster': filled_positions,
                'player_to_add': player_to_add,
                'ecr_type_preference': ecr_type_pref
            }
            
            # Call traditional endpoint logic
            return waiver_swap_analysis()
            
        except Exception as fallback_error:
            print(f"ERROR: Fallback analysis also failed: {fallback_error}")
            return jsonify({"error": f"Both enhanced and fallback analysis failed: {str(e)}"}), 500

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
            task_description="Tier-Based Waiver Wire Analysis - CRITICAL: Prioritize tier upgrades (QB2→QB1, RB2→RB1) and elite players (top 5 at position). Use clear tier classifications to guide recommendations.",
            player_data=f"CURRENT ROSTER:\n{roster_context}\n\nTOP AVAILABLE PLAYERS:\n{available_players_context}",
            examples=waiver_examples,
            methodology_steps=[
                "1. TIER-BASED ROSTER ASSESSMENT",
                "   • Identify current roster tiers: QB1/QB2, RB1/RB2/RB3, WR1/WR2/WR3, TE1/TE2",
                "   • Highlight obvious upgrade opportunities (QB2→QB1, RB3→RB2, etc.)",
                "   • Assess bye week vulnerabilities within tier context",
                "   • Consider positional scarcity and streaming requirements",
                "",
                "2. TIER-BASED AVAILABLE PLAYER EVALUATION", 
                "   • Categorize available players by tier (QB1, RB1, etc.)",
                "   • PRIORITIZE: Elite players (top 5 at position) = highest priority",
                "   • PRIORITIZE: Tier upgrades (adding QB1 when you have QB2)",
                "   • Consider trending players and role security within tiers",
                "   • Factor in schedule strength and matchup advantages",
                "",
                "3. TIER-UPGRADE PRIORITY STRATEGY",
                "   • TOP PRIORITY: Elite players (QB1, top 5 RB/WR, TE1)",
                "   • HIGH PRIORITY: Clear tier upgrades (QB2→QB1, RB2→RB1)",
                "   • MEDIUM PRIORITY: Same-tier improvements or depth adds",
                "   • Balance immediate tier upgrades vs future potential",
                "   • Account for league competition for elite/tier-upgrade players",
                "",
                "4. TIER-AWARE DROP CANDIDATE IDENTIFICATION",
                "   • Identify drop candidates from lowest tiers first",
                "   • Prioritize players with declining roles or tier downgrades",
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
YAHOO_REDIRECT_URI = 'https://localhost:5000/api/yahoo/callback'
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

        # Determine frontend URL based on request origin for local development support
        referer = request.headers.get('Referer', '')
        if 'localhost' in referer:
            frontend_url = 'http://localhost:3000'
        else:
            frontend_url = 'https://ratm-app.vercel.app'

        return redirect(f'{frontend_url}/#yahoo-leagues?token={encoded_token}')

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

    # Prepare direct request headers for Yahoo API
    yahoo_headers = {
        'Authorization': f'Bearer {access_token_string}',
        'Accept': 'application/json'
    }

    try:
        # The URL for fetching a user's games, then leagues for the NFL game (game_key=nfl)
        # We use 'use_login=1' to specify the logged-in user.
        url = 'https://fantasysports.yahooapis.com/fantasy/v2/users;use_login=1/games;game_keys=nfl/leagues;out=teams?format=json'

        response = requests.get(url, headers=yahoo_headers, timeout=10)
        response.raise_for_status()  # Raise an exception for bad status codes
        
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

def _derive_league_key_from_team_key(team_key: str) -> str:
    try:
        # Typical pattern: 461.l.12345.t.7 -> 461.l.12345
        return team_key.split('.t.')[0]
    except Exception:
        return ''

def _extract_roster_player_entries_minimal(data):
    """Extract roster player entries even when only minimal fields are present.

    Returns list of dicts with keys: player_key, player_id, selected_position, eligible_positions, status.
    """
    results = []
    try:
        fantasy_content = data.get('fantasy_content', {}) if isinstance(data, dict) else {}
        team_data = fantasy_content.get('team', [])
        roster_container = _find_roster_container(team_data)
        if not isinstance(roster_container, dict):
            return results
        players_data = roster_container.get('players', {})

        def add_entry_from_container(pc):
            if not isinstance(pc, dict):
                return
            agg = _extract_player_fields_from_any(pc)
            if not agg or not agg.get('player_key'):
                return
            results.append({
                'player_key': agg.get('player_key', ''),
                'player_id': agg.get('player_id', ''),
                'selected_position': agg.get('selected_position', ''),
                'eligible_positions': agg.get('eligible_positions', []),
                'status': agg.get('status', ''),
            })

        def handle_container(pc):
            add_entry_from_container(pc)

        if isinstance(players_data, dict):
            for key, player_container in players_data.items():
                if str(key).lower() == 'count':
                    continue
                handle_container(player_container)
        elif isinstance(players_data, list):
            for player_container in players_data:
                handle_container(player_container)
        return results
    except Exception:
        return results

def _find_first_dict_with_key(obj, key):
    """Recursively search lists/dicts for the first dict containing a key."""
    if isinstance(obj, dict):
        if key in obj:
            return obj
        for v in obj.values():
            found = _find_first_dict_with_key(v, key)
            if found:
                return found
        return None
    if isinstance(obj, list):
        for item in obj:
            found = _find_first_dict_with_key(item, key)
            if found:
                return found
        return None
    return None

def _find_roster_container(team_data):
    """Find the roster container in Yahoo's team structure (handles nested list-of-lists)."""
    holder = _find_first_dict_with_key(team_data, 'roster')
    return holder.get('roster', {}) if isinstance(holder, dict) else {}

def _extract_players_collection(roster_container):
    """Return the Yahoo 'players' collection from a roster container (recursive)."""
    holder = _find_first_dict_with_key(roster_container, 'players')
    if isinstance(holder, dict) and 'players' in holder:
        return holder.get('players', {})
    return {}

def _collect_dicts(obj, acc):
    """Recursively collect all dict nodes under obj into acc list."""
    if isinstance(obj, dict):
        acc.append(obj)
        for v in obj.values():
            _collect_dicts(v, acc)
    elif isinstance(obj, list):
        for item in obj:
            _collect_dicts(item, acc)
    return acc

def _extract_player_fields_from_any(player_container):
    """Extract player fields from any Yahoo player container shape by deep-scanning.

    Returns dict with keys: player_key, player_id, name, selected_position, eligible_positions, status.
    """
    dicts = _collect_dicts(player_container, [])
    player_key = ''
    player_id = ''
    name = ''
    selected_position = ''
    eligible_positions = []
    status = ''

    for d in dicts:
        if not player_key and 'player_key' in d:
            player_key = d.get('player_key', '')
        if not player_id and 'player_id' in d:
            player_id = d.get('player_id', '')
        if not name and 'name' in d:
            name_val = d.get('name')
            if isinstance(name_val, dict):
                name = name_val.get('full') or name
            elif isinstance(name_val, str):
                name = name_val or name
        if not selected_position and 'selected_position' in d:
            sp = d.get('selected_position')
            if isinstance(sp, dict):
                selected_position = sp.get('position', selected_position) or selected_position
            elif isinstance(sp, list):
                # Some responses provide selected_position as a list of dicts
                for item in sp:
                    if isinstance(item, dict) and item.get('position'):
                        selected_position = item.get('position')
                        break
            elif isinstance(sp, str):
                selected_position = sp or selected_position
        if not eligible_positions and 'eligible_positions' in d:
            eps = d.get('eligible_positions')
            if isinstance(eps, list):
                eligible_positions = eps
            elif isinstance(eps, str):
                eligible_positions = [eps]
        if not status and 'status' in d:
            status = d.get('status', status)

    if player_key:
        return {
            'player_key': player_key,
            'player_id': player_id,
            'name': name,
            'selected_position': selected_position,
            'eligible_positions': eligible_positions,
            'status': status,
        }
    return None

def _fetch_yahoo_player_details_by_keys(access_token: str, league_key: str, player_keys: list):
    """Batch-fetch player details using league players collection and player_keys.

    Returns dict mapping player_key -> {'name': str, 'eligible_positions': list}
    """
    details = {}
    if not access_token or not league_key or not player_keys:
        return details
    try:
        import requests as _req
        base = "https://fantasysports.yahooapis.com/fantasy/v2"
        # Yahoo supports comma-separated keys; cap batch size to reasonable number
        keys_chunk = ','.join(player_keys)
        url = f"{base}/league/{league_key}/players;player_keys={keys_chunk}?format=json"
        headers = {"Authorization": f"Bearer {access_token}"}
        resp = _req.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        fantasy_content = data.get('fantasy_content', {}) if isinstance(data, dict) else {}
        league = fantasy_content.get('league', [])
        if not (isinstance(league, list) and len(league) >= 2):
            return details
        players_container = league[1].get('players', {})
        if not isinstance(players_container, dict):
            return details
        for key, entry in players_container.items():
            if not str(key).isdigit():
                continue
            player_arr = entry.get('player', [])
            if not (isinstance(player_arr, list) and len(player_arr) >= 1):
                continue
            pdata = player_arr[0]
            pkey = pdata.get('player_key')
            name_data = pdata.get('name', {})
            full_name = name_data.get('full') if isinstance(name_data, dict) else (str(name_data) if name_data else '')
            eligible_positions = pdata.get('eligible_positions', [])
            if not isinstance(eligible_positions, list):
                eligible_positions = [str(eligible_positions)] if eligible_positions else []
            if pkey:
                details[pkey] = {
                    'name': full_name or '',
                    'eligible_positions': eligible_positions,
                }
        return details
    except Exception:
        return details

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

    # Prepare direct request headers for Yahoo API
    yahoo_headers = {
        'Authorization': f'Bearer {access_token_string}',
        'Accept': 'application/json'
    }

    try:
        # Prefer explicit players subresource per Yahoo docs
        if week:
            url_primary = f'https://fantasysports.yahooapis.com/fantasy/v2/team/{team_key}/roster/players;week={week}?format=json'
            url_fallback = f'https://fantasysports.yahooapis.com/fantasy/v2/team/{team_key}/roster;week={week}?format=json'
        else:
            url_primary = f'https://fantasysports.yahooapis.com/fantasy/v2/team/{team_key}/roster/players?format=json'
            url_fallback = f'https://fantasysports.yahooapis.com/fantasy/v2/team/{team_key}/roster?format=json'

        # Try primary (explicit players)
        print(f"DEBUG: Requesting Yahoo roster primary URL: {url_primary}")
        response = requests.get(url_primary, headers=yahoo_headers, timeout=10)
        if response.status_code == 404:
            # Some leagues may not support the explicit subresource path
            print("DEBUG: Primary roster URL 404, trying fallback URL")
            response = requests.get(url_fallback, headers=yahoo_headers, timeout=10)
        response.raise_for_status()

        try:
            raw = response.json()
        except Exception:
            print(f"ERROR: Yahoo roster response not JSON. Content-Type: {response.headers.get('Content-Type')}\nSnippet: {response.text[:200]}")
            raise
        parsed_players = parse_yahoo_roster_response(raw)
        minimal_entries = _extract_roster_player_entries_minimal(raw)
        print(f"DEBUG: Parsed {len(parsed_players) if isinstance(parsed_players, list) else 'N/A'} players; minimal_entries={len(minimal_entries)}")

        # If primary returned 200 but empty, try fallback URL anyway
        if (not parsed_players) and (not minimal_entries):
            print("DEBUG: Primary roster returned empty; attempting fallback URL despite 200 status")
            response = requests.get(url_fallback, headers=yahoo_headers, timeout=10)
            response.raise_for_status()
            raw = response.json()
            parsed_players = parse_yahoo_roster_response(raw)
            minimal_entries = _extract_roster_player_entries_minimal(raw)
            print(f"DEBUG: Fallback parse counts -> parsed={len(parsed_players) if isinstance(parsed_players, list) else 'N/A'}, minimal={len(minimal_entries)}")

        if parsed_players:
            return jsonify(parsed_players)

        # Fallback: batch-enrich using player_keys if names were missing
        if not minimal_entries:
            print("DEBUG: Minimal roster extraction returned 0 players")
            return jsonify([])

        league_key = _derive_league_key_from_team_key(team_key)
        keys = [p['player_key'] for p in minimal_entries]
        details_map = _fetch_yahoo_player_details_by_keys(access_token_string, league_key, keys)
        print(f"DEBUG: Batch details fetch resolved {len(details_map)} of {len(keys)} player keys")

        # Merge details and enrich locally
        merged = []
        for p in minimal_entries:
            d = details_map.get(p['player_key'], {})
            name = d.get('name', '')
            eligible_positions = d.get('eligible_positions', p.get('eligible_positions', []))
            entry = {
                'player_key': p['player_key'],
                'player_id': p.get('player_id', ''),
                'name': name,
                'selected_position': p.get('selected_position', ''),
                'eligible_positions': eligible_positions,
                'status': p.get('status', ''),
            }
            merged.append(entry)

        # Enrich named players; include unnamed as-is
        named = [m for m in merged if m.get('name')]
        unnamed = [m for m in merged if not m.get('name')]
        if named:
            named = enrich_roster_players(named)
        return jsonify(named + unnamed)

    except requests.exceptions.RequestException as req_e:
        print(f"Error fetching Yahoo roster: {req_e}")
        if getattr(req_e, 'response', None) is not None:
            print(f"Yahoo roster error response content: {req_e.response.text}")
        traceback.print_exc()
        return jsonify({"error": "Failed to fetch roster from Yahoo.", "details": str(req_e)}), 500
    except Exception as e:
        print(f"Error processing Yahoo roster: {e}")
        traceback.print_exc()
        return jsonify({"error": "Failed to process roster data.", "details": str(e)}), 500

@app.route('/api/yahoo/roster_debug')
def get_yahoo_roster_debug():
    """
    Debug endpoint: shows which roster URL branch is used and what we parsed.
    Requires Authorization header and team_key. Optional week.
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Not authenticated with Yahoo. Authorization header missing."}), 401

    team_key = request.args.get('team_key')
    if not team_key:
        return jsonify({"error": "team_key parameter is required."}), 400

    week = request.args.get('week')

    try:
        access_token_string = auth_header.split(' ')[1]
        if not access_token_string:
            return jsonify({"error": "Invalid token format: access_token missing."}), 401
    except Exception:
        return jsonify({"error": "Invalid token format in Authorization header."}), 401

    try:
        yahoo_headers = {
            'Authorization': f'Bearer {access_token_string}',
            'Accept': 'application/json'
        }

        if week:
            url_primary = f'https://fantasysports.yahooapis.com/fantasy/v2/team/{team_key}/roster/players;week={week}?format=json'
            url_fallback = f'https://fantasysports.yahooapis.com/fantasy/v2/team/{team_key}/roster;week={week}?format=json'
        else:
            url_primary = f'https://fantasysports.yahooapis.com/fantasy/v2/team/{team_key}/roster/players?format=json'
            url_fallback = f'https://fantasysports.yahooapis.com/fantasy/v2/team/{team_key}/roster?format=json'

        branch = 'primary'
        resp = requests.get(url_primary, headers=yahoo_headers, timeout=10)
        if resp.status_code == 404:
            branch = 'fallback'
            resp = requests.get(url_fallback, headers=yahoo_headers, timeout=10)

        status = resp.status_code
        try:
            raw = resp.json()
        except Exception:
            raw = {'__non_json__': True, 'content_type': resp.headers.get('Content-Type'), 'snippet': resp.text[:120]}

        parsed = parse_yahoo_roster_response(raw)
        minimal = _extract_roster_player_entries_minimal(raw)

        # If primary returned 200 but empty, try fallback URL anyway
        tried_secondary = False
        if (not parsed) and (not minimal):
            resp2 = requests.get(url_fallback, headers=yahoo_headers, timeout=10)
            if resp2.status_code == 200:
                tried_secondary = True
                try:
                    raw2 = resp2.json()
                except Exception:
                    raw2 = {}
                parsed2 = parse_yahoo_roster_response(raw2)
                minimal2 = _extract_roster_player_entries_minimal(raw2)
                if parsed2 or minimal2:
                    branch = 'fallback_after_empty'
                    raw = raw2
                    parsed = parsed2
                    minimal = minimal2

        # Attempt to read Yahoo's reported players count field if present
        players_count_value = None
        try:
            fantasy_content = raw.get('fantasy_content', {}) if isinstance(raw, dict) else {}
            team_data = fantasy_content.get('team', [])
            roster_container = _find_roster_container(team_data)
            players_data = _extract_players_collection(roster_container) if roster_container else {}
            if isinstance(players_data, dict) and 'count' in players_data:
                players_count_value = players_data.get('count')
        except Exception:
            pass

        # Build player slot samples for quick inspection
        slot_samples = []
        try:
            if isinstance(parsed, list) and parsed:
                for p in parsed[:5]:
                    slot_samples.append({
                        'name': p.get('name'),
                        'player_key': p.get('player_key'),
                        'selected_position': p.get('selected_position'),
                        'position': p.get('position'),
                        'eligible_positions': p.get('eligible_positions'),
                    })
        except Exception:
            pass

        result = {
            'branch': branch,
            'status': status,
            'url_used': url_primary if branch == 'primary' else url_fallback,
            'team_key': team_key,
            'parsed_count': len(parsed) if isinstance(parsed, list) else None,
            'minimal_count': len(minimal),
            'parsed_sample': parsed[:2] if isinstance(parsed, list) else [],
            'minimal_keys_sample': [p.get('player_key') for p in minimal[:5]],
            'yahoo_players_count_field': players_count_value,
            'raw_top_keys': list(raw.keys()) if isinstance(raw, dict) else None,
            'tried_secondary': tried_secondary,
            'slot_samples': slot_samples,
        }

        # If parsed empty but we have minimal entries, try batch details resolution and report count
        if (not parsed) and minimal:
            league_key = _derive_league_key_from_team_key(team_key)
            keys = [p['player_key'] for p in minimal]
            details_map = _fetch_yahoo_player_details_by_keys(access_token_string, league_key, keys)
            result['batch_details_resolved'] = len(details_map)

        return jsonify(result)
    except requests.exceptions.RequestException as req_e:
        print(f"Error fetching Yahoo roster (debug): {req_e}")
        if getattr(req_e, 'response', None) is not None:
            print(f"Yahoo roster error response content: {req_e.response.text}")
        traceback.print_exc()
        return jsonify({"error": "Failed to fetch roster from Yahoo.", "details": str(req_e)}), 500
    except Exception as e:
        print(f"Error processing Yahoo roster (debug): {e}")
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
        
        # Team data commonly is a list or dict; find the element that has 'roster'
        team_data = fantasy_content.get('team', [])
        print(f"DEBUG: team_data type: {type(team_data)}")
        print(f"DEBUG: team_data keys/length: {list(team_data.keys()) if isinstance(team_data, dict) else len(team_data) if isinstance(team_data, list) else 'Neither dict nor list'}")

        roster_container = _find_roster_container(team_data)
        if not roster_container:
            return []
        players_data = _extract_players_collection(roster_container)
        try:
            debug_pd_keys = list(players_data.keys()) if isinstance(players_data, dict) else 'N/A'
        except Exception:
            debug_pd_keys = 'N/A'
        print(f"DEBUG: players_data type: {type(players_data)}; keys: {debug_pd_keys}")
        
        # Parse players - handle dict or list shapes by deep-scan of each container
        players = []

        def handle_container(pc):
            if not isinstance(pc, dict):
                return
            # Deep-scan the entire player container so we capture sibling
            # fields like selected_position that may sit outside 'player'.
            agg = _extract_player_fields_from_any(pc)
            if agg and agg.get('player_key'):
                players.append(agg)

        if isinstance(players_data, dict):
            for key, player_container in players_data.items():
                if str(key).lower() == 'count':
                    continue
                handle_container(player_container)
        elif isinstance(players_data, list):
            for player_container in players_data:
                handle_container(player_container)
        
        # Enrich players with local data when names are present; otherwise pass through
        if players:
            named = [p for p in players if p.get('name')]
            unnamed = [p for p in players if not p.get('name')]
            if named:
                named = enrich_roster_players(named)
            players = named + unnamed

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

@app.route('/api/yahoo/waiver_wire')
def get_yahoo_waiver_wire():
    """
    Fetches free agents and waiver wire players from Yahoo API for league-aware waiver recommendations.
    Expects league_key as query parameter and token in Authorization header.
    Returns enhanced player data with ECR integration for AI analysis.
    """
    try:
        # Extract league_key parameter (required)
        league_key = request.args.get('league_key')
        if not league_key:
            return jsonify({"error": "league_key parameter is required"}), 400
            
        # Extract status parameter (optional, defaults to 'A' for all available)
        status = request.args.get('status', 'A')  # FA=free agents, W=waivers, A=all available
        
        # Extract Authorization header (required)
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Valid Authorization header with Bearer token is required"}), 401

        access_token = auth_header.split(' ')[1]
        
        # Pagination over Yahoo players collection
        base_url = "https://fantasysports.yahooapis.com/fantasy/v2"
        yahoo_headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        page_start = 0
        # Yahoo players collection typically pages in 25-item chunks regardless of requested count
        page_count = 25
        max_players_cap = 150
        aggregated_players = []

        while True:
            yahoo_url = f"{base_url}/league/{league_key}/players;status={status};start={page_start};count={page_count}"
            print(f"DEBUG: Requesting Yahoo waiver page start={page_start} count={page_count}")
            yahoo_response = requests.get(yahoo_url, headers=yahoo_headers, params={'format': 'json'}, timeout=10)

            if yahoo_response.status_code == 401:
                print("ERROR: Yahoo API authentication failed - token may be expired")
                return jsonify({"error": "Yahoo authentication failed. Please re-authenticate."}), 401
            elif yahoo_response.status_code == 403:
                print("ERROR: Yahoo API access forbidden - insufficient permissions")
                return jsonify({"error": "Insufficient permissions to access league data."}), 403
            elif yahoo_response.status_code == 404:
                print(f"ERROR: Yahoo API league not found: {league_key}")
                return jsonify({"error": "League not found or not accessible."}), 404
            elif yahoo_response.status_code != 200:
                print(f"ERROR: Yahoo API returned status {yahoo_response.status_code}: {yahoo_response.text}")
                return jsonify({"error": f"Yahoo API error: {yahoo_response.status_code}"}), 500

            try:
                page_json = yahoo_response.json()
            except ValueError as e:
                print(f"ERROR: Failed to parse Yahoo API JSON response: {e}")
                return jsonify({"error": "Invalid response format from Yahoo API"}), 500

            page_players = parse_yahoo_waiver_response(page_json)
            print(f"DEBUG: Parsed {len(page_players)} players from page start={page_start}")
            aggregated_players.extend(page_players)

            if len(page_players) < page_count or len(aggregated_players) >= max_players_cap:
                break
            page_start += page_count

        # Enrich aggregated players with local cache
        enriched_players = []
        for player in aggregated_players:
            name = player.get('name')
            if not name:
                continue
            normalized_name = normalize_player_name(name)
            player_context = combined_player_data_cache.get(normalized_name, {}) if combined_player_data_cache else {}
            enriched_player = {
                **player,
                'ecr': player_context.get('ecr_overall'),
                'ecr_rank': player_context.get('ecr_overall'),
                'sd': player_context.get('sd_overall'),
                'best_rank': player_context.get('best_overall'),
                'worst_rank': player_context.get('worst_overall'),
                'rank_delta': player_context.get('rank_delta_overall'),
                'bye_week': player_context.get('bye_week'),
                'is_rookie': player_context.get('is_rookie', False),
                'injury_status': player_context.get('injury_status'),
                'analysis_notes': player_context.get('notes', '')
            }
            enriched_players.append(enriched_player)

        print(f"DEBUG: Enriched {len(enriched_players)} players with local data (pre-sort)")

        # Sort by ECR (best first), None last
        enriched_players.sort(key=lambda x: (x['ecr'] is None, x['ecr'] if x['ecr'] is not None else 9999))

        # Limit output to top 100 for performance
        limited = enriched_players[:100]
        print(f"DEBUG: Returning {len(limited)} players after pagination + enrichment")

        return jsonify({
            'league_key': league_key,
            'available_players': limited,
            'total_count': len(enriched_players),
            'status_filter': status
        })
        
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Yahoo API request failed: {e}")
        return jsonify({"error": "Failed to connect to Yahoo API"}), 500
    except Exception as e:
        print(f"ERROR: Unexpected error in yahoo waiver wire: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/yahoo/waiver_debug')
def get_yahoo_waiver_debug():
    """
    Debug endpoint for Yahoo waiver wire requests.
    Echoes exact Yahoo URL (including status/start/count), HTTP status, parse count,
    elapsed time, and a small sample of parsed players.
    
    Query params:
      - league_key (required)
      - status (optional: A|FA|W, default A)
      - start (optional: default 0)
      - count (optional: default 50)
    """
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Valid Authorization header with Bearer token is required"}), 401

    league_key = request.args.get('league_key')
    if not league_key:
        return jsonify({"error": "league_key parameter is required"}), 400

    status = request.args.get('status', 'A')
    try:
        start = int(request.args.get('start', '0'))
    except ValueError:
        start = 0
    try:
        count = int(request.args.get('count', '50'))
    except ValueError:
        count = 50

    try:
        access_token = auth_header.split(' ')[1]
        if not access_token:
            return jsonify({"error": "Invalid token format: access_token missing."}), 401
    except Exception:
        return jsonify({"error": "Invalid token format in Authorization header."}), 401

    yahoo_headers = {
        'Authorization': f'Bearer {access_token}',
        'Accept': 'application/json'
    }

    # Build URL using Yahoo path selectors for pagination
    base = "https://fantasysports.yahooapis.com/fantasy/v2"
    yahoo_url = f"{base}/league/{league_key}/players;status={status};start={start};count={count}"

    try:
        import time as _t
        t0 = _t.time()
        resp = requests.get(yahoo_url, headers=yahoo_headers, params={'format': 'json'}, timeout=10)
        elapsed_ms = int((_t.time() - t0) * 1000)

        # Best‑effort parse
        parsed_count = None
        sample = []
        raw_keys = []
        structure = {}
        try:
            data = resp.json()
            raw_keys = list(data.keys()) if isinstance(data, dict) else []
            parsed = parse_yahoo_waiver_response(data)
            if isinstance(parsed, list):
                parsed_count = len(parsed)
                sample = parsed[:5]

            # Inspect nested structure for diagnostics
            fc = data.get('fantasy_content', {}) if isinstance(data, dict) else {}
            league = fc.get('league', []) if isinstance(fc, dict) else []
            players_container = None
            if isinstance(league, list) and len(league) >= 2 and isinstance(league[1], dict):
                players_container = league[1].get('players')
            structure = {
                'league_is_list': isinstance(league, list),
                'league_len': len(league) if isinstance(league, list) else None,
                'players_container_type': type(players_container).__name__ if players_container is not None else None,
                'players_container_keys_count': (len(players_container.keys()) if isinstance(players_container, dict) else None)
            }
        except Exception:
            pass

        print(f"DEBUG: WAIVER_DEBUG url={yahoo_url} status={resp.status_code} elapsed_ms={elapsed_ms} parsed_count={parsed_count}")

        return jsonify({
            'request': {
                'league_key': league_key,
                'status': status,
                'start': start,
                'count': count,
                'url': yahoo_url
            },
            'response': {
                'http_status': resp.status_code,
                'elapsed_ms': elapsed_ms,
                'raw_top_keys': raw_keys,
                'structure': structure
            },
            'parsed': {
                'count': parsed_count,
                'sample': sample
            }
        })

    except requests.exceptions.RequestException as e:
        print(f"ERROR: Yahoo WAIVER_DEBUG request failed: {e}")
        return jsonify({"error": "Failed to connect to Yahoo API"}), 500
    except Exception as e:
        print(f"ERROR: Unexpected error in WAIVER_DEBUG: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

def parse_yahoo_waiver_response(data):
    """
    Parse Yahoo API waiver wire response with defensive JSON parsing.
    Returns a clean array of available player objects or empty array on failure.
    Uses simplified approach based on existing Yahoo parsing patterns.
    """
    try:
        # Follow the same pattern as existing parse_yahoo_leagues_response
        fantasy_content = data.get('fantasy_content', {})
        league_data = fantasy_content.get('league', [])
        
        if not isinstance(league_data, list) or len(league_data) < 2:
            print("DEBUG: Unexpected league data structure for waiver wire")
            return []
        
        # Get players data from second element (follows existing pattern)
        players_container = league_data[1].get('players', {})
        available_players = []
        
        def _extract_from_player_container(player_container):
            player_info = player_container.get('player', []) if isinstance(player_container, dict) else []
            if not isinstance(player_info, list) or len(player_info) == 0:
                return None
            # Normalize into a flat list of dict elements to search across
            elements = []
            first = player_info[0]
            if isinstance(first, list):
                for e in first:
                    if isinstance(e, dict):
                        elements.append(e)
            elif isinstance(first, dict):
                elements.append(first)
            # Include remaining dict elements
            for e in player_info[1:]:
                if isinstance(e, dict):
                    elements.append(e)

            # Extract fields by scanning elements
            player_key = ''
            player_id = ''
            full_name = ''
            team_abbr = ''
            positions = []

            for e in elements:
                if not player_key and isinstance(e, dict) and 'player_key' in e:
                    player_key = e.get('player_key') or player_key
                if not player_id and isinstance(e, dict) and 'player_id' in e:
                    player_id = e.get('player_id') or player_id
                if not full_name and isinstance(e, dict) and 'name' in e:
                    nd = e.get('name')
                    if isinstance(nd, dict) and nd.get('full'):
                        full_name = nd.get('full')
                if not team_abbr and isinstance(e, dict) and 'editorial_team_abbr' in e:
                    team_abbr = e.get('editorial_team_abbr') or team_abbr
                if not positions and isinstance(e, dict) and 'eligible_positions' in e:
                    eps = e.get('eligible_positions', [])
                    if isinstance(eps, list):
                        for pos_data in eps:
                            if isinstance(pos_data, dict) and pos_data.get('position'):
                                positions.append(pos_data['position'])

            if not player_key or not full_name:
                return None

            return {
                'player_key': player_key,
                'player_id': player_id,
                'name': full_name,
                'team': team_abbr or '',
                'positions': positions,
                'primary_position': positions[0] if positions else 'Unknown'
            }

        if isinstance(players_container, dict):
            for key, player_container in players_container.items():
                if not str(key).isdigit():
                    continue
                extracted = _extract_from_player_container(player_container)
                if extracted:
                    available_players.append(extracted)
        elif isinstance(players_container, list):
            for entry in players_container:
                # entries might be dicts containing 'player'
                if isinstance(entry, dict):
                    extracted = _extract_from_player_container(entry)
                    if extracted:
                        available_players.append(extracted)
        
        print(f"DEBUG: Successfully parsed {len(available_players)} available players")
        return available_players
        
    except Exception as e:
        print(f"ERROR: Failed to parse Yahoo waiver wire response: {e}")
        traceback.print_exc()
        return []

def parse_yahoo_league_context(settings_data, players_data, teams_data):
    """
    Parse Yahoo API responses for comprehensive league context.
    Returns structured league data for market inefficiency analysis or None on failure.
    """
    try:
        league_context = {
            'league_settings': {},
            'player_ownership': [],
            'team_structure': {},
            'availability_stats': {}
        }
        
        # Parse league settings
        settings_content = settings_data.get('fantasy_content', {})
        league_data = settings_content.get('league', [])
        
        if isinstance(league_data, list) and len(league_data) >= 2:
            # Basic league info (first element)
            basic_info = league_data[0] if isinstance(league_data[0], dict) else {}
            league_context['league_settings'] = {
                'league_key': basic_info.get('league_key', ''),
                'name': basic_info.get('name', ''),
                'num_teams': basic_info.get('num_teams', 0),
                'scoring_type': basic_info.get('scoring_type', 'head'),
                'season': basic_info.get('season', '2025')
            }
            
            # Detailed settings (second element) - handle both dict and list cases
            settings_detail = {}
            if len(league_data) > 1:
                league_element = league_data[1]
                if isinstance(league_element, dict):
                    settings_detail = league_element.get('settings', {})
                elif isinstance(league_element, list) and len(league_element) > 0:
                    # Sometimes Yahoo returns settings as a list
                    settings_detail = league_element[0].get('settings', {}) if isinstance(league_element[0], dict) else {}
            
            roster_positions = settings_detail.get('roster_positions', {}) if isinstance(settings_detail, dict) else {}
            
            if isinstance(roster_positions, dict):
                positions_array = []
                for key, position_data in roster_positions.items():
                    if key.isdigit() and isinstance(position_data, dict):
                        pos_info = position_data.get('roster_position', {})
                        positions_array.append({
                            'position': pos_info.get('position', ''),
                            'position_type': pos_info.get('position_type', ''),
                            'count': pos_info.get('count', 0)
                        })
                
                league_context['league_settings']['roster_positions'] = positions_array
        
        # Parse player ownership data
        players_content = players_data.get('fantasy_content', {})
        players_league_data = players_content.get('league', [])
        
        if isinstance(players_league_data, list) and len(players_league_data) >= 2:
            # Handle both dict and list cases for players data
            players_element = players_league_data[1]
            players_container = {}
            if isinstance(players_element, dict):
                players_container = players_element.get('players', {})
            elif isinstance(players_element, list) and len(players_element) > 0:
                # Sometimes Yahoo returns players data as a list
                players_container = players_element[0].get('players', {}) if isinstance(players_element[0], dict) else {}
            ownership_data = []
            available_count = 0
            owned_count = 0
            
            if isinstance(players_container, dict):
                for key, player_container in players_container.items():
                    if not key.isdigit():
                        continue
                    
                    player_info = player_container.get('player', [])
                    if not isinstance(player_info, list) or len(player_info) == 0:
                        continue
                    
                    # Extract basic player data
                    player_data_list = player_info[0]
                    if not isinstance(player_data_list, list) or len(player_data_list) == 0:
                        continue
                    
                    player_basic = player_data_list[0]
                    name_data = player_basic.get('name', {})
                    full_name = name_data.get('full', '') if isinstance(name_data, dict) else str(name_data or '')
                    
                    if not full_name:
                        continue
                    
                    # Extract ownership information (check ownership structure in player data)
                    ownership_info = None
                    if len(player_info) > 1 and isinstance(player_info[1], dict):
                        ownership_info = player_info[1].get('ownership', {})
                    
                    ownership_status = 'available'  # Default
                    owner_team_key = None
                    
                    if ownership_info and isinstance(ownership_info, dict):
                        ownership_type = ownership_info.get('ownership_type', '')
                        if ownership_type == 'team':
                            ownership_status = 'owned'
                            owner_team_key = ownership_info.get('owner_team_key', '')
                            owned_count += 1
                        else:
                            available_count += 1
                    else:
                        available_count += 1
                    
                    # Extract positions
                    positions = []
                    for pos_data in player_basic.get('eligible_positions', []):
                        if isinstance(pos_data, dict) and pos_data.get('position'):
                            positions.append(pos_data['position'])
                    
                    ownership_data.append({
                        'player_key': player_basic.get('player_key', ''),
                        'player_id': player_basic.get('player_id', ''),
                        'name': full_name,
                        'team': player_basic.get('editorial_team_abbr', ''),
                        'positions': positions,
                        'primary_position': positions[0] if positions else 'Unknown',
                        'ownership_status': ownership_status,
                        'owner_team_key': owner_team_key
                    })
            
            league_context['player_ownership'] = ownership_data
            league_context['availability_stats'] = {
                'total_players': len(ownership_data),
                'available_players': available_count,
                'owned_players': owned_count,
                'ownership_percentage': (owned_count / len(ownership_data) * 100) if ownership_data else 0
            }
        
        # Parse team structure for competitive analysis
        teams_content = teams_data.get('fantasy_content', {})
        teams_league_data = teams_content.get('league', [])
        
        if isinstance(teams_league_data, list) and len(teams_league_data) >= 2:
            teams_container = teams_league_data[1].get('teams', {})
            team_info = []
            
            if isinstance(teams_container, dict):
                for key, team_container in teams_container.items():
                    if not key.isdigit():
                        continue
                    
                    team_data = team_container.get('team', [[]])[0]
                    if isinstance(team_data, list) and len(team_data) > 0:
                        team_basic = team_data[0] if isinstance(team_data[0], dict) else {}
                        team_info.append({
                            'team_key': team_basic.get('team_key', ''),
                            'team_name': team_basic.get('name', ''),
                            'manager_name': team_basic.get('managers', [{}])[0].get('manager', {}).get('nickname', '') if team_basic.get('managers') else ''
                        })
            
            league_context['team_structure'] = {
                'teams': team_info,
                'total_teams': len(team_info)
            }
        
        print(f"DEBUG: Successfully parsed league context with {len(league_context['player_ownership'])} players")
        return league_context
        
    except Exception as e:
        print(f"ERROR: Failed to parse Yahoo league context: {e}")
        traceback.print_exc()
        return None

@app.route('/api/yahoo/league_context')
def get_yahoo_league_context():
    """
    Fetches comprehensive league context for market inefficiency analysis.
    Expects league_key as query parameter and token in Authorization header.
    Returns league settings, player ownership, and roster structure for AI analysis.
    """
    try:
        # Extract league_key parameter (required)
        league_key = request.args.get('league_key')
        if not league_key:
            return jsonify({"error": "league_key parameter is required"}), 400
            
        # Extract Authorization header (required)
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Valid Authorization header with Bearer token is required"}), 401
            
        access_token = auth_header.split(' ')[1]
        
        # Build Yahoo API URLs for comprehensive league context
        league_settings_url = f"https://fantasysports.yahooapis.com/fantasy/v2/league/{league_key}/settings"
        league_players_url = f"https://fantasysports.yahooapis.com/fantasy/v2/league/{league_key}/players;status=ALL"
        league_teams_url = f"https://fantasysports.yahooapis.com/fantasy/v2/league/{league_key}/teams"
        
        yahoo_headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        yahoo_params = {'format': 'json'}
        
        print(f"DEBUG: Fetching league context for {league_key}")
        
        # Make parallel API requests for efficiency
        settings_response = requests.get(league_settings_url, headers=yahoo_headers, params=yahoo_params, timeout=10)
        players_response = requests.get(league_players_url, headers=yahoo_headers, params=yahoo_params, timeout=10)
        teams_response = requests.get(league_teams_url, headers=yahoo_headers, params=yahoo_params, timeout=10)
        
        # Handle HTTP errors with specific messaging
        responses = [
            (settings_response, "league settings"),
            (players_response, "player data"),
            (teams_response, "team data")
        ]
        
        for response, data_type in responses:
            if response.status_code == 401:
                print(f"ERROR: Yahoo API authentication failed for {data_type}")
                return jsonify({"error": "Yahoo authentication failed. Please re-authenticate."}), 401
            elif response.status_code == 403:
                print(f"ERROR: Yahoo API access forbidden for {data_type}")
                return jsonify({"error": f"Insufficient permissions to access {data_type}."}), 403
            elif response.status_code == 404:
                print(f"ERROR: Yahoo API not found for {data_type}: {league_key}")
                return jsonify({"error": f"League not found or {data_type} not accessible."}), 404
            elif response.status_code != 200:
                print(f"ERROR: Yahoo API returned status {response.status_code} for {data_type}: {response.text}")
                return jsonify({"error": f"Yahoo API error fetching {data_type}: {response.status_code}"}), 500
        
        # Parse JSON responses with defensive error handling
        try:
            settings_data = settings_response.json()
            players_data = players_response.json()
            teams_data = teams_response.json()
            print(f"DEBUG: Received Yahoo responses with keys: settings={settings_data.keys()}, players={players_data.keys()}, teams={teams_data.keys()}")
        except ValueError as e:
            print(f"ERROR: Failed to parse Yahoo API JSON responses: {e}")
            return jsonify({"error": "Invalid response format from Yahoo API"}), 500
        
        # Parse using defensive pattern matching existing Yahoo endpoints
        league_context = parse_yahoo_league_context(settings_data, players_data, teams_data)
        if league_context is None:
            print("ERROR: Failed to parse Yahoo league context response structure")
            return jsonify({"error": "Unable to parse league context data"}), 500
            
        return jsonify(league_context)
        
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Yahoo API request failed: {e}")
        return jsonify({"error": "Failed to connect to Yahoo API"}), 500
    except Exception as e:
        print(f"ERROR: Unexpected error in yahoo league context: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/diagnostics/yahoo-data-health')
def yahoo_data_health():
    """
    Diagnostics for Yahoo + CSV integration.
    Inputs: league_key (required), team_key (optional), Authorization Bearer token required.
    Returns: roster/waiver counts, enrichment match rates, CSV modified times, and quick notes.
    """
    try:
        league_key = request.args.get('league_key')
        team_key = request.args.get('team_key')
        if not league_key:
            return jsonify({"error": "league_key parameter is required"}), 400
        
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Valid Authorization header with Bearer token is required"}), 401
        access_token = auth_header.split(' ')[1]

        yahoo_headers = {
            'Authorization': f'Bearer {access_token}',
            'Accept': 'application/json'
        }
        params_json = {'format': 'json'}

        # 1) Roster metrics (if team_key provided)
        roster_count = None
        roster_match = None
        if team_key:
            try:
                url_primary = f'https://fantasysports.yahooapis.com/fantasy/v2/team/{team_key}/roster/players?format=json'
                resp = requests.get(url_primary, headers=yahoo_headers, timeout=10)
                if resp.status_code == 404:
                    url_fallback = f'https://fantasysports.yahooapis.com/fantasy/v2/team/{team_key}/roster?format=json'
                    resp = requests.get(url_fallback, headers=yahoo_headers, timeout=10)
                resp.raise_for_status()
                raw = resp.json()
                roster_players = parse_yahoo_roster_response(raw)
                roster_players = roster_players or []
                roster_count = len(roster_players)
                m = 0
                for p in roster_players:
                    name = p.get('name')
                    if not name:
                        continue
                    if combined_player_data_cache.get(normalize_player_name(name)):
                        m += 1
                roster_match = {
                    'matched': m,
                    'total': roster_count,
                    'match_rate': round((m/roster_count)*100, 1) if roster_count else 0.0
                }
            except Exception as e:
                print(f"ERROR: diagnostics roster fetch failed: {e}")
                roster_count = -1
                roster_match = {'matched': 0, 'total': 0, 'match_rate': 0.0}

        # 2) Waiver metrics (A status, first two pages)
        try:
            base = 'https://fantasysports.yahooapis.com/fantasy/v2'
            total_available = 0
            matched = 0
            for start in (0, 50):
                url = f"{base}/league/{league_key}/players;status=A;start={start};count=50"
                r = requests.get(url, headers=yahoo_headers, params=params_json, timeout=10)
                r.raise_for_status()
                data = r.json()
                players = parse_yahoo_waiver_response(data) or []
                total_available += len(players)
                for p in players:
                    nm = p.get('name')
                    if nm and combined_player_data_cache.get(normalize_player_name(nm)):
                        matched += 1
            waiver_match = {
                'matched': matched,
                'total': total_available,
                'match_rate': round((matched/total_available)*100, 1) if total_available else 0.0
            }
        except Exception as e:
            print(f"ERROR: diagnostics waiver fetch failed: {e}")
            waiver_match = {'matched': 0, 'total': 0, 'match_rate': 0.0}

        # 3) CSV freshness
        csv_files = [
            ('db_fpecr_latest.csv', os.path.join(basedir, 'db_fpecr_latest.csv')),
            ('values-players.csv', os.path.join(basedir, 'values-players.csv')),
            ('values-picks.csv', os.path.join(basedir, 'values-picks.csv')),
            ('fp_latest_weekly.csv', os.path.join(basedir, 'fp_latest_weekly.csv')),
        ]
        csv_times = {}
        for name, path in csv_files:
            try:
                mtime = os.path.getmtime(path)
                csv_times[name] = {
                    'path': path,
                    'modified': datetime.fromtimestamp(mtime).isoformat()
                }
            except Exception:
                csv_times[name] = {'path': path, 'modified': None}

        # Weekly CSV checks (row count, latest scrape_date, anchor presence)
        weekly_path = os.path.join(basedir, 'fp_latest_weekly.csv')
        weekly_rows = None
        latest_scrape_date = None
        try:
            if os.path.exists(weekly_path):
                with open(weekly_path, 'r') as fh:
                    weekly_rows = sum(1 for _ in fh) - 1  # minus header
            # derive latest scrape_date from cache
            if isinstance(weekly_projections_cache, dict) and weekly_projections_cache:
                dates = [v.get('projection_date') for v in weekly_projections_cache.values() if v.get('projection_date')]
                if dates:
                    latest_scrape_date = max(str(d) for d in dates)
        except Exception:
            pass

        anchors = ['Jalen Hurts','Christian McCaffrey','Ja\'Marr Chase','Travis Kelce','Josh Allen']
        def _norm(n):
            return normalize_player_name(n)
        anchor_presence = {}
        try:
            wk_keys = set(weekly_projections_cache.keys()) if isinstance(weekly_projections_cache, dict) else set()
            for a in anchors:
                anchor_presence[a] = (_norm(a) in wk_keys)
        except Exception:
            anchor_presence = {a: None for a in anchors}

        return jsonify({
            'league_key': league_key,
            'team_key': team_key,
            'roster': {
                'count': roster_count,
                'enrichment': roster_match
            },
            'waivers_A_first2pages': {
                'enrichment': waiver_match
            },
            'csv_freshness': csv_times,
            'weekly_checks': {
                'row_count': weekly_rows,
                'latest_scrape_date': latest_scrape_date,
                'anchor_presence': anchor_presence
            }
        })
    
    except Exception as e:
        print(f"ERROR: data health diagnostics failed: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/api/yahoo_waiver_analysis', methods=['POST'])
def yahoo_waiver_analysis():
    """
    Enhanced waiver wire analysis using actual Yahoo league data.
    Provides personalized recommendations based on user's roster and league's available players.
    """
    try:
        user_key = request.headers.get('X-API-Key')
        data = request.json
        
        league_key = data.get('league_key')
        roster = data.get('roster', [])  # List of player objects from Yahoo roster API
        available_players = data.get('available_players', [])  # List from waiver wire API
        
        if not league_key or not available_players:
            return jsonify({"error": "league_key and available_players are required"}), 400
        
        # Build context for current roster
        roster_context = "**CURRENT ROSTER:**\n"
        if roster:
            for player in roster:
                player_name = player.get('name', '')
                position = player.get('selected_position', 'FLEX')
                if player_name:
                    # Get local player context for roster player
                    player_context = get_player_context(
                        player_name,
                        ecr_type_preference='overall',
                        combined_player_data_cache=combined_player_data_cache,
                        player_name_to_id=player_name_to_id,
                        player_data_cache=player_data_cache,
                        static_ecr_overall_data=static_ecr_overall_data,
                        static_ecr_positional_data=static_ecr_positional_data,
                        static_ecr_rookie_data=static_ecr_rookie_data
                    )
                    
                    ecr_info = f"ECR: {player_context.get('ecr', 'N/A')}" if player_context.get('ecr') else "ECR: N/A"
                    bye_info = f"Bye: {player_context.get('bye_week', 'N/A')}" if player_context.get('bye_week') else ""
                    roster_context += f"- **{position}**: {player_name} ({ecr_info}, {bye_info})\n"
        else:
            roster_context += "No roster players provided\n"
        
        # Build context for available players (top 25 by ECR)
        available_context = "\n**TOP AVAILABLE PLAYERS:**\n"
        sorted_available = sorted(available_players, key=lambda x: x.get('ecr') or 999)[:25]
        
        for player in sorted_available:
            name = player.get('name', 'Unknown')
            position = player.get('primary_position', 'Unknown')
            team = player.get('team', 'Unknown')
            ecr = player.get('ecr') or 'N/A'
            bye_week = player.get('bye_week') or 'N/A'
            available_context += f"- **{name}** ({position}, {team}): ECR {ecr}, Bye Week {bye_week}\n"
        
        # Get waiver wire examples
        waiver_examples = ExampleLibrary.get_examples_for_analysis_type('waiver_wire_analysis')
        
        # Build comprehensive analysis prompt
        full_context = f"LEAGUE KEY: {league_key}\n\n{roster_context}\n{available_context}"
        
        # REVOLUTIONARY 7-Step Multi-Factor Decision Framework 
        methodology_steps = [
            "1. ROSTER COMPOSITION ANALYSIS",
            "   • Current strengths/weaknesses by position and tier",
            "   • Bye week vulnerabilities and streaming needs",
            "   • Injury risk assessment and handcuff requirements",
            "   • Positional depth charts and scarcity considerations",
            "",
            "2. WEEKLY PROJECTION EVALUATION", 
            "   • Analyze projected fantasy points vs. positional thresholds",
            "   • Evaluate expert start/sit grades and confidence levels",
            "   • Identify projection tiers (QB1/QB2, RB1/RB2, etc.)",
            "   • Cross-reference with ECR for validation and discrepancies",
            "",
            "3. MATCHUP DIFFICULTY ANALYSIS",
            "   • Assess opponent defensive strength vs. player position",
            "   • Consider home/away advantages and travel factors", 
            "   • Evaluate historical performance in similar matchups",
            "   • Factor in game script and pace-of-play implications",
            "",
            "4. OWNERSHIP ARBITRAGE ASSESSMENT",
            "   • Identify low-ownership players with high projections",
            "   • Calculate value opportunity scores for market inefficiencies",
            "   • Highlight players owned by <25% with 15+ point projections",
            "   • Assess risk/reward ratio for contrarian plays",
            "",
            "5. PLAYER AGE AND DEVELOPMENT ANALYSIS",
            "   • Evaluate age-adjusted expectations by position",
            "   • Consider career trajectory and peak performance windows",
            "   • Assess rookie development curves and breakout potential",
            "   • Factor in injury history and durability concerns",
            "",
            "6. COMPREHENSIVE OUTLOOK INTEGRATION",
            "   • Synthesize all factors into unified player evaluations",
            "   • Generate confidence-weighted recommendations",
            "   • Identify both immediate and long-term value opportunities",
            "   • Balance upside potential with floor considerations",
            "",
            "7. STRATEGIC DECISION FRAMEWORK",
            "   • Prioritize top 5-7 targets with specific reasoning",
            "   • Recommend drop candidates based on opportunity cost",
            "   • Provide FAAB bidding guidance and priority levels",
            "   • Suggest claim timing (immediate vs. speculative holds)"
        ]
        
        # Build enhanced prompt using existing infrastructure
        enhanced_prompt = PromptBuilder.build_enhanced_prompt(
            task_description="Yahoo League Waiver Wire Analysis - Provide personalized waiver wire recommendations based on actual league data",
            player_data=full_context,
            methodology_steps=methodology_steps,
            examples=waiver_examples
        )
        
        # Make AI request and process response
        response_text = make_gemini_request(enhanced_prompt, user_key)
        return jsonify({'result': process_ai_response_v2(response_text, 'yahoo_waiver')})
        
    except Exception as e:
        print(f"ERROR: Yahoo waiver analysis failed: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

# ---------------- Waiver Wire v2 Helpers ----------------
def _normalize_pos(p):
    return (p or '').upper()

def _is_excluded_position(position: str, exclude_set: set) -> bool:
    p = _normalize_pos(position)
    return p in exclude_set

def _get_combined_info_by_name(name: str) -> dict:
    try:
        if not name:
            return {}
        key = normalize_player_name(name)
        # apply alias if available
        alias = name_aliases.get(key)
        lookup_key = alias if alias else key
        return combined_player_data_cache.get(lookup_key, {}) if combined_player_data_cache else {}
    except Exception:
        return {}

def _player_weekly_score(name: str, fallback_ecr: Optional[float]) -> float:
    ci = _get_combined_info_by_name(name)
    wp = ci.get('projected_points')
    if isinstance(wp, (int, float)):
        return float(wp)
    try:
        if wp is not None:
            return float(wp)
    except (ValueError, TypeError):
        pass
    # Fallback: estimate from ECR by position (prefer combined cache ECR, else provided fallback_ecr)
    pos = (ci.get('position') or '').upper()
    ecr = ci.get('ecr_overall') if ci else None
    if isinstance(ecr, (int, float)):
        return _estimate_points_from_ecr(pos, ecr)
    if isinstance(fallback_ecr, (int, float)):
        return _estimate_points_from_ecr(pos, fallback_ecr)
    return 0.0

def _estimate_points_from_ecr(position: str, ecr: Optional[float]) -> float:
    """Conservative weekly estimate from season-long ECR.
    Curves are intentionally modest to avoid inflated deltas.
    """
    if not ecr or not isinstance(ecr, (int, float)):
        return 0.0
    try:
        e = float(ecr)
    except (ValueError, TypeError):
        return 0.0
    pos = (position or '').upper()
    # Simple piecewise-linear approximations
    if pos == 'QB':
        # ~20 at ECR 1; ~10 by ECR 30; floor at ~6
        if e <= 1:
            return 20.0
        if e >= 30:
            return 10.0
        return 20.0 - (e - 1) * (10.0 / 29.0)
    if pos in ('RB', 'WR'):
        # ~15 at ECR 1; ~6 by ECR 50
        if e <= 1:
            return 15.0
        if e >= 50:
            return 6.0
        return 15.0 - (e - 1) * (9.0 / 49.0)
    if pos == 'TE':
        # ~10 at ECR 1; ~4 by ECR 30
        if e <= 1:
            return 10.0
        if e >= 30:
            return 4.0
        return 10.0 - (e - 1) * (6.0 / 29.0)
    # Default to RB/WR-like conservative curve if position unknown
    if e <= 1:
        return 15.0
    if e >= 50:
        return 6.0
    return 15.0 - (e - 1) * (9.0 / 49.0)

def _build_required_slots_from_roster(roster_players: list[str]) -> list[str]:
    slots = []
    for p in roster_players:
        slot = _normalize_pos(p.get('selected_position'))
        if not slot or slot.startswith('BN') or slot.startswith('IR'):
            continue
        if slot in ('K', 'DEF', 'DST'):
            continue
        slots.append(slot)
    return slots

def _can_fill_slot(slot: str, player_position: str) -> bool:
    # Use existing helper when possible
    try:
        return is_valid_player_for_position({'position': player_position}, slot)
    except Exception:
        slot_u = _normalize_pos(slot)
        pos = _normalize_pos(player_position)
        if slot_u == 'W/T':
            return pos in ('WR', 'TE')
        if slot_u in ('W/R/T', 'FLEX'):
            return pos in ('WR', 'RB', 'TE')
        return slot_u == pos

def _best_lineup(players: list, slots: list[str]) -> tuple[list, float]:
    """Greedy lineup: fill each slot with highest score eligible player, once each."""
    used = set()
    lineup = []
    total = 0.0
    for slot in slots:
        best_idx = -1
        best_score = -1.0
        for i, pl in enumerate(players):
            if i in used:
                continue
            name = pl.get('name')
            position = pl.get('position') or pl.get('primary_position')
            if not name or not position:
                continue
            if not _can_fill_slot(slot, position):
                continue
            # compute score
            score = _player_weekly_score(name, pl.get('ecr_overall') or pl.get('ecr'))
            if score > best_score:
                best_score = score
                best_idx = i
        if best_idx >= 0:
            used.add(best_idx)
            lineup.append({
                'slot': slot,
                'player': players[best_idx]
            })
            total += best_score if best_score > 0 else 0.0
        else:
            lineup.append({'slot': slot, 'player': None})
    return lineup, total

# ---- Whole-roster scoring helpers ----
def _replacement_baseline(position: str) -> float:
    pos = (position or '').upper()
    if pos == 'QB':
        return 10.0
    if pos in ('RB', 'WR'):
        return 7.5
    if pos == 'TE':
        return 5.0
    return 6.0

def _effective_points_for_player(p: dict) -> float:
    name = p.get('name')
    ecr = p.get('ecr_overall') or p.get('ecr')
    return _player_weekly_score(name, ecr)

def _compute_bench_vor(enriched_roster: list, lineup: list) -> float:
    """Compute bench value-over-replacement across positions using effective points (weekly or ECR fallback)."""
    try:
        starter_names = set()
        for slot_entry in lineup:
            pl = slot_entry.get('player')
            if pl and pl.get('name'):
                starter_names.add(pl.get('name'))
        bench_players = [p for p in enriched_roster if p.get('name') not in starter_names and not _is_excluded_position(p.get('position'), {'K','DEF','DST'})]
        vor_total = 0.0
        for bp in bench_players:
            pos = bp.get('position') or bp.get('primary_position')
            eff = _effective_points_for_player(bp)
            rep = _replacement_baseline(pos)
            alpha_gain = max(0.0, eff - rep)
            vor_total += alpha_gain
        return round(vor_total, 2)
    except Exception:
        return 0.0

def _bench_players(enriched_roster: list, lineup: list) -> list:
    starter_names = set()
    for slot_entry in lineup:
        pl = slot_entry.get('player')
        if pl and pl.get('name'):
            starter_names.add(pl.get('name'))
    return [p for p in enriched_roster if p.get('name') not in starter_names and not _is_excluded_position(p.get('position'), {'K','DEF','DST'})]

def _compute_bench_counts(enriched_roster: list, lineup: list) -> dict:
    counts = {'QB': 0, 'RB': 0, 'WR': 0, 'TE': 0}
    for bp in _bench_players(enriched_roster, lineup):
        pos = (bp.get('position') or bp.get('primary_position') or '').upper()
        if pos in counts:
            counts[pos] += 1
    return counts

def _compute_balance_score(counts: dict) -> float:
    """Small penalty for imbalanced bench; conservative magnitudes.
    Targets: QB<=1, RB>=2, WR>=2, TE>=1
    """
    score = 0.0
    # QB surplus penalty
    qb_extra = max(0, counts.get('QB', 0) - 1)
    score -= 1.0 * qb_extra
    # RB/WR shortage penalty
    for pos, target, penalty in (('RB', 2, 0.5), ('WR', 2, 0.5), ('TE', 1, 0.3)):
        short = max(0, target - counts.get(pos, 0))
        score -= penalty * short
    return round(score, 2)

def _compute_bye_score(enriched_roster: list, lineup: list) -> float:
    """Small bonus if bench covers starter byes at each position (simple heuristic)."""
    try:
        starter_byes = {'QB': set(), 'RB': set(), 'WR': set(), 'TE': set()}
        for slot_entry in lineup:
            pl = slot_entry.get('player') or {}
            pos = (pl.get('position') or pl.get('primary_position') or '').upper()
            if pos in starter_byes:
                bye_w = pl.get('bye_week')
                if bye_w:
                    starter_byes[pos].add(bye_w)
        bonus = 0.0
        for bp in _bench_players(enriched_roster, lineup):
            pos = (bp.get('position') or bp.get('primary_position') or '').upper()
            if pos in starter_byes:
                bye_w = bp.get('bye_week')
                if bye_w and bye_w not in starter_byes[pos]:
                    bonus += 0.2  # tiny per-cover bonus
        return round(min(bonus, 2.0), 2)  # cap
    except Exception:
        return 0.0

def _starter_positions_and_byes(lineup: list) -> tuple[set, dict]:
    positions = set()
    pos_byes = {}
    try:
        for slot_entry in lineup:
            pl = slot_entry.get('player') or {}
            pos = (pl.get('position') or pl.get('primary_position') or '').upper()
            if not pos:
                continue
            positions.add(pos)
            bye_w = pl.get('bye_week')
            if bye_w:
                pos_byes.setdefault(pos, set()).add(bye_w)
    except Exception:
        pass
    return positions, pos_byes

def _compute_badges(add_player: dict, drop_player: dict, enriched_roster: list, baseline_lineup: list) -> list:
    badges = []
    try:
        add_pos = (add_player.get('position') or add_player.get('primary_position') or '').upper()
        drop_pos = (drop_player.get('position') or drop_player.get('primary_position') or '').upper()
        baseline_counts = _compute_bench_counts(enriched_roster, baseline_lineup)
        # Count after swap (approximate)
        counts_after = dict(baseline_counts)
        if drop_pos in counts_after:
            counts_after[drop_pos] = max(0, counts_after.get(drop_pos, 0) - 1)
        if add_pos in counts_after:
            counts_after[add_pos] = counts_after.get(add_pos, 0) + 1

        # Depth badge: if the add position count increases or was below target
        targets = {'RB': 2, 'WR': 2, 'TE': 1}
        if add_pos in targets:
            before = baseline_counts.get(add_pos, 0)
            after = counts_after.get(add_pos, 0)
            if after > before or before < targets[add_pos]:
                badges.append('Depth')

        # Bye Coverage: if starters at add_pos have byes and add's bye is different
        starter_pos, starter_byes = _starter_positions_and_byes(baseline_lineup)
        add_bye = add_player.get('bye_week')
        if add_pos in starter_byes and add_bye and add_bye not in starter_byes.get(add_pos, set()):
            badges.append('Bye Coverage')

        # Insurance: if any starter shares same team+position
        add_team = (add_player.get('team') or '').upper()
        insurance_flag = False
        for slot_entry in baseline_lineup:
            pl = slot_entry.get('player') or {}
            ppos = (pl.get('position') or pl.get('primary_position') or '').upper()
            pteam = (pl.get('team') or '').upper()
            if ppos == add_pos and pteam and add_team and pteam == add_team:
                insurance_flag = True
                break
        if insurance_flag and add_pos in ('RB','WR','TE'):
            badges.append('Insurance')

        # Upside: rookie or improving ECR (negative rank_delta)
        if add_player.get('is_rookie'):
            badges.append('Upside')
        rd = add_player.get('rank_delta_overall') or add_player.get('rank_delta')
        if isinstance(rd, (int, float)) and rd < 0:
            if 'Upside' not in badges:
                badges.append('Upside')

        # Risk: injury/suspension or high uncertainty
        status = (add_player.get('status') or '').upper()
        sd = add_player.get('sd_overall') or add_player.get('sd')
        if status in ('IR','SUSP','OUT') or (isinstance(sd, (int, float)) and sd > 20):
            badges.append('Risk')

    except Exception:
        pass
    return badges

def _collect_enriched_pool(access_token: str, league_key: str, status: str, exclude_set: set, cap: int = 200) -> list:
    base_url = "https://fantasysports.yahooapis.com/fantasy/v2"
    headers = {'Authorization': f'Bearer {access_token}', 'Accept': 'application/json'}
    players = []
    start = 0
    step = 25
    while len(players) < cap:
        url = f"{base_url}/league/{league_key}/players;status={status};start={start};count={step}"
        resp = requests.get(url, headers=headers, params={'format': 'json'}, timeout=10)
        if resp.status_code != 200:
            break
        data = resp.json()
        page_players = parse_yahoo_waiver_response(data)
        if not page_players:
            break
        for p in page_players:
            pos_list = p.get('positions') or []
            primary = (pos_list[0] if pos_list else p.get('primary_position'))
            if _is_excluded_position(primary, exclude_set):
                continue
            name = p.get('name')
            ci = _get_combined_info_by_name(name)
            if (not ci) and p.get('player_id'):
                # Try Yahoo ID join
                joined_key = yahoo_id_to_key.get(str(p.get('player_id')))
                if joined_key and combined_player_data_cache:
                    ci = combined_player_data_cache.get(joined_key, {})
            enriched = {
                **p,
                'position': ci.get('position', primary),
                'ecr_overall': ci.get('ecr_overall') or ci.get('ecr'),
                'sd_overall': ci.get('sd_overall') or ci.get('sd'),
                'best_overall': ci.get('best_overall') or ci.get('best'),
                'worst_overall': ci.get('worst_overall') or ci.get('worst'),
                'rank_delta_overall': ci.get('rank_delta_overall') or ci.get('rank_delta'),
                'bye_week': ci.get('bye_week'),
                'weekly_points': ci.get('projected_points'),
                'weekly_ecr': ci.get('weekly_ecr'),
                'weekly_ownership': ci.get('weekly_ownership'),
            }
            players.append(enriched)
            if len(players) >= cap:
                break
        if len(page_players) < step:
            break
        start += step
    # Sort by effective weekly score (weekly_points or estimated) then ECR
    def _eff_score(c):
        wp = c.get('weekly_points')
        if isinstance(wp, (int, float)):
            return float(wp)
        return _estimate_points_from_ecr((c.get('position') or c.get('primary_position') or ''), c.get('ecr_overall'))

    players.sort(key=lambda x: (-_eff_score(x), x['ecr_overall'] if x.get('ecr_overall') is not None else 9999))
    return players

@app.route('/api/yahoo/waiver_pool')
def yahoo_waiver_pool():
    try:
        league_key = request.args.get('league_key')
        if not league_key:
            return jsonify({'error': 'league_key parameter is required'}), 400
        status = request.args.get('status', 'A')
        max_count = int(request.args.get('max', '200'))
        exclude = request.args.get('exclude_positions', 'K,DEF')
        exclude_set = {s.strip().upper() for s in exclude.split(',') if s.strip()}

        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Valid Authorization header with Bearer token is required'}), 401
        access_token = auth_header.split(' ')[1]

        pool = _collect_enriched_pool(access_token, league_key, status, exclude_set, max_count)
        return jsonify({
            'league_key': league_key,
            'status_filter': status,
            'total_count': len(pool),
            'available_players': pool
        })
    except Exception as e:
        print(f"ERROR: yahoo_waiver_pool failed: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/yahoo/waiver_recommendations_v2', methods=['POST'])
def yahoo_waiver_recommendations_v2():
    try:
        payload = request.get_json(force=True, silent=True) or {}
        league_key = payload.get('league_key')
        team_key = payload.get('team_key')
        week = payload.get('week')
        status = payload.get('status', 'A')
        top_n = int(payload.get('top_n', 10))
        exclude = payload.get('exclude_positions', ['K', 'DEF'])
        exclude_set = {str(s).upper() for s in exclude}
        if not league_key or not team_key:
            return jsonify({'error': 'league_key and team_key are required'}), 400

        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Valid Authorization header with Bearer token is required'}), 401
        access_token = auth_header.split(' ')[1]

        # Fetch roster from Yahoo (reuse roster endpoint logic)
        headers = {'Authorization': f'Bearer {access_token}', 'Accept': 'application/json'}
        if week:
            url_primary = f'https://fantasysports.yahooapis.com/fantasy/v2/team/{team_key}/roster/players;week={week}?format=json'
            url_fallback = f'https://fantasysports.yahooapis.com/fantasy/v2/team/{team_key}/roster;week={week}?format=json'
        else:
            url_primary = f'https://fantasysports.yahooapis.com/fantasy/v2/team/{team_key}/roster/players?format=json'
            url_fallback = f'https://fantasysports.yahooapis.com/fantasy/v2/team/{team_key}/roster?format=json'
        r = requests.get(url_primary, headers=headers, timeout=10)
        if r.status_code == 404:
            r = requests.get(url_fallback, headers=headers, timeout=10)
        r.raise_for_status()
        roster_raw = r.json()
        roster_players = parse_yahoo_roster_response(roster_raw) or []
        # Enrich roster players minimally
        enriched_roster = []
        for p in roster_players:
            name = p.get('name')
            if not name:
                continue
            ci = _get_combined_info_by_name(name)
            if (not ci) and p.get('player_id'):
                joined_key = yahoo_id_to_key.get(str(p.get('player_id')))
                if joined_key and combined_player_data_cache:
                    ci = combined_player_data_cache.get(joined_key, {})
            pos = ci.get('position') or p.get('selected_position')
            if _is_excluded_position(pos, exclude_set):
                continue
            enriched_roster.append({
                **p,
                'position': pos,
                'weekly_points': ci.get('projected_points'),
                'ecr_overall': ci.get('ecr_overall'),
                'bye_week': ci.get('bye_week')
            })

        # Build required slots from roster
        required_slots = _build_required_slots_from_roster(enriched_roster)

        # Collect candidate pool
        pool = _collect_enriched_pool(access_token, league_key, status, exclude_set, cap=300)
        # Bias candidate selection by position to avoid QB crowding the pool
        def _eff_score_local(c):
            wp = c.get('weekly_points')
            if isinstance(wp, (int, float)):
                return float(wp)
            return _estimate_points_from_ecr((c.get('position') or c.get('primary_position') or ''), c.get('ecr_overall'))
        buckets = {'QB': [], 'RB': [], 'WR': [], 'TE': []}
        for c in pool:
            pos = (c.get('position') or c.get('primary_position') or '').upper()
            if pos in buckets:
                buckets[pos].append(c)
        for pos in buckets:
            buckets[pos].sort(key=lambda x: -_eff_score_local(x))
        # Quotas to reach ~120
        quotas = {'QB': 10, 'RB': 40, 'WR': 50, 'TE': 20}
        candidates = []
        for pos, limit in quotas.items():
            candidates.extend(buckets.get(pos, [])[:limit])
        # If short of 120, fill with best remaining from pool not yet selected
        if len(candidates) < 120:
            selected_ids = set(id(x) for x in candidates)
            remainder = [c for c in pool if id(c) not in selected_ids]
            remainder.sort(key=lambda x: -_eff_score_local(x))
            candidates.extend(remainder[:(120 - len(candidates))])
        # Coverage metrics
        roster_proj_total = len(enriched_roster)
        roster_proj_have = sum(1 for rp in enriched_roster if isinstance(rp.get('weekly_points'), (int, float)))
        pool_proj_total = len(candidates)
        pool_proj_have = sum(1 for c in candidates if isinstance(c.get('weekly_points'), (int, float)))

        # Baseline lineup and whole-roster score
        baseline_lineup, baseline_points = _best_lineup(enriched_roster, required_slots)
        baseline_bench_vor = _compute_bench_vor(enriched_roster, baseline_lineup)
        baseline_counts = _compute_bench_counts(enriched_roster, baseline_lineup)
        baseline_balance = _compute_balance_score(baseline_counts)
        baseline_bye = _compute_bye_score(enriched_roster, baseline_lineup)
        # Conservative weights
        alpha = 0.7  # bench VOR weight
        beta = 0.3   # balance weight (small)
        gamma = 0.3  # bye coverage weight (small)
        baseline_overall = round(baseline_points + alpha * baseline_bench_vor + beta * baseline_balance + gamma * baseline_bye, 2)

        # Prepare drop candidates list (prefer bench; then weakest eligible starter by position)
        bench = [rp for rp in enriched_roster if str(rp.get('selected_position','')).upper().startswith('BN')]
        starters = [rp for rp in enriched_roster if rp not in bench and not str(rp.get('selected_position','')).upper().startswith('IR')]

        recs = []
        for c in candidates:
            cpos = c.get('position') or c.get('primary_position')
            if not cpos:
                continue
            # potential drops: bench first, then starters of same position group
            potential_drops = []
            for rp in bench:
                potential_drops.append(rp)
            for rp in starters:
                if _normalize_pos(rp.get('position') or rp.get('selected_position')) == _normalize_pos(cpos):
                    potential_drops.append(rp)
            # limit evaluation
            potential_drops = potential_drops[:5]
            best_delta = 0.0
            best_after = None
            best_drop = None
            for dp in potential_drops:
                new_roster = [rp for rp in enriched_roster if rp is not dp] + [
                    {
                        'name': c.get('name'),
                        'position': cpos,
                        'selected_position': dp.get('selected_position'),
                        'weekly_points': c.get('weekly_points'),
                        'ecr_overall': c.get('ecr_overall'),
                        'bye_week': c.get('bye_week'),
                    }
                ]
                lineup_after, points_after = _best_lineup(new_roster, required_slots)
                bench_vor_after = _compute_bench_vor(new_roster, lineup_after)
                counts_after = _compute_bench_counts(new_roster, lineup_after)
                balance_after = _compute_balance_score(counts_after)
                bye_after = _compute_bye_score(new_roster, lineup_after)

                # Cross-position penalty unless move improves balance
                dp_pos = (dp.get('position') or dp.get('selected_position') or '').upper()
                cross_penalty = 0.0
                if (cpos or '').upper() != dp_pos:
                    # If after balance improves over baseline, waive penalty; else apply small penalty
                    if balance_after <= baseline_balance:
                        cross_penalty = 1.5

                # Bench composition penalties/guards
                # 1) Surplus QB penalty (prefer max 1 QB on bench in 1QB leagues)
                qb_after = counts_after.get('QB', 0)
                qb_surplus_pen = max(0, qb_after - 1) * 2.5
                # 2) RB/WR shortage penalty: avoid dropping below 2 on bench
                shortage_pen = 0.0
                for posx, target, pen in (('RB', 2, 2.0), ('WR', 2, 2.0)):
                    if counts_after.get(posx, 0) < target:
                        shortage_pen += pen
                # 3) Adding second QB when one already on bench: extra penalty
                add_pos_u = (cpos or '').upper()
                dp_pos_u = dp_pos
                extra_qb_pen = 0.0
                if add_pos_u == 'QB' and baseline_counts.get('QB', 0) >= 1:
                    extra_qb_pen = 2.0

                overall_after = round(
                    points_after + alpha * bench_vor_after + beta * balance_after + gamma * bye_after
                    - cross_penalty - qb_surplus_pen - shortage_pen - extra_qb_pen,
                    2
                )
                delta_overall = overall_after - baseline_overall
                if delta_overall > best_delta:
                    best_delta = delta_overall
                    best_after = lineup_after
                    best_drop = dp
            if best_delta > 0 and best_drop is not None:
                badges = _compute_badges(c, best_drop, enriched_roster, baseline_lineup)
                recs.append({
                    'add_player': {
                        'name': c.get('name'),
                        'team': c.get('team'),
                        'position': cpos,
                        'weekly_points': c.get('weekly_points'),
                        'ecr_overall': c.get('ecr_overall'),
                        'status': status
                    },
                    'drop_player': {
                        'name': best_drop.get('name'),
                        'team': best_drop.get('team'),
                        'position': best_drop.get('position'),
                        'weekly_points': best_drop.get('weekly_points'),
                        'ecr_overall': best_drop.get('ecr_overall')
                    },
                    'estimated_benefit': round(best_delta, 2),
                    'score_breakdown': {
                        'baseline': {
                            'overall': baseline_overall,
                            'lineup': round(baseline_points, 2),
                            'bench_vor': baseline_bench_vor,
                            'balance': baseline_balance,
                            'bye': baseline_bye
                        },
                        'after': {
                            'overall': round(baseline_overall + best_delta, 2)
                        }
                    },
                    'badges': badges,
                    'notes': [
                        'Slot-aware lineup optimization for current week',
                        'Whole-roster score includes bench value, balance, and bye coverage'
                    ],
                    'claim_only': (status == 'W')
                })

        recs.sort(key=lambda x: x['estimated_benefit'], reverse=True)
        # Unmatched diagnostics for alias improvements
        unmatched_roster = [rp.get('name') for rp in enriched_roster if not isinstance(rp.get('weekly_points'), (int, float))][:10]
        unmatched_pool = [c.get('name') for c in candidates if not isinstance(c.get('weekly_points'), (int, float))][:10]
        # Alternatives mode: include near-neutral suggestions if requested
        include_alts = bool(payload.get('include_alternatives', False))
        min_benefit = float(payload.get('min_benefit', 0.0))
        if not recs and include_alts and min_benefit < 0:
            # Re-evaluate candidates capturing top near-neutral moves
            alt_recs = []
            for c in candidates:
                cpos = c.get('position') or c.get('primary_position')
                if not cpos:
                    continue
                potential_drops = []
                for rp in bench:
                    potential_drops.append(rp)
                for rp in starters:
                    if _normalize_pos(rp.get('position') or rp.get('selected_position')) == _normalize_pos(cpos):
                        potential_drops.append(rp)
                potential_drops = potential_drops[:8]
                best_delta = -999.0
                best_drop = None
                for dp in potential_drops:
                    new_roster = [rp for rp in enriched_roster if rp is not dp] + [{
                        'name': c.get('name'),
                        'position': cpos,
                        'selected_position': dp.get('selected_position'),
                        'weekly_points': c.get('weekly_points'),
                        'ecr_overall': c.get('ecr_overall'),
                        'bye_week': c.get('bye_week'),
                    }]
                    lineup_after, points_after = _best_lineup(new_roster, required_slots)
                    bench_vor_after = _compute_bench_vor(new_roster, lineup_after)
                    counts_after = _compute_bench_counts(new_roster, lineup_after)
                    balance_after = _compute_balance_score(counts_after)
                    bye_after = _compute_bye_score(new_roster, lineup_after)
                    dp_pos = (dp.get('position') or dp.get('selected_position') or '').upper()
                    cross_penalty = 0.0
                    if (cpos or '').upper() != dp_pos:
                        if balance_after <= baseline_balance:
                            cross_penalty = 1.5
                    qb_after = counts_after.get('QB', 0)
                    qb_surplus_pen = max(0, qb_after - 1) * 2.5
                    shortage_pen = 0.0
                    for posx, target, pen in (('RB', 2, 2.0), ('WR', 2, 2.0)):
                        if counts_after.get(posx, 0) < target:
                            shortage_pen += pen
                    extra_qb_pen = 0.0
                    if (cpos or '').upper() == 'QB' and baseline_counts.get('QB', 0) >= 1:
                        extra_qb_pen = 2.0
                    overall_after = round(points_after + alpha * bench_vor_after + beta * balance_after + gamma * bye_after
                                           - cross_penalty - qb_surplus_pen - shortage_pen - extra_qb_pen, 2)
                    delta_overall = overall_after - baseline_overall
                    if delta_overall > best_delta:
                        best_delta = delta_overall
                        best_drop = dp
                if best_drop is not None and best_delta >= min_benefit:
                    badges = _compute_badges(c, best_drop, enriched_roster, baseline_lineup)
                    alt_recs.append({
                        'add_player': {
                            'name': c.get('name'), 'team': c.get('team'), 'position': cpos,
                            'weekly_points': c.get('weekly_points'), 'ecr_overall': c.get('ecr_overall'), 'status': status
                        },
                        'drop_player': {
                            'name': best_drop.get('name'), 'team': best_drop.get('team'), 'position': best_drop.get('position'),
                            'weekly_points': best_drop.get('weekly_points'), 'ecr_overall': best_drop.get('ecr_overall')
                        },
                        'estimated_benefit': round(best_delta, 2),
                        'badges': badges,
                        'claim_only': (status == 'W'),
                        'notes': ['Consider: near‑neutral move with rationale badges']
                    })
            alt_recs.sort(key=lambda x: x['estimated_benefit'], reverse=True)
            recs = alt_recs[:top_n]

        return jsonify({'recommendations': recs[:top_n], 'metadata': {
            'baseline_points': round(baseline_points, 2),
            'baseline_bench_vor': baseline_bench_vor,
            'baseline_overall': baseline_overall,
            'baseline_balance': baseline_balance,
            'baseline_bye': baseline_bye,
            'slots': required_slots,
            'pool_considered': len(candidates),
            'roster_projection_coverage': {
                'have': roster_proj_have,
                'total': roster_proj_total,
                'rate': round((roster_proj_have/roster_proj_total)*100, 1) if roster_proj_total else 0.0
            },
            'pool_projection_coverage': {
                'have': pool_proj_have,
                'total': pool_proj_total,
                'rate': round((pool_proj_have/pool_proj_total)*100, 1) if pool_proj_total else 0.0
            },
            'unmatched_roster': unmatched_roster,
            'unmatched_pool': unmatched_pool
        }})
    except requests.exceptions.RequestException as e:
        return jsonify({'error': 'Failed to connect to Yahoo API'}), 500
    except Exception as e:
        print(f"ERROR: yahoo_waiver_recommendations_v2 failed: {e}")
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

@app.route('/api/yahoo/league_inefficiencies', methods=['POST'])
def yahoo_league_inefficiencies():
    """
    Enhanced market inefficiency analysis using actual Yahoo league context.
    Provides league-specific sleeper and bust identification based on ownership patterns,
    league settings, and competitive landscape analysis.
    """
    try:
        user_key = request.headers.get('X-API-Key')
        data = request.json
        
        league_key = data.get('league_key')
        position = data.get('position', 'all')
        league_context = data.get('league_context', {})
        
        if not league_key or not league_context:
            return jsonify({"error": "league_key and league_context are required"}), 400
        
        # Extract league-specific data
        league_settings = league_context.get('league_settings', {})
        player_ownership = league_context.get('player_ownership', [])
        availability_stats = league_context.get('availability_stats', {})
        team_structure = league_context.get('team_structure', {})
        
        # Build league-aware candidate analysis
        league_candidates = []
        
        # Focus on available players for deeper inefficiency analysis
        available_players = [p for p in player_ownership if p['ownership_status'] == 'available']
        
        for player in available_players:
            if position != 'all' and player['primary_position'] != position:
                continue
            
            # Normalize player name for local database lookup
            normalized_name = normalize_player_name(player['name'])
            
            # Get enhanced player context using existing function
            player_context = get_player_context(
                player['name'],
                ecr_type_preference='overall',
                combined_player_data_cache=combined_player_data_cache,
                player_name_to_id=player_name_to_id,
                player_data_cache=player_data_cache,
                static_ecr_overall_data=static_ecr_overall_data,
                static_ecr_positional_data=static_ecr_positional_data,
                static_ecr_rookie_data=static_ecr_rookie_data
            )
            
            # Skip players without sufficient data
            if not player_context.get('ecr'):
                continue
            
            # Calculate league-specific inefficiency metrics
            league_specific_context = calculate_league_inefficiency_metrics(
                player_context, league_settings, availability_stats, team_structure
            )
            
            # Merge Yahoo data with local enrichment and league context
            enhanced_player = {
                **player,  # Yahoo ownership data
                **player_context,  # Local ECR and analysis data
                **league_specific_context  # League-specific metrics
            }
            
            league_candidates.append(enhanced_player)
        
        # Sort by league-adjusted inefficiency score (descending for sleepers)
        league_candidates.sort(key=lambda x: x.get('league_inefficiency_score', 0), reverse=True)
        
        # Limit candidates for AI analysis (top 50 most interesting)
        analysis_candidates = league_candidates[:50]
        
        # Build league context summary for AI
        league_summary = build_league_context_summary(league_settings, availability_stats, team_structure)
        
        # Build candidates context for AI analysis
        candidates_context = build_candidates_context_for_ai(analysis_candidates)
        
        # Get market inefficiency examples
        market_examples = ExampleLibrary.get_examples_for_analysis_type('yahoo_market_inefficiency')
        
        # Build enhanced prompt with Yahoo league-specific methodology
        enhanced_prompt = PromptBuilder.build_enhanced_prompt(
            task_description="Yahoo League Market Inefficiency Analysis - Identify league-specific sleeper and bust opportunities based on ownership patterns and league context",
            player_data=f"LEAGUE CONTEXT:\n{league_summary}\n\nAVAILABLE PLAYERS ANALYSIS:\n{candidates_context}",
            methodology_steps=[
                "1. LEAGUE-SPECIFIC OPPORTUNITY ASSESSMENT",
                "   • Evaluate player availability vs. general market ECR rankings",
                "   • Consider league size impact on player scarcity and value",
                "   • Assess roster construction needs based on league settings",
                "   • Factor in competitive landscape and manager sophistication",
                "",
                "2. OWNERSHIP PATTERN ANALYSIS",
                "   • Identify high-ECR players surprisingly available in league",
                "   • Evaluate position scarcity based on roster requirements",
                "   • Consider bench depth needs and streaming opportunities",
                "   • Assess handcuff availability and injury insurance options",
                "",
                "3. LEAGUE-ADJUSTED VALUE IDENTIFICATION",
                "   • Compare player ECR to typical ownership patterns in similar leagues",
                "   • Identify players with upside potential overlooked by league",
                "   • Evaluate schedule-based advantages and matchup benefits",
                "   • Consider league-specific scoring system impact on player value",
                "",
                "4. STRATEGIC ACQUISITION RECOMMENDATIONS",
                "   • Prioritize sleepers with highest league-specific upside",
                "   • Identify potential busts being overvalued by league managers",
                "   • Recommend specific acquisition strategies (waivers, trades, FA)",
                "   • Consider timing and competition for targeted players"
            ],
            examples=market_examples
        )
        
        # Make AI request and process response
        response_text = make_gemini_request(enhanced_prompt, user_key)
        processed_response = process_ai_response_v2(response_text, 'yahoo_league_market')
        
        # Structure response with league context
        return jsonify({
            'result': processed_response,
            'league_key': league_key,
            'league_context_summary': {
                'league_name': league_settings.get('name', ''),
                'total_teams': league_settings.get('num_teams', 0),
                'available_players': availability_stats.get('available_players', 0),
                'ownership_percentage': availability_stats.get('ownership_percentage', 0)
            },
            'candidates_analyzed': len(analysis_candidates),
            'total_available': len(available_players)
        })
        
    except Exception as e:
        print(f"ERROR: Yahoo league inefficiency analysis failed: {e}")
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

def calculate_league_inefficiency_metrics(player_context, league_settings, availability_stats, team_structure):
    """
    Calculate league-specific inefficiency metrics for a player.
    Returns dictionary with league-adjusted scores and contextual data.
    """
    try:
        ecr = player_context.get('ecr', 999)
        sd = player_context.get('sd', 0)
        num_teams = league_settings.get('num_teams', 12)
        ownership_pct = availability_stats.get('ownership_percentage', 0)
        
        # League-adjusted value score (lower ECR = higher value, adjusted for league size)
        base_value_score = max(0, (200 - ecr) / 200) * 100
        
        # League size adjustment (smaller leagues = higher value threshold)
        league_size_multiplier = max(0.8, 1.2 - (num_teams - 10) * 0.05)
        
        # Standard deviation bonus (higher disagreement = more opportunity)
        sd_bonus = min(sd * 10, 25) if sd else 0
        
        # Availability bonus (being available in high-ownership league = inefficiency)
        availability_bonus = (ownership_pct / 100) * 20
        
        # Calculate final league inefficiency score
        league_inefficiency_score = (base_value_score * league_size_multiplier) + sd_bonus + availability_bonus
        
        return {
            'league_inefficiency_score': round(league_inefficiency_score, 2),
            'league_size_factor': round(league_size_multiplier, 2),
            'standard_deviation_bonus': round(sd_bonus, 2),
            'availability_bonus': round(availability_bonus, 2),
            'league_context_notes': f"Available in {num_teams}-team league with {ownership_pct:.1f}% overall ownership"
        }
        
    except Exception as e:
        print(f"ERROR: Failed to calculate league inefficiency metrics: {e}")
        return {
            'league_inefficiency_score': 0,
            'league_size_factor': 1.0,
            'standard_deviation_bonus': 0,
            'availability_bonus': 0,
            'league_context_notes': 'Unable to calculate league-specific metrics'
        }

def build_league_context_summary(league_settings, availability_stats, team_structure):
    """Build formatted league context for AI analysis."""
    try:
        league_name = league_settings.get('name', 'Unknown League')
        num_teams = league_settings.get('num_teams', 0)
        total_players = availability_stats.get('total_players', 0)
        available_players = availability_stats.get('available_players', 0)
        ownership_pct = availability_stats.get('ownership_percentage', 0)
        
        # Build roster positions summary
        roster_positions = league_settings.get('roster_positions', [])
        positions_summary = []
        for pos_info in roster_positions:
            position = pos_info.get('position', '')
            count = pos_info.get('count', 0)
            if position and count > 0:
                positions_summary.append(f"{count} {position}")
        
        roster_structure = " + ".join(positions_summary) if positions_summary else "Standard roster"
        
        return f"""
League: {league_name}
Teams: {num_teams}
Roster Structure: {roster_structure}
Player Pool: {total_players} total players
Availability: {available_players} available ({100-ownership_pct:.1f}% available)
Competitive Level: {'High' if ownership_pct > 85 else 'Medium' if ownership_pct > 70 else 'Low'} (based on {ownership_pct:.1f}% ownership rate)
"""
    except Exception as e:
        return f"League context unavailable: {e}"

def build_candidates_context_for_ai(candidates):
    """Build formatted candidates list for AI analysis."""
    try:
        if not candidates:
            return "No qualified candidates found for analysis."
        
        analysis_lines = []
        for player in candidates[:25]:  # Top 25 for prompt efficiency
            name = player.get('name', 'Unknown')
            position = player.get('primary_position', 'Unknown')
            team = player.get('team', 'Unknown')
            ecr = player.get('ecr', 'N/A')
            sd = player.get('sd', 'N/A')
            inefficiency_score = player.get('league_inefficiency_score', 0)
            league_notes = player.get('league_context_notes', '')
            
            analysis_lines.append(
                f"- **{name}** ({position}, {team}): ECR {ecr}, SD {sd}, "
                f"League Score: {inefficiency_score:.1f} ({league_notes})"
            )
        
        return "\n".join(analysis_lines)
        
    except Exception as e:
        return f"Candidates analysis unavailable: {e}"

if __name__ == '__main__':
    # This block is for local development only.
    # When deployed on Render with Gunicorn, this block is not executed.
    # Data loading is handled by the `load_all_data()` call at the top level.
    if static_ecr_overall_data and player_data_cache is not None:
        # Use SSL context for HTTPS
        app.run(debug=True, host='0.0.0.0', port=5000, ssl_context=('certs/localhost.pem', 'certs/localhost-key.pem'))
    else:
        print("Application will not start because essential data failed to load.")
