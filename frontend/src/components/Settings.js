import React, { useState, useEffect, useContext } from 'react';
import { AppContext } from '../context/AppContext';
import styles from './Settings.module.css';

const Settings = ({ lastUpdateDate, toggleTheme, resetApplication }) => {
  const { API_BASE_URL } = useContext(AppContext);
  const [isYahooLoggedIn, setIsYahooLoggedIn] = useState(false);
  const [theme, setTheme] = useState(localStorage.getItem('theme') || 'dark');
  const [leagues, setLeagues] = useState([]);
  const [leagueKey, setLeagueKey] = useState('');
  const [teamKey, setTeamKey] = useState('');
  const [diagLoading, setDiagLoading] = useState(false);
  const [diagError, setDiagError] = useState('');
  const [diagData, setDiagData] = useState(null);
  const [refreshLoading, setRefreshLoading] = useState(false);

  useEffect(() => {
    const token = localStorage.getItem('yahoo_token');
    setIsYahooLoggedIn(!!token);
    // On mount, if logged in, attempt to load leagues for diagnostics
    if (token) {
      try {
        const tok = JSON.parse(token);
        const auth = `Bearer ${tok.access_token}`;
        fetch(`${API_BASE_URL}/yahoo/leagues`, { headers: { Authorization: auth }})
          .then(r => r.ok ? r.json() : Promise.reject(new Error('Failed to load leagues')))
          .then(ls => {
            if (Array.isArray(ls)) {
              setLeagues(ls);
              if (ls.length === 1) {
                setLeagueKey(ls[0].league_key);
                setTeamKey(ls[0].team_key);
              }
            }
          })
          .catch(() => {});
      } catch (_) {}
    }

    const handleThemeChange = () => {
      setTheme(document.body.getAttribute('data-theme') || 'dark');
    };

    window.addEventListener('storage', handleThemeChange);
    document.body.addEventListener('themeChanged', handleThemeChange);

    return () => {
      window.removeEventListener('storage', handleThemeChange);
      document.body.removeEventListener('themeChanged', handleThemeChange);
    };
  }, []);

  const handleYahooLogin = () => {
    window.location.href = `${API_BASE_URL}/yahoo/login`;
  };

  const handleYahooLogout = () => {
    localStorage.removeItem('yahoo_token');
    setIsYahooLoggedIn(false);
    window.location.hash = '#settings';
  };

  const fetchDiagnostics = async () => {
    setDiagError(''); setDiagLoading(true); setDiagData(null);
    try {
      if (!leagueKey) throw new Error('Select a league');
      const token = JSON.parse(localStorage.getItem('yahoo_token') || '{}');
      const auth = `Bearer ${token.access_token}`;
      const qs = new URLSearchParams({ league_key: leagueKey });
      if (teamKey) qs.set('team_key', teamKey);
      const rsp = await fetch(`${API_BASE_URL}/diagnostics/yahoo-data-health?${qs.toString()}`, { headers: { Authorization: auth }});
      if (!rsp.ok) { const e = await rsp.json().catch(()=>({})); throw new Error(e.error || `HTTP ${rsp.status}`); }
      const data = await rsp.json();
      setDiagData(data);
    } catch (e) {
      setDiagError(e.message || 'Failed to load diagnostics');
    } finally { setDiagLoading(false); }
  };

  const refreshData = async () => {
    setRefreshLoading(true); setDiagError('');
    try {
      const rsp = await fetch(`${API_BASE_URL}/admin/refresh_data`, { method: 'POST' });
      if (!rsp.ok) { const e = await rsp.json().catch(()=>({})); throw new Error(e.error || `HTTP ${rsp.status}`); }
      // Re-run diagnostics after refresh if league selected
      if (leagueKey) {
        await fetchDiagnostics();
      }
    } catch (e) {
      setDiagError(e.message || 'Refresh failed');
    } finally { setRefreshLoading(false); }
  };

  const loginButtonImage = theme === 'dark' ? '/images/yahoo_login_dark.png' : '/images/yahoo_login_light.png';

  return (
    <section id="settings" className={styles.settings}>
      <div className="tool-header">
        <h2>Settings</h2>
        <p>Manage application data and preferences.</p>
      </div>

      <div className="card">
        <h3>Yahoo Fantasy Integration</h3>
        <p>Connect your Yahoo account to enable personalized features like roster analysis and league-aware recommendations.</p>
        {isYahooLoggedIn ? (
          <button onClick={handleYahooLogout} className={`${styles.yahooButton} ${styles.logout}`}>
            Sign Out of Yahoo
          </button>
        ) : (
          <button onClick={handleYahooLogin} className={styles.yahooImageButton}>
            <img src={loginButtonImage} alt="Sign in with Yahoo" />
          </button>
        )}
      </div>

      <div className="card">
        <h3>Theme</h3>
        <p>Switch between light and dark mode.</p>
        <button onClick={toggleTheme}>Toggle Theme</button>
      </div>

      <div className="card">
        <h3>Clear Saved Data</h3>
        <p>This action will permanently delete your saved Google API key, draft board, and target list from this browser.</p>
        <button onClick={resetApplication} className="btn-danger">Clear All Data & Reset</button>
      </div>

      <div className="card">
        <h3>Data Last Updated</h3>
        <p>Dynasty process files were last updated on: <strong>{lastUpdateDate}</strong></p>
      </div>

      <div className="card">
        <h3>Data Health</h3>
        <p>Check CSV freshness and enrichment coverage for your Yahoo league.</p>
        {isYahooLoggedIn ? (
          <>
            <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center', marginBottom: 8 }}>
              <div>
                <label>League:&nbsp;</label>
                <select value={leagueKey} onChange={(e)=>{ const lk = e.target.value; setLeagueKey(lk); const l = leagues.find(x=>x.league_key===lk); setTeamKey(l?.team_key||''); }}>
                  <option value="">Select a league…</option>
                  {leagues.map(l => (
                    <option key={l.league_key} value={l.league_key}>{l.league_name}</option>
                  ))}
                </select>
              </div>
              <button onClick={fetchDiagnostics} disabled={!leagueKey || diagLoading}>{diagLoading ? 'Checking…' : 'Check Data Health'}</button>
              <button onClick={refreshData} disabled={refreshLoading}>{refreshLoading ? 'Refreshing…' : 'Refresh Data (Admin)'}</button>
            </div>
            {diagError && <div className="error-text" style={{ marginTop: 6 }}>{diagError}</div>}
            {diagData && (
              <div style={{ marginTop: 8 }}>
                <div style={{ marginBottom: 8 }}>
                  <strong>Roster Match:</strong> {diagData.roster?.enrichment?.match_rate ?? 0}% ({diagData.roster?.enrichment?.matched ?? 0}/{diagData.roster?.enrichment?.total ?? 0})
                </div>
                <div style={{ marginBottom: 8 }}>
                  <strong>Waiver Coverage (A, first 100):</strong> {diagData.waivers_A_first2pages?.enrichment?.match_rate ?? 0}% ({diagData.waivers_A_first2pages?.enrichment?.matched ?? 0}/{diagData.waivers_A_first2pages?.enrichment?.total ?? 0})
                </div>
                <div style={{ marginBottom: 8 }}>
                  <strong>Weekly Projections:</strong> {diagData.weekly_checks?.row_count ?? 0} rows • Latest scrape: {diagData.weekly_checks?.latest_scrape_date || 'N/A'}
                </div>
                <div style={{ marginBottom: 8 }}>
                  <strong>CSV Freshness:</strong>
                  <ul>
                    {Object.entries(diagData.csv_freshness || {}).map(([name, info]) => (
                      <li key={name}>{name}: {info.modified || 'N/A'}</li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </>
        ) : (
          <p>Sign in to Yahoo above to view league diagnostics.</p>
        )}
      </div>
    </section>
  );
};

export default Settings;
