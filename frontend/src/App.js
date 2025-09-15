import React, { useState, useEffect, useCallback, useMemo, useContext } from 'react';
import autoComplete from '@tarekraafat/autocomplete.js';
import './App.css';
import WaiverWireAssistant from './components/WaiverWireAssistant';
import PlayerDossier from './components/PlayerDossier';
import RookieRankings from './components/RookieRankings';
import PositionalTiers from './components/PositionalTiers';
import MarketInefficiencyFinder from './components/MarketInefficiencyFinder';
import TrendingPlayers from './components/TrendingPlayers';
import KeeperEvaluator from './components/KeeperEvaluator';
import TradeAnalyzer from './components/TradeAnalyzer'; // Import TradeAnalyzer
import DraftAssistant from './components/DraftAssistant'; // Import DraftAssistant
import TargetList from './components/TargetList'; // Import TargetList
import Settings from './components/Settings'; // Import Settings
import Documentation from './components/Documentation'; // Import Documentation
import SitStartOptimizer from './components/SitStartOptimizer';
import YahooLeagues from './components/YahooLeagues'; // Import YahooLeagues
import MyTeam from './components/MyTeam'; // Import MyTeam
import Sidebar from './components/Sidebar'; // Import Sidebar
import { AppContext } from './context/AppContext';
import { useApi } from './hooks/useApi';

// This is a meaningless change to trigger a Vercel deployment.
function App() {
  const {
    showApiKeyModal,
    saveApiKey,
    activeTool,
    setActiveTool,
    allPlayers,
    staticPlayerData,
    trendingData,
    setTrendingData,
    marketInefficiencies,
    setMarketInefficiencies,
    rookieRankings,
    setRookieRankings,
    dossierResult,
    setDossierResult,
    tiersResult,
    setTiersResult,
    keeperResult,
    setKeeperResult,
    waiverSwapResult,
    setWaiverSwapResult,
    isWaiverSwapLoading,
    setIsWaiverSwapLoading,
    lastUpdateDate,
    setLastUpdateDate,
    targetList,
    setTargetList,
    converter,
    API_BASE_URL,
    setShowApiKeyModal
  } = useContext(AppContext);

  const { makeApiRequest, get } = useApi();

  // Legacy navSections removed; sidebar now groups by season mode internally

  const [sortDirection, setSortDirection] = useState({ name: 'asc', position: 'asc', adds: 'desc', team: 'asc', ecr: 'asc' });
  const [keeperList, setKeeperList] = useState([]);
  const [keeperPlayerName, setKeeperPlayerName] = useState('');
  const [keeperRoundInput, setKeeperRoundInput] = useState('');
  const [keeperContextInput, setKeeperContextInput] = useState('');
  const [editingKeeperIndex, setEditingKeeperIndex] = useState(null);
  const [editRoundInput, setEditRoundInput] = useState('');
  const [editContextInput, setEditContextInput] = useState('');
  
  // Yahoo integration state
  const [userLeagues, setUserLeagues] = useState([]);

  /**
   * Determines the consensus label and icon for Rookie SD values.
   * @param {number} sdValue - The Standard Deviation value.
   * @returns {object} - An object containing the label and icon.
   */
  const getRookieSdLabel = useCallback((sdValue) => {
    if (typeof sdValue !== 'number' || isNaN(sdValue)) {
      return { label: 'N/A', icon: '' };
    }

    if (sdValue < 2.0) {
      return { label: 'High Consensus', icon: '✅' };
    } else if (sdValue >= 2.0 && sdValue < 6.0) {
      return { label: 'Moderate Consensus', icon: '🤔' };
    } else {
      return { label: 'Low Consensus', icon: '⚠️' };
    }
  }, []);

  /**
   * Determines the consensus label and icon for Overall ECR SD values.
   * @param {number} sdValue - The Standard Deviation value.
   * @returns {object} - An object containing the label and icon.
   */
  const getOverallSdLabel = useCallback((sdValue) => {
    if (typeof sdValue !== 'number' || isNaN(sdValue)) {
      return { label: 'N/A', icon: '' };
    }

    if (sdValue < 5.0) {
      return { label: 'High Consensus', icon: '✅' };
    } else if (sdValue >= 5.0 && sdValue < 20.0) {
      return { label: 'Moderate Consensus', icon: '🤔' };
    } else {
      return { label: 'Low Consensus', icon: '⚠️' };
    }
  }, []);

  /**
   * Determines the consensus label and icon for Positional ECR SD values.
   * @param {number} sdValue - The Standard Deviation value.
   * @returns {object} - An object containing the label and icon.
   */
  const getPositionalSdLabel = useCallback((sdValue) => {
    if (typeof sdValue !== 'number' || isNaN(sdValue)) {
      return { label: 'N/A', icon: '' };
    }

    if (sdValue < 2.0) {
      return { label: 'High Consensus', icon: '✅' };
    } else if (sdValue >= 2.0 && sdValue < 8.0) {
      return { label: 'Moderate Consensus', icon: '🤔' };
    } else {
      return { label: 'Low Consensus', icon: '⚠️' };
    }
  }, []);

  /**
   * Normalizes player names for consistent matching on the frontend.
   * Mirrors the backend's normalize_player_name function.
   * @param {string} name - The player name to normalize.
   * @returns {string} - The normalized player name.
   */
  const normalizePlayerName = useCallback((name) => {
    if (!name) return '';
    let normalized = name.replace(/\s(Jr|Sr|[IVX]+)\.?$/i, '').trim();
    normalized = normalized.replace(/[^a-zA-Z0-9\s]/g, '').trim();
    return normalized.toLowerCase();
  }, []);

  /**
   * Calculates the estimated draft round for a given ECR in a 12-team league.
   * @param {number} ecrValue - The Expert Consensus Ranking value.
   * @returns {string} - The estimated draft round (e.g., "Round 1") or "N/A".
   */
  const getEstimatedDraftRound = useCallback((ecrValue) => {
    if (typeof ecrValue !== 'number' || isNaN(ecrValue) || ecrValue <= 0) {
      return 'N/A';
    }
    const round = Math.ceil(ecrValue / 12);
    return `Rnd ${round}`;
  }, []);

  // Verify API_BASE_URL port
  useEffect(() => {
    try {
      const urlObj = new URL(API_BASE_URL);
      if (urlObj.port !== '5001') {
        // console.warn(`API_BASE_URL port is set to ${urlObj.port}, expected 5001.`);
      } else {
        // console.log(`API_BASE_URL port is correctly set to ${urlObj.port}.`);
      }
    } catch (e) {
      // console.error('Invalid API_BASE_URL:', API_BASE_URL);
    }
  }, [API_BASE_URL]);

  /**
   * Generic function to render results for tools that return simple markdown.
   * @param {string} toolName - The name of the tool (e.g., 'dossier').
   * @param {string} endpoint - The API endpoint.
   * @param {object} body - The request body.
   * @param {function} setResult - The state setter function for the result.
   */
  const renderGeneric = useCallback(async (toolName, endpoint, body, setResult) => {
    const loader = document.getElementById(`${toolName}-loader`);
    if (loader) loader.style.display = 'block';
    setResult(''); // Clear previous results

    try {
      const data = await makeApiRequest(endpoint, body);
      if (data && (data.result || data.analysis)) { // Accommodate new dossier structure
        setResult(data.result || data.analysis);
      } else {
        const errorMessage = toolName === 'dossier' ? null : '<p style="color: var(--text-muted);">The Analyst returned an empty response.</p>';
		setResult(errorMessage);
	  }
    } catch (error) {
      const errorMessage = toolName === 'dossier' ? { error: error.message } : `<p style="color: var(--danger-color);">An error occurred: ${error.message}</p>`;
      setResult(errorMessage);
    } finally {
      if (loader) loader.style.display = 'none';
    }
  }, [makeApiRequest, setDossierResult, setTiersResult, setKeeperResult, setWaiverSwapResult]);

  // --- Target List Management ---
  const handleAddToTargets = useCallback((playerName) => {
    if (!playerName) return;
    setTargetList(prevList => {
      if (prevList.find(p => p.toLowerCase() === playerName.toLowerCase())) {
        alert(`${playerName} is already on your target list.`);
        return prevList;
      }
      return [...prevList, playerName];
    });
  }, []);

  const handleRemoveFromTargets = useCallback((playerName) => {
    setTargetList(prevList => prevList.filter(p => p.toLowerCase() !== playerName.toLowerCase()));
  }, []);

  const generateDossier = useCallback((playerName) => {
    const nameToFetch = playerName || document.getElementById('dossier-player-name')?.value;
    if (!nameToFetch) { alert('Please enter a player name.'); return; }
    
    const loader = document.getElementById('dossier-loader');
    if (loader) loader.style.display = 'block';
    setDossierResult(null); // Clear previous results

    makeApiRequest('/player_dossier', { player_name: nameToFetch })
      .then(data => {
        if (data) {
          setDossierResult(data);
          // Record recent player for quick access in sidebar
          try {
            const key = 'recentDossierPlayers';
            const arr = JSON.parse(localStorage.getItem(key) || '[]');
            const nm = nameToFetch.trim();
            const next = [nm, ...arr.filter(x => x.toLowerCase() !== nm.toLowerCase())].slice(0,4);
            localStorage.setItem(key, JSON.stringify(next));
          } catch (_) {}
        } else {
          setDossierResult({ error: 'The Analyst returned an empty response.' });
        }
      })
      .catch(error => {
        setDossierResult({ error: error.message });
      })
      .finally(() => {
        if (loader) loader.style.display = 'none';
      });
  }, [makeApiRequest, setDossierResult]);

  const handleGlobalSearch = useCallback((playerName) => {
    setActiveTool('dossier');
    // Use a setTimeout to ensure the dossier section is rendered before trying to populate the input
    setTimeout(() => {
      const dossierInput = document.getElementById('dossier-player-name');
      if (dossierInput) {
        dossierInput.value = playerName;
        generateDossier(playerName);
      }
    }, 100); // A small delay (e.g., 100ms)
  }, [generateDossier]);

  const generateTiers = useCallback(async () => {
    const position = document.getElementById('tiers-pos')?.value;
    if (!position) { alert('Please select a position.'); return; }

    const loader = document.getElementById('tiers-loader');
    if (loader) loader.style.display = 'block';
    setTiersResult([]); // Clear previous results

    try {
      const data = await makeApiRequest('/generate_tiers', { position });
      if (data && data.result && Array.isArray(data.result)) {
        setTiersResult(data.result);
      } else {
        setTiersResult([]); // Set to empty array if no valid data
      }
    } catch (error) {
      console.error("Error generating tiers:", error);
      setTiersResult([]); // Set to empty array on error
    } finally {
      if (loader) loader.style.display = 'none';
    }
  }, [makeApiRequest, setTiersResult]);

  // Autocomplete for Global Search
  useEffect(() => {
    console.log('Initializing global search autocomplete. allPlayers length:', allPlayers.length);
    if (allPlayers.length === 0) return;
    const ac = new autoComplete({
        selector: '#global-player-search',
        placeHolder: "Quick Find Player...",
        data: { src: allPlayers, cache: true },
        resultItem: { highlight: true },
        events: {
            input: {
                selection: (event) => {
                    const selection = event.detail.selection.value;
                    handleGlobalSearch(selection);
                    ac.input.value = '';
                },
            },
        },
    });
    return () => {
      console.log('Uninitializing global search autocomplete.');
      ac.unInit();
    };
  }, [allPlayers, handleGlobalSearch]);

  // Autocomplete for Dossier
  useEffect(() => {
    console.log('Initializing dossier autocomplete. activeTool:', activeTool, 'allPlayers length:', allPlayers.length);
    if (activeTool !== 'dossier' || allPlayers.length === 0) return;
    const ac = new autoComplete({
        selector: '#dossier-player-name',
        placeHolder: "Enter player name...",
        data: { src: allPlayers, cache: true },
        resultItem: { highlight: true },
        events: {
            input: {
                selection: (event) => {
                    const selection = event.detail.selection.value;
                    document.getElementById('dossier-player-name').value = selection;
                },
            },
        },
    });
    return () => {
      console.log('Uninitializing dossier autocomplete.');
      ac.unInit();
    };
  }, [allPlayers, activeTool]);

  // Autocomplete for Draft Assistant
  useEffect(() => {
    console.log('Initializing draft autocomplete. activeTool:', activeTool, 'allPlayers length:', allPlayers.length);
    if (activeTool !== 'draft' || allPlayers.length === 0) return;
    const ac = new autoComplete({
        selector: '#draft-pick-player',
        placeHolder: "Player being considered...",
        data: { src: allPlayers, cache: true },
        resultItem: { highlight: true },
        events: {
            input: {
                selection: (event) => {
                    const selection = event.detail.selection.value;
                    document.getElementById('draft-pick-player').value = selection;
                },
            },
        },
    });
    return () => {
      console.log('Uninitializing draft autocomplete.');
      ac.unInit();
    };
  }, [allPlayers, activeTool]);

  // Autocomplete for Keeper Evaluator - Commented out to avoid conflict with react-autosuggest in KeeperEvaluator.js
  /*
  useEffect(() => {
    console.log('Initializing keeper autocomplete. activeTool:', activeTool, 'allPlayers length:', allPlayers.length);
    if (activeTool !== 'keeper' || allPlayers.length === 0) return;
    const ac = new autoComplete({
        selector: '#keeper-player-name',
        placeHolder: "Player Name...",
        data: { src: allPlayers, cache: true },
        resultItem: { highlight: true },
        events: {
            input: {
                selection: (event) => {
                    const selection = event.detail.selection.value;
                    setKeeperPlayerName(selection);
                },
            },
        },
    });
    return () => {
      console.log('Uninitializing keeper autocomplete.');
      ac.unInit();
    };
  }, [allPlayers, activeTool]);
  */

  const findMarketInefficiencies = useCallback(async () => {
    const loader = document.getElementById('market-loader');
    if (loader) loader.style.display = 'block';
    setMarketInefficiencies({ sleepers: [], busts: [] });
    try {
      const data = await makeApiRequest('/find_market_inefficiencies', { position: document.getElementById('market-pos').value });
      if (data) {
        setMarketInefficiencies(data);
      }
    } catch (error) {
      console.error(error);
    } finally {
      if (loader) loader.style.display = 'none';
    }
  }, [makeApiRequest, setMarketInefficiencies]);

  // Helper function to get player data from static sources
  const getPlayerDataFromStatic = useCallback((playerName) => {
    try {
      // Use existing staticPlayerData or search functions
      const normalizedName = playerName.toLowerCase();
      const foundPlayer = Object.keys(staticPlayerData).find(key => 
        key.toLowerCase().includes(normalizedName) || 
        normalizedName.includes(key.toLowerCase())
      );
      
      if (foundPlayer) {
        const data = staticPlayerData[foundPlayer];
        return {
          ecr: data.ecr,
          sd: data.sd,
          best: data.best,
          worst: data.worst,
          rank_delta: data.rank_delta,
          is_rookie: data.is_rookie || false,
          position: data.position,
          team: data.team
        };
      }
      
      return {};
    } catch (error) {
      console.error('Error getting static player data:', error);
      return {};
    }
  }, [staticPlayerData]);

  // Add helper function to parse AI response
  const parseMarketInefficiencyResponse = useCallback((aiResponse) => {
    try {
      // The AI response should be markdown text containing structured analysis
      // Parse for sleepers and busts sections
      const sleepers = [];
      const busts = [];
      
      // Split response into sections
      const sections = aiResponse.split(/#{1,3}\s*(sleepers?|busts?|undervalued|overvalued)/i);
      
      for (let i = 1; i < sections.length; i += 2) {
        const sectionType = sections[i].toLowerCase();
        const sectionContent = sections[i + 1] || '';
        
        // Parse player entries from section content
        const playerMatches = sectionContent.match(/\*\*([^*]+)\*\*[^:]*:([^]*?)(?=\*\*|\n\n|$)/g);
        
        if (playerMatches) {
          const players = playerMatches.map(match => {
            const nameMatch = match.match(/\*\*([^*]+)\*\*/);
            const justificationMatch = match.match(/:\s*([^]*?)(?=\*\*|\n\n|$)/);
            
            const name = nameMatch ? nameMatch[1].trim() : '';
            const justification = justificationMatch ? justificationMatch[1].trim() : '';
            
            // Extract player data from existing static data if available
            const playerData = getPlayerDataFromStatic(name);
            
            return {
              name: name,
              justification: justification,
              confidence: 'medium', // Default confidence
              ...playerData
            };
          });
          
          if (sectionType.includes('sleeper') || sectionType.includes('undervalued')) {
            sleepers.push(...players);
          } else if (sectionType.includes('bust') || sectionType.includes('overvalued')) {
            busts.push(...players);
          }
        }
      }
      
      return { sleepers, busts };
      
    } catch (error) {
      console.error('Error parsing market inefficiency response:', error);
      return { 
        sleepers: [], 
        busts: [],
        error: 'Unable to parse analysis results.' 
      };
    }
  }, [getPlayerDataFromStatic]);

  // Yahoo market inefficiency analysis handler
  const handleYahooMarketInefficiencies = useCallback(async (leagueKey, position, token) => {
    const loader = document.getElementById('market-loader');
    if (loader) loader.style.display = 'block';
    setMarketInefficiencies({ sleepers: [], busts: [] });
    
    try {
      // Parse token object and extract access_token
      const tokenObject = JSON.parse(token);
      const authHeader = `Bearer ${tokenObject.access_token}`;
      
      // First, fetch comprehensive league context
      const leagueContext = await get(`/yahoo/league_context?league_key=${leagueKey}`, {
        headers: {
          'Authorization': authHeader
        }
      });
      // Also fetch available player pools separately to classify FA vs Waivers
      const [poolFA, poolW] = await Promise.all([
        get(`/yahoo/waiver_pool?league_key=${leagueKey}&status=FA`, { headers: { 'Authorization': authHeader } }),
        get(`/yahoo/waiver_pool?league_key=${leagueKey}&status=W`, { headers: { 'Authorization': authHeader } })
      ]);
      const availablePlayers = [
        ...((poolFA && poolFA.available_players) ? poolFA.available_players.map(p => ({ ...p, availability_type: 'FA' })) : []),
        ...((poolW && poolW.available_players) ? poolW.available_players.map(p => ({ ...p, availability_type: 'W' })) : []),
      ];

      // Call enhanced Yahoo league inefficiency analysis endpoint
      const analysisData = await makeApiRequest('/yahoo/league_inefficiencies', {
        league_key: leagueKey,
        team_key: getTeamKeyForLeague(leagueKey) || undefined,
        position: position,
        league_context: leagueContext,
        available_players: availablePlayers,
        // Provide bearer in body so backend can fetch roster if needed
        auth_bearer: tokenObject.access_token
      });
      
      // Build quick availability lookup by normalized name
      const normalize = (s) => (s || '').toLowerCase().replace(/\s+(jr|sr|iii|iv|v)\.?$/i,'').replace(/[^a-z0-9 ]/gi,'').trim();
      const availMap = new Map();
      for (const p of availablePlayers) {
        availMap.set(normalize(p.name), { availability_type: p.availability_type, waiver_deadline: p.waiver_deadline || null });
      }

      if (analysisData && (analysisData.sleepers || analysisData.busts)) {
        // Prefer structured JSON if provided by backend
        const enrich = (arr) => (arr || []).map(p => {
          const meta = availMap.get(normalize(p.name)) || {};
          return { ...p, availability_type: meta.availability_type, waiver_deadline: meta.waiver_deadline };
        });
        setMarketInefficiencies({
          sleepers: enrich(analysisData.sleepers),
          busts: enrich(analysisData.busts),
          source: analysisData.fallback === 'general' ? 'general' : 'league'
        });
      } else if (analysisData && analysisData.result) {
        // Fallback: parse markdown result
        const parsedResults = parseMarketInefficiencyResponse(analysisData.result);
        const enrich = (arr) => (arr || []).map(p => {
          const meta = availMap.get(normalize(p.name)) || {};
          return { ...p, availability_type: meta.availability_type, waiver_deadline: meta.waiver_deadline };
        });
        setMarketInefficiencies({ sleepers: enrich(parsedResults.sleepers), busts: enrich(parsedResults.busts), source: 'league-markdown' });
      } else {
        setMarketInefficiencies({ 
          sleepers: [], 
          busts: [],
          error: 'The Analyst returned an empty response.' 
        });
      }
    } catch (error) {
      console.error('Yahoo market inefficiency analysis failed:', error);
      // Handle 401 token expiration following existing patterns
      if (error.response && error.response.status === 401) {
        setMarketInefficiencies({ 
          sleepers: [], 
          busts: [],
          error: 'Yahoo authentication expired. Please re-authenticate with Yahoo.' 
        });
        localStorage.removeItem('yahoo_token');
      } else {
        setMarketInefficiencies({ 
          sleepers: [], 
          busts: [],
          error: `Analysis failed: ${error.message}` 
        });
      }
    } finally {
      if (loader) loader.style.display = 'none';
    }
  }, [get, makeApiRequest, setMarketInefficiencies, parseMarketInefficiencyResponse]);

  const generateRookieRankings = useCallback(async () => {
    const loader = document.getElementById('rookie-loader');
    if (loader) loader.style.display = 'block';
    setRookieRankings([]);
    try {
      const rookies = await makeApiRequest('/rookie_rankings', { position: document.getElementById('rookie-pos').value });
      if (rookies) {
        setRookieRankings(rookies);
      }
    } catch (error) {
      console.error(error);
    } finally {
      if (loader) loader.style.display = 'none';
    }
  }, [makeApiRequest, setRookieRankings]);

  const evaluateKeepers = useCallback(() => {
    if (keeperList.length === 0) { alert('Please add at least one keeper.'); return; }
    renderGeneric('keeper', '/keeper_evaluation', { keepers: keeperList }, setKeeperResult);
  }, [renderGeneric, keeperList]);


  const addKeeper = () => {
    const roundValue = parseInt(keeperRoundInput, 10);
    if (keeperPlayerName && !isNaN(roundValue) && roundValue > 0) {
      setKeeperList(prevList => [...prevList, { name: keeperPlayerName, round: roundValue, context: keeperContextInput }]);
      setKeeperPlayerName('');
      setKeeperRoundInput('');
      setKeeperContextInput('');
      document.getElementById('keeper-player-name')?.focus();
    } else {
      alert('Please enter a valid player name and a positive number for the draft round.');
    }
  };

  const startEditingKeeper = (index) => {
    setEditingKeeperIndex(index);
    setEditRoundInput(keeperList[index].round.toString());
    setEditContextInput(keeperList[index].context || '');
  };

  const saveEditedKeeper = () => {
    const roundValue = parseInt(editRoundInput, 10);
    if (!isNaN(roundValue) && roundValue > 0) {
      setKeeperList(prevList => {
        const updatedList = [...prevList];
        updatedList[editingKeeperIndex] = { ...updatedList[editingKeeperIndex], round: roundValue, context: editContextInput };
        return updatedList;
      });
      setEditingKeeperIndex(null);
      setEditRoundInput('');
      setEditContextInput('');
    } else {
      alert('Please enter a valid positive number for the draft round.');
    }
  };

  const cancelEditingKeeper = () => {
    setEditingKeeperIndex(null);
    setEditRoundInput('');
    setEditContextInput('');
  };

  const fetchTrending = useCallback(async () => {
    const loader = document.getElementById('trending-loader');
    if(loader) loader.style.display = 'block';
    try {
        const response = await fetch(`${API_BASE_URL}/trending_players`);
        if (!response.ok) throw new Error('Network response was not ok.');
        const data = await response.json();
        setTrendingData(data);
    } catch (error) {
        console.error("Could not fetch trending data", error);
    } finally {
        if(loader) loader.style.display = 'none';
    }
  }, []);

  const handleWaiverSwapAnalysis = useCallback(async (roster, playerToAdd) => {
    if (Object.keys(roster).length === 0 || !playerToAdd) {
      alert('Please fill out your roster and specify a player to add.');
      return;
    }
    setIsWaiverSwapLoading(true);
    setWaiverSwapResult('');
    try {
      const data = await makeApiRequest('/waiver_swap_analysis', { roster, player_to_add: playerToAdd });
      if (data && data.result) {
        setWaiverSwapResult(converter.makeHtml(data.result));
      } else {
        setWaiverSwapResult('<p style="color: var(--text-muted);">The Analyst returned an empty response.</p>');
      }
    } catch (error) {
      setWaiverSwapResult(`<p style="color: var(--danger-color);">An error occurred: ${error.message}</p>`);
    } finally {
      setIsWaiverSwapLoading(false);
    }
  }, [makeApiRequest, converter, setWaiverSwapResult, setIsWaiverSwapLoading]);

  // Enhanced waiver swap analysis with complete roster data including empty positions  
  const handleWaiverSwapAnalysisEnhanced = useCallback(async (rosterData, playerToAdd, filledPositions) => {
    // Validate input data
    if (!rosterData || (!rosterData.filled_positions && !filledPositions) || !playerToAdd) {
      alert('Please fill out your roster and specify a player to add.');
      return;
    }
    
    setIsWaiverSwapLoading(true);
    setWaiverSwapResult('');
    
    try {
      console.log('Enhanced Analysis - Roster Data:', {
        filled: Object.keys(rosterData.filled_positions || filledPositions).length,
        empty: rosterData.empty_positions?.length || 0,
        total: rosterData.total_roster_spots || 0
      });
      
      // Try enhanced endpoint first
      const enhancedData = await makeApiRequest('/waiver_swap_analysis_enhanced', {
        roster_data: rosterData,
        player_to_add: playerToAdd
      });
      
      if (enhancedData && enhancedData.result) {
        // Enhanced response may include additional data
        let resultHtml = converter.makeHtml(enhancedData.result);
        
        // Add enhanced features indicators if available
        if (enhancedData.enhanced) {
          resultHtml += '<div style="margin-top: 15px; padding: 10px; background: var(--success-bg); border-radius: 8px; border-left: 4px solid var(--success-color);"><strong>✨ Enhanced Analysis:</strong> Complete roster analysis including bench depth and drop recommendations.</div>';
        }
        
        setWaiverSwapResult(resultHtml);
      } else {
        setWaiverSwapResult('<p style="color: var(--text-muted);">The Enhanced Analyst returned an empty response.</p>');
      }
      
    } catch (error) {
      console.warn('Enhanced analysis failed, trying fallback:', error);
      
      // Fallback to traditional analysis
      try {
        const fallbackData = await makeApiRequest('/waiver_swap_analysis', { 
          roster: filledPositions || rosterData.filled_positions, 
          player_to_add: playerToAdd 
        });
        
        if (fallbackData && fallbackData.result) {
          let resultHtml = converter.makeHtml(fallbackData.result);
          resultHtml += '<div style="margin-top: 15px; padding: 10px; background: var(--warning-bg); border-radius: 8px; border-left: 4px solid var(--warning-color);"><strong>⚠️ Fallback Analysis:</strong> Enhanced analysis unavailable, using traditional analysis.</div>';
          setWaiverSwapResult(resultHtml);
        } else {
          setWaiverSwapResult('<p style="color: var(--text-muted);">Both enhanced and traditional analysis returned empty responses.</p>');
        }
        
      } catch (fallbackError) {
        console.error('Both enhanced and fallback analysis failed:', fallbackError);
        setWaiverSwapResult(`<p style="color: var(--danger-color);">Analysis failed: ${error.message}</p>`);
      }
    } finally {
      setIsWaiverSwapLoading(false);
    }
  }, [makeApiRequest, converter, setWaiverSwapResult, setIsWaiverSwapLoading]);

  // Helper function to get team key from leagues data
  const getTeamKeyForLeague = useCallback((leagueKey) => {
    const league = userLeagues.find(l => l.league_key === leagueKey);
    return league ? league.team_key : null;
  }, [userLeagues]);

  // Yahoo waiver wire analysis handler
  const handleYahooWaiverAnalysis = useCallback(async (leagueKey, yahooToken) => {
    if (!leagueKey || !yahooToken) {
      alert('Yahoo league data is required for analysis.');
      return;
    }

    setIsWaiverSwapLoading(true);
    setWaiverSwapResult('');

    try {
      // Parse token object and extract access_token
      const tokenObject = JSON.parse(yahooToken);
      const authHeader = `Bearer ${tokenObject.access_token}`;
      
      // Get team key for the selected league
      const teamKey = getTeamKeyForLeague(leagueKey);
      if (!teamKey) {
        throw new Error('Unable to find team information for selected league.');
      }

      // Fetch roster data
      const rosterResponse = await fetch(`${API_BASE_URL}/yahoo/roster?team_key=${teamKey}`, {
        headers: {
          'Authorization': authHeader,
          'Content-Type': 'application/json'
        }
      });

      if (!rosterResponse.ok) {
        throw new Error(`Failed to fetch roster: ${rosterResponse.status}`);
      }

      const rosterData = await rosterResponse.json();

      // Fetch available players data
      const waiverResponse = await fetch(`${API_BASE_URL}/yahoo/waiver_wire?league_key=${leagueKey}&status=A`, {
        headers: {
          'Authorization': authHeader,
          'Content-Type': 'application/json'
        }
      });

      if (!waiverResponse.ok) {
        throw new Error(`Failed to fetch waiver wire: ${waiverResponse.status}`);
      }

      const waiverData = await waiverResponse.json();

      // Call the Yahoo waiver analysis endpoint
      const analysisData = {
        league_key: leagueKey,
        roster: rosterData.roster || [],
        available_players: waiverData.available_players || []
      };

      const data = await makeApiRequest('/yahoo_waiver_analysis', analysisData);
      if (data && data.result) {
        setWaiverSwapResult(converter.makeHtml(data.result));
      } else {
        setWaiverSwapResult('<p style="color: var(--text-muted);">The Analyst returned an empty response.</p>');
      }

    } catch (error) {
      console.error('Yahoo waiver analysis error:', error);
      
      // Handle specific error cases
      if (error.message.includes('401') || error.message.includes('authentication')) {
        setWaiverSwapResult('<p style="color: var(--danger-color);">Yahoo authentication expired. Please re-authenticate with Yahoo.</p>');
        // Remove expired token
        localStorage.removeItem('yahoo_token');
      } else {
        setWaiverSwapResult(`<p style="color: var(--danger-color);">An error occurred: ${error.message}</p>`);
      }
    } finally {
      setIsWaiverSwapLoading(false);
    }
  }, [makeApiRequest, setWaiverSwapResult, setIsWaiverSwapLoading, converter, API_BASE_URL, getTeamKeyForLeague]);

  // Handler for when leagues data is updated from WaiverWireAssistant
  const handleLeaguesUpdate = useCallback((leagues) => {
    setUserLeagues(leagues);
  }, []);

  // --- Effect Hooks for Initialization and Side Effects ---

  // Load target list from local storage on initial mount
  useEffect(() => {
    const savedTargets = localStorage.getItem('targetList');
    if (savedTargets) {
      setTargetList(JSON.parse(savedTargets));
    }
  }, [setTargetList]);

  // Save target list to local storage when it changes
  useEffect(() => {
    if (targetList.length > 0) {
      localStorage.setItem('targetList', JSON.stringify(targetList));
    } else {
      localStorage.removeItem('targetList'); // Clean up if list is empty
    }
  }, [targetList]);



  // Fetch trending data only when the trending tool is active
  useEffect(() => {
    if (activeTool === 'trending' && trendingData.length === 0) {
      fetchTrending();
    }
  }, [activeTool, trendingData.length, fetchTrending]);

  // Fetch last update date when settings tool is active
  useEffect(() => {
    if (activeTool === 'settings') {
      fetch(`${API_BASE_URL}/last_update_date`)
        .then(response => response.json())
        .then(data => {
          if (data && data.last_update) {
            setLastUpdateDate(data.last_update);
          } else {
            setLastUpdateDate('N/A');
          }
        })
        .catch(error => {
          console.error("Error fetching last update date:", error);
          setLastUpdateDate('Error loading date.');
        });
    }
  }, [activeTool]);

  // Handle URL parameters and hash changes for tool navigation
  useEffect(() => {
    const handleNavigation = () => {
      const hash = window.location.hash.substring(1).split('?')[0]; // Correctly parse hash
      const urlParams = new URLSearchParams(window.location.search);
      const toolFromParam = urlParams.get('tool');
      const playerFromParam = urlParams.get('player');

      if (hash) {
        setActiveTool(hash);
        // Clear search params when navigating via hash
        if (window.location.search) {
          window.history.replaceState({}, document.title, window.location.pathname + window.location.hash);
        }
      } else if (toolFromParam === 'dossier' && playerFromParam) {
        setActiveTool('dossier');
        const decodedPlayerName = decodeURIComponent(playerFromParam);
        const dossierInput = document.getElementById('dossier-player-name');
        if (dossierInput) {
          dossierInput.value = decodedPlayerName;
        }
        generateDossier(decodedPlayerName);
      } else { // Default to dossier if no hash or specific tool param
        setActiveTool('dossier');
      }
    };

    handleNavigation();
    window.addEventListener('hashchange', handleNavigation, false);
    
    // Also handle popstate for back/forward browser buttons
    window.addEventListener('popstate', handleNavigation, false);

    return () => {
      window.removeEventListener('hashchange', handleNavigation, false);
      window.removeEventListener('popstate', handleNavigation, false);
    };
  }, [generateDossier]); // generateDossier is a dependency

  // Note: Legacy navSections state and toggler were removed in a prior refactor.
  // Any references to setNavSections have been eliminated to avoid undefined usage.

  const resetApplication = () => {
    if (window.confirm("Are you sure you want to clear all saved data? This will remove your API key, saved draft board, and target list and cannot be undone.")) {
      localStorage.removeItem('geminiApiKey');
      localStorage.removeItem('draftBoard');
      localStorage.removeItem('targetList');
      localStorage.removeItem('theme');
      setTargetList([]);
      setShowApiKeyModal(true);
      document.documentElement.setAttribute('data-theme', 'dark');
      window.location.href = window.location.pathname; // Reload the page without hash/params
    }
  };

  const toggleTheme = () => {
    const currentTheme = document.body.getAttribute('data-theme') || 'dark';
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.body.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
  };

  useEffect(() => {
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.body.setAttribute('data-theme', savedTheme);
  }, []);

  const sortTrendingData = (key) => {
    const newDirection = sortDirection[key] === 'asc' ? 'desc' : 'asc';
    const sortedData = [...trendingData].sort((a, b) => {
      let valA = a[key];
      let valB = b[key];
  
      // Handle numeric sorting for 'adds' and 'pos_rank'
      if (key === 'adds') {
        valA = Number(valA);
        valB = Number(valB);
      } else if (key === 'pos_rank' && valA && valB) {
        valA = parseInt(valA.replace(/\D/g, ''), 10);
        valB = parseInt(valB.replace(/\D/g, ''), 10);
      }
  
      if (valA < valB) {
        return newDirection === 'asc' ? -1 : 1;
      }
      if (valA > valB) {
        return newDirection === 'asc' ? 1 : -1;
      }
      return 0;
    });
  
    setTrendingData(sortedData);
    setSortDirection({ ...sortDirection, [key]: newDirection });
  };

  // --- JSX ---
  return (
    <div className="app-container">
      {showApiKeyModal && (
        <div id="api-key-modal" className="api-key-modal" style={{ display: 'flex' }}>
          <div className="api-key-modal-content">
            <h2>Welcome to the RATM Draft Kit</h2>
            <p>To power the AI features, please enter your Google Gemini API key. This key is saved only in your browser.</p>
            <input type="password" id="api-key-input" placeholder="Paste your API key here" />
            <button onClick={() => saveApiKey(document.getElementById('api-key-input').value)}>Save Key & Start</button>
            <a href="https://aistudio.google.com/" target="_blank" rel="noopener noreferrer">Get Your Free API Key &rarr;</a>
          </div>
        </div>
      )}

      <Sidebar
        activeTool={activeTool}
        targetList={targetList}
      />

      <div className="main-content">
        <div className="content-wrapper">
          {activeTool === 'dossier' && (
            <PlayerDossier
              dossierResult={dossierResult}
              generateDossier={generateDossier}
              handleAddToTargets={handleAddToTargets}
              getEstimatedDraftRound={getEstimatedDraftRound}
              getOverallSdLabel={getOverallSdLabel}
              getPositionalSdLabel={getPositionalSdLabel}
              converter={converter}
            />
          )}

          {activeTool === 'rookie' && (
            <RookieRankings
              rookieRankings={rookieRankings}
              generateRookieRankings={generateRookieRankings}
              handleAddToTargets={handleAddToTargets}
              getRookieSdLabel={getRookieSdLabel}
            />
          )}

          {activeTool === 'tiers' && (
            <PositionalTiers
              tiersResult={tiersResult}
              generateTiers={generateTiers}
              handleAddToTargets={handleAddToTargets}
              getEstimatedDraftRound={getEstimatedDraftRound}
              getPositionalSdLabel={getPositionalSdLabel}
            />
          )}

          {activeTool === 'targets' && (
            <TargetList
              targetList={targetList}
              setTargetList={setTargetList}
              staticPlayerData={staticPlayerData}
              handleRemoveFromTargets={handleRemoveFromTargets}
              getOverallSdLabel={getOverallSdLabel}
              getPositionalSdLabel={getPositionalSdLabel}
            />
          )}

          {activeTool === 'market' && (
            <MarketInefficiencyFinder
              marketInefficiencies={marketInefficiencies}
              findMarketInefficiencies={findMarketInefficiencies}
              onFindYahooInefficiencies={handleYahooMarketInefficiencies}
              onLeaguesUpdate={setUserLeagues}
              handleAddToTargets={handleAddToTargets}
              getOverallSdLabel={getOverallSdLabel}
              isLoading={false}
            />
          )}

          {activeTool === 'keeper' && (
            <KeeperEvaluator
              keeperList={keeperList}
              setKeeperList={setKeeperList}
              staticPlayerData={staticPlayerData}
              normalizePlayerName={normalizePlayerName}
              getEstimatedDraftRound={getEstimatedDraftRound}
              evaluateKeepers={evaluateKeepers}
              keeperResult={keeperResult}
              converter={converter}
              isLoading={false}
              allPlayers={allPlayers}
            />
          )}
          
          {activeTool === 'trade' && (
            <TradeAnalyzer
              makeApiRequest={makeApiRequest}
              allPlayers={allPlayers}
              converter={converter}
            />
          )}

          {activeTool === 'draft' && (
            <DraftAssistant
              makeApiRequest={makeApiRequest}
              staticPlayerData={staticPlayerData}
              allPlayers={allPlayers}
              handleGlobalSearch={handleGlobalSearch}
              converter={converter}
              activeTool={activeTool}
              getOverallSdLabel={getOverallSdLabel}
              getPositionalSdLabel={getPositionalSdLabel}
              normalizePlayerName={normalizePlayerName}
            />
          )}

          {activeTool === 'trending' && (
            <TrendingPlayers
              trendingData={trendingData}
              sortTrendingData={sortTrendingData}
            />
          )}

          {activeTool === 'waiver' && (
            <WaiverWireAssistant
              allPlayers={allPlayers}
              onAnalyze={handleWaiverSwapAnalysis}
              onAnalyzeEnhanced={handleWaiverSwapAnalysisEnhanced}
              onAnalyzeYahoo={handleYahooWaiverAnalysis}
              onLeaguesUpdate={handleLeaguesUpdate}
              analysisResult={waiverSwapResult}
              isLoading={isWaiverSwapLoading}
            />
          )}

          {activeTool === 'lineup' && (
            <SitStartOptimizer />
          )}

          {activeTool === 'settings' && (
            <Settings
              lastUpdateDate={lastUpdateDate}
              toggleTheme={toggleTheme}
              resetApplication={resetApplication}
            />
          )}

          {activeTool === 'documentation' && (
            <Documentation />
          )}

          {activeTool === 'yahoo-leagues' && (
            <YahooLeagues />
          )}

          {activeTool === 'my-team' && (
            <MyTeam />
          )}

        </div>
      </div>
    </div>
  );
}


export default App;
