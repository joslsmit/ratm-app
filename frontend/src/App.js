import React, { useState, useEffect, useCallback, useMemo } from 'react';
import showdown from 'showdown';
import autoComplete from '@tarekraafat/autocomplete.js';
import './App.css';
import DynastyValues from './components/DynastyValues';
import WaiverWireAssistant from './components/WaiverWireAssistant';

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
  const [staticPlayerData, setStaticPlayerData] = useState({});
  const [trendingData, setTrendingData] = useState([]);
  const [sortDirection, setSortDirection] = useState({ name: 'asc', position: 'asc', adds: 'desc', team: 'asc', pos_rank: 'asc' });
  const [marketInefficiencies, setMarketInefficiencies] = useState({ sleepers: [], busts: [] });
  const [rookieRankings, setRookieRankings] = useState([]);
  const [draftBoard, setDraftBoard] = useState({});

  // State for results that are simple markdown/HTML
  const [dossierResult, setDossierResult] = useState(null);
  const [tiersResult, setTiersResult] = useState('');
  const [keeperResult, setKeeperResult] = useState('');
  const [tradeResult, setTradeResult] = useState('');
  const [draftAnalysisResult, setDraftAnalysisResult] = useState('');
  const [rosterCompositionResult, setRosterCompositionResult] = useState('');
  const [waiverSwapResult, setWaiverSwapResult] = useState('');
  const [isWaiverSwapLoading, setIsWaiverSwapLoading] = useState(false);
  const [lastUpdateDate, setLastUpdateDate] = useState('Loading...');

  // States for list-based tools
  const [targetList, setTargetList] = useState([]);
  const [keeperList, setKeeperList] = useState([]);
  const [myTradeAssets, setMyTradeAssets] = useState([]);
  const [partnerTradeAssets, setPartnerTradeAssets] = useState([]);
  const [keeperPlayerName, setKeeperPlayerName] = useState('');
  const [keeperRoundInput, setKeeperRoundInput] = useState('');
  const [tradeScoringFormat, setTradeScoringFormat] = useState('PPR');
  const [myPlayerInput, setMyPlayerInput] = useState('');
  const [partnerPlayerInput, setPartnerPlayerInput] = useState('');
  const [myPickInput, setMyPickInput] = useState('');
  const [partnerPickInput, setPartnerPickInput] = useState('');

  // Memoize the Showdown converter to avoid recreating it on every render
  const converter = useMemo(() => new showdown.Converter({ simplifiedAutoLink: true, tables: true, strikethrough: true }), []);

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
        body: JSON.stringify(body),
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
  }, [userApiKey]);

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

  const getDraftBoardState = useCallback(() => {
    const board = {};
    for (let i = 1; i <= 15; i++) {
      const input = document.getElementById(`round-${i}-player-hidden`);
      if (input && input.value) {
        board[`Round ${i}`] = input.value;
      }
    }
    return board;
  }, []);

  const updateRosterComposition = useCallback(() => {
    const counts = { QB: 0, RB: 0, WR: 0, TE: 0, K: 0, DST: 0 };
    const draftedPlayers = getDraftBoardState();
    Object.values(draftedPlayers).forEach(playerName => {
      const key = playerName.toLowerCase();
      const playerData = staticPlayerData[key];
      if (playerData && playerData.pos_rank) {
        const pos = playerData.pos_rank.replace(/\d/g, '');
        if (pos in counts) {
          counts[pos]++;
        }
      }
    });

    // Update the UI
    for (const pos in counts) {
      const cell = document.getElementById(`comp-${pos.toLowerCase()}`);
      if (cell) {
        cell.textContent = counts[pos];
      }
    }
    return counts;
  }, [staticPlayerData, getDraftBoardState]);


  const saveDraftBoard = useCallback(() => {
    const board = {};
    let hasChanges = false;
    for (let i = 1; i <= 15; i++) {
      const playerName = document.getElementById(`round-${i}-player-hidden`)?.value;
      if (playerName) {
        board[i] = playerName;
        hasChanges = true;
      }
    }
    if (hasChanges) {
      localStorage.setItem('draftBoard', JSON.stringify(board));
    }
    updateRosterComposition();
  }, [updateRosterComposition]);

  const loadDraftBoard = useCallback(() => {
    const savedBoard = localStorage.getItem('draftBoard');
    if (savedBoard) {
        return JSON.parse(savedBoard);
    }
    return {};
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

  const generateTiers = useCallback(() => {
    const position = document.getElementById('tiers-pos')?.value;
    renderGeneric('tiers', '/generate_tiers', { position }, setTiersResult);
  }, [renderGeneric]);

  // Autocomplete for Global Search
  useEffect(() => {
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
    return () => ac.unInit();
  }, [allPlayers, handleGlobalSearch]);

  // Autocomplete for Dossier
  useEffect(() => {
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
    return () => ac.unInit();
  }, [allPlayers, activeTool]);

  // Autocomplete for Keeper Evaluator
  useEffect(() => {
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
    return () => ac.unInit();
  }, [allPlayers, activeTool]);

  // Autocomplete for Trade Analyzer
  useEffect(() => {
    if (activeTool !== 'trade' || allPlayers.length === 0) return;

    const myPlayerAC = new autoComplete({
        selector: '#trade-my-player-input',
        placeHolder: "Enter player name...",
        data: { src: allPlayers, cache: true },
        resultItem: { highlight: true },
        events: {
            input: {
                selection: (event) => {
                    const selection = event.detail.selection.value;
                    setMyPlayerInput(selection);
                },
            },
        },
    });

    const partnerPlayerAC = new autoComplete({
        selector: '#trade-partner-player-input',
        placeHolder: "Enter player name...",
        data: { src: allPlayers, cache: true },
        resultItem: { highlight: true },
        events: {
            input: {
                selection: (event) => {
                    const selection = event.detail.selection.value;
                    setPartnerPlayerInput(selection);
                },
            },
        },
    });

    return () => {
        if (myPlayerAC) myPlayerAC.unInit();
        if (partnerPlayerAC) partnerPlayerAC.unInit();
    };
  }, [allPlayers, activeTool]);

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

  const evaluateTrade = useCallback(() => {
    if (myTradeAssets.length === 0 || partnerTradeAssets.length === 0) { alert('Please add assets to both sides of the trade.'); return; }
    renderGeneric('trade', '/trade_analyzer', { my_assets: myTradeAssets, partner_assets: partnerTradeAssets, scoring_format: tradeScoringFormat }, setTradeResult);
  }, [renderGeneric, myTradeAssets, partnerTradeAssets, tradeScoringFormat]);

  const suggestPosition = useCallback(() => {
    const currentRound = document.getElementById('draft-current-round')?.value;
    if (!currentRound) { alert('Please enter the current round.'); return; }
    renderGeneric('draft-analysis', '/suggest_position', { draft_board: getDraftBoardState(), current_round: currentRound }, setDraftAnalysisResult);
  }, [renderGeneric, getDraftBoardState]);

  const evaluatePick = useCallback(() => {
    const playerToPick = document.getElementById('draft-pick-player')?.value;
    const currentRound = document.getElementById('draft-current-round')?.value;
    if (!playerToPick || !currentRound) { alert('Please enter both a player and the current round.'); return; }
    renderGeneric('draft-analysis', '/pick_evaluator', { draft_board: getDraftBoardState(), player_to_pick: playerToPick, current_round: currentRound }, setDraftAnalysisResult);
  }, [renderGeneric, getDraftBoardState]);

  const analyzeComposition = useCallback(() => {
    renderGeneric('draft-comp', '/roster_composition_analysis', { composition: updateRosterComposition() }, setRosterCompositionResult);
  }, [renderGeneric, updateRosterComposition]);

  const addKeeper = () => {
    const roundValue = parseInt(keeperRoundInput, 10);
    if (keeperPlayerName && !isNaN(roundValue) && roundValue > 0) {
      setKeeperList(prevList => [...prevList, { name: keeperPlayerName, round: roundValue }]);
      setKeeperPlayerName('');
      setKeeperRoundInput('');
      document.getElementById('keeper-player-name')?.focus();
    } else {
      alert('Please enter a valid player name and a positive number for the draft round.');
    }
  };

  const addAsset = (side, assetType) => {
    const playerInput = side === 'my' ? myPlayerInput : partnerPlayerInput;
    const pickInput = side === 'my' ? myPickInput : partnerPickInput;
    const setAssets = side === 'my' ? setMyTradeAssets : setPartnerTradeAssets;
    const setPlayerInput = side === 'my' ? setMyPlayerInput : setPartnerPlayerInput;
    const setPickInput = side === 'my' ? setMyPickInput : setPartnerPickInput;

    let assetToAdd = '';
    if (assetType === 'player' && playerInput) {
      assetToAdd = playerInput;
    } else if (assetType === 'pick' && pickInput) {
      assetToAdd = pickInput;
    }

    if (assetToAdd) {
      setAssets(prevAssets => [...prevAssets, assetToAdd]);
      if (assetType === 'player') {
        setPlayerInput('');
        document.getElementById(`trade-${side}-player-input`)?.focus();
      } else {
        setPickInput('');
        document.getElementById(`trade-${side}-pick-input`)?.focus();
      }
    }
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

  // Fetch all player names for autocomplete functionality
  useEffect(() => {
    fetch(`${API_BASE_URL}/all_player_names_with_data`)
      .then(response => response.json())
      .then(data => {
        if (data && Array.isArray(data)) {
          setAllPlayers(data.map(p => p.name));
          const staticData = data.reduce((acc, p) => {
            acc[p.name.toLowerCase()] = p;
            return acc;
          }, {});
          setStaticPlayerData(staticData);
        }
      })
      .catch(error => console.error("Error fetching player names:", error));
  }, []);

  // Create and load the draft board on initial mount
  useEffect(() => {
    // Only run if the draft tool is the active one initially
    if (activeTool === 'draft') {
        const board = loadDraftBoard();
        setDraftBoard(board);
    }
  }, [activeTool, loadDraftBoard]);


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
                <li><a href="#dynasty" className={activeTool === 'dynasty' ? 'active' : ''}>Dynasty Values</a></li>
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
            <section id="dossier">
              <div className="tool-header">
                <h2>Player Dossier</h2>
                <p>Get a complete 360-degree scouting report on any player.</p>
              </div>
              <div className="card">
                <div className="form-group-inline">
                  <div className="autoComplete_wrapper"><input id="dossier-player-name" type="text" placeholder="Enter player name..." /></div>
                  <button onClick={() => generateDossier()}>Generate</button>
                </div>
              </div>
              <div id="dossier-loader" className="loader" style={{ display: 'none' }}></div>
              {dossierResult && !dossierResult.error && (
                <div className="dossier-output">
                  <div className="dossier-header-card card">
                    <div className="dossier-title-container">
                      <h3>{dossierResult.player_data.name}</h3>
                      <button className="add-target-btn" title="Add to Target List" onClick={() => handleAddToTargets(dossierResult.player_data.name)}>
                        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="feather feather-plus-circle"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="16"></line><line x1="8" y1="12" x2="16" y2="12"></line></svg>
                      </button>
                    </div>
                    <div className="dossier-header-stats">
                      <span><strong>Team:</strong> {dossierResult.player_data.team}</span>
                      <span><strong>Position:</strong> {dossierResult.player_data.position}</span>
                      <span><strong>Pos. Rank:</strong> {dossierResult.player_data.pos_rank}</span>
                      <span><strong>ADP:</strong> {dossierResult.player_data.adp ? dossierResult.player_data.adp.toFixed(1) : 'N/A'}</span>
                      <span><strong>Bye:</strong> {dossierResult.player_data.bye_week || 'N/A'}</span>
                    </div>
                  </div>
                  <div id="dossier-result" className="result-box" dangerouslySetInnerHTML={{ __html: converter.makeHtml(dossierResult.analysis) }}></div>
                </div>
              )}
              {dossierResult && dossierResult.error && (
                <div className="result-box">
                  <p style={{ color: 'var(--danger-color)' }}>An error occurred: {dossierResult.error}</p>
                </div>
              )}
            </section>
          )}

          {activeTool === 'rookie' && (
            <section id="rookie">
                <div className="tool-header"><h2>2025 Rookie Rankings</h2><p>Get AI-powered rankings and analysis for the incoming rookie class.</p></div>
                <div className="card"><div className="form-group-inline"><select id="rookie-pos"><option value="all">All</option><option value="QB">QB</option><option value="RB">RB</option><option value="WR">WR</option><option value="TE">TE</option></select><button onClick={generateRookieRankings}>Generate</button></div></div>
                <div id="rookie-loader" className="loader" style={{ display: 'none' }}></div>
                <div className="result-box-cards">
                    {rookieRankings.length > 0 ? rookieRankings.map((rookie, index) => (
                        <div key={index} className="rookie-card">
                            <div className="rookie-header">
                                <h3><a href={`/?tool=dossier&player=${encodeURIComponent(rookie.name)}`} target="_blank" rel="noopener noreferrer" className="player-link">{rookie.name}</a> ({rookie.position}, {rookie.team || 'N/A'})</h3>
                                <div className="rookie-actions">
                                  <button className="add-target-btn-small" title="Add to Target List" onClick={() => handleAddToTargets(rookie.name)}>
                                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="16"></line><line x1="8" y1="12" x2="16" y2="12"></line></svg>
                                  </button>
                                  <span className="rank">#{rookie.rank}</span>
                                </div>
                            </div>
                            <div className="rookie-details">
                                <span>Pos. Rank: {rookie.pos_rank || 'N/A'}</span>
                                <span>ADP: {rookie.adp || 'N/A'}</span>
                            </div>
                            <p className="rookie-analysis">{rookie.analysis}</p>
                        </div>
                    )) : <p>No rookie rankings to display. Generate a new list.</p>}
                </div>
            </section>
          )}

          {activeTool === 'tiers' && (
            <section id="tiers">
              <div className="tool-header"><h2>Positional Tiers</h2><p>Generate tier-based rankings to understand value drop-offs.</p></div>
              <div className="card"><div className="form-group-inline"><select id="tiers-pos"><option value="QB">QB</option><option value="RB">RB</option><option value="WR">WR</option><option value="TE">TE</option></select><button onClick={generateTiers}>Generate Tiers</button></div></div>
              <div id="tiers-loader" className="loader" style={{ display: 'none' }}></div>
              <div id="tiers-result" className="result-box" dangerouslySetInnerHTML={{ __html: converter.makeHtml(tiersResult) }}></div>
            </section>
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
                          <th>ADP</th>
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
                              <td>{playerData?.adp ? playerData.adp.toFixed(1) : 'N/A'}</td>
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
              <section id="market">
                  <div className="tool-header"><h2>Market Inefficiency Finder</h2><p>Discover potential sleepers and busts by comparing data sources.</p></div>
                  <div className="card"><div className="form-group-inline"><select id="market-pos"><option value="all">All</option><option value="QB">QB</option><option value="RB">RB</option><option value="WR">WR</option><option value="TE">TE</option></select><button onClick={findMarketInefficiencies}>Find</button></div></div>
                  <div id="market-loader" className="loader" style={{ display: 'none' }}></div>
                  <div className="market-results">
                      <div className="market-column">
                          <h3>Sleepers (Undervalued)</h3>
                          {marketInefficiencies.sleepers.length > 0 ? marketInefficiencies.sleepers.map((player, index) => (
                              <div key={`sleeper-${index}`} className="analysis-card sleeper">
                                  <div className="analysis-card-header">
                                    <h4><a href={`/?tool=dossier&player=${encodeURIComponent(player.name)}`} className="player-link">{player.name}</a></h4>
                                    <span className={`confidence-badge ${player.confidence}`}>{player.confidence}</span>
                                    <button className="add-target-btn-small" title="Add to Target List" onClick={() => handleAddToTargets(player.name)}>
                                      <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="16"></line><line x1="8" y1="12" x2="16" y2="12"></line></svg>
                                    </button>
                                  </div>
                                  <p>{player.justification}</p>
                              </div>
                          )) : <p>No sleepers found.</p>}
                      </div>
                      <div className="market-column">
                          <h3>Busts (Overvalued)</h3>
                          {marketInefficiencies.busts.length > 0 ? marketInefficiencies.busts.map((player, index) => (
                              <div key={`bust-${index}`} className="analysis-card bust">
                                  <div className="analysis-card-header">
                                    <h4><a href={`/?tool=dossier&player=${encodeURIComponent(player.name)}`} className="player-link">{player.name}</a></h4>
                                    <span className={`confidence-badge ${player.confidence}`}>{player.confidence}</span>
                                    <button className="add-target-btn-small" title="Add to Target List" onClick={() => handleAddToTargets(player.name)}>
                                      <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="16"></line><line x1="8" y1="12" x2="16" y2="12"></line></svg>
                                    </button>
                                  </div>
                                  <p>{player.justification}</p>
                              </div>
                          )) : <p>No busts found.</p>}
                      </div>
                  </div>
              </section>
          )}

          {activeTool === 'keeper' && (
            <section id="keeper">
              <div className="tool-header"><h2>Keeper Evaluator</h2><p>Analyze multiple keeper options based on cost vs. value.</p></div>
              <div className="card">
                <div className="form-group-inline">
                  <div className="autoComplete_wrapper"><input id="keeper-player-name" type="text" placeholder="Player Name..." value={keeperPlayerName} onChange={(e) => setKeeperPlayerName(e.target.value)} /></div>
                  <input id="keeper-round" type="number" placeholder="Original Draft Round" value={keeperRoundInput} onChange={(e) => setKeeperRoundInput(e.target.value)} />
                  <button onClick={addKeeper}>Add</button>
                </div>
                <ul className="item-list">
                  {keeperList.map((keeper, index) => {
                    const playerData = staticPlayerData[keeper.name.toLowerCase()];
                    const adp = playerData?.adp;
                    const value = adp ? (keeper.round * 12) - adp : null; // A simple value calculation
                    return (
                      <li key={index} className="list-item">
                        <div>
                          <strong>{keeper.name}</strong> (Cost: Rd {keeper.round})
                          <br />
                          <small>ADP: {adp ? adp.toFixed(1) : 'N/A'} {value !== null && `(Value: ${value > 0 ? '+' : ''}${(value / 12).toFixed(1)})`}</small>
                        </div>
                        <button className="remove-btn" onClick={() => setKeeperList(prev => prev.filter((_, i) => i !== index))}>
                          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                        </button>
                      </li>
                    );
                  })}
                </ul>
              </div>
              <button onClick={evaluateKeepers} className="action-button">Analyze All Keepers</button>
              <div id="keeper-loader" className="loader" style={{ display: 'none' }}></div>
              <div id="keeper-result" className="result-box" dangerouslySetInnerHTML={{ __html: converter.makeHtml(keeperResult) }}></div>
            </section>
          )}
          
          {activeTool === 'trade' && (
            <section id="trade">
              <div className="tool-header">
                <h2>Trade Analyzer</h2>
                <p>Get an unbiased analysis of any trade proposal.</p>
              </div>
              <div className="trade-box">
                <div className="card trade-settings-card">
                  <div className="form-group-inline">
                    <label htmlFor="scoring-format">Scoring Format:</label>
                    <select id="scoring-format" value={tradeScoringFormat} onChange={(e) => setTradeScoringFormat(e.target.value)}>
                      <option value="PPR">PPR</option>
                      <option value="Half-PPR">Half-PPR</option>
                      <option value="Standard">Standard</option>
                    </select>
                  </div>
                </div>
                <div className="trade-side card">
                  <h3>Your Team Receives:</h3>
                  <div className="form-group-inline">
                    <div className="autoComplete_wrapper">
                      <input id="trade-my-player-input" type="text" placeholder="Enter player name..." value={myPlayerInput} onChange={(e) => setMyPlayerInput(e.target.value)} />
                    </div>
                    <button onClick={() => addAsset('my', 'player')}>Add Player</button>
                  </div>
                  <div className="form-group-inline">
                    <input id="trade-my-pick-input" type="text" placeholder="e.g., 2025 1st or Pick 1.05" value={myPickInput} onChange={(e) => setMyPickInput(e.target.value)} />
                    <button onClick={() => addAsset('my', 'pick')}>Add Pick</button>
                  </div>
                  <ul className="item-list">
                    {myTradeAssets.map((asset, index) => (
                      <li key={index} className="list-item">
                        <span>{asset}</span>
                        <button className="remove-btn" onClick={() => setMyTradeAssets(prev => prev.filter((_, i) => i !== index))}>
                          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="trade-side card">
                  <h3>Your Team Gives Away:</h3>
                  <div className="form-group-inline">
                    <div className="autoComplete_wrapper">
                      <input id="trade-partner-player-input" type="text" placeholder="Enter player name..." value={partnerPlayerInput} onChange={(e) => setPartnerPlayerInput(e.target.value)} />
                    </div>
                    <button onClick={() => addAsset('partner', 'player')}>Add Player</button>
                  </div>
                  <div className="form-group-inline">
                    <input id="trade-partner-pick-input" type="text" placeholder="e.g., 2025 1st or Pick 1.05" value={partnerPickInput} onChange={(e) => setPartnerPickInput(e.target.value)} />
                    <button onClick={() => addAsset('partner', 'pick')}>Add Pick</button>
                  </div>
                  <ul className="item-list">
                    {partnerTradeAssets.map((asset, index) => (
                      <li key={index} className="list-item">
                        <span>{asset}</span>
                        <button className="remove-btn" onClick={() => setPartnerTradeAssets(prev => prev.filter((_, i) => i !== index))}>
                          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
              <button onClick={evaluateTrade} className="action-button">Analyze Trade</button>
              <div id="trade-loader" className="loader" style={{ display: 'none' }}></div>
              <div id="trade-result" className="result-box" dangerouslySetInnerHTML={{ __html: converter.makeHtml(tradeResult) }}></div>
            </section>
          )}

          {activeTool === 'draft' && (
            <section id="draft">
                <div className="tool-header"><h2>Live Draft Assistant</h2><p>Track your draft and get real-time advice.</p></div>
                <div className="draft-dashboard">
                    <div className="draft-main-panel">
                        <div className="card">
                            <h3>Analysis & Advice</h3>
                            <div className="form-group-inline">
                                <input type="number" id="draft-current-round" placeholder="Current Round #" />
                                <div className="autoComplete_wrapper"><input id="draft-pick-player" type="text" placeholder="Player being considered..." /></div>
                            </div>
                            <div className="form-group-inline">
                                <button onClick={suggestPosition}>Suggest Position</button>
                                <button onClick={evaluatePick}>Evaluate Player</button>
                            </div>
                            <div id="draft-analysis-loader" className="loader" style={{ display: 'none' }}></div>
                            <div id="draft-analysis-result" className="result-box" dangerouslySetInnerHTML={{ __html: converter.makeHtml(draftAnalysisResult) }}></div>
                        </div>
                    </div>
                    <div className="draft-sidebar-panel">
                        <div className="card">
                            <h3>Roster Composition</h3>
                            <table className="composition-table">
                                <thead><tr><th>QB</th><th>RB</th><th>WR</th><th>TE</th><th>K</th><th>DST</th></tr></thead>
                                <tbody><tr><td id="comp-qb">0</td><td id="comp-rb">0</td><td id="comp-wr">0</td><td id="comp-te">0</td><td id="comp-k">0</td><td id="comp-dst">0</td></tr></tbody>
                            </table>
                            <div style={{ textAlign: 'center', marginTop: '15px' }}>
                                <button onClick={analyzeComposition}>Analyze Balance</button>
                            </div>
                            <div id="draft-comp-loader" className="loader" style={{ display: 'none' }}></div>
                            <div id="draft-comp-result" className="result-box" style={{ marginTop: '15px' }} dangerouslySetInnerHTML={{ __html: converter.makeHtml(rosterCompositionResult) }}></div>
                        </div>
                    </div>
                </div>
                <div className="draft-board-container" style={{ display: activeTool === 'draft' ? 'flex' : 'none', flexDirection: 'column' }}>
                    <h3>Your Draft Board</h3>
                    <div className="draft-board">
                        {Array.from({ length: 15 }, (_, i) => i + 1).map(round => (
                            <DraftCard
                                key={round}
                                round={round}
                                staticPlayerData={staticPlayerData}
                                saveDraftBoard={saveDraftBoard}
                                allPlayers={allPlayers}
                                handleGlobalSearch={handleGlobalSearch}
                                initialPlayerName={draftBoard[round]}
                            />
                        ))}
                    </div>
                    <button onClick={() => {
                        if(window.confirm("Are you sure you want to reset the entire draft board?")) {
                            localStorage.removeItem('draftBoard');
                            setDraftBoard({});
                        }
                    }} className="action-button btn-danger btn-small" style={{marginTop: "20px", alignSelf: "center"}}>Reset Board</button>
                </div>
            </section>
          )}

          {activeTool === 'trending' && (
            <section id="trending">
              <div className="tool-header"><h2>Trending Players</h2><p>See who's being added most on Sleeper in the last 48 hours.</p></div>
              <div className="card">
                <table id="trending-table">
                  <thead>
                    <tr>
                      <th className="sortable" onClick={() => sortTrendingData('name')}>Player {sortDirection.name === 'asc' ? '▲' : '▼'}</th>
                      <th className="sortable" onClick={() => sortTrendingData('team')}>Team {sortDirection.team === 'asc' ? '▲' : '▼'}</th>
                      <th className="sortable" onClick={() => sortTrendingData('position')}>Position {sortDirection.position === 'asc' ? '▲' : '▼'}</th>
                      <th className="sortable" onClick={() => sortTrendingData('pos_rank')}>Pos. Rank {sortDirection.pos_rank === 'asc' ? '▲' : '▼'}</th>
                      <th className="sortable" onClick={() => sortTrendingData('adds')}>Adds (48hr) {sortDirection.adds === 'asc' ? '▲' : '▼'}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trendingData.length > 0 ? trendingData.map((player, index) => (
                      <tr key={index}>
                        <td><a href={`/?tool=dossier&player=${encodeURIComponent(player.name)}`} className="player-link">{player.name}</a></td>
                        <td>{player.team || 'N/A'}</td>
                        <td>{player.position}</td>
                        <td>{player.pos_rank || 'N/A'}</td>
                        <td>{player.adds}</td>
                      </tr>
                    )) : (
                      <tr><td colSpan="5">No trending data to display.</td></tr>
                    )}
                  </tbody>
                </table>
                <div id="trending-loader" className="loader" style={{ display: 'none' }}></div>
              </div>
            </section>
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

          {activeTool === 'dynasty' && (
            <section id="dynasty">
              <div className="tool-header"><h2>Dynasty Values</h2><p>View dynasty trade values for players and picks.</p></div>
              <div className="card">
                <DynastyValues />
              </div>
            </section>
          )}

        </div>
      </div>
    </div>
  );
}

function DraftCard({ round, staticPlayerData, saveDraftBoard, allPlayers, handleGlobalSearch, initialPlayerName }) {
    const [isEditing, setIsEditing] = useState(false);
    const [playerName, setPlayerName] = useState(initialPlayerName || '');
    const autoCompleteRef = React.useRef(null);

    useEffect(() => {
        setPlayerName(initialPlayerName || '');
    }, [initialPlayerName]);

    useEffect(() => {
        if (isEditing && !autoCompleteRef.current) {
            const inputId = `round-${round}-player`;
            autoCompleteRef.current = new autoComplete({
                selector: `#${inputId}`,
                placeHolder: "Player...",
                data: { src: allPlayers, cache: true },
                resultItem: { highlight: true },
                events: {
                    input: {
                        selection: event => {
                            const selectedValue = event.detail.selection.value;
                            setPlayerName(selectedValue);
                            const hiddenInput = document.getElementById(`round-${round}-player-hidden`);
                            if(hiddenInput) {
                                hiddenInput.value = selectedValue;
                            }
                            saveDraftBoard();
                            if (autoCompleteRef.current) {
                                autoCompleteRef.current.unInit();
                                autoCompleteRef.current = null;
                            }
                            setIsEditing(false);
                        }
                    }
                }
            });
        }
    }, [isEditing, round, allPlayers, saveDraftBoard]);

    const handleEdit = () => {
        setIsEditing(true);
    };

    const handleCancel = () => {
        if (autoCompleteRef.current) {
            autoCompleteRef.current.unInit();
            autoCompleteRef.current = null;
        }
        setIsEditing(false);
    };

    const handleClear = () => {
        setPlayerName('');
        const hiddenInput = document.getElementById(`round-${round}-player-hidden`);
        if(hiddenInput) {
            hiddenInput.value = '';
        }
        saveDraftBoard();
    };

    const playerData = playerName ? staticPlayerData[playerName.toLowerCase()] : null;
    const position = playerData?.pos_rank?.replace(/\d/g, '');

    return (
        <div className={`round-card pos-${position?.toLowerCase()}`}>
            <input type="hidden" id={`round-${round}-player-hidden`} value={playerName} />
            <label>Round {round}</label>
            {isEditing ? (
                <div className="autoComplete_wrapper">
                    <input id={`round-${round}-player`} type="text" placeholder="Player..." />
                    <button onClick={handleCancel}>Cancel</button>
                </div>
            ) : (
                <div className="player-display" onClick={handleEdit}>
                    {playerName || 'Click to add player'}
                </div>
            )}
            {playerName && <button onClick={handleClear} className="remove-btn-small">Clear</button>}
            {playerData && (
                <div className="draft-card-details">
                    <span>ADP: {playerData.adp ? playerData.adp.toFixed(1) : 'N/A'}</span>
                    <span>Bye: {playerData.bye_week || 'N/A'}</span>
                </div>
            )}
        </div>
    );
}

export default App;
