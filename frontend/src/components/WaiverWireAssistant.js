import React, { useEffect, useState, useCallback, useContext } from 'react';
import autoComplete from '@tarekraafat/autocomplete.js';
import styles from './WaiverWireAssistant.module.css';
import { useApi } from '../hooks/useApi';
import { AppContext } from '../context/AppContext';

const RosterInput = ({ id, label, allPlayers, description = null, onPlayerChange }) => {
  useEffect(() => {
    let autocompleteInstance;
    if (allPlayers.length > 0) {
      autocompleteInstance = new autoComplete({
        selector: `#${id}`,
        placeHolder: `Enter player for ${label}...`,
        data: { src: allPlayers, cache: true },
        resultItem: { highlight: true },
        events: {
          input: {
            selection: (event) => {
              const selection = event.detail.selection.value;
              const input = document.querySelector(`#${id}`);
              if (input) {
                input.value = selection;
              }
              // Notify parent of autocomplete selection
              if (onPlayerChange) {
                onPlayerChange(label, selection);
              }
            },
          },
        },
      });
    }
    return () => {
      // Attempt to clean up autocomplete instance if possible
      if (autocompleteInstance) {
        autocompleteInstance.unInit && autocompleteInstance.unInit();
      }
    };
  }, [allPlayers, id, label, onPlayerChange]);

  const handleClearInput = () => {
    const input = document.querySelector(`#${id}`);
    if (input) {
      input.value = '';
      // Notify parent of change
      if (onPlayerChange) {
        onPlayerChange(label, '');
      }
    }
  };
  
  const handleInputChange = (e) => {
    if (onPlayerChange) {
      onPlayerChange(label, e.target.value);
    }
  };

  return (
    <div className={styles.rosterInputGroup}>
      <label htmlFor={id}>
        {label}
        {description && <span className={styles.positionDescription}> ({description})</span>}
      </label>
      <div>
        <div className={styles.autoCompleteWrapper}>
          <input 
            id={id} 
            type="text" 
            onChange={handleInputChange}
          />
        </div>
        <button 
          onClick={handleClearInput} 
          className={styles.clearButton}
          aria-label={`Clear ${label} input`}
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
    </div>
  );
};

const WaiverWireAssistant = ({ 
  allPlayers, 
  onAnalyze, 
  onAnalyzeEnhanced = null, // Optional: New prop for enhanced analysis with complete roster data
  // onAnalyzeYahoo deprecated in favor of direct v2 call from this component
  onAnalyzeYahoo = null, // kept for backward compatibility; not used in Yahoo mode
  onLeaguesUpdate = null, // Optional: New prop to pass leagues to parent
  analysisResult, 
  isLoading 
}) => {
  // API_BASE_URL is provided by app context; GET helper via useApi
  const { API_BASE_URL, userApiKey } = useContext(AppContext);
  const { get, makeApiRequest } = useApi();
  
  const rosterPositions = {
    Starters: ['QB', 'WR1', 'WR2', 'RB1', 'RB2', 'W/T', 'W/R/T', 'DEF'],
    'Bench & IR': ['BN1', 'BN2', 'BN3', 'BN4', 'BN5', 'BN6', 'IR1', 'IR2'],
  };

  // Position descriptions for user clarity
  const positionDescriptions = {
    'W/T': 'Wide Receiver or Tight End',
    'W/R/T': 'Wide Receiver, Running Back, or Tight End',
    'IR1': 'Injury Reserve (optional)',
    'IR2': 'Injury Reserve (optional)'
  };

  // Position validation helper (for future use)
  // const getValidPositions = (positionSlot) => {
  //   switch (positionSlot) {
  //     case 'W/T': return ['WR', 'TE'];
  //     case 'W/R/T': return ['WR', 'RB', 'TE'];
  //     case 'IR1':
  //     case 'IR2': return ['QB', 'WR', 'RB', 'TE', 'DEF']; // IR can hold any position
  //     default: return null; // Standard positions don't need validation
  //   }
  // };

  // Traditional waiver wire state
  const [playerToAdd, setPlayerToAdd] = useState('');
  const [activeTab, setActiveTab] = useState('Starters');
  
  // Roster persistence state (used internally for change detection)
  const [, setRosterData] = useState({});
  
  // Get all roster positions for easy iteration
  const allRosterPositions = Object.values(rosterPositions).flat();
  
  // Yahoo integration state
  const [isYahooUser, setIsYahooUser] = useState(false);
  const [userLeagues, setUserLeagues] = useState([]);
  const [selectedLeague, setSelectedLeague] = useState('');
  const [yahooAvailablePlayers, setYahooAvailablePlayers] = useState([]);
  const [yahooRosterNames, setYahooRosterNames] = useState(new Set());
  const [yahooRosterIds, setYahooRosterIds] = useState(new Set());
  const [isLoadingYahooData, setIsLoadingYahooData] = useState(false);
  const [yahooError, setYahooError] = useState('');
  const [useYahooMode, setUseYahooMode] = useState(false);
  // Recommendations state (Yahoo v2 endpoint)
  const [recommendations, setRecommendations] = useState([]); // deterministic fallback
  const [aiMoves, setAiMoves] = useState([]); // AI-authority moves
  const [recMeta, setRecMeta] = useState(null);
  const [recError, setRecError] = useState('');
  const [statusFilter, setStatusFilter] = useState('A'); // A|FA|W
  const [includeAlternatives, setIncludeAlternatives] = useState(false);
  const [hideNegativeAi, setHideNegativeAi] = useState(true);
  const [minBenefit, setMinBenefit] = useState(0.0); // toggled to -1.0 when alternatives enabled
  const [showFilters, setShowFilters] = useState(false);
  const [showPool, setShowPool] = useState(false);
  const [showMeta, setShowMeta] = useState(false);
  const [expandedRecs, setExpandedRecs] = useState({});
  // Hide AI debug controls by default (available via developer tools only)
  const [showAiDebug, setShowAiDebug] = useState(false);
  const [aiDebug, setAiDebug] = useState(null);

  const sanitizeId = (label) => label.replace(/\//g, '-');
  
  // Roster persistence functions (inspired by Draft Assistant pattern)
  const loadWaiverRoster = useCallback(() => {
    const savedRoster = localStorage.getItem('waiverWireRoster');
    if (savedRoster) {
      try {
        return JSON.parse(savedRoster);
      } catch (error) {
        console.error('Error parsing saved roster:', error);
        return {};
      }
    }
    return {};
  }, []);
  
  const saveWaiverRoster = useCallback(() => {
    const newRoster = {};
    let changesDetected = false;
    
    // Get current saved roster to compare for changes
    const currentSavedRoster = loadWaiverRoster();
    
    // Collect current values from all roster input fields
    allRosterPositions.forEach(pos => {
      const sanitizedId = sanitizeId(pos);
      const input = document.getElementById(`roster-input-${sanitizedId}`);
      const playerName = input ? input.value.trim() : '';
      newRoster[pos] = playerName;
      
      // Check if value changed from saved version
      if (playerName !== (currentSavedRoster[pos] || '')) {
        changesDetected = true;
      }
    });
    
    // Only write to localStorage if there were actual changes
    if (changesDetected) {
      localStorage.setItem('waiverWireRoster', JSON.stringify(newRoster));
      console.log('Roster saved to localStorage');
    }
    
    // Don't update React state here to avoid re-renders that cause focus loss
    // setRosterData is only used for initial load, not for ongoing saves
    
  }, [allRosterPositions, loadWaiverRoster]);
  
  const updateRosterField = useCallback((position, playerName) => {
    // Only update localStorage in traditional mode
    if (useYahooMode) return;
    
    // Update the specific input field
    const sanitizedId = sanitizeId(position);
    const input = document.getElementById(`roster-input-${sanitizedId}`);
    if (input) {
      input.value = playerName;
    }
    
    // Save the entire roster (with change detection)
    saveWaiverRoster(); // Save immediately, no delay needed
  }, [saveWaiverRoster, useYahooMode]);
  
  const clearWaiverRoster = useCallback(() => {
    // Only allow clearing in traditional mode
    if (useYahooMode) {
      console.log('Cannot clear roster in Yahoo mode - roster is managed by Yahoo');
      return;
    }
    
    // Clear all input fields
    allRosterPositions.forEach(pos => {
      const sanitizedId = sanitizeId(pos);
      const input = document.getElementById(`roster-input-${sanitizedId}`);
      if (input) {
        input.value = '';
      }
    });
    
    // Clear localStorage and state
    localStorage.removeItem('waiverWireRoster');
    // Only update React state when we actually need to clear the UI
    setRosterData({});
    
    console.log('Waiver wire roster cleared');
  }, [allRosterPositions, useYahooMode]);
  
  // Load roster data on component mount (only in traditional mode)
  useEffect(() => {
    // Skip localStorage loading in Yahoo mode
    if (useYahooMode) return;
    
    const savedRoster = loadWaiverRoster();
    setRosterData(savedRoster);
    
    // Small delay to ensure DOM elements are rendered before populating
    const populateFields = () => {
      Object.entries(savedRoster).forEach(([position, playerName]) => {
        if (playerName) {
          const sanitizedId = sanitizeId(position);
          const input = document.getElementById(`roster-input-${sanitizedId}`);
          if (input) {
            input.value = playerName;
          }
        }
      });
    };
    
    // Populate immediately and also after a short delay to handle async rendering
    populateFields();
    setTimeout(populateFields, 100);
    
  }, [loadWaiverRoster, useYahooMode]); // Also depend on useYahooMode

  // Yahoo authentication detection and leagues fetching
  const fetchUserLeagues = async (token) => {
    try {
      setIsLoadingYahooData(true);
      setYahooError('');
      
      // Parse token object and extract access_token
      const tokenObject = JSON.parse(token);
      const authHeader = `Bearer ${tokenObject.access_token}`;
      
      const leagues = await get('/yahoo/leagues', {
        headers: {
          'Authorization': authHeader
        }
      });
      
      setUserLeagues(leagues);
      
      // Pass leagues data to parent component for team key lookup
      if (onLeaguesUpdate) {
        onLeaguesUpdate(leagues);
      }
      
      // Auto-select first league if only one available, and load pool
      if (leagues.length === 1) {
        const lk = leagues[0].league_key;
        setSelectedLeague(lk);
        try { await fetchAvailablePlayers(lk); } catch(_) {}
        try { await fetchUserRosterNames(lk); } catch(_) {}
      }
    } catch (error) {
      console.error('Error fetching leagues:', error);
      // Handle 401 token expiration following existing patterns
      if (error.response && error.response.status === 401) {
        setYahooError('Yahoo authentication expired. Please re-authenticate.');
        setIsYahooUser(false);
        localStorage.removeItem('yahoo_token');
      } else {
        setYahooError('Unable to connect to Yahoo API.');
      }
    } finally {
      setIsLoadingYahooData(false);
    }
  };

  // Check Yahoo authentication on component mount
  useEffect(() => {
    const checkYahooAuth = async () => {
      try {
        const token = localStorage.getItem('yahoo_token');
        if (token) {
          setIsYahooUser(true);
          // Default to Yahoo mode when token present
          setUseYahooMode(true);
          // Fetch user's leagues
          await fetchUserLeagues(token);
        } else {
          setIsYahooUser(false);
          setUseYahooMode(false);
        }
      } catch (error) {
        console.error('Error checking Yahoo authentication:', error);
        setIsYahooUser(false);
        setUseYahooMode(false);
      }
    };
    
    checkYahooAuth();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // Run once on mount

  // Fetch available players for selected league
  const fetchAvailablePlayers = async (leagueKey) => {
    try {
      setIsLoadingYahooData(true);
      setYahooError('');
      
      const token = localStorage.getItem('yahoo_token');
      // Parse token object and extract access_token
      const tokenObject = JSON.parse(token);
      const authHeader = `Bearer ${tokenObject.access_token}`;
      
      const data = await get(`/yahoo/waiver_wire?league_key=${leagueKey}&status=A`, {
        headers: {
          'Authorization': authHeader
        }
      });
      
      setYahooAvailablePlayers(data.available_players || []);
    } catch (error) {
      console.error('Error fetching available players:', error);
      // Handle 401 token expiration following existing patterns
      if (error.response && error.response.status === 401) {
        setYahooError('Yahoo authentication expired. Please re-authenticate.');
        setIsYahooUser(false);
        localStorage.removeItem('yahoo_token');
      } else {
        setYahooError('Unable to load waiver wire data.');
      }
    } finally {
      setIsLoadingYahooData(false);
    }
  };

  // Fetch current roster names for client-side guard
  const fetchUserRosterNames = async (leagueKey) => {
    try {
      const token = localStorage.getItem('yahoo_token');
      if (!token) return;
      const tokenObject = JSON.parse(token);
      const authHeader = `Bearer ${tokenObject.access_token}`;
      const leagueObj = userLeagues.find(l => l.league_key === leagueKey);
      const teamKey = leagueObj?.team_key;
      if (!teamKey) return;
      const roster = await get(`/yahoo/roster?team_key=${encodeURIComponent(teamKey)}`, {
        headers: { 'Authorization': authHeader }
      });
      const norm = (s) => (typeof s === 'string' ? s.trim().toLowerCase() : '');
      const arr = Array.isArray(roster) ? roster : [];
      const names = new Set(arr.map(p => norm(p.name)).filter(Boolean));
      const ids = new Set(arr.map(p => String(p.player_id || '')).filter(v => v && v !== 'null' && v !== 'undefined'));
      setYahooRosterNames(names);
      setYahooRosterIds(ids);
    } catch (e) {
      console.warn('Could not fetch roster names for guard', e);
      setYahooRosterNames(new Set());
      setYahooRosterIds(new Set());
    }
  };

  // Handle league selection change
  const handleLeagueChange = async (event) => {
    const leagueKey = event.target.value;
    setSelectedLeague(leagueKey);
    
    if (leagueKey && useYahooMode) {
      await fetchAvailablePlayers(leagueKey);
      await fetchUserRosterNames(leagueKey);
      // Clear stale recommendations on league change
      setRecommendations([]);
      setRecMeta(null);
      setRecError('');
    }
  };

  // Toggle Yahoo mode
  const toggleYahooMode = () => {
    const next = !useYahooMode;
    setUseYahooMode(next);
    if (next && selectedLeague) {
      fetchAvailablePlayers(selectedLeague);
      fetchUserRosterNames(selectedLeague);
    }
  };

  const handleAnalyzeClick = () => {
    if (useYahooMode && selectedLeague) {
      // Yahoo mode: call deterministic v2 recommendations endpoint directly
      const token = localStorage.getItem('yahoo_token');
      if (!token) {
        alert('Yahoo authentication required. Please log in with Yahoo.');
        return;
      }
      // Refresh roster names guard before generating recommendations
      try { fetchUserRosterNames(selectedLeague); } catch (_) {}
      generateRecommendations(selectedLeague, token);
    } else {
      // Traditional mode: use manual roster input
      // First save any pending changes, then use saved roster data
      saveWaiverRoster();
      const currentRoster = loadWaiverRoster();
      
      // Enhanced: Send complete roster context including empty positions
      const filledPositions = {};
      const emptyPositions = [];
      
      allRosterPositions.forEach(pos => {
        const playerName = currentRoster[pos];
        if (playerName && playerName.trim()) {
          filledPositions[pos] = playerName.trim();
        } else {
          emptyPositions.push(pos);
        }
      });
      
      const enhancedRosterData = {
        filled_positions: filledPositions,
        empty_positions: emptyPositions,
        all_positions: allRosterPositions,
        total_roster_spots: allRosterPositions.length,
        bench_spots: allRosterPositions.filter(pos => pos.startsWith('BN')),
        starter_spots: allRosterPositions.filter(pos => !pos.startsWith('BN') && !pos.startsWith('IR'))
      };
      
      // Try enhanced analysis first, fallback to traditional if needed
      if (onAnalyzeEnhanced) {
        onAnalyzeEnhanced(enhancedRosterData, playerToAdd, filledPositions);
      } else {
        // Fallback to traditional analysis
        onAnalyze(filledPositions, playerToAdd);
      }
    }
  };

  const generateRecommendations = async (leagueKey, yahooToken) => {
    try {
      setIsLoadingYahooData(true);
      setRecError('');
      setRecommendations([]);
      setRecMeta(null);

      // Parse token object and extract access_token
      const tokenObject = JSON.parse(yahooToken);
      const authHeader = `Bearer ${tokenObject.access_token}`;

      // Determine team key from userLeagues
      const leagueObj = userLeagues.find(l => l.league_key === leagueKey);
      const teamKey = leagueObj?.team_key;
      if (!teamKey) {
        throw new Error('Unable to find your team in the selected league.');
      }

      // Build payload for v2 endpoint
      const body = {
        league_key: leagueKey,
        team_key: teamKey,
        status: statusFilter,
        top_n: 10,
        include_alternatives: includeAlternatives,
        min_benefit: includeAlternatives ? (minBenefit ?? -1.0) : 0.0,
        exclude_positions: ['K', 'DEF']
      };

      // Fetch both AI (when available) and deterministic v2 in parallel to build a merged view
      let aiPromise = null;
      if (userApiKey) {
        aiPromise = fetch(`${API_BASE_URL}/yahoo/waiver_recommendations_ai?debug=1`, {
          method: 'POST',
          headers: {
            'Authorization': authHeader,
            'X-API-Key': userApiKey,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(body)
        });
      }

      const v2Promise = fetch(`${API_BASE_URL}/yahoo/waiver_recommendations_v2`, {
        method: 'POST',
        headers: {
          'Authorization': authHeader,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(body)
      });

      // Resolve deterministic first so we always have a baseline list
      const v2Resp = await v2Promise;
      if (!v2Resp.ok) {
        const errData = await v2Resp.json().catch(() => ({}));
        throw new Error(errData.error || `Failed to fetch recommendations (${v2Resp.status})`);
      }
      const v2Data = await v2Resp.json();
      setRecommendations(Array.isArray(v2Data.recommendations) ? v2Data.recommendations : []);
      setRecMeta(v2Data.metadata || null);

      // If AI available, resolve and set AI-specific state; UI merges both lists
      if (aiPromise) {
        try {
          const aiResp = await aiPromise;
          if (aiResp.ok) {
            const aiData = await aiResp.json();
            setAiMoves(Array.isArray(aiData.moves) ? aiData.moves : []);
            setAiDebug(aiData.debug || { ai_used: true, ai_moves_count: (aiData.moves||[]).length });
            // We keep recommendations from v2; AI recs are merged in render
          } else {
            try { const errData = await aiResp.json(); setAiDebug(errData && errData.debug ? errData.debug : { ai_used: false, error: `HTTP ${aiResp.status}` }); } catch(_) {}
          }
        } catch (e) {
          // AI failed; we keep deterministic-only view
          setAiDebug({ ai_used: false, error: String(e) });
        }
      }
    } catch (err) {
      console.error('Recommendations error:', err);
      setRecError(err.message || 'Unknown error fetching recommendations');
    } finally {
      setIsLoadingYahooData(false);
    }
  };

  const getConfidence = (rec) => {
    const b = typeof rec.estimated_benefit === 'number' ? rec.estimated_benefit : 0;
    if (b >= 2.0) return 'High';
    if (b >= 0.5) return 'Medium';
    return 'Low';
  };

  const badgeToReason = (badge) => {
    switch ((badge || '').toLowerCase()) {
      case 'depth': return 'Strengthens bench depth at a need position';
      case 'bye coverage': return 'Improves coverage for upcoming starter byes';
      case 'insurance': return 'Adds insurance behind a key starter';
      case 'upside': return 'Adds upside profile for later weeks';
      case 'risk': return 'Carries some uncertainty (monitor)';
      default: return null;
    }
  };

  const toggleRecExpanded = (idx) => {
    setExpandedRecs(prev => ({ ...prev, [idx]: !prev[idx] }));
  };
  
  useEffect(() => {
    let autocompleteInstance;
    if (allPlayers.length > 0) {
        autocompleteInstance = new autoComplete({
            selector: '#player-to-add',
            placeHolder: "Enter player to add...",
            data: { src: allPlayers, cache: true },
            resultItem: { highlight: true },
            events: {
                input: {
                    selection: (event) => {
                        const selection = event.detail.selection.value;
                        const input = document.querySelector('#player-to-add');
                        if (input) {
                            input.value = selection;
                        }
                        setPlayerToAdd(selection);
                    },
                },
            },
        });
    }
    return () => {
      // Attempt to clean up autocomplete instance if possible
      if (autocompleteInstance) {
        autocompleteInstance.unInit && autocompleteInstance.unInit();
      }
    };
  }, [allPlayers]);

  const handleTabChange = (tab) => {
    console.log(`Switching to tab: ${tab}`);
    setActiveTab(tab);
  };

  return (
    <section id="waiver-swap" className={styles.waiverSection}>
      <div className={styles.toolHeader}>
        <h2>Waiver Wire Swap Analyzer</h2>
        <p>Enter your roster and a player to see if you should make a move.</p>
      </div>
      
      {/* Yahoo Mode Section */}
      {isYahooUser && onAnalyzeYahoo && (
        <div className={styles.yahooModeSection}>
          <div className={styles.modeToggle}>
            <label>
              <input 
                type="checkbox" 
                checked={useYahooMode} 
                onChange={toggleYahooMode}
                disabled={isLoadingYahooData}
              />
              Use Yahoo League Data
            </label>
          </div>
          
          {useYahooMode && (
            <div className={styles.leagueSelector}>
              <label htmlFor="league-select">Select League:</label>
              <select 
                id="league-select"
                value={selectedLeague} 
                onChange={handleLeagueChange}
                disabled={isLoadingYahooData}
              >
                <option value="">Choose a league...</option>
                {userLeagues.map(league => (
                  <option key={league.league_key} value={league.league_key}>
                    {league.league_name}
                  </option>
                ))}
              </select>
              {isLoadingYahooData && <span className={styles.loadingText}>Loading...</span>}
              {yahooError && <div className={styles.errorText}>{yahooError}</div>}
            </div>
          )}
        </div>
      )}
      
      <div className={styles.singleColumnLayout}>
        {/* Only show manual roster input in traditional mode */}
        {!useYahooMode && (
          <div className={styles.rosterSection}>
          <div className={styles.card}>
            <div className={styles.rosterHeader}>
              <div>
                <h3>Your Roster</h3>
                <p style={{ color: 'var(--text-muted)', marginBottom: '10px' }}>Use the tabs below to input your current roster for each position.</p>
              </div>
              <button 
                onClick={clearWaiverRoster}
                className={styles.clearAllButton}
                title="Clear all roster positions"
              >
                Clear All
              </button>
            </div>
            <div className={styles.tabNavigation}>
              {Object.keys(rosterPositions).map(tab => (
                <button
                  key={tab}
                  className={`${styles.tabButton} ${activeTab === tab ? 'active' : ''}`}
                  onClick={() => handleTabChange(tab)}
                >
                  {tab}
                </button>
              ))}
            </div>
            <div className={styles.tabContent}>
              {Object.entries(rosterPositions).map(([category, positions]) => (
                <div
                  key={category}
                  className={`${styles.tabPane} ${activeTab === category ? styles.active : ''}`}
                >
                  <h4>{category}</h4>
                  <div className={styles.waiverGrid}>
                    {positions.map((pos) => {
                      const sanitizedId = sanitizeId(pos);
                      const description = positionDescriptions[pos] || null;
                      return (
                        <RosterInput 
                          key={pos} 
                          id={`roster-input-${sanitizedId}`} 
                          label={pos} 
                          allPlayers={allPlayers}
                          description={description}
                          onPlayerChange={updateRosterField}
                        />
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>
          </div>
        )}
        <div className={styles.waiverPlayerSection}>
          <div className={styles.card}>
            {useYahooMode && selectedLeague ? (
              <>
                <div className={styles.controlsHeader}>
                  <div className={styles.controlsRow}>
                    <div className={styles.controlGroup}>
                      <button 
                        onClick={handleAnalyzeClick} 
                        className={styles.actionButton} 
                        disabled={isLoadingYahooData}
                      >
                        {isLoadingYahooData ? 'Refreshing…' : 'Refresh Recommendations'}
                      </button>
                    </div>
                    <button className={styles.linkButton} onClick={() => setShowFilters(!showFilters)}>
                      {showFilters ? 'Hide Filters' : 'Filters'}
                    </button>
                    <button className={styles.linkButton} onClick={() => setShowMeta(!showMeta)}>
                      {showMeta ? 'Hide Details' : 'Show Details'}
                    </button>
                  </div>
                  {showFilters && (
                    <div className={styles.advancedRow}>
                      <div className={styles.controlGroup}>
                        <label>Status</label>
                        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)}>
                          <option value="A">All (A)</option>
                          <option value="FA">Free Agents (FA)</option>
                          <option value="W">Waivers (W)</option>
                        </select>
                      </div>
                      <div className={styles.controlGroup}>
                        <label className={styles.inlineToggle}>
                          <input
                            type="checkbox"
                            checked={includeAlternatives}
                            onChange={(e) => {
                              const v = e.target.checked;
                              setIncludeAlternatives(v);
                              // Default to slight negative floor so small DEF→depth swaps appear
                              setMinBenefit(v ? -0.5 : 0.0);
                            }}
                          />
                          Include near‑neutral moves
                          <span className={styles.helpText} style={{ marginLeft: 6 }}>
                            Show small or lateral upgrades that improve balance/depth
                          </span>
                        </label>
                      </div>
                      <div className={styles.controlGroup}>
                        <label className={styles.inlineToggle}>
                          <input
                            type="checkbox"
                            checked={hideNegativeAi}
                            onChange={(e) => setHideNegativeAi(e.target.checked)}
                          />
                          Hide negative AI moves
                          <span className={styles.helpText} style={{ marginLeft: 6 }}>
                            If enabled, AI items below 0 are hidden even when near‑neutral is on
                          </span>
                        </label>
                      </div>
                      {includeAlternatives && (
                        <div className={styles.controlGroup}>
                          <label>Min Estimated Benefit</label>
                          <input
                            type="range"
                            min={-5}
                            max={5}
                            step={0.5}
                            value={minBenefit}
                            onChange={(e) => setMinBenefit(parseFloat(e.target.value))}
                          />
                          <span className={styles.rangeValue}>{Number.isFinite(minBenefit) ? minBenefit.toFixed(1) : '-'}</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>

                {/* Analyst Summary removed to reduce redundancy with opinion banner */}

                {showAiDebug && (
                  <div className={styles.analystBox}>
                    <div className={styles.analystHeading}>AI Debug</div>
                    <div className={styles.detailsGrid}>
                      <span>API Key Present</span><span>{userApiKey ? 'Yes' : 'No'}</span>
                      <span>AI Endpoint Used</span><span>{aiMoves && aiMoves.length ? 'Yes' : 'No (fallback)'}</span>
                      <span>AI Moves Count</span><span>{aiMoves ? aiMoves.length : 0}</span>
                      {aiDebug && aiDebug.pool_coverage && <>
                        <span>Pool Coverage</span><span>{aiDebug.pool_coverage.rate}% ({aiDebug.pool_coverage.have}/{aiDebug.pool_coverage.total})</span>
                      </>}
                      {aiDebug && aiDebug.roster_coverage && <>
                        <span>Roster Coverage</span><span>{aiDebug.roster_coverage.rate}% ({aiDebug.roster_coverage.have}/{aiDebug.roster_coverage.total})</span>
                      </>}
                      {aiDebug && aiDebug.error && <>
                        <span>Error</span><span style={{color:'var(--danger-color)'}}>{aiDebug.error}</span>
                      </>}
                    </div>
                    {aiDebug && (aiDebug.prompt || aiDebug.prompt_sample) && (
                      <details style={{marginTop:'8px'}}>
                        <summary>Prompt Preview</summary>
                        <pre style={{whiteSpace:'pre-wrap'}}>{aiDebug.prompt || aiDebug.prompt_sample}</pre>
                      </details>
                    )}
                  </div>
                )}

                {showMeta && recMeta && (
                  <div className={styles.summaryChips}>
                    <span className={styles.chip}>Baseline Overall: {recMeta.baseline_overall}</span>
                    <span className={styles.chip}>Lineup: {recMeta.baseline_points}</span>
                    <span className={styles.chip}>Bench VOR: {recMeta.baseline_bench_vor}</span>
                    <span className={styles.chip}>Balance: {recMeta.baseline_balance}</span>
                    <span className={styles.chip}>Bye: {recMeta.baseline_bye}</span>
                    <span className={styles.chipMuted}>Pool: {recMeta.pool_considered} • Coverage: {recMeta.pool_projection_coverage?.rate}%</span>
                  </div>
                )}

                {recError && <div className={styles.errorText}>{recError}</div>}

                <h3>Top Waiver Moves</h3>
                {/* Opinionated banner: show strongest call or low-impact disclaimer (merged AI + deterministic) */}
                {(aiMoves.length > 0 || recommendations.length > 0) && (
                  <div className={styles.opinionBanner}>
                    {(() => {
                      const norm = (s) => (typeof s === 'string' ? s.trim().toLowerCase() : '');
                      const mkAddName = (r) => (typeof r.add === 'string' ? r.add : (r.add?.name || r.add_player?.name));
                      const mkDropName = (r) => (typeof r.drop === 'string' ? r.drop : (r.drop?.name || r.drop_player?.name));
                      const detL = (recommendations || []).map(r => ({
                        ...r,
                        __source:'Deterministic',
                        __add_id: String(r.add_player?.player_id || ''),
                        __drop_id: String(r.drop_player?.player_id || ''),
                      }));
                      const keyByNames = (a,d) => `${norm(a||'')}|${norm(d||'')}`;
                      const idsByPair = new Map();
                      for (const r of detL) {
                        idsByPair.set(keyByNames(mkAddName(r), mkDropName(r)), {addId: r.__add_id, dropId: r.__drop_id});
                      }
                      const aiL = (aiMoves || []).map(r => {
                        const ids = idsByPair.get(keyByNames(mkAddName(r), mkDropName(r))) || {};
                        return { ...r, __source:'AI', __add_id: String(ids.addId || ''), __drop_id: String(ids.dropId || '') };
                      });
                      const raw = [...aiL, ...detL];
                      const filtered = raw.filter(r => {
                        const addName = mkAddName(r);
                        const addId = String(r.__add_id || '');
                        const b = Number(r.estimated_benefit || 0);
                        const selfAdd = (addId && yahooRosterIds.has(addId)) || (!!addName && yahooRosterNames.has(norm(addName)));
                        if (selfAdd) return false;
                        if (r.__source === 'AI' && hideNegativeAi && Number.isFinite(b) && b < 0) return false;
                        return (Number.isFinite(b) ? b >= minBenefit : true);
                      });
                      const seen = new Set();
                      const deduped = [];
                      for (const r of filtered) {
                        const addId = String(r.__add_id || '');
                        const dropId = String(r.__drop_id || '');
                        const k = (addId && dropId) ? `${addId}|${dropId}` : `${norm(mkAddName(r)||'')}|${norm(mkDropName(r)||'')}`;
                        if (seen.has(k)) continue;
                        seen.add(k);
                        deduped.push(r);
                      }
                      deduped.sort((a,b) => Number(b.estimated_benefit||0) - Number(a.estimated_benefit||0));
                      if (!deduped.length) return <span>No clear upgrades this week — small, balance‑only gains.</span>;
                      const first = deduped[0];
                      const addName = mkAddName(first);
                      const dropName = mkDropName(first);
                      return <span>Do this: Add {addName} • Drop {dropName} <span className={styles.chipMuted}>(merged AI + deterministic)</span></span>;
                    })()}
                  </div>
                )}
                <div className={styles.recommendationsList}>
                  {(() => {
                    const norm = (s) => (typeof s === 'string' ? s.trim().toLowerCase() : '');
                    const mkAddName = (r) => (typeof r.add === 'string' ? r.add : (r.add?.name || r.add_player?.name));
                    const mkDropName = (r) => (typeof r.drop === 'string' ? r.drop : (r.drop?.name || r.drop_player?.name));
                    const detL = (recommendations || []).map(r => ({
                      ...r,
                      __source:'Deterministic',
                      __add_id: String(r.add_player?.player_id || ''),
                      __drop_id: String(r.drop_player?.player_id || ''),
                    }));
                    const keyByNames = (a,d) => `${norm(a||'')}|${norm(d||'')}`;
                    const idsByPair = new Map();
                    for (const r of detL) {
                      idsByPair.set(keyByNames(mkAddName(r), mkDropName(r)), {addId: r.__add_id, dropId: r.__drop_id});
                    }
                    const aiL = (aiMoves || []).map(r => {
                      const ids = idsByPair.get(keyByNames(mkAddName(r), mkDropName(r))) || {};
                      return { ...r, __source:'AI', __add_id: String(ids.addId || ''), __drop_id: String(ids.dropId || '') };
                    });
                    const raw = [...aiL, ...detL];
                    const filtered = raw.filter(r => {
                      const addName = mkAddName(r);
                      const addId = String(r.__add_id || '');
                      const b = Number(r.estimated_benefit || 0);
                      const selfAdd = (addId && yahooRosterIds.has(addId)) || (!!addName && yahooRosterNames.has(norm(addName)));
                      if (selfAdd) return false;
                      if (r.__source === 'AI' && hideNegativeAi && Number.isFinite(b) && b < 0) return false;
                      return (Number.isFinite(b) ? b >= minBenefit : true);
                    });
                    const counts = filtered.reduce((acc, r) => { acc[r.__source] = (acc[r.__source]||0)+1; return acc; }, {});
                    const hiddenCount = raw.length - filtered.length;
                    // Ensure at least one AI option is visible when available (pin top AI move)
                    const aiOnly = filtered.filter(r => r.__source === 'AI').sort((a,b) => Number(b.estimated_benefit||0) - Number(a.estimated_benefit||0));
                    const rest = filtered.filter(r => r.__source !== 'AI').sort((a,b) => Number(b.estimated_benefit||0) - Number(a.estimated_benefit||0));
                    const cap = 10;
                    const pinned = aiOnly.length ? [aiOnly[0]] : [];
                    // Merge pinned AI with the rest, highest benefit first, avoiding duplicates
                    const seen = new Set(pinned.map(r => {
                      const addId = String(r.__add_id || '');
                      const dropId = String(r.__drop_id || '');
                      return (addId && dropId) ? `${addId}|${dropId}` : `${norm(mkAddName(r)||'')}|${norm(mkDropName(r)||'')}`;
                    }));
                    const merged = [...pinned];
                    const sortedAll = [...aiOnly.slice(1), ...rest].sort((a,b) => Number(b.estimated_benefit||0) - Number(a.estimated_benefit||0));
                    for (const r of sortedAll) {
                      if (merged.length >= cap) break;
                      const addId = String(r.__add_id || '');
                      const dropId = String(r.__drop_id || '');
                      const k = (addId && dropId) ? `${addId}|${dropId}` : `${norm(mkAddName(r)||'')}|${norm(mkDropName(r)||'')}`;
                      if (seen.has(k)) continue;
                      seen.add(k);
                      merged.push(r);
                    }
                    const capped = merged;
                    const movesTop = capped.filter(r => Number(r.estimated_benefit || 0) >= 0);
                    const movesExplore = capped.filter(r => {
                      const b = Number(r.estimated_benefit || 0);
                      return Number.isFinite(b) && b < 0 && b >= (minBenefit ?? 0);
                    }).slice(0, 5);
                    return (
                      <>
                        {(counts['AI'] || counts['Deterministic']) && (
                          <div className={styles.chipMuted} style={{ marginBottom: 8 }}>
                            Showing {(counts['AI']||0)} AI + {(counts['Deterministic']||0)} deterministic options (sorted by benefit)
                          </div>
                        )}
                        {hiddenCount > 0 && (
                          <div className={styles.chipMuted} style={{ marginBottom: 8 }}>
                            {hiddenCount} move{hiddenCount>1?'s':''} hidden (already on your roster)
                          </div>
                        )}
                        {movesTop.map((rec, idx) => (
                          <div key={idx} className={styles.recCard}>
                            <div className={styles.recHeader}>
                              <div className={styles.recTitle}>Add {typeof rec.add === 'string' ? rec.add : (rec.add?.name || rec.add_player?.name)} • Drop {typeof rec.drop === 'string' ? rec.drop : (rec.drop?.name || rec.drop_player?.name)}</div>
                              <div className={styles.headerRight}>
                                <span className={`${styles.confidence} ${styles['conf_'+getConfidence(rec).toLowerCase()]}`}>{getConfidence(rec)}</span>
                                {(() => { const b=Number(rec.estimated_benefit||0); const cls=b>0?styles.benefitBadgePos:(b<0?styles.benefitBadgeNeg:styles.benefitBadgeZero); const s=b>0?'+':(b<0?'−':'±'); return (<span className={`${styles.benefitBadge} ${cls}`}>{s}{Math.abs(b).toFixed(2)}</span>); })()}
                                <span className={styles.sourceChip}>{rec.__source || (aiMoves.length ? 'AI' : 'Deterministic')}</span>
                              </div>
                            </div>
                            <div className={styles.recBody}>
                        <div className={styles.recRow}>
                          <div>
                            <div className={styles.recLabel}>Add</div>
                            <div className={styles.playerLine}>
                              <a href={`/?tool=dossier&player=${encodeURIComponent((typeof rec.add === 'string' ? rec.add : (rec.add?.name || rec.add_player?.name)) || '')}`} target="_blank" rel="noopener noreferrer" className={styles.playerLink}>
                                {typeof rec.add === 'string' ? rec.add : (rec.add?.name || rec.add_player?.name)}
                              </a>
                              {(rec.add?.position || rec.add_player?.position || rec.add?.team || rec.add_player?.team) && (
                                <>
                                  {` (`}
                                  {rec.add?.position || rec.add_player?.position || 'Pos?'}
                                  {`, `}
                                  {rec.add?.team || rec.add_player?.team || 'Team?'}
                                  {`)`}
                                </>
                              )}
                            </div>
                          </div>
                          <div>
                            <div className={styles.recLabel}>Drop</div>
                            <div className={styles.playerLine}>
                              <a href={`/?tool=dossier&player=${encodeURIComponent((typeof rec.drop === 'string' ? rec.drop : (rec.drop?.name || rec.drop_player?.name)) || '')}`} target="_blank" rel="noopener noreferrer" className={styles.playerLink}>
                                {typeof rec.drop === 'string' ? rec.drop : (rec.drop?.name || rec.drop_player?.name)}
                              </a>
                              {(rec.drop?.position || rec.drop_player?.position || rec.drop?.team || rec.drop_player?.team) && (
                                <>
                                  {` (`}
                                  {rec.drop?.position || rec.drop_player?.position || 'Pos?'}
                                  {`, `}
                                  {rec.drop?.team || rec.drop_player?.team || 'Team?'}
                                  {`)`}
                                </>
                              )}
                            </div>
                          </div>
                        </div>
                        {Array.isArray(rec.badges) && rec.badges.length > 0 && (
                          <div className={styles.badgesRow}>
                            {rec.badges.slice(0,3).map((b, i) => (
                              <span key={i} className={styles.badge}>{b}</span>
                            ))}
                          </div>
                        )}
                        <div className={styles.whyBox}>
                            {Array.isArray(rec.rationale_bullets) && rec.rationale_bullets.length > 0 ? (
                              <ul>
                                {rec.rationale_bullets.slice(0,4).map((t, i) => <li key={i}>{t}</li>)}
                              </ul>
                            ) : (
                              <ul>
                                {Array.isArray(rec.badges) && rec.badges.slice(0,3).map((b, i) => {
                                  const reason = badgeToReason(b);
                                  return reason ? <li key={i}>{reason}</li> : null;
                                })}
                                {!rec.badges?.length && <li>Small improvement this week based on roster balance.</li>}
                              </ul>
                            )}
                            <details className={styles.detailsBox}>
                              <summary>Show details</summary>
                             <div className={styles.detailsGrid}>
                                <span>Estimated Benefit</span><span>+{(rec.estimated_benefit ?? 0).toFixed(2)} <em className={styles.helpText}>(overall roster score gain)</em></span>
                                {recMeta && <>
                                  <span>Baseline Overall</span><span>{recMeta.baseline_overall}</span>
                                  <span>Source</span><span>{rec.__source || (aiMoves.length ? 'AI' : 'Deterministic')}</span>
                                </>}
                              </div>
                            </details>
                        </div>
                      </div>
                      {rec.claim_only && <div className={styles.claimOnly}>Claim only (on waivers)</div>}
                    </div>
                        ))}
                        {movesExplore.length > 0 && (
                          <div className={styles.chipMuted} style={{ marginTop: 16, marginBottom: 8 }}>
                            Explore options — small or lateral moves to improve balance/depth
                          </div>
                        )}
                        {movesExplore.map((rec, idx) => (
                          <div key={`x-${idx}`} className={styles.recCard}>
                            <div className={styles.recHeader}>
                              <div className={styles.recTitle}>Add {typeof rec.add === 'string' ? rec.add : (rec.add?.name || rec.add_player?.name)} • Drop {typeof rec.drop === 'string' ? rec.drop : (rec.drop?.name || rec.drop_player?.name)}</div>
                              <div className={styles.headerRight}>
                                <span className={`${styles.confidence} ${styles['conf_'+getConfidence(rec).toLowerCase()]}`}>{getConfidence(rec)}</span>
                                {(() => { const b=Number(rec.estimated_benefit||0); const cls=b>0?styles.benefitBadgePos:(b<0?styles.benefitBadgeNeg:styles.benefitBadgeZero); const s=b>0?'+':(b<0?'−':'±'); return (<span className={`${styles.benefitBadge} ${cls}`}>{s}{Math.abs(b).toFixed(2)}</span>); })()}
                                <span className={styles.sourceChip}>{rec.__source || (aiMoves.length ? 'AI' : 'Deterministic')}</span>
                              </div>
                            </div>
                            <div className={styles.recBody}>
                              <div className={styles.recRow}>
                                <div>
                                  <div className={styles.recLabel}>Add</div>
                                  <div className={styles.playerLine}>
                                    <a href={`/?tool=dossier&player=${encodeURIComponent((typeof rec.add === 'string' ? rec.add : (rec.add?.name || rec.add_player?.name)) || '')}`} target="_blank" rel="noopener noreferrer" className={styles.playerLink}>
                                      {typeof rec.add === 'string' ? rec.add : (rec.add?.name || rec.add_player?.name)}
                                    </a>
                                    {(rec.add?.position || rec.add_player?.position || rec.add?.team || rec.add_player?.team) && (
                                      <>
                                        {` (`}
                                        {rec.add?.position || rec.add_player?.position || 'Pos?'}
                                        {`, `}
                                        {rec.add?.team || rec.add_player?.team || 'Team?'}
                                        {`)`}
                                      </>
                                    )}
                                  </div>
                                </div>
                                <div>
                                  <div className={styles.recLabel}>Drop</div>
                                  <div className={styles.playerLine}>
                                    <a href={`/?tool=dossier&player=${encodeURIComponent((typeof rec.drop === 'string' ? rec.drop : (rec.drop?.name || rec.drop_player?.name)) || '')}`} target="_blank" rel="noopener noreferrer" className={styles.playerLink}>
                                      {typeof rec.drop === 'string' ? rec.drop : (rec.drop?.name || rec.drop_player?.name)}
                                    </a>
                                    {(rec.drop?.position || rec.drop_player?.position || rec.drop?.team || rec.drop_player?.team) && (
                                      <>
                                        {` (`}
                                        {rec.drop?.position || rec.drop_player?.position || 'Pos?'}
                                        {`, `}
                                        {rec.drop?.team || rec.drop_player?.team || 'Team?'}
                                        {`)`}
                                      </>
                                    )}
                                  </div>
                                </div>
                              </div>
                              <div className={styles.whyBox}>
                                {Array.isArray(rec.rationale_bullets) && rec.rationale_bullets.length > 0 ? (
                                  <ul>
                                    {rec.rationale_bullets.slice(0,4).map((t, i) => <li key={i}>{t}</li>)}
                                  </ul>
                                ) : (
                                  <ul>
                                    {Array.isArray(rec.badges) && rec.badges.slice(0,3).map((b, i) => {
                                      const reason = badgeToReason(b);
                                      return reason ? <li key={i}>{reason}</li> : null;
                                    })}
                                    {!rec.badges?.length && <li>Small improvement this week based on roster balance.</li>}
                                  </ul>
                                )}
                                <details className={styles.detailsBox}>
                                  <summary>Show details</summary>
                                  <div className={styles.detailsGrid}>
                                    <span>Estimated Benefit</span><span>+{(rec.estimated_benefit ?? 0).toFixed(2)} <em className={styles.helpText}>(overall roster score gain)</em></span>
                                    {recMeta && <>
                                      <span>Baseline Overall</span><span>{recMeta.baseline_overall}</span>
                                      <span>Source</span><span>{rec.__source || (aiMoves.length ? 'AI' : 'Deterministic')}</span>
                                    </>}
                                  </div>
                                </details>
                              </div>
                              {rec.claim_only && <div className={styles.claimOnly}>Claim only (on waivers)</div>}
                            </div>
                          </div>
                        ))}
                      </>
                    );
                  })()}
                  {!recommendations.length && !isLoadingYahooData && (
                    <div className={styles.emptyState}>
                      No clear upgrades found. Open Filters and enable “Include near‑neutral moves” to see small depth/balance improvements. 
                      Try adjusting Status (A/FA/W) if needed.
                    </div>
                  )}
                </div>

                {showPool && (
                  <>
                    <div className={styles.divider} />
                    <h3>Available Players</h3>
                    <p>Top available players in {userLeagues.find(l => l.league_key === selectedLeague)?.league_name}</p>
                    <div className={styles.availablePlayersGrid}>
                      {yahooAvailablePlayers.slice(0, 20).map((player) => (
                        <div key={player.player_key} className={styles.availablePlayerCard}>
                          <div className={styles.playerName}>{player.name}</div>
                          <div className={styles.playerMeta}>
                            {(player.position || player.primary_position)} - {player.team}
                            {player.ecr_overall && <span className={styles.ecrBadge}>ECR: {player.ecr_overall}</span>}
                          </div>
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </>
            ) : (
              <>
                <h3>Player to Consider Adding</h3>
                <div className={styles.formGroupInline}>
                    <div className={styles.autoCompleteWrapper}>
                        <input 
                          id="player-to-add" 
                          type="text" 
                          defaultValue={playerToAdd}
                          onChange={(e) => setPlayerToAdd(e.target.value)}
                          placeholder="Enter player to add..."
                        />
                    </div>
                    <button onClick={handleAnalyzeClick} className={styles.actionButton} disabled={isLoading}>
                    {isLoading ? 'Analyzing...' : 'Analyze Swap'}
                  </button>
                </div>
              </>
            )}
          </div>
          {isLoading && <div id="waiver-swap-loader" className={styles.loader} style={{ display: 'block' }}></div>}
          
          {analysisResult && (
            <div id="waiver-swap-result" className={styles.resultBox} dangerouslySetInnerHTML={{ __html: analysisResult }}></div>
          )}
        </div>
      </div>
    </section>
  );
};

export default WaiverWireAssistant;
