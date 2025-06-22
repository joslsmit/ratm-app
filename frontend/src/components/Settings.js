import React from 'react';
import styles from './Settings.module.css';

const Settings = ({ lastUpdateDate, toggleTheme, resetApplication }) => {
  return (
    <section id="settings" className={styles.settings}>
      <div className="tool-header">
        <h2>Settings</h2>
        <p>Manage application data and preferences.</p>
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
