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
  const [showAll, setShowAll] = useState(false);
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
          <a href="#lineup" className={activeTool === 'lineup' ? 'active chip' : 'chip'} title="Sit/Start Optimizer">Sit/Start</a>
          <a href="#waiver" className={activeTool === 'waiver' ? 'active chip' : 'chip'} title="Waiver Wire Assistant">Waiver</a>
          <span className={`chip ${isYahooLoggedIn ? 'chip-success' : 'chip-muted'}`} title="Yahoo status">{isYahooLoggedIn ? 'Yahoo Connected' : 'Yahoo Logged Out'}</span>
        </div>
        {recentPlayers && recentPlayers.length > 0 && (
          <div style={{ marginTop: 8 }}>
            <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 4 }}>Recent Dossiers</div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              {recentPlayers.map((p) => (
                <a key={p} href={`/?tool=dossier&player=${encodeURIComponent(p)}`} className="chip" title={p}>{p}</a>
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
        <label style={{ marginLeft: 'auto', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
          <input type="checkbox" checked={showAll} onChange={(e)=>setShowAll(e.target.checked)} /> Show All
        </label>
      </div>

      <nav className="sidebar-nav">
        {/* Filtered lists by season mode */}
        {showAll ? (
          <>
            <div className="nav-section">
              <h3>In‑Season</h3>
              <ul>
                {inSeason.map(item => (
                  <li key={`in-${item.key}`}>
                    <a href={`#${item.key}`} className={activeTool === item.key ? 'active' : ''}>
                      {item.label}
                      {item.yahoo && <span className="badge" title="Yahoo"><span>Y</span></span>}
                      {typeof item.badge === 'number' ? <span className="badge">{item.badge}</span> : null}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
            <div className="nav-section">
              <h3>Pre‑Season</h3>
              <ul>
                {preSeason.map(item => (
                  <li key={`pre-${item.key}`}>
                    <a href={`#${item.key}`} className={activeTool === item.key ? 'active' : ''}>
                      {item.label}
                      {typeof item.badge === 'number' ? <span className="badge">{item.badge}</span> : null}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          </>
        ) : (
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
        )}
        <div className="nav-section">
          <h3>Utilities</h3>
          <ul>
            {utilities.map(u => (
              <li key={u.key}><a href={`#${u.key}`} className={activeTool === u.key ? 'active' : ''}>{u.label}</a></li>
            ))}
          </ul>
        </div>
      </nav>
      <div className="sidebar-footer">
        <nav className="utility-nav">
          <a href="#yahoo-leagues" className={activeTool === 'yahoo-leagues' ? 'active' : ''}>Yahoo Login</a>
          <a href="#settings" className={activeTool === 'settings' ? 'active' : ''}>Settings</a>
          <a href="#documentation" className={activeTool === 'documentation' ? 'active' : ''}>Help</a>
        </nav>
        <p>© 2025 RATM</p>
      </div>
    </div>
  );
};

export default Sidebar;
