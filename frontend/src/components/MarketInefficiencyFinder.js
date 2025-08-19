import { useState, useEffect, useCallback } from 'react';
import { useApi } from '../hooks/useApi';
import styles from './MarketInefficiencyFinder.module.css';

export default function MarketInefficiencyFinder({
  marketInefficiencies,
  findMarketInefficiencies,
  onFindYahooInefficiencies = null, // Optional: New prop for Yahoo analysis
  onLeaguesUpdate = null, // Optional: New prop to pass leagues to parent
  handleAddToTargets,
  getOverallSdLabel,
  isLoading = false
}) {
  // Add Yahoo integration state
  const [isYahooUser, setIsYahooUser] = useState(false);
  const [userLeagues, setUserLeagues] = useState([]);
  const [selectedLeague, setSelectedLeague] = useState('');
  const [yahooError, setYahooError] = useState('');
  const [isLoadingYahooData, setIsLoadingYahooData] = useState(false);
  const [useYahooMode, setUseYahooMode] = useState(false);
  
  // Hooks
  const { get } = useApi();

  // Fetch user's leagues for dropdown
  const fetchUserLeagues = useCallback(async (token) => {
    try {
      setIsLoadingYahooData(true);
      setYahooError('');
      
      // Parse token object and extract access_token
      const tokenObject = JSON.parse(token);
      const authHeader = `Bearer ${tokenObject.access_token}`;
      
      const leagues = await get('/yahoo/leagues', {
        headers: {
          'Authorization': authHeader
        }
      });
      
      setUserLeagues(leagues);
      
      // Pass leagues data to parent component
      if (onLeaguesUpdate) {
        onLeaguesUpdate(leagues);
      }
      
      // Auto-select first league if only one available
      if (leagues.length === 1) {
        setSelectedLeague(leagues[0].league_key);
      }
    } catch (error) {
      console.error('Error fetching leagues:', error);
      if (error.response && error.response.status === 401) {
        setYahooError('Yahoo authentication expired. Please re-authenticate.');
        setIsYahooUser(false);
        localStorage.removeItem('yahoo_token');
      } else {
        setYahooError('Unable to connect to Yahoo API.');
      }
    } finally {
      setIsLoadingYahooData(false);
    }
  }, [get, onLeaguesUpdate]);

  // Add Yahoo authentication check effect
  useEffect(() => {
    const checkYahooAuth = async () => {
      try {
        const token = localStorage.getItem('yahoo_token');
        if (token) {
          setIsYahooUser(true);
          await fetchUserLeagues(token);
        } else {
          setIsYahooUser(false);
          setUseYahooMode(false);
        }
      } catch (error) {
        console.error('Error checking Yahoo authentication:', error);
        setIsYahooUser(false);
        setUseYahooMode(false);
      }
    };
    
    checkYahooAuth();
  }, [fetchUserLeagues]);
  
  // Handle league selection change
  const handleLeagueChange = (event) => {
    setSelectedLeague(event.target.value);
  };
  
  // Toggle between Yahoo and traditional mode
  const toggleYahooMode = () => {
    setUseYahooMode(!useYahooMode);
  };
  
  // Handle analysis with mode detection
  const handleAnalyzeClick = () => {
    const position = document.getElementById('market-pos').value;
    
    if (useYahooMode && selectedLeague) {
      // Yahoo mode: use league-specific analysis
      if (!onFindYahooInefficiencies) {
        console.error('Yahoo analysis handler not provided');
        alert('Yahoo analysis not available. Please contact support.');
        return;
      }
      
      const token = localStorage.getItem('yahoo_token');
      if (!token) {
        alert('Yahoo authentication required. Please log in with Yahoo.');
        return;
      }
      
      onFindYahooInefficiencies(selectedLeague, position, token);
    } else {
      // Traditional mode: use general market analysis
      findMarketInefficiencies();
    }
  };
  return (
    <section id="market" className={styles.marketSection}>
      <div className={styles.toolHeader}>
        <h2>Market Inefficiency Finder</h2>
        <p>
          {useYahooMode 
            ? "Discover league-specific sleepers and busts based on your Yahoo league context." 
            : "Discover potential sleepers and busts by comparing data sources."
          }
        </p>
      </div>
      
      {/* Yahoo Mode Section */}
      {isYahooUser && onFindYahooInefficiencies && (
        <div className={styles.yahooModeSection}>
          <div className={styles.modeToggle}>
            <label>
              <input 
                type="checkbox" 
                checked={useYahooMode} 
                onChange={toggleYahooMode}
                disabled={isLoadingYahooData}
              />
              Use Yahoo League Analysis
            </label>
          </div>
          
          {useYahooMode && (
            <div className={styles.leagueSelector}>
              <label htmlFor="league-select">Select League:</label>
              <select 
                id="league-select"
                value={selectedLeague} 
                onChange={handleLeagueChange}
                disabled={isLoadingYahooData}
              >
                <option value="">Choose a league...</option>
                {userLeagues.map(league => (
                  <option key={league.league_key} value={league.league_key}>
                    {league.league_name}
                  </option>
                ))}
              </select>
              {isLoadingYahooData && <span className={styles.loadingText}>Loading...</span>}
              {yahooError && <div className={styles.errorText}>{yahooError}</div>}
            </div>
          )}
        </div>
      )}
      
      {/* Position Filter and Find Button */}
      <div className={styles.card}>
        <div className={styles.formGroupInline}>
          <select id="market-pos" className={styles.select}>
            <option value="all">All</option>
            <option value="QB">QB</option>
            <option value="RB">RB</option>
            <option value="WR">WR</option>
            <option value="TE">TE</option>
          </select>
          <button 
            onClick={handleAnalyzeClick} 
            className={styles.button}
            disabled={isLoading || isLoadingYahooData || (useYahooMode && !selectedLeague)}
          >
            {isLoading ? 'Analyzing...' : useYahooMode ? 'Find League Opportunities' : 'Find'}
          </button>
        </div>
        {useYahooMode && !selectedLeague && (
          <p className={styles.selectionPrompt}>Please select a league to analyze league-specific opportunities.</p>
        )}
      </div>
      <div id="market-loader" className={styles.loader} style={{ display: 'none' }}></div>
      
      {/* Results Section - Enhanced for Yahoo Mode */}
      <div className={styles.marketResults}>
        {useYahooMode && selectedLeague && (
          <div className={styles.leagueContextBanner}>
            <h3>Analysis for: {userLeagues.find(l => l.league_key === selectedLeague)?.league_name}</h3>
            <p>League-specific opportunities based on player availability and ownership patterns</p>
          </div>
        )}
        
        <div className={styles.marketColumn}>
          <h3>{useYahooMode ? 'League Sleepers (Available Undervalued)' : 'Sleepers (Undervalued)'}</h3>
          {marketInefficiencies.sleepers.length > 0 ? marketInefficiencies.sleepers.map((player, index) => (
            <div key={`sleeper-${index}`} className={`${styles.analysisCard} ${styles.sleeper}`}>
              <div className={styles.analysisCardHeader}>
                <h4><a href={`/?tool=dossier&player=${encodeURIComponent(player.name)}`} className={styles.playerLink}>{player.name}</a></h4>
                <span className={`${styles.confidenceBadge} ${styles[player.confidence]}`}>{player.confidence}</span>
                <button className={styles.addTargetBtnSmall} title="Add to Target List" onClick={() => handleAddToTargets(player.name)}>
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="16"></line><line x1="8" y1="12" x2="16" y2="12"></line></svg>
                </button>
              </div>
              <div className={styles.playerDetailsGrid}>
                <span>ECR: {typeof player.ecr === 'number' ? player.ecr.toFixed(1) : 'N/A'}</span>
                <span title={`Standard Deviation: ${typeof player.sd === 'number' ? player.sd.toFixed(2) : 'N/A'}`}>
                  SD: {getOverallSdLabel(player.sd).icon} {getOverallSdLabel(player.sd).label}
                </span>
                <span>Best: {player.best || 'N/A'}</span>
                <span>Worst: {player.worst || 'N/A'}</span>
                <span>Rank Delta: {typeof player.rank_delta === 'number' ? player.rank_delta.toFixed(1) : 'N/A'}</span>
                <span>Rookie: {player.is_rookie ? 'Yes' : 'No'}</span>
                {useYahooMode && player.league_inefficiency_score && (
                  <span className={styles.leagueScore} title="League-specific opportunity score">
                    League Score: {player.league_inefficiency_score}
                  </span>
                )}
              </div>
              <p>{player.justification}</p>
              {useYahooMode && player.league_context_notes && (
                <div className={styles.leagueContext}>
                  <small><strong>League Context:</strong> {player.league_context_notes}</small>
                </div>
              )}
            </div>
          )) : <p>No {useYahooMode ? 'league-specific sleepers' : 'sleepers'} found.</p>}
        </div>
        
        <div className={styles.marketColumn}>
          <h3>{useYahooMode ? 'League Busts (Overvalued)' : 'Busts (Overvalued)'}</h3>
          {marketInefficiencies.busts.length > 0 ? marketInefficiencies.busts.map((player, index) => (
            <div key={`bust-${index}`} className={`${styles.analysisCard} ${styles.bust}`}>
              <div className={styles.analysisCardHeader}>
                <h4><a href={`/?tool=dossier&player=${encodeURIComponent(player.name)}`} className={styles.playerLink}>{player.name}</a></h4>
                <span className={`${styles.confidenceBadge} ${styles[player.confidence]}`}>{player.confidence}</span>
                <button className={styles.addTargetBtnSmall} title="Add to Target List" onClick={() => handleAddToTargets(player.name)}>
                  <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="16"></line><line x1="8" y1="12" x2="16" y2="12"></line></svg>
                </button>
              </div>
              <div className={styles.playerDetailsGrid}>
                <span>ECR: {typeof player.ecr === 'number' ? player.ecr.toFixed(1) : 'N/A'}</span>
                <span title={`Standard Deviation: ${typeof player.sd === 'number' ? player.sd.toFixed(2) : 'N/A'}`}>
                  SD: {getOverallSdLabel(player.sd).icon} {getOverallSdLabel(player.sd).label}
                </span>
                <span>Best: {player.best || 'N/A'}</span>
                <span>Worst: {player.worst || 'N/A'}</span>
                <span>Rank Delta: {typeof player.rank_delta === 'number' ? player.rank_delta.toFixed(1) : 'N/A'}</span>
                <span>Rookie: {player.is_rookie ? 'Yes' : 'No'}</span>
                {useYahooMode && player.league_inefficiency_score && (
                  <span className={styles.leagueScore} title="League-specific risk score">
                    League Score: {player.league_inefficiency_score}
                  </span>
                )}
              </div>
              <p>{player.justification}</p>
              {useYahooMode && player.league_context_notes && (
                <div className={styles.leagueContext}>
                  <small><strong>League Context:</strong> {player.league_context_notes}</small>
                </div>
              )}
            </div>
          )) : <p>No {useYahooMode ? 'league-specific busts' : 'busts'} found.</p>}
        </div>
      </div>
    </section>
  );
}
