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

                    // Backend now returns clean array format: [{league_key, league_name, team_key}]
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
                            <h3>{league.league_name}</h3>
                            <p>League Key: {league.league_key}</p>
                            <p>Team Key: {league.team_key}</p>
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
