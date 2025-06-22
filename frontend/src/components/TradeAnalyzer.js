import React, { useState, useEffect, useCallback } from 'react';
import autoComplete from '@tarekraafat/autocomplete.js';
import showdown from 'showdown'; // Import showdown for rendering markdown

function TradeAnalyzer({ makeApiRequest, allPlayers, converter }) {
  const [tradeResult, setTradeResult] = useState('');
  const [myTradeAssets, setMyTradeAssets] = useState([]);
  const [partnerTradeAssets, setPartnerTradeAssets] = useState([]);
  const [tradeScoringFormat, setTradeScoringFormat] = useState('PPR');
  const [myPlayerInput, setMyPlayerInput] = useState('');
  const [partnerPlayerInput, setPartnerPlayerInput] = useState('');
  const [myPickInput, setMyPickInput] = useState('');
  const [partnerPickInput, setPartnerPickInput] = useState('');

  const evaluateTrade = useCallback(() => {
    if (myTradeAssets.length === 0 || partnerTradeAssets.length === 0) {
      alert('Please add assets to both sides of the trade.');
      return;
    }
    const loader = document.getElementById('trade-loader');
    if (loader) loader.style.display = 'block';
    setTradeResult(''); // Clear previous results

    makeApiRequest('/trade_analyzer', { my_assets: myTradeAssets, partner_assets: partnerTradeAssets, scoring_format: tradeScoringFormat })
      .then(data => {
        if (data && (data.result || data.analysis)) {
          setTradeResult(data.result || data.analysis);
        } else {
          setTradeResult('<p style="color: var(--text-muted);">The Analyst returned an empty response.</p>');
        }
      })
      .catch(error => {
        setTradeResult(`<p style="color: var(--danger-color);">An error occurred: ${error.message}</p>`);
      })
      .finally(() => {
        if (loader) loader.style.display = 'none';
      });
  }, [makeApiRequest, myTradeAssets, partnerTradeAssets, tradeScoringFormat]);

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

  // Autocomplete for Trade Analyzer
  useEffect(() => {
    if (allPlayers.length === 0) return;

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
  }, [allPlayers]);

  return (
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
  );
}

export default TradeAnalyzer;
