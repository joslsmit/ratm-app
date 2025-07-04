import React, { useState, useEffect, useCallback } from 'react';
import { useApi } from '../hooks/useApi';
import styles from './YahooLeagues.module.css';

const YahooLeagues = () => {
    const [leagues, setLeagues] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const { get } = useApi();

    // This single, consolidated useEffect handles the entire authentication and data fetching flow.
    // It's designed to run only once on component mount and avoids race conditions
    // between setting state and fetching data.
    useEffect(() => {
        const initializeAndFetch = async () => {
            let tokenObject = null;

            // Step 1: Check for a token in the URL hash.
            const hash = window.location.hash;
            const tokenParam = new URLSearchParams(hash.split('?')[1]).get('token');

            if (tokenParam) {
                try {
                    const decodedToken = decodeURIComponent(tokenParam);
                    tokenObject = JSON.parse(decodedToken);
                    localStorage.setItem('yahoo_token', decodedToken);
                    // Clean the token from the URL to prevent re-processing on refresh.
                    window.history.replaceState({}, document.title, window.location.pathname + hash.split('?')[0]);
                } catch (e) {
                    console.error("Error parsing Yahoo token from URL:", e);
                    setError("Failed to process Yahoo login. Please try again.");
                    setLoading(false);
                    return; // Stop execution if token is invalid
                }
            } else {
                // Step 2: If no token in URL, try to load it from localStorage.
                const storedToken = localStorage.getItem('yahoo_token');
                if (storedToken) {
                    try {
                        tokenObject = JSON.parse(storedToken);
                    } catch (e) {
                        console.error("Error parsing Yahoo token from localStorage:", e);
                        setError("Stored Yahoo token is invalid. Please log in again.");
                        localStorage.removeItem('yahoo_token');
                        setLoading(false);
                        return; // Stop execution if stored token is invalid
                    }
                }
            }

            // Step 3: If we have a valid token object (from URL or localStorage), fetch leagues.
            if (tokenObject) {
                try {
                    const authHeader = `Bearer ${tokenObject.access_token}`;
                    const response = await get('/yahoo/leagues', {
                        headers: { 'Authorization': authHeader }
                    });

                    // --- Robust parsing logic for Yahoo API response ---
                    const fantasyContent = response?.fantasy_content;
                    if (!fantasyContent) {
                        throw new Error('Could not retrieve fantasy content. Please ensure your Yahoo account has fantasy sports data.');
                    }

                    const gamesObject = fantasyContent.users?.[0]?.user?.[1]?.games;
                    if (!gamesObject) {
                        throw new Error('No fantasy games found in your Yahoo account data.');
                    }

                    const gamesArray = Array.isArray(gamesObject)
                        ? gamesObject
                        : Object.values(gamesObject).filter(item => typeof item === 'object' && item.hasOwnProperty('game'));

                    if (!gamesArray || gamesArray.length === 0) {
                        throw new Error('Fantasy games data is not in the expected format.');
                    }

                    const nflGame = gamesArray.find(g => g.game?.[0]?.code === 'nfl')?.game;
                    if (!nflGame) {
                        throw new Error('No NFL fantasy game found for your account.');
                    }

                    const leaguesData = Array.isArray(nflGame)
                        ? nflGame.find(item => item.leagues)?.leagues
                        : Object.values(nflGame).find(item => typeof item === 'object' && item.hasOwnProperty('leagues'))?.leagues;
                    
                    if (leaguesData) {
                        const leaguesArray = Array.isArray(leaguesData)
                            ? leaguesData
                            : Object.values(leaguesData).filter(item => typeof item === 'object' && item.hasOwnProperty('league'));
                        
                        const extractedLeagues = leaguesArray.map(l => l.league?.[0]).filter(Boolean);
                        setLeagues(extractedLeagues);

                        if (extractedLeagues.length === 0) {
                            setError('While we connected to your Yahoo account, no fantasy football leagues were found.');
                        }
                    } else {
                        setError('No leagues found within the NFL game data for your account.');
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
                // Step 4: No token found anywhere.
                setError('Not authenticated with Yahoo. Please log in.');
                setLoading(false);
            }
        };

        initializeAndFetch();
    }, [get]); // The 'get' function from useApi is a stable dependency.

    // Logout function
    const handleLogout = useCallback(() => {
        localStorage.removeItem('yahoo_token');
        setYahooToken(null);
        setLeagues([]);
        setError(null);
        setLoading(false);
        // Optionally redirect to home or login page
        window.location.hash = ''; // Go to default tool
    }, []);


    if (loading) {
        return <div className={styles.loading}>Loading your leagues...</div>;
    }

    if (error) {
        return <div className={styles.error}>{error}</div>;
    }

    return (
        <div className={styles.container}>
            <h2>Your Yahoo Fantasy Football Leagues</h2>
            {leagues.length > 0 ? (
                <ul className={styles.leagueList}>
                    {leagues.map(league => (
                        <li key={league.league_key} className={styles.leagueItem}>
                            <h3>{league.name}</h3>
                            <p>Scoring Type: {league.scoring_type}</p>
                            <p>Number of Teams: {league.num_teams}</p>
                            <a href={league.url} target="_blank" rel="noopener noreferrer">
                                Go to League
                            </a>
                        </li>
                    ))}
                </ul>
            ) : (
                <p>No fantasy football leagues found for the current season.</p>
            )}
        </div>
    );
};

export default YahooLeagues;
