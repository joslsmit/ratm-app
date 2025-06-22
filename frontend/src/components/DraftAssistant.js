import React, { useState, useCallback, useEffect } from 'react';
import DraftCard from './DraftCard'; // Import DraftCard
// import styles from './DraftAssistant.module.css'; // Assuming you'll create this CSS module

function DraftAssistant({
  makeApiRequest,
  staticPlayerData,
  allPlayers,
  handleGlobalSearch,
  converter,
  activeTool,
  ecrTypePreference
}) {
  const [draftAnalysisResult, setDraftAnalysisResult] = useState('');
  const [rosterCompositionResult, setRosterCompositionResult] = useState('');
  const [draftBoard, setDraftBoard] = useState({});

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
      if (playerData && playerData.position) {
        const pos = playerData.position;
        if (pos in counts) {
          counts[pos]++;
        }
      }
    });

    for (const pos in counts) {
      const cell = document.getElementById(`comp-${pos.toLowerCase()}`);
      if (cell) {
        cell.textContent = counts[pos];
      }
    }
    return counts;
  }, [staticPlayerData, getDraftBoardState]);

  const saveDraftBoard = useCallback(() => {
    const newBoard = {};
    let changesDetected = false;

    // Get the current board from localStorage to compare for changes
    const currentSavedBoard = loadDraftBoard();

    for (let i = 1; i <= 15; i++) {
      const playerName = document.getElementById(`round-${i}-player-hidden`)?.value || ''; // Ensure it's always a string
      newBoard[i] = playerName;

      // Check if the current value is different from the previously saved value
      if (playerName !== (currentSavedBoard[i] || '')) {
        changesDetected = true;
      }
    }

    // Only write to localStorage if there were actual changes
    if (changesDetected) {
      localStorage.setItem('draftBoard', JSON.stringify(newBoard));
    }
    
    // Always update the component's state to reflect the latest board
    setDraftBoard(newBoard); // This is crucial for React to re-render with the updated board
    updateRosterComposition();
  }, [updateRosterComposition, loadDraftBoard]);

  const loadDraftBoard = useCallback(() => {
    const savedBoard = localStorage.getItem('draftBoard');
    if (savedBoard) {
        return JSON.parse(savedBoard);
    }
    return {};
  }, []);

  const renderGeneric = useCallback(async (toolName, endpoint, body, setResult) => {
    const loader = document.getElementById(`${toolName}-loader`);
    if (loader) loader.style.display = 'block';
    setResult(''); // Clear previous results

    try {
      const data = await makeApiRequest(endpoint, body);
      if (data && (data.result || data.analysis)) {
        setResult(data.result || data.analysis);
      } else {
        const errorMessage = '<p style="color: var(--text-muted);">The Analyst returned an empty response.</p>';
		setResult(errorMessage);
	  }
    } catch (error) {
      const errorMessage = `<p style="color: var(--danger-color);">An error occurred: ${error.message}</p>`;
      setResult(errorMessage);
    } finally {
      if (loader) loader.style.display = 'none';
    }
  }, [makeApiRequest]);

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

  // Create and load the draft board on initial mount
  useEffect(() => {
    if (activeTool === 'draft') {
        const board = loadDraftBoard();
        setDraftBoard(board);
    }
  }, [activeTool, loadDraftBoard]);

  return (
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
              ecrTypePreference={ecrTypePreference}
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
  );
}

export default DraftAssistant;
