import React, { useState, useEffect, useContext } from 'react';
import { AppContext } from '../context/AppContext';
import styles from './Settings.module.css';

const Settings = ({ lastUpdateDate, toggleTheme, resetApplication }) => {
  const { API_BASE_URL } = useContext(AppContext);
  const [isYahooLoggedIn, setIsYahooLoggedIn] = useState(false);
  const [theme, setTheme] = useState(localStorage.getItem('theme') || 'dark');

  useEffect(() => {
    const token = localStorage.getItem('yahoo_token');
    setIsYahooLoggedIn(!!token);

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
    </section>
  );
};

export default Settings;
