import React, { useEffect, useState, useCallback } from 'react';
import autoComplete from '@tarekraafat/autocomplete.js';

const RosterInput = ({ id, label, allPlayers }) => {
  useEffect(() => {
    if (allPlayers.length > 0) {
      new autoComplete({
        selector: `#${id}`,
        placeHolder: `Enter player for ${label}...`,
        data: { src: allPlayers, cache: true },
        resultItem: { highlight: true },
        events: {
          input: {
            selection: (event) => {
              const selection = event.detail.selection.value;
              document.querySelector(`#${id}`).value = selection;
            },
          },
        },
      });
    }
  }, [allPlayers, id, label]);

  return (
    <div className="roster-input-group">
      <label htmlFor={id}>{label}</label>
      <div className="autoComplete_wrapper">
        <input id={id} type="text" />
      </div>
    </div>
  );
};

const WaiverWireAssistant = ({ allPlayers, onAnalyze, analysisResult, isLoading }) => {
  const rosterPositions = {
    Starters: ['QB', 'WR1', 'WR2', 'RB1', 'RB2', 'TE', 'W-T', 'W-R-T', 'K', 'DEF'],
    'Bench & IR': ['BN1', 'BN2', 'BN3', 'BN4', 'BN5', 'BN6', 'IR1', 'IR2'],
  };

  const [playerToAdd, setPlayerToAdd] = useState('');
  const [activeTab, setActiveTab] = useState('Starters');

  const sanitizeId = (label) => label.replace(/\//g, '-');

  const handleAnalyzeClick = () => {
    const roster = {};
    Object.values(rosterPositions).flat().forEach(pos => {
        const sanitizedId = sanitizeId(pos);
        const input = document.getElementById(`roster-input-${sanitizedId}`);
        if (input && input.value) {
            roster[pos] = input.value;
        }
    });
    onAnalyze(roster, playerToAdd);
  };
  
  useEffect(() => {
    if (allPlayers.length > 0) {
        new autoComplete({
            selector: '#player-to-add',
            placeHolder: "Enter player to add...",
            data: { src: allPlayers, cache: true },
            resultItem: { highlight: true },
            events: {
                input: {
                    selection: (event) => {
                        const selection = event.detail.selection.value;
                        setPlayerToAdd(selection);
                    },
                },
            },
        });
    }
  }, [allPlayers]);

  const handleTabChange = (tab) => {
    setActiveTab(tab);
  };

  return (
    <section id="waiver-swap">
      <div className="tool-header">
        <h2>Waiver Wire Swap Analyzer</h2>
        <p>Enter your roster and a player to see if you should make a move.</p>
      </div>
      <div className="two-column-layout">
        <div className="column-left">
          <div className="card">
            <h3>Your Roster</h3>
            <div className="tab-navigation">
              {Object.keys(rosterPositions).map(tab => (
                <button
                  key={tab}
                  className={`tab-button ${activeTab === tab ? 'active' : ''}`}
                  onClick={() => handleTabChange(tab)}
                >
                  {tab}
                </button>
              ))}
            </div>
            <div className="tab-content">
              {Object.entries(rosterPositions).map(([category, positions]) => (
                <div
                  key={category}
                  className={`tab-pane ${activeTab === category ? 'active' : 'hidden'}`}
                >
                  <h4>{category}</h4>
                  <div className="waiver-grid">
                    {positions.map((pos) => {
                      const sanitizedId = sanitizeId(pos);
                      return <RosterInput key={pos} id={`roster-input-${sanitizedId}`} label={pos} allPlayers={allPlayers} />;
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
        <div className="column-right">
          <div className="card">
            <h3>Player to Consider Adding</h3>
            <div className="form-group-inline">
                <div className="autoComplete_wrapper" style={{ flexGrow: 1 }}>
                    <input id="player-to-add" type="text" value={playerToAdd} onChange={(e) => setPlayerToAdd(e.target.value)} />
                </div>
                <button onClick={handleAnalyzeClick} className="action-button" disabled={isLoading}>
                {isLoading ? 'Analyzing...' : 'Analyze Swap'}
              </button>
            </div>
          </div>
          {isLoading && <div id="waiver-swap-loader" className="loader" style={{ display: 'block' }}></div>}
          
          {analysisResult && (
            <div id="waiver-swap-result" className="result-box" dangerouslySetInnerHTML={{ __html: analysisResult }}></div>
          )}
        </div>
      </div>
    </section>
  );
};

export default WaiverWireAssistant;
