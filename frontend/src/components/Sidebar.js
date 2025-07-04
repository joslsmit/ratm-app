import React from 'react';
import styles from './Sidebar.module.css';

const Sidebar = ({ activeTool, targetList, navSections, toggleNavSection, setEcrTypePreference }) => {
  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <a href="/" title="Start Over" className="sidebar-logo-link">
          <img src="/images/redd-logo.png" alt="Redd Against the Machine Logo" className="app-logo" />
        </a>
      </div>
      <div className="global-search-container">
        <div className="autoComplete_wrapper">
          <input id="global-player-search" type="text" placeholder="Quick Find Player..." />
        </div>
      </div>
      <div className="ecr-preference-selector">
        <label htmlFor="ecr-type-preference">ECR Type:</label>
        <select id="ecr-type-preference" onChange={(e) => setEcrTypePreference(e.target.value)}>
          <option value="overall">Overall ECR</option>
          <option value="positional">Positional ECR</option>
        </select>
      </div>
      <nav className="sidebar-nav">
        <ul>
          <li><a href="#targets" className={activeTool === 'targets' ? 'active' : ''}>Target List <span className="badge">{targetList.length}</span></a></li>
        </ul>
        <div className="nav-section">
          <h3 onClick={() => toggleNavSection('playerAnalysis')}>
            Player Analysis <span className={navSections.playerAnalysis ? 'arrow down' : 'arrow right'}></span>
          </h3>
          {navSections.playerAnalysis && (
            <ul>
              <li><a href="#dossier" className={activeTool === 'dossier' ? 'active' : ''}>Player Dossier</a></li>
              <li><a href="#rookie" className={activeTool === 'rookie' ? 'active' : ''}>Rookie Rankings</a></li>
              <li><a href="#tiers" className={activeTool === 'tiers' ? 'active' : ''}>Positional Tiers</a></li>
              <li><a href="#market" className={activeTool === 'market' ? 'active' : ''}>Sleepers & Busts</a></li>
              <li><a href="#trending" className={activeTool === 'trending' ? 'active' : ''}>Trending Players</a></li>
            </ul>
          )}
        </div>

        <div className="nav-section">
          <h3 onClick={() => toggleNavSection('teamManagement')}>
            Team Management <span className={navSections.teamManagement ? 'arrow down' : 'arrow right'}></span>
          </h3>
          {navSections.teamManagement && (
            <ul>
              <li><a href="#keeper" className={activeTool === 'keeper' ? 'active' : ''}>Keeper Evaluator</a></li>
              <li><a href="#trade" className={activeTool === 'trade' ? 'active' : ''}>Trade Analyzer</a></li>
              <li><a href="#draft" className={activeTool === 'draft' ? 'active' : ''}>Draft Assistant</a></li>
              <li><a href="#waiver" className={activeTool === 'waiver' ? 'active' : ''}>Waiver Wire Assistant</a></li>
              <li><a href="http://localhost:5000/api/yahoo/login" className="yahoo-login-button">Sign in with Yahoo</a></li>
            </ul>
          )}
        </div>
      </nav>
      <div className="sidebar-footer">
        <nav className="utility-nav">
          <a href="#settings" className={activeTool === 'settings' ? 'active' : ''}>
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="feather feather-settings"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
            Settings
          </a>
          <a href="#documentation" className={activeTool === 'documentation' ? 'active' : ''}>
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="feather feather-help-circle"><circle cx="12" cy="12" r="10"></circle><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
            Help
          </a>
          <a href="#" onClick={() => { localStorage.removeItem('yahoo_token'); window.location.hash = ''; }} className="utility-nav-item">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="feather feather-log-out"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path><polyline points="17 16 22 12 17 8"></polyline><line x1="22" y1="12" x2="10" y2="12"></line></svg>
            Logout (Yahoo)
          </a>
        </nav>
        <p>© 2025 RATM</p>
      </div>
    </div>
  );
};

export default Sidebar;
