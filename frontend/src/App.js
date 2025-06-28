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
import Sidebar from './components/Sidebar'; // Import Sidebar
import { AppContext } from './context/AppContext';
import { useApi } from './hooks/useApi';

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
    ecrTypePreference,
    setEcrTypePreference,
    converter,
    API_BASE_URL,
    setShowApiKeyModal
  } = useContext(AppContext);

  const { makeApiRequest } = useApi();

  const [navSections, setNavSections] = useState({
    playerAnalysis: false,
    teamManagement: false,
  });

  const [sortDirection, setSortDirection] = useState({ name: 'asc', position: 'asc', adds: 'desc', team: 'asc', ecr: 'asc' });
  const [keeperList, setKeeperList] = useState([]);
  const [keeperPlayerName, setKeeperPlayerName] = useState('');
  const [keeperRoundInput, setKeeperRoundInput] = useState('');
  const [keeperContextInput, setKeeperContextInput] = useState('');
  const [editingKeeperIndex, setEditingKeeperIndex] = useState(null);
  const [editRoundInput, setEditRoundInput] = useState('');
  const [editContextInput, setEditContextInput] = useState('');

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
        navSections={navSections}
        toggleNavSection={toggleNavSection}
        setEcrTypePreference={setEcrTypePreference}
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
            <Settings
              lastUpdateDate={lastUpdateDate}
              toggleTheme={toggleTheme}
              resetApplication={resetApplication}
            />
          )}

          {activeTool === 'documentation' && (
            <Documentation />
          )}


        </div>
      </div>
    </div>
  );
}


export default App;
