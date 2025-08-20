import React, { useEffect, useState, useCallback } from 'react';
import autoComplete from '@tarekraafat/autocomplete.js';
import styles from './WaiverWireAssistant.module.css';
import { useApi } from '../hooks/useApi';

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
  onAnalyzeYahoo = null, // Optional: New prop for Yahoo analysis
  onLeaguesUpdate = null, // Optional: New prop to pass leagues to parent
  analysisResult, 
  isLoading 
}) => {
  // API_BASE_URL is provided by useApi hook context
  const { get } = useApi();
  
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
  const [isLoadingYahooData, setIsLoadingYahooData] = useState(false);
  const [yahooError, setYahooError] = useState('');
  const [useYahooMode, setUseYahooMode] = useState(false);

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
      
      // Auto-select first league if only one available
      if (leagues.length === 1) {
        setSelectedLeague(leagues[0].league_key);
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

  // Handle league selection change
  const handleLeagueChange = async (event) => {
    const leagueKey = event.target.value;
    setSelectedLeague(leagueKey);
    
    if (leagueKey && useYahooMode) {
      await fetchAvailablePlayers(leagueKey);
    }
  };

  // Toggle Yahoo mode
  const toggleYahooMode = () => {
    setUseYahooMode(!useYahooMode);
    if (!useYahooMode && selectedLeague) {
      fetchAvailablePlayers(selectedLeague);
    }
  };

  const handleAnalyzeClick = () => {
    if (useYahooMode && selectedLeague) {
      // Yahoo mode: use league roster and available players
      if (!onAnalyzeYahoo) {
        console.error('Yahoo analysis handler not provided');
        alert('Yahoo analysis not available. Please contact support.');
        return;
      }
      
      const token = localStorage.getItem('yahoo_token');
      if (!token) {
        alert('Yahoo authentication required. Please log in with Yahoo.');
        return;
      }
      
      onAnalyzeYahoo(selectedLeague, token);
    } else {
      // Traditional mode: use manual roster input
      // First save any pending changes, then use saved roster data
      saveWaiverRoster();
      const currentRoster = loadWaiverRoster();
      
      // Filter out empty positions for cleaner API call
      const roster = {};
      Object.entries(currentRoster).forEach(([pos, playerName]) => {
        if (playerName && playerName.trim()) {
          roster[pos] = playerName.trim();
        }
      });
      
      onAnalyze(roster, playerToAdd);
    }
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
                <h3>Available Players in Your League</h3>
                <p>Based on your {userLeagues.find(l => l.league_key === selectedLeague)?.league_name} league</p>
                <div className={styles.availablePlayersGrid}>
                  {yahooAvailablePlayers.slice(0, 20).map((player) => (
                    <div key={player.player_key} className={styles.availablePlayerCard}>
                      <div className={styles.playerName}>{player.name}</div>
                      <div className={styles.playerMeta}>
                        {player.primary_position} - {player.team}
                        {player.ecr && <span className={styles.ecrBadge}>ECR: {player.ecr}</span>}
                      </div>
                    </div>
                  ))}
                </div>
                <button 
                  onClick={handleAnalyzeClick} 
                  className={styles.actionButton} 
                  disabled={isLoading || isLoadingYahooData}
                >
                  {isLoading ? 'Analyzing...' : 'Get Waiver Recommendations'}
                </button>
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
