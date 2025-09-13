import React, { useState, useEffect, useCallback } from 'react';
import { useApi } from '../hooks/useApi';
import styles from './MyTeam.module.css';

// Map Yahoo roster slot codes to human-friendly descriptions
const SLOT_DESCRIPTIONS = {
    'QB': 'Quarterback (starter) — scores points',
    'WR': 'Wide receiver (starter) — scores points',
    'RB': 'Running back (starter) — scores points',
    'TE': 'Tight end (starter) — scores points',
    'W/T': 'Flex: wide receiver or tight end — scores points',
    'W/R': 'Flex: wide receiver or running back — scores points',
    'W/R/T': 'Flex: wide receiver, running back, or tight end — scores points',
    'BN': 'Bench — does not score in lineup',
    'IR': 'Injured reserve — does not score in lineup',
    'DEF': 'Team defense (starter) — scores points',
    'K': 'Kicker (starter) — scores points'
};

const POS_DESCRIPTIONS = {
    'QB': 'Quarterback (player position on roster)',
    'WR': 'Wide receiver (player position on roster)',
    'RB': 'Running back (player position on roster)',
    'TE': 'Tight end (player position on roster)',
    'DEF': 'Team defense (player position)',
    'K': 'Kicker (player position)'
};

const getRosterSlotLabel = (player) => {
    // Only trust Yahoo's roster slot for the badge.
    // If missing, show a dash rather than guessing from natural position.
    const slot = (player?.selected_position || '').toString().toUpperCase().trim();
    return slot || '—';
};

const getRosterSlotDescription = (slot) => {
    if (!slot) return 'Roster slot';
    const key = String(slot).toUpperCase().trim();
    return SLOT_DESCRIPTIONS[key] || 'Roster slot';
};

const classifySlot = (slot) => {
    const s = String(slot || '').toUpperCase();
    if (s === 'BN') return 'bench';
    if (s === 'IR') return 'ir';
    if (s === 'W/T' || s === 'W/R' || s === 'W/R/T') return 'flex';
    return 'starter';
};

const MyTeam = () => {
    const [leagues, setLeagues] = useState([]);
    const [selectedLeague, setSelectedLeague] = useState(null);
    const [roster, setRoster] = useState([]);
    const [loading, setLoading] = useState(true);
    const [rosterLoading, setRosterLoading] = useState(false);
    const [error, setError] = useState(null);
    const { get } = useApi();

    // This consolidated useEffect handles authentication and initial data fetching
    // following the same pattern as YahooLeagues.js
    useEffect(() => {
        const initializeAndFetch = async () => {
            let tokenObject = null;

            // Step 1: Check for a token in the URL hash
            const hash = window.location.hash;
            const tokenParam = new URLSearchParams(hash.split('?')[1]).get('token');

            if (tokenParam) {
                try {
                    const decodedToken = decodeURIComponent(tokenParam);
                    tokenObject = JSON.parse(decodedToken);
                    localStorage.setItem('yahoo_token', decodedToken);
                    // Clean the token from the URL to prevent re-processing on refresh
                    window.history.replaceState({}, document.title, window.location.pathname + hash.split('?')[0]);
                } catch (e) {
                    console.error("Error parsing Yahoo token from URL:", e);
                    setError("Failed to process Yahoo login. Please try again.");
                    setLoading(false);
                    return;
                }
            } else {
                // Step 2: If no token in URL, try to load it from localStorage
                const storedToken = localStorage.getItem('yahoo_token');
                if (storedToken) {
                    try {
                        tokenObject = JSON.parse(storedToken);
                    } catch (e) {
                        console.error("Error parsing Yahoo token from localStorage:", e);
                        setError("Stored Yahoo token is invalid. Please log in again.");
                        localStorage.removeItem('yahoo_token');
                        setLoading(false);
                        return;
                    }
                }
            }

            // Step 3: If we have a valid token, fetch leagues
            if (tokenObject) {
                try {
                    const authHeader = `Bearer ${tokenObject.access_token}`;
                    const response = await get('/yahoo/leagues', {
                        headers: { 'Authorization': authHeader }
                    });

                    // Backend returns clean array format: [{league_key, league_name, team_key}]
                    if (!Array.isArray(response)) {
                        throw new Error('Invalid response format from server.');
                    }

                    if (response.length === 0) {
                        setError('No fantasy football leagues found for your Yahoo account.');
                    } else {
                        setLeagues(response);
                    }
                } catch (err) {
                    console.error("Error fetching leagues:", err);
                    if (err.response && err.response.status === 401) {
                        setError('Authentication failed or token expired. Please log in again.');
                        localStorage.removeItem('yahoo_token');
                    } else {
                        setError(err.message || 'Failed to fetch leagues. Please try again later.');
                    }
                } finally {
                    setLoading(false);
                }
            } else {
                // Step 4: No token found anywhere
                setError('Not authenticated with Yahoo. Please log in.');
                setLoading(false);
            }
        };

        initializeAndFetch();
    }, [get]);

    // Handle league selection and fetch roster
    const handleLeagueSelect = useCallback(async (event) => {
        const selectedLeagueKey = event.target.value;
        
        if (!selectedLeagueKey) {
            setSelectedLeague(null);
            setRoster([]);
            return;
        }

        const league = leagues.find(l => l.league_key === selectedLeagueKey);
        setSelectedLeague(league);
        setRosterLoading(true);
        setError(null);

        try {
            const tokenObject = JSON.parse(localStorage.getItem('yahoo_token'));
            const authHeader = `Bearer ${tokenObject.access_token}`;

            const rosterData = await get(`/yahoo/roster?team_key=${league.team_key}`, {
                headers: { 'Authorization': authHeader }
            });

            setRoster(rosterData);
        } catch (err) {
            console.error("Error fetching roster:", err);
            // Handle 401 token expiration
            if (err.response && err.response.status === 401) {
                setError('Token expired. Please log in again.');
                localStorage.removeItem('yahoo_token');
            } else {
                setError(err.message || 'Failed to fetch roster. Please try again.');
            }
        } finally {
            setRosterLoading(false);
        }
    }, [get, leagues]);

    // Render player card
    const renderPlayerCard = (player, index) => {
        return (
            <div key={player.player_key || index} className={styles.playerCard}>
                <div className={styles.playerHeader}>
                    <h3 className={styles.playerName}>{player.name || 'Unknown Player'}</h3>
                    {(() => {
                        const slot = getRosterSlotLabel(player);
                        const slotDesc = getRosterSlotDescription(slot);
                        const category = classifySlot(slot);
                        const slotClass = category === 'bench' ? styles.slotBench
                                         : category === 'ir' ? styles.slotIR
                                         : category === 'flex' ? styles.slotFlex
                                         : styles.slotStarter;
                        return (
                            <div className={styles.badgeGroup}>
                                <span className={`${styles.slotBadge} ${slotClass}`} title={slotDesc} aria-label={slotDesc}>
                                    {slot}
                                </span>
                            </div>
                        );
                    })()}
                </div>

                {(() => {
                    const slot = getRosterSlotLabel(player);
                    const category = classifySlot(slot);
                    const naturalPos = (player?.position || '').toUpperCase() || '—';
                    const categoryLabel = category === 'bench' ? 'Bench'
                                          : category === 'ir' ? 'Injured Reserve'
                                          : category === 'flex' ? 'Flex'
                                          : category === 'starter' ? 'Starter' : '—';
                    const elig = Array.isArray(player?.eligible_positions)
                        ? player.eligible_positions.map(p => typeof p === 'string' ? p : p?.position).filter(Boolean)
                        : [];
                    const eligText = elig.length ? `Eligible: ${elig.join('/')}` : '';
                    return (
                        <div className={styles.slotLine}>
                            <span>Slot: <strong>{slot}</strong>{categoryLabel !== '—' ? ` (${categoryLabel})` : ''} • Position: <strong>{naturalPos}</strong>{eligText ? ` • ${eligText}` : ''}</span>
                        </div>
                    );
                })()}
                
                <div className={styles.playerStats}>
                    <div className={styles.statRow}>
                        <span className={styles.statLabel}>Team:</span>
                        <span className={styles.statValue}>{player.team || 'N/A'}</span>
                    </div>
                    <div className={styles.statRow}>
                        <span className={styles.statLabel}>ECR Overall:</span>
                        <span className={styles.statValue}>
                            {player.ecr_overall ? player.ecr_overall.toFixed(1) : 'N/A'}
                        </span>
                    </div>
                    <div className={styles.statRow}>
                        <span className={styles.statLabel}>Bye Week:</span>
                        <span className={styles.statValue}>{player.bye_week || 'N/A'}</span>
                    </div>
                    {player.analysis && (
                        <div className={styles.playerAnalysis}>
                            <h4>AI Analysis</h4>
                            <p>{player.analysis}</p>
                        </div>
                    )}
                </div>
            </div>
        );
    };

    if (loading) {
        return <div className={styles.loading}>Loading your leagues...</div>;
    }

    if (error) {
        return <div className={styles.error}>{error}</div>;
    }

    return (
        <div className={styles.container}>
            <div className={styles.header}>
                <h2>My Team</h2>
                <p>View your Yahoo Fantasy Football roster with integrated AI analysis</p>
            </div>

            <div className={styles.leagueSelector}>
                <label htmlFor="league-select" className={styles.label}>
                    Select a League:
                </label>
                <select 
                    id="league-select"
                    className={styles.dropdown}
                    value={selectedLeague?.league_key || ''}
                    onChange={handleLeagueSelect}
                >
                    <option value="">Choose your league...</option>
                    {leagues.map(league => (
                        <option key={league.league_key} value={league.league_key}>
                            {league.league_name}
                        </option>
                    ))}
                </select>
            </div>

            {selectedLeague && (
                <div className={styles.rosterSection}>
                    <h3>Roster for {selectedLeague.league_name}</h3>
                    
                    {rosterLoading ? (
                        <div className={styles.loading}>Loading your roster...</div>
                    ) : roster.length === 0 ? (
                        <div className={styles.emptyRoster}>
                            <h3>No Players Drafted Yet</h3>
                            <p>Your roster will appear here after your draft.</p>
                            <p><strong>Draft Status:</strong> Pre-Draft</p>
                        </div>
                    ) : (
                        <div className={styles.rosterGrid}>
                            {roster.map((player, index) => renderPlayerCard(player, index))}
                        </div>
                    )}
                </div>
            )}
        </div>
    );
};

export default MyTeam;
