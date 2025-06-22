import React, { useState, useEffect, useRef } from 'react';
import autoComplete from '@tarekraafat/autocomplete.js';

function DraftCard({ round, staticPlayerData, saveDraftBoard, allPlayers, handleGlobalSearch, initialPlayerName, ecrTypePreference }) {
    const [isEditing, setIsEditing] = useState(false);
    const [playerName, setPlayerName] = useState(initialPlayerName || '');
    const autoCompleteRef = useRef(null);

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
    const position = playerData?.position;

    // Determine which ECR to display based on the global preference
    const displayEcr = (ecrType) => {
        if (!playerData) return 'N/A';
        const ecrValue = playerData[`ecr_${ecrType}`];
        return ecrValue ? ecrValue.toFixed(1) : 'N/A';
    };

    const displaySd = (ecrType) => {
        if (!playerData) return 'N/A';
        const sdValue = playerData[`sd_${ecrType}`];
        return sdValue ? sdValue.toFixed(2) : 'N/A';
    };

    const displayBest = (ecrType) => {
        if (!playerData) return 'N/A';
        return playerData[`best_${ecrType}`] || 'N/A';
    };

    const displayWorst = (ecrType) => {
        if (!playerData) return 'N/A';
        return playerData[`worst_${ecrType}`] || 'N/A';
    };

    const displayRankDelta = (ecrType) => {
        if (!playerData) return 'N/A';
        const rankDeltaValue = playerData[`rank_delta_${ecrType}`];
        return rankDeltaValue ? rankDeltaValue.toFixed(1) : 'N/A';
    };

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
                    <span>ECR ({ecrTypePreference === 'overall' ? 'Overall' : 'Positional'}): {displayEcr(ecrTypePreference)}</span>
                    <span>SD ({ecrTypePreference === 'overall' ? 'Overall' : 'Positional'}): {displaySd(ecrTypePreference)}</span>
                    <span>Best ({ecrTypePreference === 'overall' ? 'Overall' : 'Positional'}): {displayBest(ecrTypePreference)}</span>
                    <span>Worst ({ecrTypePreference === 'overall' ? 'Overall' : 'Positional'}): {displayWorst(ecrTypePreference)}</span>
                    <span>Rank Delta ({ecrTypePreference === 'overall' ? 'Overall' : 'Positional'}): {displayRankDelta(ecrTypePreference)}</span>
                    <span>Bye: {playerData.bye_week || 'N/A'}</span>
                </div>
            )}
        </div>
    );
}

export default DraftCard;
