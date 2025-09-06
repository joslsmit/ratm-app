import React, { useEffect, useMemo, useState } from 'react';
import styles from './Sidebar.module.css';

const Sidebar = ({ activeTool, targetList }) => {
  // Season mode (Pre‑Season vs In‑Season)
  const defaultMode = useMemo(() => {
    try {
      const saved = localStorage.getItem('season_mode');
      if (saved === 'pre' || saved === 'in') return saved;
    } catch (_) {}
    const m = new Date().getMonth(); // 0=Jan
    // Default: Pre‑Season in Aug/Sep, otherwise In‑Season
    return (m === 7 || m === 8) ? 'pre' : 'in';
  }, []);
  const [seasonMode, setSeasonMode] = useState(defaultMode);
  useEffect(() => { try { localStorage.setItem('season_mode', seasonMode); } catch(_){} }, [seasonMode]);

  const isYahooLoggedIn = !!localStorage.getItem('yahoo_token');

  // Recent players for quick access (last 3)
  const [recentPlayers, setRecentPlayers] = useState([]);
  useEffect(() => {
    try {
      const v = JSON.parse(localStorage.getItem('recentDossierPlayers') || '[]');
      if (Array.isArray(v)) setRecentPlayers(v.slice(0,3));
    } catch(_){}
  }, [activeTool]);

  const preSeason = [
    { key: 'draft', label: 'Draft Assistant', icon: '📝' },
    { key: 'tiers', label: 'Positional Tiers', icon: '📊' },
    { key: 'rookie', label: 'Rookie Rankings', icon: '🧒' },
    { key: 'keeper', label: 'Keeper Evaluator', icon: '🔒' },
    { key: 'dossier', label: 'Player Dossier', icon: '🧠' },
    { key: 'targets', label: `Target List`, icon: '🎯', badge: targetList.length },
  ];
  const inSeason = [
    ...(isYahooLoggedIn ? [{ key: 'my-team', label: 'My Team', icon: '👥', yahoo: true }] : []),
    ...(isYahooLoggedIn ? [{ key: 'lineup', label: 'Sit/Start Optimizer', icon: '🏈', yahoo: true }] : []),
    { key: 'waiver', label: 'Waiver Wire Assistant', icon: '🔄' },
    { key: 'market', label: 'Sleepers & Busts', icon: '💡' },
    { key: 'trade', label: 'Trade Analyzer', icon: '🤝' },
    { key: 'trending', label: 'Trending Players', icon: '📈' },
    { key: 'dossier', label: 'Player Dossier', icon: '🧠' },
  ];

  const utilities = [
    { key: 'yahoo-leagues', label: `Yahoo ${isYahooLoggedIn ? 'Connected' : 'Login'}`, icon: '🔑' },
    { key: 'settings', label: 'Settings', icon: '⚙️' },
    { key: 'documentation', label: 'Help', icon: '❓' },
  ];

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <a href="/" title="Start Over" className="sidebar-logo-link">
          <img src="/images/redd-logo.png" alt="Redd Against the Machine Logo" className="app-logo" />
        </a>
      </div>
      {/* Quick actions */}
      <div className="global-search-container">
        <div className="autoComplete_wrapper">
          <input id="global-player-search" type="text" placeholder="Search player (Dossier)…" />
        </div>
        <div style={{ display: 'flex', gap: 6, marginTop: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <a href="#lineup" className={activeTool === 'lineup' ? 'active chip' : 'chip'} title="Sit/Start Optimizer">🏈 Sit/Start</a>
          <a href="#waiver" className={activeTool === 'waiver' ? 'active chip' : 'chip'} title="Waiver Wire Assistant">🔄 Waiver</a>
          <span className={`chip ${isYahooLoggedIn ? 'chip-success' : 'chip-muted'}`} title="Yahoo status">{isYahooLoggedIn ? 'Yahoo Connected' : 'Yahoo Logged Out'}</span>
        </div>
        {recentPlayers && recentPlayers.length > 0 && (
          <div style={{ marginTop: 8 }}>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>Recent Dossiers</div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              {recentPlayers.map((p) => (
                <a key={p} href={`/#dossier?player=${encodeURIComponent(p)}`} className="chip" title={p}>{p}</a>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Season Mode Toggle */}
      <div className="ecr-preference-selector" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <label>Season Mode:</label>
        <select value={seasonMode} onChange={(e)=>setSeasonMode(e.target.value)}>
          <option value="in">In‑Season</option>
          <option value="pre">Pre‑Season</option>
        </select>
      </div>

      <nav className="sidebar-nav">
        {/* Filtered lists by season mode */}
        <div className="nav-section">
          <h3>{seasonMode === 'in' ? 'In‑Season' : 'Pre‑Season'}</h3>
          <ul>
            {(seasonMode === 'in' ? inSeason : preSeason).map(item => (
              <li key={item.key}>
                <a href={`#${item.key}`} className={activeTool === item.key ? 'active' : ''}>
                  <span className="nav-icon" aria-hidden>{item.icon}</span> {item.label}
                  {item.yahoo && <span className="badge" title="Yahoo"><span>Y</span></span>}
                  {typeof item.badge === 'number' ? <span className="badge">{item.badge}</span> : null}
                </a>
              </li>
            ))}
          </ul>
        </div>
        <div className="nav-section">
          <h3>Utilities</h3>
          <ul>
            {utilities.map(u => (
              <li key={u.key}><a href={`#${u.key}`} className={activeTool === u.key ? 'active' : ''}><span className="nav-icon" aria-hidden>{u.icon}</span> {u.label}</a></li>
            ))}
          </ul>
        </div>
      </nav>
      <div className="sidebar-footer">
        <nav className="utility-nav">
          <a href="#yahoo-leagues" className={activeTool === 'yahoo-leagues' ? 'active' : ''}>
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="feather feather-user"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
            Yahoo Login
          </a>
          <a href="#settings" className={activeTool === 'settings' ? 'active' : ''}>
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="feather feather-settings"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
            Settings
          </a>
          <a href="#documentation" className={activeTool === 'documentation' ? 'active' : ''}>
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="feather feather-help-circle"><circle cx="12" cy="12" r="10"></circle><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
            Help
          </a>
        </nav>
        <p>© 2025 RATM</p>
      </div>
    </div>
  );
};

export default Sidebar;
