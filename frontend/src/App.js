import React, { useState, useEffect, useCallback, useMemo } from 'react';
import showdown from 'showdown';
import autoComplete from '@tarekraafat/autocomplete.js';
import './App.css';

// The backend API URL. This can be changed to your production URL when you deploy.
const API_BASE_URL = 'http://localhost:5001/api';

function App() {
  // State for API Key and Modal
  const [userApiKey, setUserApiKey] = useState(() => localStorage.getItem('geminiApiKey') || '');
  const [showApiKeyModal, setShowApiKeyModal] = useState(() => !localStorage.getItem('geminiApiKey'));

  // State for active tool and data
  const [activeTool, setActiveTool] = useState('dossier');
  const [allPlayers, setAllPlayers] = useState([]);
  const [staticPlayerData, setStaticPlayerData] = useState({});
  const [trendingData, setTrendingData] = useState([]);
  const [sortDirection, setSortDirection] = useState({ position: 'asc', adds: 'desc', team: 'asc', pos_rank: 'asc' });
  const [marketInefficiencies, setMarketInefficiencies] = useState({ sleepers: [], busts: [] });
  const [rookieRankings, setRookieRankings] = useState([]);

  // State for results that are simple markdown/HTML
  const [dossierResult, setDossierResult] = useState('');
  const [tiersResult, setTiersResult] = useState('');
  const [keeperResult, setKeeperResult] = useState('');
  const [tradeResult, setTradeResult] = useState('');
  const [draftAnalysisResult, setDraftAnalysisResult] = useState('');
  const [rosterCompositionResult, setRosterCompositionResult] = useState('');

  // States for list-based tools
  const [keeperList, setKeeperList] = useState([]);
  const [myTradeAssets, setMyTradeAssets] = useState([]);
  const [partnerTradeAssets, setPartnerTradeAssets] = useState([]);
  const [keeperPlayerName, setKeeperPlayerName] = useState('');
  const [keeperRoundInput, setKeeperRoundInput] = useState('');

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
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': userApiKey
        },
        body: JSON.stringify(body),
      });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.error || `An unknown server error occurred on endpoint: ${endpoint}`);
      }
      return data;
    } catch (error) {
      console.error('API Request Error:', error);
      throw error; // Re-throw the error to be caught by the calling function
    }
  }, [userApiKey]);

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
      if (data && data.result) {
        setResult(data.result);
      } else {
		setResult('<p style="color: var(--text-muted);">The Analyst returned an empty response.</p>');
	  }
    } catch (error) {
      setResult(`<p style="color: var(--danger-color);">An error occurred: ${error.message}</p>`);
    } finally {
      if (loader) loader.style.display = 'none';
    }
  }, [makeApiRequest]);


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

  const getDraftBoardState = useCallback(() => {
    const board = {};
    for (let i = 1; i <= 15; i++) {
      const input = document.getElementById(`round-${i}-player`);
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
      const playerName = document.getElementById(`round-${i}-player`)?.value;
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
      const board = JSON.parse(savedBoard);
      for (const round in board) {
        const input = document.getElementById(`round-${round}-player`);
        if (input) {
          input.value = board[round];
        }
      }
    }
    updateRosterComposition();
  }, [updateRosterComposition]);


  // Initialize autocomplete fields
  useEffect(() => {
    const initAutoComplete = (selector) => {
      if (document.querySelector(selector) && allPlayers.length > 0) {
        const autoCompleteInstance = new autoComplete({
          selector: selector,
          placeHolder: "Search for a player...",
          data: { src: allPlayers, cache: true },
          resultItem: { highlight: true },
          events: {
            input: {
              selection: event => {
                const inputElement = document.querySelector(selector);
                const selectedValue = event.detail.selection.value;
                inputElement.value = selectedValue;
                if (selector === '#keeper-player-name') {
                  setKeeperPlayerName(selectedValue);
                }
                if (inputElement.id.startsWith("round-")) {
                  saveDraftBoard();
                }
              }
            }
          }
        });
      }
    };

    if (activeTool === 'dossier') initAutoComplete('#dossier-player-name');
    if (activeTool === 'keeper') initAutoComplete('#keeper-player-name');
    if (activeTool === 'draft') {
      initAutoComplete('#draft-pick-player');
      for (let i = 1; i <= 15; i++) {
        initAutoComplete(`#round-${i}-player`);
      }
    }
  }, [allPlayers, activeTool, saveDraftBoard]);


  // --- Tool-Specific Functions ---

  const generateDossier = useCallback(() => {
    const playerName = document.getElementById('dossier-player-name')?.value;
    if (!playerName) { alert('Please enter a player name.'); return; }
    renderGeneric('dossier', '/player_dossier', { player_name: playerName }, setDossierResult);
  }, [renderGeneric]);

  const generateTiers = useCallback(() => {
    const position = document.getElementById('tiers-pos')?.value;
    renderGeneric('tiers', '/generate_tiers', { position }, setTiersResult);
  }, [renderGeneric]);

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
    renderGeneric('trade', '/trade_analyzer', { my_assets: myTradeAssets, partner_assets: partnerTradeAssets }, setTradeResult);
  }, [renderGeneric, myTradeAssets, partnerTradeAssets]);

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

  const addAsset = (side) => {
    const input = document.getElementById(`trade-${side}-asset-input`);
    if (input && input.value) {
      if (side === 'my') {
        setMyTradeAssets(prevAssets => [...prevAssets, input.value]);
      } else {
        setPartnerTradeAssets(prevAssets => [...prevAssets, input.value]);
      }
      input.value = '';
      input.focus();
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

  // --- Effect Hooks for Initialization and Side Effects ---

  // Create and load the draft board on initial mount
  useEffect(() => {
    // Only run if the draft tool is the active one initially
    if (activeTool === 'draft') {
        loadDraftBoard();
    }
  }, [activeTool, loadDraftBoard]);


  // Fetch trending data only when the trending tool is active
  useEffect(() => {
    if (activeTool === 'trending' && trendingData.length === 0) {
      fetchTrending();
    }
  }, [activeTool, trendingData.length, fetchTrending]);

  // Handle URL parameters and hash changes for tool navigation
  useEffect(() => {
    const handleNavigation = () => {
        const urlParams = new URLSearchParams(window.location.search);
        const toolFromParam = urlParams.get('tool');
        const playerFromParam = urlParams.get('player');
        const hash = window.location.hash.substring(1);

        if (toolFromParam === 'dossier' && playerFromParam) {
            setActiveTool('dossier');
            // Use a timeout to ensure the dossier tool is rendered before we manipulate its input
            setTimeout(() => {
                const dossierInput = document.getElementById('dossier-player-name');
                if (dossierInput) {
                    dossierInput.value = decodeURIComponent(playerFromParam);
                    generateDossier();
                }
            }, 100);
        } else {
            setActiveTool(hash || 'dossier');
        }
    };
    handleNavigation();
    window.addEventListener('hashchange', handleNavigation);
    return () => window.removeEventListener('hashchange', handleNavigation);
  }, [generateDossier]); // generateDossier is a dependency


  const resetApplication = () => {
    if (window.confirm("Are you sure you want to clear all saved data? This will remove your API key and saved draft board and cannot be undone.")) {
      localStorage.removeItem('geminiApiKey');
      localStorage.removeItem('draftBoard');
      setUserApiKey('');
      setShowApiKeyModal(true);
      window.location.href = window.location.pathname; // Reload the page without hash/params
    }
  };

  const checkYahooAuthStatus = useCallback(async () => {
    const statusDiv = document.getElementById('yahoo-auth-status');
    const profileDiv = document.getElementById('yahoo-profile-data');
    if (statusDiv) statusDiv.innerHTML = '<p style="color: var(--text-muted);">Checking authorization status...</p>';
    if (profileDiv) profileDiv.innerHTML = '';
    try {
      const response = await fetch(`${API_BASE_URL}/yahoo/user_profile`);
      const data = await response.json();
      if (response.ok) {
        if (statusDiv) statusDiv.innerHTML = '<p style="color: var(--success-color);">✅ Successfully authorized with Yahoo!</p>';
        if (profileDiv) profileDiv.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
      } else {
        if (statusDiv) statusDiv.innerHTML = `<p style="color: var(--danger-color);">❌ Authorization failed: ${data.error || 'Unknown error'}</p>`;
      }
    } catch (error) {
      if (statusDiv) statusDiv.innerHTML = `<p style="color: var(--danger-color);">❌ Could not connect to backend to check status: ${error.message}</p>`;
    }
  }, []);

  // --- JSX ---
  return (
    <>
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
        <nav className="sidebar-nav">
          <ul>
            <li><a href="#dossier" className={activeTool === 'dossier' ? 'active' : ''} onClick={() => setActiveTool('dossier')}>Player Dossier</a></li>
            <li><a href="#rookie" className={activeTool === 'rookie' ? 'active' : ''} onClick={() => setActiveTool('rookie')}>Rookie Rankings</a></li>
            <li><a href="#tiers" className={activeTool === 'tiers' ? 'active' : ''} onClick={() => setActiveTool('tiers')}>Positional Tiers</a></li>
            <li><a href="#market" className={activeTool === 'market' ? 'active' : ''} onClick={() => setActiveTool('market')}>Sleepers & Busts</a></li>
            <hr />
            <li><a href="#keeper" className={activeTool === 'keeper' ? 'active' : ''} onClick={() => setActiveTool('keeper')}>Keeper Evaluator</a></li>
            <li><a href="#trade" className={activeTool === 'trade' ? 'active' : ''} onClick={() => setActiveTool('trade')}>Trade Analyzer</a></li>
            <li><a href="#draft" className={activeTool === 'draft' ? 'active' : ''} onClick={() => setActiveTool('draft')}>Draft Assistant</a></li>
            <hr />
            <li><a href="#trending" className={activeTool === 'trending' ? 'active' : ''} onClick={() => setActiveTool('trending')}>Trending Players</a></li>
          </ul>
        </nav>
        <div className="sidebar-footer">
          <nav className="utility-nav">
             <a href="#settings" className={activeTool === 'settings' ? 'active' : ''} onClick={() => setActiveTool('settings')}>Settings</a>
          </nav>
          <p>© 2025 RATM</p>
        </div>
      </div>

      <div className="main-content">
        <div className="content-wrapper">

          {activeTool === 'dossier' && (
            <section id="dossier">
              <div className="tool-header"><h2>Player Dossier</h2><p>Get a complete 360-degree scouting report on any player.</p></div>
              <div className="card"><div className="form-group-inline"><div className="autoComplete_wrapper"><input id="dossier-player-name" type="text" placeholder="Enter player name..." /></div><button onClick={generateDossier}>Generate</button></div></div>
              <div id="dossier-loader" className="loader" style={{ display: 'none' }}></div>
              <div id="dossier-result" className="result-box" dangerouslySetInnerHTML={{ __html: converter.makeHtml(dossierResult) }}></div>
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
                                <h3><a href={`/?tool=dossier&player=${encodeURIComponent(rookie.name)}`} className="player-link">{rookie.name}</a> ({rookie.position}, {rookie.team || 'N/A'})</h3>
                                <span className="rank">#{rookie.rank}</span>
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
                                  <h4><a href={`/?tool=dossier&player=${encodeURIComponent(player.name)}`} className="player-link">{player.name}</a></h4>
                                  <p>{player.justification}</p>
                              </div>
                          )) : <p>No sleepers found.</p>}
                      </div>
                      <div className="market-column">
                          <h3>Busts (Overvalued)</h3>
                          {marketInefficiencies.busts.length > 0 ? marketInefficiencies.busts.map((player, index) => (
                              <div key={`bust-${index}`} className="analysis-card bust">
                                  <h4><a href={`/?tool=dossier&player=${encodeURIComponent(player.name)}`} className="player-link">{player.name}</a></h4>
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
                  {keeperList.map((keeper, index) => (
                    <li key={index} className="list-item"><span><strong>{keeper.name}</strong> (Round {keeper.round})</span><button className="remove-btn" onClick={() => setKeeperList(prev => prev.filter((_, i) => i !== index))}>×</button></li>
                  ))}
                </ul>
              </div>
              <button onClick={evaluateKeepers} className="action-button">Analyze All Keepers</button>
              <div id="keeper-loader" className="loader" style={{ display: 'none' }}></div>
              <div id="keeper-result" className="result-box" dangerouslySetInnerHTML={{ __html: converter.makeHtml(keeperResult) }}></div>
            </section>
          )}
          
          {activeTool === 'trade' && (
            <section id="trade">
              <div className="tool-header"><h2>Trade Analyzer</h2><p>Get an unbiased analysis of any trade proposal.</p></div>
              <div className="trade-box">
                <div className="trade-side card">
                  <h3>I Receive:</h3>
                  <div className="form-group-inline"><input type="text" id="trade-my-asset-input" placeholder="Add player or pick..." /><button onClick={() => addAsset('my')}>Add</button></div>
                  <ul className="item-list">
                    {myTradeAssets.map((asset, index) => (
                      <li key={index} className="list-item"><span>{asset}</span><button className="remove-btn" onClick={() => setMyTradeAssets(prev => prev.filter((_, i) => i !== index))}>×</button></li>
                    ))}
                  </ul>
                </div>
                <div className="trade-side card">
                  <h3>I Give Away:</h3>
                  <div className="form-group-inline"><input type="text" id="trade-partner-asset-input" placeholder="Add player or pick..." /><button onClick={() => addAsset('partner')}>Add</button></div>
                  <ul className="item-list">
                    {partnerTradeAssets.map((asset, index) => (
                      <li key={index} className="list-item"><span>{asset}</span><button className="remove-btn" onClick={() => setPartnerTradeAssets(prev => prev.filter((_, i) => i !== index))}>×</button></li>
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
                <div className="draft-board-container">
                    <h3>Your Draft Board</h3>
                    <div className="draft-board">
                        {Array.from({ length: 15 }, (_, i) => i + 1).map(round => (
                            <div key={round} className="round-card">
                                <label htmlFor={`round-${round}-player`}>Round {round}</label>
                                <div className="autoComplete_wrapper">
                                    <input id={`round-${round}-player`} type="text" placeholder="Enter player..." onChange={saveDraftBoard} />
                                </div>
                            </div>
                        ))}
                    </div>
                </div>
            </section>
          )}

          {activeTool === 'trending' && (
            <section id="trending">
              <div className="tool-header"><h2>Trending Players</h2><p>See who's being added most on Sleeper in the last 48 hours.</p></div>
              <div className="card">
                <table id="trending-table">
                  <thead><tr><th>Player</th><th>Team</th><th>Position</th><th>Pos. Rank</th><th>Adds (48hr)</th></tr></thead>
                  <tbody>
                    {trendingData.length > 0 ? trendingData.map((player, index) => (
                      <tr key={index}>
                        <td><a href={`/?tool=d_ossier&player=${encodeURIComponent(player.name)}`} className="player-link">{player.name}</a></td>
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

          {activeTool === 'settings' && (
            <section id="settings">
              <div className="tool-header"><h2>Settings</h2><p>Manage application data and integrations.</p></div>
              <div className="card">
                <h3>Clear Saved Data</h3>
                <p>This action will permanently delete your saved Google API key and your draft board from this browser.</p>
                <button onClick={resetApplication} className="btn-danger">Clear All Data & Reset</button>
                <h3 style={{ marginTop: '40px' }}>Yahoo Fantasy Integration</h3>
                <p>Connect your Yahoo Fantasy account to unlock live data features (coming soon).</p>
                <a href="https://ratm-yff.onrender.com/auth/yahoo" className="action-button">Authorize with Yahoo</a>
                <div id="yahoo-auth-status" style={{ marginTop: '20px' }}></div>
                <button onClick={checkYahooAuthStatus} style={{ marginTop: '10px' }}>Check Auth Status</button>
                <div id="yahoo-profile-data" className="result-box" style={{ marginTop: '10px' }}></div>
              </div>
            </section>
          )}

        </div>
      </div>
    </>
  );
}

export default App;