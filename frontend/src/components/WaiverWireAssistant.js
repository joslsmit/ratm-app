import React, { useEffect, useState, useCallback } from 'react';
import autoComplete from '@tarekraafat/autocomplete.js';
import styles from './WaiverWireAssistant.module.css';

const RosterInput = ({ id, label, allPlayers }) => {
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
              document.querySelector(`#${id}`).value = selection;
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
  }, [allPlayers, id, label]);

  const handleClearInput = () => {
    const input = document.querySelector(`#${id}`);
    if (input) {
      input.value = '';
    }
  };

  return (
    <div className={styles.rosterInputGroup}>
      <label htmlFor={id}>{label}</label>
      <div>
        <div className={styles.autoCompleteWrapper}>
          <input id={id} type="text" />
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
      <div className={styles.singleColumnLayout}>
        <div className={styles.rosterSection}>
          <div className={styles.card}>
            <h3>Your Roster</h3>
            <p style={{ color: 'var(--text-muted)', marginBottom: '10px' }}>Use the tabs below to input your current roster for each position.</p>
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
                      return <RosterInput key={pos} id={`roster-input-${sanitizedId}`} label={pos} allPlayers={allPlayers} />;
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
        <div className={styles.waiverPlayerSection}>
          <div className={styles.card}>
            <h3>Player to Consider Adding</h3>
            <div className={styles.formGroupInline}>
                <div className={styles.autoCompleteWrapper}>
                    <input id="player-to-add" type="text" value={playerToAdd} onChange={(e) => setPlayerToAdd(e.target.value)} />
                </div>
                <button onClick={handleAnalyzeClick} className={styles.actionButton} disabled={isLoading}>
                {isLoading ? 'Analyzing...' : 'Analyze Swap'}
              </button>
            </div>
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
