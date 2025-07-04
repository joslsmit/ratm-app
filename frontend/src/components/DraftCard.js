import React, { useState, useEffect, useRef } from 'react';
import autoComplete from '@tarekraafat/autocomplete.js';

function DraftCard({ round, staticPlayerData, saveDraftBoard, allPlayers, handleGlobalSearch, initialPlayerName, ecrTypePreference, getOverallSdLabel, getPositionalSdLabel, normalizePlayerName }) {
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

    const playerData = playerName ? staticPlayerData[normalizePlayerName(playerName)] : null;
    const position = playerData?.position;

    // Determine which ECR to display based on the global preference

    const getSdConsensus = (ecrType) => {
        if (!playerData) return { label: 'N/A', icon: '' };
        const sdValue = playerData[`sd_${ecrType}`];
        if (ecrType === 'overall') {
            return getOverallSdLabel(sdValue);
        } else if (ecrType === 'positional') {
            return getPositionalSdLabel(sdValue);
        }
        return { label: 'N/A', icon: '' };
    };

    const displayEcr = (ecrType) => {
        if (!playerData) return 'N/A';
        const ecrValue = playerData[`ecr_${ecrType}`];
        return ecrValue ? ecrValue.toFixed(1) : 'N/A';
    };

    const displayBest = (ecrType) => {
        if (!playerData) return 'N/A';
        return playerData[`best_${ecrType}`] || 'N/A';
    };

    const displayWorst = (ecrType) => {
        if (!playerData) return 'N/A';
        return playerData[`worst_${ecrType}`] || 'N/A';
    };

    const sdConsensus = getSdConsensus(ecrTypePreference);

    return (
        <div className={`round-card pos-${position?.toLowerCase()}`}>
            <input type="hidden" id={`round-${round}-player-hidden`} value={playerName} />
            <div className="draft-card-header">
                <label>Round {round}</label>
                {playerName && <button onClick={handleClear} className="remove-btn-small">Clear</button>}
            </div>
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
            {playerData && (
                <div className="draft-card-details">
                    <div className="detail-row">
                        <span>ECR ({ecrTypePreference === 'overall' ? 'Overall' : 'Positional'}):</span>
                        <span>{displayEcr(ecrTypePreference)}</span>
                    </div>
                    <div className="detail-row">
                        <span>Consensus:</span>
                        <span>{sdConsensus.icon} {sdConsensus.label}</span>
                    </div>
                    <div className="detail-row">
                        <span>Best:</span>
                        <span>{displayBest(ecrTypePreference)}</span>
                    </div>
                    <div className="detail-row">
                        <span>Worst:</span>
                        <span>{displayWorst(ecrTypePreference)}</span>
                    </div>
                    <div className="detail-row">
                        <span>Bye:</span>
                        <span>{playerData.bye_week || 'N/A'}</span>
                    </div>
                </div>
            )}
        </div>
    );
}

export default DraftCard;
