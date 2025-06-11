import React, { useState, useEffect, useCallback } from 'react';
import showdown from 'showdown';
import autoComplete from '@tarekraafat/autocomplete.js';

const API_BASE_URL = 'https://ratm-yff.onrender.com/api'; // Backend API URL

function App() {
  const [userApiKey, setUserApiKey] = useState(localStorage.getItem('geminiApiKey'));
  const [showApiKeyModal, setShowApiKeyModal] = useState(!userApiKey);
  const [activeTool, setActiveTool] = useState('dossier');
  const [allPlayers, setAllPlayers] = useState([]);
  const [staticPlayerData, setStaticPlayerData] = useState({});
  const [trendingData, setTrendingData] = useState([]);
  const [sortDirection, setSortDirection] = useState({ position: 'asc', adds: 'desc', team: 'asc', pos_rank: 'asc' });
  const [marketInefficiencies, setMarketInefficiencies] = useState({ sleepers: [], busts: [] });
  const [rookieRankings, setRookieRankings] = useState([]);
  const [tiersResult, setTiersResult] = useState(''); // State for tiers markdown
  const [keeperResult, setKeeperResult] = useState(''); // State for keeper evaluator markdown
  const [tradeResult, setTradeResult] = useState(''); // State for trade analyzer markdown
  const [draftAnalysisResult, setDraftAnalysisResult] = useState(''); // State for draft analysis markdown
  const [rosterCompositionResult, setRosterCompositionResult] = useState(''); // State for roster composition analysis markdown

  // States for list items
  const [keeperList, setKeeperList] = useState([]);
  const [myTradeAssets, setMyTradeAssets] = useState([]);
  const [partnerTradeAssets, setPartnerTradeAssets] = useState([]);
  const [keeperPlayerName, setKeeperPlayerName] = useState(''); // New state for keeper player name input
  const [keeperRoundInput, setKeeperRoundInput] = useState(''); // New state for keeper round input

  const converter = new showdown.Converter({ simplifiedAutoLink: true, tables: true, strikethrough: true });

  const checkApiKey = useCallback(() => {
    if (!userApiKey) {
      setShowApiKeyModal(true);
    } else {
      setShowApiKeyModal(false);
    }
  }, [userApiKey]);

  const saveApiKey = (key) => {
    if (key) {
      setUserApiKey(key);
      localStorage.setItem('geminiApiKey', key);
      setShowApiKeyModal(false);
    } else {
      alert('Please enter a valid API key.');
    }
  };

  const makeApiRequest = useCallback(async (endpoint, body) => {
    if (!userApiKey) {
      alert('API Key not found. Please enter your key.');
      checkApiKey();
      return null;
    }
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-API-Key': userApiKey }, // X-API-Key is still sent but unused on backend
      body: JSON.stringify(body)
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "An unknown server error occurred.");
    return data;
  }, [userApiKey, checkApiKey]);

  const renderGeneric = useCallback(async (toolName, endpoint, body) => {
    const loader = document.getElementById(`${toolName}-loader`);
    const resultArea = document.getElementById(`${toolName}-result`);
    if(loader) loader.style.display = 'block';
    if(resultArea) resultArea.innerHTML = `<p style="color: var(--text-muted);">The Analyst is thinking...</p>`;
    try {
        const data = await makeApiRequest(endpoint, body);
        if(data && data.result) {
            // For generic markdown results, set the state
            switch(toolName) {
                case 'tiers': setTiersResult(data.result); break;
                case 'keeper': setKeeperResult(data.result); break;
                case 'trade': setTradeResult(data.result); break;
                case 'draft-analysis': setDraftAnalysisResult(data.result); break;
                case 'draft-comp': setRosterCompositionResult(data.result); break;
                default: // For dossier, directly update innerHTML as it's a single result
                    if(resultArea) resultArea.innerHTML = converter.makeHtml(data.result);
            }
        }
    } catch (error) {
        if(resultArea) resultArea.innerHTML = `<p style="color: var(--danger-color);">An error occurred: ${error.message}</p>`;
    } finally {
        if(loader) loader.style.display = 'none';
    }
  }, [makeApiRequest, converter]);

  useEffect(() => {
    fetch(`${API_BASE_URL}/all_player_names_with_data`)
      .then(response => response.json())
      .then(data => {
        setAllPlayers(data.map(p => p.name));
        const staticData = {};
        data.forEach(p => { staticData[p.name.toLowerCase()] = p; });
        setStaticPlayerData(staticData);
      })
      .catch(error => console.error("Error fetching player names:", error));
  }, []);

  useEffect(() => {
    const initAutoComplete = (selector) => {
      const element = document.querySelector(selector);
      if (element && allPlayers.length > 0) { // Ensure element exists and players are loaded
        new autoComplete({
          selector: selector,
          placeHolder: "Search for a player...",
          data: { src: allPlayers, cache: true },
          resultItem: { highlight: true },
          events: {
            input: {
              selection: event => {
                const inputElement = document.querySelector(selector);
                inputElement.value = event.detail.selection.value;
                // Update React state for specific inputs
                if (selector === '#keeper-player-name') {
                  setKeeperPlayerName(event.detail.selection.value);
                }
                if (inputElement.id.startsWith("round-")) saveDraftBoard();
              }
            }
          }
        });
      }
    };

    // Initialize autocomplete for currently active/rendered inputs
    if (activeTool === 'dossier') initAutoComplete('#dossier-player-name');
    if (activeTool === 'keeper') initAutoComplete('#keeper-player-name');
    if (activeTool === 'draft') {
      initAutoComplete('#draft-pick-player');
      for (let i = 1; i <= 15; i++) initAutoComplete(`#round-${i}-player`);
    }
  }, [allPlayers, activeTool]); // Re-run when allPlayers or activeTool changes


  useEffect(() => {
    const handleUrlParams = () => {
      const urlParams = new URLSearchParams(window.location.search);
      const tool = urlParams.get('tool');
      const player = urlParams.get('player');
      if (tool === 'dossier' && player) {
        setActiveTool('dossier');
        setTimeout(() => {
          const dossierInput = document.getElementById('dossier-player-name');
          if (dossierInput) {
            dossierInput.value = decodeURIComponent(player);
            generateDossier();
          }
        }, 500);
      } else {
        const initialTool = window.location.hash.substring(1) || 'dossier';
        setActiveTool(initialTool);
      }
    };

    window.addEventListener('hashchange', () => setActiveTool(window.location.hash.substring(1) || 'dossier'));
    handleUrlParams();
    checkApiKey();
  }, [checkApiKey]);

  // Helper functions for draft board and roster composition
  const getDraftBoardState = () => {
    const board = {};
    for (let i = 1; i <= 15; i++) {
      const playerName = document.getElementById(`round-${i}-player`)?.value;
      if (playerName) board[`Round ${i}`] = playerName;
    }
    return board;
  };

  const saveDraftBoard = () => {
    const board = {};
    for (let i = 1; i <= 15; i++) {
      const playerName = document.getElementById(`round-${i}-player`)?.value;
      if (playerName) board[i] = playerName;
    }
    localStorage.setItem('draftBoard', JSON.stringify(board));
    updateRosterComposition();
  };

  const loadDraftBoard = () => {
    const savedBoard = localStorage.getItem('draftBoard');
    if (savedBoard) {
      const board = JSON.parse(savedBoard);
      for (const round in board) {
        const input = document.getElementById(`round-${round}-player`);
        if (input) input.value = board[round];
      }
    }
    updateRosterComposition();
  };

  const updateRosterComposition = () => {
    const counts = { QB: 0, RB: 0, WR: 0, TE: 0, K: 0, DST: 0 };
    const draftedPlayers = getDraftBoardState();
    for (const round in draftedPlayers) {
      const playerName = draftedPlayers[round].toLowerCase();
      const playerData = staticPlayerData[playerName] || Object.values(staticPlayerData).find(p => p.name.toLowerCase() === playerName);
      if (playerData && playerData.pos_rank) {
        const pos = playerData.pos_rank.replace(/\d/g, '');
        if (pos in counts) counts[pos]++;
      }
    }
    for (const pos in counts) {
      const cell = document.getElementById(`comp-${pos.toLowerCase()}`);
      if (cell) cell.textContent = counts[pos];
    }
    return counts;
  };


  const createDraftBoard = () => {
    const boardContainer = document.querySelector('.draft-board');
    if (!boardContainer) return;
    let boardHTML = '';
    for (let i = 1; i <= 15; i++) {
      boardHTML += `<div class="round-card"><label for="round-${i}-player">Round ${i}</label><div class="autoComplete_wrapper"><input id="round-${i}-player" type="text" placeholder="Enter player..." onChange={saveDraftBoard}></div></div>`;
    }
    boardContainer.innerHTML = boardHTML;
  };

  const resetApplication = () => {
    if (window.confirm("Are you sure you want to clear all saved data? This will remove your API key and saved draft board and cannot be undone.")) {
      localStorage.removeItem('geminiApiKey');
      localStorage.removeItem('draftBoard');
      window.location.href = '/';
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
      if (statusDiv) statusDiv.innerHTML = `<p style="color: var(--danger-color);">❌ Could not connect to backend or check status: ${error.message}</p>`;
    }
  }, [makeApiRequest]); // makeApiRequest is a dependency

  const generateDossier = () => renderGeneric('dossier', '/player_dossier', { player_name: document.getElementById('dossier-player-name').value });
  
  const generateTiers = useCallback(async () => {
    const loader = document.getElementById('tiers-loader');
    const resultArea = document.getElementById('tiers-result');
    if(loader) loader.style.display = 'block';
    if(resultArea) resultArea.innerHTML = '';
    try {
        const data = await makeApiRequest('/generate_tiers', { position: document.getElementById('tiers-pos').value });
        setTiersResult(data.result); // Set state with raw markdown
    } catch(error) {
        if(resultArea) resultArea.innerHTML = `<p style="color: var(--danger-color);">An error occurred: ${error.message}</p>`;
    } finally {
        if(loader) loader.style.display = 'none';
    }
  }, [makeApiRequest]);

  const showDossierForPlayer = useCallback((event, playerName) => {
    event.preventDefault();
    setActiveTool('dossier');
    setTimeout(() => {
        const dossierInput = document.getElementById('dossier-player-name');
        if (dossierInput) {
            dossierInput.value = playerName;
            generateDossier();
        }
    }, 100);
  }, [generateDossier]);

  const findMarketInefficiencies = useCallback(async () => {
    const loader = document.getElementById('market-loader');
    const resultArea = document.getElementById('market-result');
    if(loader) loader.style.display = 'block';
    if(resultArea) resultArea.innerHTML = '';
    try {
        const data = await makeApiRequest('/find_market_inefficiencies', { position: document.getElementById('market-pos').value });
        setMarketInefficiencies(data); // Set state instead of innerHTML
    } catch(error) {
        if(resultArea) resultArea.innerHTML = `<p style="color: var(--danger-color);">An error occurred: ${error.message}</p>`;
    } finally {
        if(loader) loader.style.display = 'none';
    }
  }, [makeApiRequest]);

  const generateRookieRankings = useCallback(async () => {
    const loader = document.getElementById('rookie-loader');
    const resultArea = document.getElementById('rookie-result');
    if(loader) loader.style.display = 'block';
    if(resultArea) resultArea.innerHTML = '';
    try {
        const rookies = await makeApiRequest('/rookie_rankings', { position: document.getElementById('rookie-pos').value });
        setRookieRankings(rookies); // Set state instead of innerHTML
    } catch (error) {
        if(resultArea) resultArea.innerHTML = `<p style="color: var(--danger-color);">An error occurred: ${error.message}</p>`;
    } finally {
        if(loader) loader.style.display = 'none';
    }
  }, [makeApiRequest]);

  const evaluateKeepers = useCallback(() => {
    const items = document.querySelectorAll('#keeper-list .list-item');
    if (items.length === 0) return alert('Please add at least one keeper.');
    const keepers = Array.from(items).map(item => ({ name: item.dataset.name, round: item.dataset.round }));
    const loader = document.getElementById('keeper-loader');
    const resultArea = document.getElementById('keeper-result');
    if(loader) loader.style.display = 'block';
    if(resultArea) resultArea.innerHTML = `<p style="color: var(--text-muted);">The Analyst is thinking...</p>`;
    try {
        makeApiRequest('/keeper_evaluation', { keepers: keepers }).then(data => {
            if(data && data.result) {
                setKeeperResult(data.result); // Set state with raw markdown
            }
        });
    } catch (error) {
        if(resultArea) resultArea.innerHTML = `<p style="color: var(--danger-color);">An error occurred: ${error.message}</p>`;
    } finally {
        if(loader) loader.style.display = 'none';
    }
  }, [makeApiRequest]);

  const evaluateTrade = useCallback(() => {
    const myAssets = Array.from(document.querySelectorAll('#trade-my-assets .list-item')).map(item => item.dataset.value);
    const partnerAssets = Array.from(document.querySelectorAll('#trade-partner-assets .list-item')).map(item => item.dataset.value);
    if (myAssets.length === 0 || partnerAssets.length === 0) return alert('Please add assets to both sides.');
    const loader = document.getElementById('trade-loader');
    const resultArea = document.getElementById('trade-result');
    if(loader) loader.style.display = 'block';
    if(resultArea) resultArea.innerHTML = `<p style="color: var(--text-muted);">The Analyst is thinking...</p>`;
    try {
        makeApiRequest('/trade_analyzer', { my_assets: myAssets, partner_assets: partnerAssets }).then(data => {
            if(data && data.result) {
                setTradeResult(data.result); // Set state with raw markdown
            }
        });
    } catch (error) {
        if(resultArea) resultArea.innerHTML = `<p style="color: var(--danger-color);">An error occurred: ${error.message}</p>`;
    } finally {
        if(loader) loader.style.display = 'none';
    }
  }, [makeApiRequest]);

  const suggestPosition = useCallback(() => {
    const currentRound = document.getElementById('draft-current-round').value;
    if (!currentRound) return alert('Please enter the current round.');
    const loader = document.getElementById('draft-analysis-loader');
    const resultArea = document.getElementById('draft-analysis-result');
    if(loader) loader.style.display = 'block';
    if(resultArea) resultArea.innerHTML = `<p style="color: var(--text-muted);">The Analyst is thinking...</p>`;
    try {
        makeApiRequest('/suggest_position', { draft_board: getDraftBoardState(), current_round: currentRound }).then(data => {
            if(data && data.result) {
                setDraftAnalysisResult(data.result); // Set state with raw markdown
            }
        });
    } catch (error) {
        if(resultArea) resultArea.innerHTML = `<p style="color: var(--danger-color);">An error occurred: ${error.message}</p>`;
    } finally {
        if(loader) loader.style.display = 'none';
    }
  }, [makeApiRequest]);

  const evaluatePick = useCallback(() => {
    const playerToPick = document.getElementById('draft-pick-player').value;
    const currentRound = document.getElementById('draft-current-round').value;
    if (!playerToPick || !currentRound) return alert('Please enter a player and the current round.');
    const loader = document.getElementById('draft-analysis-loader');
    const resultArea = document.getElementById('draft-analysis-result');
    if(loader) loader.style.display = 'block';
    if(resultArea) resultArea.innerHTML = `<p style="color: var(--text-muted);">The Analyst is thinking...</p>`;
    try {
        makeApiRequest('/pick_evaluator', { draft_board: getDraftBoardState(), player_to_pick: playerToPick, current_round: currentRound }).then(data => {
            if(data && data.result) {
                setDraftAnalysisResult(data.result); // Set state with raw markdown
            }
        });
    } catch (error) {
        if(resultArea) resultArea.innerHTML = `<p style="color: var(--danger-color);">An error occurred: ${error.message}</p>`;
    } finally {
        if(loader) loader.style.display = 'none';
    }
  }, [makeApiRequest]);

  const analyzeComposition = useCallback(() => {
    const loader = document.getElementById('draft-comp-loader');
    const resultArea = document.getElementById('draft-comp-result');
    if(loader) loader.style.display = 'block';
    if(resultArea) resultArea.innerHTML = `<p style="color: var(--text-muted);">The Analyst is thinking...</p>`;
    try {
        makeApiRequest('/roster_composition_analysis', { composition: updateRosterComposition() }).then(data => {
            if(data && data.result) {
                setRosterCompositionResult(data.result); // Set state with raw markdown
            }
        });
    } catch (error) {
        if(resultArea) resultArea.innerHTML = `<p style="color: var(--danger-color);">An error occurred: ${error.message}</p>`;
    } finally {
        if(loader) loader.style.display = 'none';
    }
  }, [makeApiRequest]);

  const addKeeper = () => {
    const roundValue = parseInt(keeperRoundInput, 10); // Use state for round input
    if (keeperPlayerName && !isNaN(roundValue) && roundValue > 0) { // Use state for player name
        setKeeperList(prevList => [...prevList, { name: keeperPlayerName, round: roundValue }]);
        setKeeperPlayerName(''); // Clear input using state
        setKeeperRoundInput(''); // Clear input using state
        document.getElementById('keeper-player-name').focus(); // Focus for next entry
    } else {
        alert('Please enter a valid player name and a positive number for the draft round.');
    }
  };
  const addAsset = (side) => {
    const input = document.getElementById(`trade-${side}-asset-input`);
    if (input.value) {
        if (side === 'my') {
            setMyTradeAssets(prevAssets => [...prevAssets, input.value]);
        } else {
            setPartnerTradeAssets(prevAssets => [...prevAssets, input.value]);
        }
        input.value = ''; input.focus();
    }
    };
    
    const sortTable = useCallback((column, dataToSort = trendingData) => {
        const dir = sortDirection[column];
        const getRankNumber = (rankString) => {
            if (typeof rankString !== 'string') return 999;
            const match = rankString.match(/\d+/);
            return match ? parseInt(match[0], 10) : 999;
        };
        const getRankPrefix = (rankString) => {
            if (typeof rankString !== 'string') return 'ZZZ';
            const match = rankString.match(/^[A-Z]+/);
            return match ? match[0] : 'ZZZ';
        };
        const sorted = [...dataToSort].sort((a, b) => {
            let valA = a[column], valB = b[column];
            if (column === 'pos_rank') {
                const partsA = { prefix: getRankPrefix(valA), num: getRankNumber(valA) };
                const partsB = { prefix: getRankPrefix(valB), num: getRankNumber(valB) };
                if (partsA.prefix !== partsB.prefix) return dir === 'asc' ? partsA.prefix.localeCompare(partsB.prefix) : partsB.prefix.localeCompare(partsA.prefix);
                return dir === 'asc' ? partsA.num - partsB.num : partsB.num - partsA.num;
            }
            if (typeof valA === 'number') { return dir === 'asc' ? valA - valB : valB - valA; }
            if (typeof valA === 'string') { return dir === 'asc' ? (valA || '').localeCompare(valB || '') : (valB || '').localeCompare(valA || ''); }
            return 0;
        });
        setTrendingData(sorted);
        setSortDirection(prev => ({ ...prev, [column]: dir === 'asc' ? 'desc' : 'asc' }));
    }, [sortDirection, trendingData]);

    const fetchTrending = useCallback(async () => {
        const loader = document.getElementById('trending-loader');
        const tableBody = document.querySelector('#trending-table tbody');
        if(loader) loader.style.display = 'block';
        try {
            const response = await fetch(`${API_BASE_URL}/trending_players`);
            if (!response.ok) throw new Error('Network response was not ok.');
            const data = await response.json();
            setTrendingData(data);
            sortTable('adds', data); // Pass data to sortTable
        } catch (error) {
            if(tableBody) tableBody.innerHTML = `<tr><td colspan="5" style="text-align: center; color: var(--danger-color);">Could not fetch data.</td></tr>`;
        } finally {
            if(loader) loader.style.display = 'none';
        }
    }, [sortTable]);

  // Initial setup for draft board
  useEffect(() => {
    createDraftBoard();
    loadDraftBoard();
  }, []);

  // Fetch trending data when component mounts or activeTool changes to 'trending'
  useEffect(() => {
    if (activeTool === 'trending' && trendingData.length === 0) {
      fetchTrending();
    }
  }, [activeTool, trendingData.length, fetchTrending]);


  return (
    <>
      {showApiKeyModal && (
        <div id="api-key-modal" className="api-key-modal" style={{ display: 'flex' }}>
          <div className="api-key-modal-content">
            <h2>Welcome to the RATM Draft Kit</h2>
            <p>To power the AI features, please enter your Google Gemini API key. This key is saved only in your browser and is never sent to our server.</p>
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
            <hr style={{ borderColor: '#e2e8f0', margin: '10px 5px' }} />
            <li><a href="#keeper" className={activeTool === 'keeper' ? 'active' : ''} onClick={() => setActiveTool('keeper')}>Keeper Evaluator</a></li>
            <li><a href="#trade" className={activeTool === 'trade' ? 'active' : ''} onClick={() => setActiveTool('trade')}>Trade Analyzer</a></li>
            <li><a href="#draft" className={activeTool === 'draft' ? 'active' : ''} onClick={() => setActiveTool('draft')}>Draft Assistant</a></li>
            <hr style={{ borderColor: '#e2e8f0', margin: '10px 5px' }} />
            <li><a href="#trending" className={activeTool === 'trending' ? 'active' : ''} onClick={() => setActiveTool('trending')}>Trending Players</a></li>
          </ul>
        </nav>
        <nav className="utility-nav">
          <ul>
            <li className="nav-item-bottom"><a href="#settings" className={activeTool === 'settings' ? 'active' : ''} onClick={() => setActiveTool('settings')}>Settings</a></li>
          </ul>
        </nav>
        <div className="sidebar-footer"><p>© 2025 Redd Against the Machine</p></div>
      </div>

      <div className="main-content">
        <div className="content-wrapper">
          {activeTool === 'dossier' && (
            <section id="dossier" className="tool-section active">
              <div className="tool-header"><h2>Player Dossier</h2><p>Get a complete 360-degree scouting report on any player.</p></div>
              <div className="card"><div className="form-group-inline"><div className="autoComplete_wrapper"><input id="dossier-player-name" type="text" placeholder="Enter player name..." /></div><button onClick={generateDossier}>Generate</button></div></div>
              <div id="dossier-loader" className="loader" style={{ display: 'none' }}></div><div id="dossier-result" className="result-box"></div>
            </section>
          )}
          {activeTool === 'rookie' && (
            <section id="rookie" className="tool-section active">
              <div className="tool-header"><h2>2025 Rookie Rankings</h2><p>Get AI-powered rankings and analysis for the incoming rookie class.</p></div>
              <div className="card"><div className="form-group-inline"><select id="rookie-pos"><option value="all">All Offensive Positions</option><option value="QB">QB</option><option value="RB">RB</option><option value="WR">WR</option><option value="TE">TE</option></select><button onClick={generateRookieRankings}>Generate Rankings</button></div></div>
              <div id="rookie-loader" className="loader" style={{ display: 'none' }}></div>
              {/* Render Rookie Rankings using React state */}
              {rookieRankings.length > 0 && (
                <div className="result-box-cards">
                  {rookieRankings.map((rookie, index) => (
                    <div key={index} className="rookie-card">
                      <div className="rookie-header">
                        <h3><a href={`/?tool=dossier&player=${encodeURIComponent(rookie.name)}`} target="_blank" className="player-link">{rookie.name}</a> ({rookie.position}, {rookie.team || 'N/A'})</h3>
                        <span className="rank">#{rookie.rank}</span>
                      </div>
                      <div className="rookie-details">
                        <span><strong>Pos. Rank:</strong> {rookie.pos_rank || 'N/A'}</span>
                        <span><strong>ADP: {rookie.adp || 'N/A'}</strong></span>
                      </div>
                      <div className="rookie-analysis"><p>{rookie.analysis}</p></div>
                    </div>
                  ))}
                </div>
              )}
              {rookieRankings.length === 0 && (
                <p>No rookie rankings found based on current data.</p>
              )}
            </section>
          )}
          {activeTool === 'tiers' && (
            <section id="tiers" className="tool-section active">
              <div className="tool-header"><h2>Positional Tiers</h2><p>Generate tier-based rankings to understand value drop-offs.</p></div>
              <div className="card"><div className="form-group-inline"><select id="tiers-pos"><option value="QB">QB</option><option value="RB">RB</option><option value="WR">WR</option><option value="TE">TE</option><option value="K">K</option><option value="DST">DST</option></select><button onClick={generateTiers}>Generate Tiers</button></div></div>
              <div id="tiers-loader" className="loader" style={{ display: 'none' }}></div>
              {tiersResult && <div id="tiers-result" className="result-box" dangerouslySetInnerHTML={{ __html: converter.makeHtml(tiersResult) }}></div>}
            </section>
          )}
          {activeTool === 'market' && (
            <section id="market" className="tool-section active">
              <div className="tool-header"><h2>Market Inefficiency Finder</h2><p>Discover potential sleepers and busts by comparing data sources.</p></div>
              <div className="card"><div className="form-group-inline"><select id="market-pos"><option value="all">All Positions</option><option value="QB">QB</option><option value="RB">RB</option><option value="WR">WR</option><option value="TE">TE</option><option value="K">K</option><option value="DST">DST</option></select><button onClick={findMarketInefficiencies}>Find</button></div></div>
              <div id="market-loader" className="loader" style={{ display: 'none' }}></div>
              {/* Render Market Inefficiencies using React state */}
              {marketInefficiencies.sleepers.length > 0 && (
                <>
                  <h3>Sleepers (Undervalued)</h3>
                  <div className="result-box-grid">
                    {marketInefficiencies.sleepers.map((player, index) => (
                      <div key={index} className="analysis-card" style={{ borderLeftColor: 'var(--success-color)' }}>
                        <div className="analysis-header">
                          <h3><a href={`/?tool=dossier&player=${encodeURIComponent(player.name)}`} target="_blank" className="player-link">{player.name}</a></h3>
                        </div>
                        <div className="analysis-body"><p>{player.justification}</p></div>
                      </div>
                    ))}
                  </div>
                </>
              )}
              {marketInefficiencies.sleepers.length === 0 && (
                <p>No clear sleepers found based on current data.</p>
              )}
              {marketInefficiencies.busts.length > 0 && (
                <>
                  <h3 style={{ marginTop: '40px' }}>Busts (Overvalued)</h3>
                  <div className="result-box-grid">
                    {marketInefficiencies.busts.map((player, index) => (
                      <div key={index} className="analysis-card" style={{ borderLeftColor: 'var(--danger-color)' }}>
                        <div className="analysis-header">
                          <h3><a href={`/?tool=dossier&player=${encodeURIComponent(player.name)}`} target="_blank" className="player-link">{player.name}</a></h3>
                        </div>
                        <div className="analysis-body"><p>{player.justification}</p></div>
                      </div>
                    ))}
                  </div>
                </>
              )}
              {marketInefficiencies.busts.length === 0 && (
                <p>No clear busts found based on current data.</p>
              )}
            </section>
          )}
          {activeTool === 'keeper' && (
            <section id="keeper" className="tool-section active">
              <div className="tool-header"><h2>Keeper Evaluator</h2><p>Analyze multiple keeper options based on cost vs. value.</p></div>
              <div className="card">
                <div className="form-group-inline">
                  <div className="autoComplete_wrapper">
                    <input
                      id="keeper-player-name"
                      type="text"
                      placeholder="Player Name..."
                      value={keeperPlayerName} // Bind value to state
                      onChange={(e) => setKeeperPlayerName(e.target.value)} // Update state on change
                    />
                  </div>
                  <input
                    id="keeper-round"
                    type="number"
                    placeholder="Original Draft Round"
                    value={keeperRoundInput} // Bind value to state
                    onChange={(e) => setKeeperRoundInput(e.target.value)} // Update state on change
                  />
                  <button onClick={addKeeper}>Add</button>
                </div>
                <ul id="keeper-list" className="item-list">
                  {keeperList.map((keeper, index) => (
                    <li key={index} className="list-item" data-name={keeper.name} data-round={keeper.round}>
                      <span><strong>{keeper.name}</strong> (Round {keeper.round})</span>
                      <button className="remove-btn" onClick={() => setKeeperList(prev => prev.filter((_, i) => i !== index))}>×</button>
                    </li>
                  ))}
                </ul>
              </div>
              <button onClick={evaluateKeepers} className="action-button">Analyze All Keepers</button>
              <div id="keeper-loader" className="loader" style={{ display: 'none' }}></div>
              {keeperResult && <div id="keeper-result" className="result-box" dangerouslySetInnerHTML={{ __html: converter.makeHtml(keeperResult) }}></div>}
            </section>
          )}
          {activeTool === 'trade' && (
            <section id="trade" className="tool-section active">
              <div className="tool-header"><h2>Trade Analyzer</h2><p>Get an unbiased analysis of any trade proposal.</p></div>
              <div className="trade-box">
                <div className="trade-side card">
                  <h3>I Receive:</h3>
                  <div className="form-group-inline">
                    <input type="text" id="trade-my-asset-input" placeholder="Add player or pick..." />
                    <button onClick={() => addAsset('my')}>Add</button>
                  </div>
                  <ul id="trade-my-assets" className="item-list">
                    {myTradeAssets.map((asset, index) => (
                      <li key={index} className="list-item" data-value={asset}>
                        <span>{asset}</span>
                        <button className="remove-btn" onClick={() => setMyTradeAssets(prev => prev.filter((_, i) => i !== index))}>×</button>
                      </li>
                    ))}
                  </ul>
                </div>
                <div className="trade-side card">
                  <h3>I Give Away:</h3>
                  <div className="form-group-inline">
                    <input type="text" id="trade-partner-asset-input" placeholder="Add player or pick..." />
                    <button onClick={() => addAsset('partner')}>Add</button>
                  </div>
                  <ul id="trade-partner-assets" className="item-list">
                    {partnerTradeAssets.map((asset, index) => (
                      <li key={index} className="list-item" data-value={asset}>
                        <span>{asset}</span>
                        <button className="remove-btn" onClick={() => setPartnerTradeAssets(prev => prev.filter((_, i) => i !== index))}>×</button>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
              <button onClick={evaluateTrade} className="action-button">Analyze Trade</button>
              <div id="trade-loader" className="loader" style={{ display: 'none' }}></div>
              {tradeResult && <div id="trade-result" className="result-box" dangerouslySetInnerHTML={{ __html: converter.makeHtml(tradeResult) }}></div>}
            </section>
          )}
          {activeTool === 'draft' && (
            <section id="draft" className="tool-section active">
              <div className="tool-header"><h2>Live Draft Assistant</h2><p>Track your draft round-by-round to get real-time, value-based advice.</p></div>
              <div className="draft-dashboard">
                <div className="draft-main-panel">
                  <div className="card"><h3>Analysis & Advice</h3><div className="form-group-inline"><input type="number" id="draft-current-round" placeholder="What round is it now?" /><div className="autoComplete_wrapper"><input id="draft-pick-player" type="text" placeholder="Player being considered..." /></div></div><div className="form-group-inline"><button onClick={suggestPosition} style={{ flexGrow: 1 }}>Suggest Position</button><button onClick={evaluatePick} style={{ flexGrow: 1 }}>Evaluate Player</button></div><div id="draft-analysis-loader" className="loader" style={{ display: 'none' }}></div>
                  {draftAnalysisResult && <div id="draft-analysis-result" className="result-box" dangerouslySetInnerHTML={{ __html: converter.makeHtml(draftAnalysisResult) }}></div>}
                  </div>
                </div>
                <div className="draft-sidebar-panel">
                  <div className="card"><h3>Roster Composition</h3><table className="composition-table"><thead><tr><th>QB</th><th>RB</th><th>WR</th><th>TE</th><th>K</th><th>DST</th></tr></thead><tbody><tr><td id="comp-qb">0</td><td id="comp-rb">0</td><td id="comp-wr">0</td><td id="comp-te">0</td><td id="comp-k">0</td><td id="comp-dst">0</td></tr></tbody></table><div style={{ textAlign: 'center', marginTop: '15px' }}><button onClick={analyzeComposition}>Analyze Balance</button></div><div id="draft-comp-loader" className="loader" style={{ display: 'none' }}></div>
                  {rosterCompositionResult && <div id="draft-comp-result" className="result-box" style={{ marginTop: '15px' }} dangerouslySetInnerHTML={{ __html: converter.makeHtml(rosterCompositionResult) }}></div>}
                  </div>
                </div>
              </div>
            </section>
          )}
          {activeTool === 'trending' && (
            <section id="trending" className="tool-section active">
              <div className="tool-header"><h2>Trending Players</h2><p>See who's being added most on Sleeper in the last 48 hours.</p></div>
              <div className="card">
                <table id="trending-table">
                  <thead>
                    <tr>
                      <th>Player</th><th>Team</th><th className="sortable" onClick={() => sortTable('position')}>Position</th><th className="sortable" onClick={() => sortTable('pos_rank')}>Pos. Rank</th><th className="sortable" onClick={() => sortTable('adds')}>Adds</th>
                    </tr>
                  </thead>
                  <tbody>
                    {trendingData.map((player, index) => (
                      <tr key={index}>
                        <td><a href={`/?tool=dossier&player=${encodeURIComponent(player.name)}`} target="_blank" className="player-link">{player.name}</a></td>
                        <td>{player.team || 'N/A'}</td>
                        <td>{player.position}</td>
                        <td>{player.pos_rank || 'N/A'}</td>
                        <td>{player.adds}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <div id="trending-loader" className="loader" style={{ display: 'none' }}></div>
              </div>
            </section>
          )}
          {activeTool === 'settings' && (
            <section id="settings" className="tool-section active">
              <div className="tool-header"><h2>Settings</h2><p>Manage application data saved in your browser.</p></div>
              <div className="card">
                <h3>Clear Saved Data</h3>
                <p className="tool-header" style={{ textAlign: 'left', fontSize: '16px' }}>This action will permanently delete your saved Google API key and your saved Draft Board from this browser's local storage. The app will restart, and you will need to re-enter your API key.</p>
                <button onClick={resetApplication} className="btn-danger">Clear All Data & Reset Application</button>
                <h3 style={{ marginTop: '40px' }}>Yahoo Fantasy Integration</h3>
                <p>Connect your Yahoo Fantasy account to unlock live data features.</p>
                <button onClick={() => window.location.href = 'https://ratm-yff.onrender.com/auth/yahoo'}>Authorize with Yahoo</button>
                <div id="yahoo-auth-status" style={{ marginTop: '20px' }}></div>
                <button onClick={checkYahooAuthStatus} style={{ marginTop: '10px' }}>Check Authorization Status</button>
                <div id="yahoo-profile-data" className="result-box" style={{ marginTop: '10px' }}></div>
              </div>
            </section>
          )}
        </div>
      </div>
      <div id="draft-board-container" className="draft-board-container" style={{ display: activeTool === 'draft' ? 'flex' : 'none' }}>
        <div className="draft-board"></div>
      </div>
    </>
  );
}

export default App;
