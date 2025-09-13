# Yahoo Fantasy Roster Endpoint Implementation Guide - GO-FORWARD

> **File Type**: GO-FORWARD  
> **Review Priority**: High  
> **Last Updated**: August 31, 2025  
> **Purpose**: Yahoo API implementation details and patterns

## Overview

This document provides comprehensive implementation guidance for creating the `/api/yahoo/roster` endpoint based on thorough research of the Yahoo Fantasy Sports API documentation and analysis of the existing codebase patterns.

## Update (Resolved 2025-08-31): NFL Roster Parsing & Auth Notes

- NFL roster responses often nest data in list-of-lists, and `selected_position` (the roster slot) may be a sibling to `player` and can be a dict, string, or an array of dicts. Do not rely solely on `player.selected_position`.
- Robust approach implemented:
  - Recursively locate `roster` and `players` containers regardless of nesting using helper search.
  - Deep-scan each player container to extract `player_key`, `name.full`, `eligible_positions`, `status`, and `selected_position` across dict/string/list forms.
  - Primary endpoint: `/team/{team_key}/roster/players;week={n}?format=json`; fallback to `/team/{team_key}/roster;week={n}?format=json` when the first returns empty.
  - Requests use explicit `Authorization: Bearer <access_token>` and `Accept: application/json` (no OAuth session wrapper needed once you have the token).
- Debugging aid: `/api/yahoo/roster_debug` returns counts and `slot_samples` for quick verification of `selected_position`.
- Frontend mapping: Display a single roster-slot badge (Starter/Flex/Bench/IR) driven strictly by `selected_position`, plus a visible line: `Slot: <code> (<category>) • Position: <pos> • Eligible: ...`.

## API Research Findings

### Yahoo Fantasy Sports API Structure

**Base URL:** `https://fantasysports.yahooapis.com/fantasy/v2/team/{team_key}/roster`

**Parameters:**
- `format=json` - Required to get JSON response (defaults to XML)
- `week={week}` - For NFL: retrieve specific week roster (e.g., `roster;week=10`)
- `date={YYYY-MM-DD}` - For MLB/NHL/NBA: retrieve specific date roster
- If no week/date specified, returns current roster

**Team Key Format:** `{game_id}.l.{league_id}.t.{team_id}`
- Example: `223.l.431.t.1`

### Critical Field Name Corrections

**Implementation Plan vs Actual API:**

| Implementation Plan Field | Actual API Field | Status |
|--------------------------|------------------|---------|
| `player_key` | `player_key` | ✅ Correct |
| `name.full` | `name` | ❌ Incorrect - just `name` |
| `editorial_position` | `selected_position` | ❌ Incorrect - use `selected_position` |
| `editorial_team_abbr` | Need to verify | ⚠️ Unknown |

**Additional Fields Available:**
- `player_id` - Numeric player identifier
- `eligible_positions` - Array of positions player can play
- `position_type` - Position category (e.g., 'B' for batter)
- `status` - Player status (active, DTD, etc.)

### JSON Response Structure

Based on research, the roster response follows this structure:
```json
{
  "fantasy_content": {
    "team": [{
      "team_key": "328.l.34014.t.1",
      "team_id": "1",
      "name": "Team Name",
      // ... team metadata
    }, {
      "roster": {
        "players": {
          "0": {
            "player": [{
              "player_key": "253.p.8332",
              "player_id": "8332",
              "name": {
                "full": "Player Name"
              },
              "selected_position": {
                "position": "QB"
              },
              "eligible_positions": ["QB"],
              "status": "Healthy"
              // ... additional player fields
            }]
          },
          "1": {
            // ... next player
          }
          // ... more players
        }
      }
    }]
  }
}
```

**Important Notes:**
- Yahoo API converts XML to JSON, creating unpredictable nesting
- Single items may be objects, multiple items may be arrays
- Structure varies and requires defensive parsing
- Maximum 25 players per request (use pagination if needed)

## Existing Codebase Analysis

### Functions Available

**✅ Available Functions:**
- `normalize_player_name(name)` - In utils.py, normalizes player names
- `get_player_context()` - In utils.py, gets player analysis data
- `parse_yahoo_leagues_response(data)` - In app.py, example of defensive parsing

**❌ Missing Functions:**
- `get_player_analysis()` - Referenced in implementation plan but doesn't exist

### Authentication Pattern

Preferred pattern once you have the access token:
```python
auth_header = request.headers.get('Authorization')  # Expect: Bearer <token>
access_token = auth_header.split(' ')[1]
yahoo_headers = { 'Authorization': f'Bearer {access_token}', 'Accept': 'application/json' }
resp = requests.get(yahoo_url, headers=yahoo_headers, timeout=10)
```

### Defensive Parsing Pattern

From `parse_yahoo_leagues_response()` (lines 1005-1080):
- Always use `.get()` with defaults
- Check `isinstance()` before iterating
- Handle nested arrays within objects
- Wrap entire function in try-except
- Return `[]` on any failure

## Implementation Plan

### Phase 1: Foundation & API Integration (15 min)

#### 1.1 Add Route and Authentication
```python
@app.route('/api/yahoo/roster')
def get_yahoo_roster():
    """
    Fetches the user's fantasy team roster from the Yahoo API.
    Expects team_key as query parameter and token in Authorization header.
    """
    # Copy authentication pattern from leagues endpoint
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Not authenticated with Yahoo."}), 401
    
    # Get and validate team_key parameter
    team_key = request.args.get('team_key')
    if not team_key:
        return jsonify({"error": "team_key parameter is required."}), 400
    
    # Optional week parameter for NFL
    week = request.args.get('week')
    
    access_token_string = auth_header.split(' ')[1]
    yahoo = OAuth2Session(YAHOO_CLIENT_ID, token={'access_token': access_token_string})
```

#### 1.2 Construct Yahoo API URL
```python
    # Build URL with optional week parameter
    if week:
        url = f'https://fantasysports.yahooapis.com/fantasy/v2/team/{team_key}/roster;week={week}?format=json'
    else:
        url = f'https://fantasysports.yahooapis.com/fantasy/v2/team/{team_key}/roster?format=json'
```

#### 1.3 Make API Call
```python
    try:
        response = yahoo.get(url)
        response.raise_for_status()
        
        # Parse and transform the response using defensive JSON parsing
        return jsonify(parse_yahoo_roster_response(response.json()))
    
    except requests.exceptions.RequestException as req_e:
        print(f"Error fetching Yahoo roster: {req_e}")
        return jsonify({"error": "Failed to fetch roster from Yahoo."}), 500
    except Exception as e:
        print(f"Error processing Yahoo roster: {e}")
        return jsonify({"error": "Failed to process roster data."}), 500
```

### Phase 2: Defensive JSON Parser (20 min)

#### 2.1 Create Parser Function
```python
def parse_yahoo_roster_response(data):
    """
    Parse Yahoo API roster response with defensive JSON parsing.
    Returns a clean array of player objects or empty array on failure.
    """
    try:
        # Navigate the complex JSON structure using defensive .get() calls
        fantasy_content = data.get('fantasy_content', {})
        
        # Team data is typically an array where [1] contains roster
        team_data = fantasy_content.get('team', [])
        if not isinstance(team_data, list) or len(team_data) < 2:
            print("DEBUG: Team data structure unexpected")
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
                        
                        # Handle roster slot (NFL may return dict, string, or list)
                        selected_pos_data = player_data.get('selected_position', {})
                        if isinstance(selected_pos_data, dict):
                            selected_position = selected_pos_data.get('position', '')
                        elif isinstance(selected_pos_data, list):
                            selected_position = next((d.get('position') for d in selected_pos_data if isinstance(d, dict) and d.get('position')), '')
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
        
        return players
        
    except Exception as e:
        print(f"ERROR: Failed to parse Yahoo roster response: {e}")
        traceback.print_exc()
        return []
```

### Phase 3: Player Data Enrichment (15 min)

#### 3.1 Enrich with Local Data
```python
def enrich_roster_players(yahoo_players):
    """
    Enrich Yahoo roster players with local ECR and analysis data.
    """
    enriched_players = []
    
    for player in yahoo_players:
        try:
            # Normalize player name for matching
            normalized_name = normalize_player_name(player['name'])
            
            # Get local player context (ECR, analysis, etc.)
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
```

#### 3.2 Update Main Parser to Include Enrichment
```python
# In parse_yahoo_roster_response(), before return:
if players:
    players = enrich_roster_players(players)

return players
```

### Phase 4: Testing & Validation (10 min)

#### 4.1 Test Cases
1. **Valid team_key**: Use team_key from working `/api/yahoo/leagues` response
2. **Invalid team_key**: Verify error handling
3. **Missing team_key**: Verify 400 error
4. **Invalid token**: Verify 401 error
5. **With week parameter**: Test NFL week-specific roster
6. **Player enrichment**: Verify local data integration

#### 4.2 Example Test URLs
```
GET /api/yahoo/roster?team_key=414.l.12345.t.1
GET /api/yahoo/roster?team_key=414.l.12345.t.1&week=10
```

## Integration Points

### Required Imports
```python
# Already available in app.py:
from flask import Flask, request, jsonify
from requests_oauthlib import OAuth2Session
import requests
import traceback
from utils import normalize_player_name, get_player_context
```

### Global Variables Used
- `YAHOO_CLIENT_ID`
- `combined_player_data_cache`
- `player_name_to_id`
- `player_data_cache`
- `static_ecr_overall_data`
- `static_ecr_positional_data`
- `static_ecr_rookie_data`

## Response Format

### Success Response
```json
[
  {
    "player_key": "414.p.8332",
    "player_id": "8332",
    "name": "Patrick Mahomes",
    "selected_position": "QB",
    "eligible_positions": ["QB"],
    "status": "Healthy",
    "team": "KC",
    "position": "QB",
    "bye_week": 10,
    "ecr_overall": 15.2,
    "sd_overall": 2.1,
    "best_overall": 12,
    "worst_overall": 18,
    "rank_delta_overall": 0.5,
    "years_exp": 8,
    "is_rookie": false
  }
]
```

### Error Responses
```json
{"error": "team_key parameter is required."}  // 400
{"error": "Not authenticated with Yahoo."}   // 401
{"error": "Failed to fetch roster from Yahoo."}  // 500
```

## Troubleshooting Guide

### Common Issues

#### 1. Empty Response from Yahoo
- **Cause**: Invalid team_key or user not in league
- **Solution**: Verify team_key from `/api/yahoo/leagues` response
- **Debug**: Check Yahoo API response logs

#### 2. Player Names Not Matching Local Data
- **Cause**: Name variations between Yahoo and local database
- **Solution**: Enhance `normalize_player_name()` function
- **Debug**: Log normalized names for comparison

#### 3. Complex JSON Structure Errors
- **Cause**: Yahoo API structure variations
- **Solution**: Add more defensive parsing levels
- **Debug**: Log raw Yahoo response to analyze structure

#### 4. Missing Player Enrichment Data
- **Cause**: Players not in local database
- **Solution**: Graceful degradation - return Yahoo data only
- **Debug**: Check `combined_player_data_cache` for player

### Debugging Tools

#### Log Raw Response
```python
print(f"Raw Yahoo roster response: {response.json()}")
```

#### Test Parser Independently
```python
# Test with saved response data
test_data = {...}  # Paste actual Yahoo response
result = parse_yahoo_roster_response(test_data)
print(f"Parsed result: {result}")
```

## Future Enhancements

### 1. Caching
- Cache roster responses to reduce API calls
- Implement cache invalidation strategies

### 2. Subresources
- Add support for Yahoo subresources (stats, ownership, etc.)
- Example: `/api/yahoo/roster?team_key=X&subresource=stats`

### 3. Multiple Weeks
- Support fetching multiple weeks in single request
- Batch processing for historical data

### 4. Error Recovery
- Implement retry logic for transient failures
- Token refresh handling

## Success Criteria

- [ ] Endpoint responds to valid requests with 200 status
- [ ] Returns clean JSON array of player objects
- [ ] Includes both Yahoo and enriched local data
- [ ] Handles errors gracefully with appropriate HTTP codes
- [ ] Works with both current roster and week-specific requests
- [ ] Player names normalized and matched with local data
- [ ] Defensive parsing handles various JSON structures
- [ ] Comprehensive error logging for debugging

## Implementation Checklist

- [ ] Add route with authentication
- [ ] Implement Yahoo API call with parameters
- [ ] Create defensive JSON parser function
- [ ] Add player enrichment logic
- [ ] Test with real Yahoo data
- [ ] Verify error handling
- [ ] Add comprehensive logging
- [ ] Document any additional findings

---

**Last Updated:** [Current Date]
**Status:** Ready for Implementation
**Estimated Time:** 60 minutes total
