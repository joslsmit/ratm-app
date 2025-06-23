import React, { useState, useEffect } from 'react';
import autoComplete from '@tarekraafat/autocomplete.js';
import styles from './KeeperEvaluator.module.css';

function KeeperEvaluator({
  keeperList,
  setKeeperList,
  staticPlayerData,
  normalizePlayerName,
  getEstimatedDraftRound,
  evaluateKeepers,
  keeperResult,
  converter,
  isLoading,
  allPlayers, // This prop is needed for autosuggest data
}) {
  const [keeperPlayerName, setKeeperPlayerName] = useState('');
  const [keeperRoundInput, setKeeperRoundInput] = useState('');
  const [keeperContextInput, setKeeperContextInput] = useState('');
  const [editingKeeperIndex, setEditingKeeperIndex] = useState(null);
  const [editRoundInput, setEditRoundInput] = useState('');
  const [editContextInput, setEditContextInput] = useState('');

  const addKeeper = () => {
    const roundValue = parseInt(keeperRoundInput, 10);
    if (keeperPlayerName && !isNaN(roundValue) && roundValue > 0) {
      setKeeperList(prevList => [...prevList, { name: keeperPlayerName, round: roundValue, context: keeperContextInput }]);
      setKeeperPlayerName('');
      setKeeperRoundInput('');
      setKeeperContextInput('');
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

  const removeKeeper = (index) => {
    setKeeperList(prev => prev.filter((_, i) => i !== index));
  };

  useEffect(() => {
    if (allPlayers && allPlayers.length > 0) {
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
        ac.unInit();
      };
    }
  }, [allPlayers]);

  return (
    <section id="keeper" className={styles.keeperSection}>
      <div className={styles.toolHeader}>
        <h2>Keeper Evaluator</h2>
        <p>Analyze multiple keeper options based on cost vs. value.</p>
      </div>
      <div className={styles.card}>
        <div className={styles.formGroupInline}>
          <div className={styles.autoComplete_wrapper}>
            <input
              id="keeper-player-name"
              type="text"
              placeholder="Player Name..."
              value={keeperPlayerName}
              onChange={(e) => setKeeperPlayerName(e.target.value)}
              className={styles.input}
            />
          </div>
          <input
            id="keeper-round"
            type="number"
            placeholder="Round"
            value={keeperRoundInput}
            onChange={(e) => setKeeperRoundInput(e.target.value)}
            className={styles.inputSmall}
          />
          <div className={styles.autoComplete_wrapper}>
            <input
              id="keeper-context-input"
              type="text"
              placeholder="Context (e.g., status, role)"
              value={keeperContextInput}
              onChange={(e) => setKeeperContextInput(e.target.value)}
              className={styles.input}
            />
          </div>
          <button onClick={addKeeper} className={styles.button}>Add</button>
        </div>
        <div className={styles.keeperList}>
          {keeperList.length === 0 && (
            <p style={{ color: 'var(--text-muted)', textAlign: 'center', margin: '20px 0' }}>
              No keepers added yet. Use the form above to add players.
            </p>
          )}
          <div className={styles.keeperListGrid}>
            {keeperList.map((keeper, index) => {
              const normalizedKeeperName = normalizePlayerName(keeper.name);
              const playerData = staticPlayerData[normalizedKeeperName];
              const ecrOverall = playerData?.ecr_overall;
              const estimatedRound = getEstimatedDraftRound(ecrOverall);

              if (editingKeeperIndex === index) {
                return (
                  <div key={index} className={styles.keeperCard}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      <strong>{keeper.name}</strong>
                      <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                        <input
                          type="number"
                          placeholder="Round"
                          value={editRoundInput}
                          onChange={(e) => setEditRoundInput(e.target.value)}
                          className={styles.inputSmall}
                        />
                        <input
                          type="text"
                          placeholder="Context (e.g., status, role)"
                          value={editContextInput}
                          onChange={(e) => setEditContextInput(e.target.value)}
                          className={styles.input}
                        />
                      </div>
                      <div style={{ display: 'flex', gap: '10px' }}>
                        <button onClick={saveEditedKeeper} className={styles.buttonSmall}>Save</button>
                        <button onClick={cancelEditingKeeper} className={styles.buttonSmallDanger}>Cancel</button>
                      </div>
                    </div>
                  </div>
                );
              } else {
                return (
                  <div key={index} className={styles.keeperCard}>
                    <div>
                      <strong>{keeper.name}</strong>
                      <div className={styles.keeperInfo}>
                        <span>Cost: Round {keeper.round}</span>
                        {keeper.context && <span>Context: {keeper.context}</span>}
                      </div>
                      <small>
                        ECR: {ecrOverall ? ecrOverall.toFixed(1) : 'N/A'}
                        {ecrOverall && ` (${estimatedRound})`}
                      </small>
                    </div>
                    <div className={styles.keeperActions}>
                      <button onClick={() => startEditingKeeper(index)} className={styles.iconButton} title="Edit Keeper">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="feather feather-edit"><path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path></svg>
                      </button>
                      <button onClick={() => removeKeeper(index)} className={styles.iconButtonDanger} title="Remove Keeper">
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="feather feather-x"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                      </button>
                    </div>
                  </div>
                );
              }
            })}
          </div>
        </div>
      </div>
      <button onClick={evaluateKeepers} className={styles.actionButton} disabled={isLoading}>
        {isLoading ? 'Analyzing...' : 'Analyze All Keepers'}
      </button>
      <div id="keeper-loader" className={styles.loader} style={{ display: isLoading ? 'flex' : 'none', justifyContent: 'center', alignItems: 'center', margin: '20px auto' }}>
        <div style={{ border: '4px solid #f3f3f3', borderRadius: '50%', borderTop: '4px solid var(--primary-color)', width: '40px', height: '40px', animation: 'spin 1s linear infinite' }}></div>
        <span style={{ marginLeft: '10px', color: 'var(--text-muted)' }}>Analyzing keepers...</span>
      </div>
      <div id="keeper-result" className={styles.resultBox} dangerouslySetInnerHTML={{ __html: converter.makeHtml(keeperResult) }}></div>
    </section>
  );
}

export default KeeperEvaluator;
