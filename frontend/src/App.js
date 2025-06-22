import React, { useState, useEffect, useCallback, useMemo } from 'react';
import showdown from 'showdown';
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

// The backend API URL. This can be changed to your production URL when you deploy.
const API_BASE_URL = 'http://localhost:5001/api';

function App() {
  // State for API Key and Modal
  const [userApiKey, setUserApiKey] = useState(() => localStorage.getItem('geminiApiKey') || '');
  const [showApiKeyModal, setShowApiKeyModal] = useState(() => !localStorage.getItem('geminiApiKey'));

  // State for navigation sections collapse/expand
  const [navSections, setNavSections] = useState({
    playerAnalysis: false,
    teamManagement: false,
  });

  // State for active tool and data
  const [activeTool, setActiveTool] = useState('dossier');
  const [allPlayers, setAllPlayers] = useState([]);
  const [staticPlayerData, setStaticPlayerData] = useState({}); // This will now hold combined data
  const [trendingData, setTrendingData] = useState([]);
  const [sortDirection, setSortDirection] = useState({ name: 'asc', position: 'asc', adds: 'desc', team: 'asc', ecr: 'asc' });
  const [marketInefficiencies, setMarketInefficiencies] = useState({ sleepers: [], busts: [] });
  const [rookieRankings, setRookieRankings] = useState([]);
  // Removed draftBoard state
  // Removed draftAnalysisResult state
  // Removed rosterCompositionResult state
  const [dossierResult, setDossierResult] = useState(null);
  const [tiersResult, setTiersResult] = useState([]);
  const [keeperResult, setKeeperResult] = useState('');
  const [waiverSwapResult, setWaiverSwapResult] = useState('');
  const [isWaiverSwapLoading, setIsWaiverSwapLoading] = useState(false);
  const [lastUpdateDate, setLastUpdateDate] = useState('Loading...');

  // States for list-based tools
  const [targetList, setTargetList] = useState([]);
  const [keeperList, setKeeperList] = useState([]);
  const [keeperPlayerName, setKeeperPlayerName] = useState('');
  const [keeperRoundInput, setKeeperRoundInput] = useState('');
  const [keeperContextInput, setKeeperContextInput] = useState('');
  const [editingKeeperIndex, setEditingKeeperIndex] = useState(null);
  const [editRoundInput, setEditRoundInput] = useState('');
  const [editContextInput, setEditContextInput] = useState('');
  const [ecrTypePreference, setEcrTypePreference] = useState('overall'); // New state for ECR type preference

  // Memoize the Showdown converter to avoid recreating it on every render
  const converter = useMemo(() => new showdown.Converter({ simplifiedAutoLink: true, tables: true, strikethrough: true }), []);

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

  /**
   * Saves the user's API key to state and local storage.
   * @param {string} key - The Google Gemini API key.
   */
  const saveApiKey = (key) => {
    if (key) {
      setUserApiKey(key);
      localStorage.setItem('geminiApiKey', key);
      setShowApiKeyModal(false);
    } else {
      alert('Please enter a valid API key.');
    }
  };

  /**
   * A centralized function for making API requests to the backend.
   * @param {string} endpoint - The API endpoint to call (e.g., '/player_dossier').
   * @param {object} body - The JSON body for the request.
   * @returns {Promise<object|null>} - The JSON response from the server or null on error.
   */
  const makeApiRequest = useCallback(async (endpoint, body) => {
    if (!userApiKey) {
      alert('API Key not found. Please enter your key.');
      setShowApiKeyModal(true);
      return null;
    }
    if (!endpoint || typeof endpoint !== 'string') {
      return null;
    }
    const url = `${API_BASE_URL}${endpoint}`;
    try {
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': userApiKey
        },
        body: JSON.stringify({ ...body, ecr_type_preference: ecrTypePreference }), // Include ECR type preference
      });
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || `An unknown server error occurred on endpoint: ${endpoint}`);
      }
      const data = await response.json();
      return data;
    } catch (error) {
      throw error; // Re-throw the error to be caught by the calling function
    }
  }, [userApiKey, ecrTypePreference]); // Add ecrTypePreference as a dependency

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
  }, []);

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
  }, [makeApiRequest]);

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

  const handleRemoveFromTargets = (playerName) => {
    setTargetList(prevList => prevList.filter(p => p.toLowerCase() !== playerName.toLowerCase()));
  };

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
  }, [makeApiRequest]);

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
  }, [makeApiRequest]);

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
  }, [makeApiRequest]);

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
  }, [makeApiRequest]);

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
  }, [makeApiRequest, converter]);

  // --- Effect Hooks for Initialization and Side Effects ---

  // Load target list from local storage on initial mount
  useEffect(() => {
    const savedTargets = localStorage.getItem('targetList');
    if (savedTargets) {
      setTargetList(JSON.parse(savedTargets));
    }
  }, []);

  // Save target list to local storage when it changes
  useEffect(() => {
    if (targetList.length > 0) {
      localStorage.setItem('targetList', JSON.stringify(targetList));
    } else {
      localStorage.removeItem('targetList'); // Clean up if list is empty
    }
  }, [targetList]);

  // Fetch all player names for autocomplete functionality and static player data
  useEffect(() => {
    fetch(`${API_BASE_URL}/all_player_names_with_data`)
      .then(response => response.json())
      .then(data => {
        if (data && Array.isArray(data)) {
          // Use display_name for the autocomplete list, fall back to name if display_name is not present
          // Use autocomplete_name for the autocomplete list
          setAllPlayers(data.map(p => p.autocomplete_name));
          // Store the full player data object, keyed by the normalized 'name' from the backend
          const staticData = data.reduce((acc, p) => {
            if (p.name) { // Ensure player name exists (this is the normalized name key)
              acc[p.name.toLowerCase()] = p;
            }
            return acc;
          }, {});
          setStaticPlayerData(staticData);
        }
      })
      .catch(error => console.error("Error fetching player names:", error));
  }, []);



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
      const hash = window.location.hash.substring(1);
      if (hash) {
        setActiveTool(hash);
        // Clear search params when navigating via hash
        if (window.location.search) {
          window.history.replaceState({}, document.title, window.location.pathname + window.location.hash);
        }
        return;
      }

      const urlParams = new URLSearchParams(window.location.search);
      const toolFromParam = urlParams.get('tool');
      const playerFromParam = urlParams.get('player');

      if (toolFromParam === 'dossier' && playerFromParam) {
        setActiveTool('dossier');
        const decodedPlayerName = decodeURIComponent(playerFromParam);
        // Set the input value immediately
        const dossierInput = document.getElementById('dossier-player-name');
        if (dossierInput) {
          dossierInput.value = decodedPlayerName;
        }
        // Then generate the dossier
        generateDossier(decodedPlayerName);
      } else {
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

  const toggleNavSection = (section) => {
    setNavSections(prevSections => ({
      ...prevSections,
      [section]: !prevSections[section]
    }));
  };

  const resetApplication = () => {
    if (window.confirm("Are you sure you want to clear all saved data? This will remove your API key, saved draft board, and target list and cannot be undone.")) {
      localStorage.removeItem('geminiApiKey');
      localStorage.removeItem('draftBoard');
      localStorage.removeItem('targetList');
      localStorage.removeItem('theme');
      setUserApiKey('');
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

      <div className="sidebar">
        <div className="sidebar-header">
          <a href="/" title="Start Over" className="sidebar-logo-link">
            <img src="/images/redd-logo.png" alt="Redd Against the Machine Logo" className="app-logo" />
          </a>
        </div>
        <div className="global-search-container">
          <div className="autoComplete_wrapper">
            <input id="global-player-search" type="text" placeholder="Quick Find Player..." />
          </div>
        </div>
        <div className="ecr-preference-selector">
            <label htmlFor="ecr-type-preference">ECR Type:</label>
            <select id="ecr-type-preference" value={ecrTypePreference} onChange={(e) => setEcrTypePreference(e.target.value)}>
              <option value="overall">Overall ECR</option>
              <option value="positional">Positional ECR</option>
            </select>
          </div>
        <nav className="sidebar-nav">
          <ul>
            <li><a href="#targets" className={activeTool === 'targets' ? 'active' : ''}>Target List <span className="badge">{targetList.length}</span></a></li>
          </ul>
          <div className="nav-section">
            <h3 onClick={() => toggleNavSection('playerAnalysis')}>
              Player Analysis <span className={navSections.playerAnalysis ? 'arrow down' : 'arrow right'}></span>
            </h3>
            {navSections.playerAnalysis && (
              <ul>
                <li><a href="#dossier" className={activeTool === 'dossier' ? 'active' : ''}>Player Dossier</a></li>
                <li><a href="#rookie" className={activeTool === 'rookie' ? 'active' : ''}>Rookie Rankings</a></li>
                <li><a href="#tiers" className={activeTool === 'tiers' ? 'active' : ''}>Positional Tiers</a></li>
                <li><a href="#market" className={activeTool === 'market' ? 'active' : ''}>Sleepers & Busts</a></li>
                <li><a href="#trending" className={activeTool === 'trending' ? 'active' : ''}>Trending Players</a></li>
              </ul>
            )}
          </div>

          <div className="nav-section">
            <h3 onClick={() => toggleNavSection('teamManagement')}>
              Team Management <span className={navSections.teamManagement ? 'arrow down' : 'arrow right'}></span>
            </h3>
            {navSections.teamManagement && (
              <ul>
                <li><a href="#keeper" className={activeTool === 'keeper' ? 'active' : ''}>Keeper Evaluator</a></li>
                <li><a href="#trade" className={activeTool === 'trade' ? 'active' : ''}>Trade Analyzer</a></li>
                <li><a href="#draft" className={activeTool === 'draft' ? 'active' : ''}>Draft Assistant</a></li>
                <li><a href="#waiver" className={activeTool === 'waiver' ? 'active' : ''}>Waiver Wire Assistant</a></li>
              </ul>
            )}
          </div>
        </nav>
        <div className="sidebar-footer">
          <nav className="utility-nav">
             <a href="#settings" className={activeTool === 'settings' ? 'active' : ''}>
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="feather feather-settings"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
                Settings
             </a>
          </nav>
          <p>© 2025 RATM</p>
        </div>
      </div>

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
            <section id="targets">
              <div className="tool-header"><h2>My Target List</h2><p>A list of players you are targeting in your draft.</p></div>
              <div className="card">
                <div className="target-list-container">
                  {targetList.length > 0 ? (
                    <table className="target-table">
                      <thead>
                        <tr>
                          <th>Player</th>
                          <th>Pos.</th>
                          <th>Team</th>
                          <th>ECR</th>
                          <th>SD</th>
                          <th>Bye</th>
                          <th></th>
                        </tr>
                      </thead>
                      <tbody>
                        {targetList.map(playerName => {
                          const playerData = staticPlayerData[playerName.toLowerCase()];
                          return (
                            <tr key={playerName}>
                              <td><a href={`/?tool=dossier&player=${encodeURIComponent(playerName)}`} className="player-link">{playerName}</a></td>
                              <td>{playerData?.position || 'N/A'}</td>
                              <td>{playerData?.team || 'N/A'}</td>
                              <td>{playerData?.ecr ? playerData.ecr.toFixed(1) : 'N/A'}</td>
                              <td>{playerData?.sd ? playerData.sd.toFixed(2) : 'N/A'}</td>
                              <td>{playerData?.bye_week || 'N/A'}</td>
                              <td>
                                <button className="remove-btn-small" onClick={() => handleRemoveFromTargets(playerName)}>
                                  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path><line x1="10" y1="11" x2="10" y2="17"></line><line x1="14" y1="11" x2="14" y2="17"></line></svg>
                                </button>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  ) : (
                    <p>Your target list is empty. Add players from the Dossier, Rankings, or Tiers tools.</p>
                  )}
                </div>
              </div>
            </section>
          )}

          {activeTool === 'market' && (
            <MarketInefficiencyFinder
              marketInefficiencies={marketInefficiencies}
              findMarketInefficiencies={findMarketInefficiencies}
              handleAddToTargets={handleAddToTargets}
              getOverallSdLabel={getOverallSdLabel}
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
              ecrTypePreference={ecrTypePreference}
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
              analysisResult={waiverSwapResult}
              isLoading={isWaiverSwapLoading}
            />
          )}

          {activeTool === 'settings' && (
            <section id="settings">
              <div className="tool-header"><h2>Settings</h2><p>Manage application data and preferences.</p></div>
              <div className="card">
                <h3>Theme</h3>
                <p>Switch between light and dark mode.</p>
                <button onClick={toggleTheme}>Toggle Theme</button>
              </div>
              <div className="card">
                <h3>Clear Saved Data</h3>
                <p>This action will permanently delete your saved Google API key, draft board, and target list from this browser.</p>
                <button onClick={resetApplication} className="btn-danger">Clear All Data & Reset</button>
              </div>
              <div className="card">
                <h3>Data Last Updated</h3>
                <p>Dynasty process files were last updated on: <strong>{lastUpdateDate}</strong></p>
              </div>
            </section>
          )}


        </div>
      </div>
    </div>
  );
}


export default App;
